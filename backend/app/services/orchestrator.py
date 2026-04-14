import time

from backend.app.config import settings
from backend.app.logger import get_logger
from backend.app.schemas.responses import AgentResponse, SourceItem
from backend.app.services.decision_engine import DecisionEngine
from backend.app.services.tool_executor import execute
from backend.app.services.memory import update_session
from shared.constants import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW

logger = get_logger(__name__)
decision_engine = DecisionEngine()


def _has_indexed_documents() -> bool:
    faiss_index = settings.vectorstore_path / "faiss.index"
    numpy_vectors = settings.vectorstore_path / "vectors.npy"
    metadata = settings.vectorstore_path / "metadata.json"
    return (faiss_index.exists() or numpy_vectors.exists()) and metadata.exists()


def run_agent(session_id: str, query: str, mode: str = None) -> AgentResponse:
    start = time.time()
    has_documents = _has_indexed_documents()

    try:
        decision = decision_engine.decide(
            query=query,
            mode=mode,
            has_documents=has_documents,
        )
    except Exception as e:
        logger.exception(f"Decision engine error: {e}")
        return _error(session_id)

    if decision.needs_clarification:
        signal = decision.detected_signals[0] if decision.detected_signals else "default"
        tool_result = execute("ask_clarification", query, [], signal=signal)
        return _build(
            session_id,
            query,
            "ask_clarification",
            tool_result,
            [],
            decision.confidence,
            True,
            start,
        )

    chunks = []
    if decision.needs_retrieval:
        try:
            retrieval = execute("retrieve_documents", query, [])
            chunks = retrieval.get("chunks", [])
        except Exception as e:
            logger.exception(f"Retrieval error: {e}")
            return _error(session_id)

        if not chunks:
            tool_result = execute(
                "refuse_if_no_evidence",
                query,
                [],
                reason="No chunks retrieved",
            )
            return _build(
                session_id,
                query,
                "refuse_if_no_evidence",
                tool_result,
                [],
                CONFIDENCE_LOW,
                False,
                start,
            )

    try:
        tool_result = execute(decision.action, query, chunks)
    except Exception as e:
        logger.exception(f"Tool executor error: {e}")
        return _error(session_id)

    if not tool_result.get("answer") and decision.needs_retrieval:
        tool_result = execute(
            "refuse_if_no_evidence",
            query,
            chunks,
            reason="Empty answer",
        )

    return _build(
        session_id,
        query,
        decision.action,
        tool_result,
        chunks,
        decision.confidence,
        False,
        start,
    )


def _build(session_id, query, action, tool_result, chunks, dec_confidence, needs_clar, start):
    answer = tool_result.get("answer", "")
    success = tool_result.get("success", False)
    confidence = tool_result.get("confidence", dec_confidence)
    conf_map = {
        "high": CONFIDENCE_HIGH,
        "medium": CONFIDENCE_MEDIUM,
        "low": CONFIDENCE_LOW,
    }

    sources = [
        SourceItem(
            document=c["document"],
            chunk_id=c["chunk_id"],
            page=c["page"],
            text=c["text"][:400],
            score=c["score"],
        )
        for c in chunks
        if c.get("score", 0) >= settings.retrieval_score_threshold
    ]

    try:
        update_session(session_id, query, action, answer[:200])
    except Exception:
        pass

    elapsed = round((time.time() - start) * 1000)
    logger.info(f"Response: {action} | success={success} | sources={len(sources)} | {elapsed}ms")

    return AgentResponse(
        success=success,
        action=action,
        answer=answer,
        sources=sources,
        confidence=conf_map.get(confidence, CONFIDENCE_LOW),
        needs_clarification=needs_clar,
        session_id=session_id,
    )


def _error(session_id):
    return AgentResponse(
        success=False,
        action="refuse_if_no_evidence",
        answer="",
        sources=[],
        confidence=CONFIDENCE_LOW,
        needs_clarification=False,
        message="An unexpected error occurred.",
        session_id=session_id,
    )