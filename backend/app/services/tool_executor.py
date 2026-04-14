import time

from shared.constants import ALLOWED_ACTIONS_SET
from backend.app.tools import TOOL_REGISTRY
from backend.app.logger import get_logger

logger = get_logger(__name__)


def execute(action: str, query: str, chunks: list, signal: str = "default", reason: str = "") -> dict:
    start = time.time()

    if action not in ALLOWED_ACTIONS_SET:
        logger.error(f"Invalid action: {action}")
        return {
            "action": action,
            "answer": "",
            "success": False,
            "confidence": "low",
            "message": f"Invalid action: {action}",
            "latency_ms": 0,
        }

    tool_fn = TOOL_REGISTRY.get(action)
    if not tool_fn:
        logger.error(f"Tool not found: {action}")
        return {
            "action": action,
            "answer": "",
            "success": False,
            "confidence": "low",
            "message": f"Tool not found: {action}",
            "latency_ms": 0,
        }

    try:
        if action == "ask_clarification":
            result = tool_fn(query=query, chunks=chunks, signal=signal)
        elif action == "refuse_if_no_evidence":
            result = tool_fn(query=query, chunks=chunks, reason=reason)
        elif action == "retrieve_documents":
            result = tool_fn(query=query)
        else:
            result = tool_fn(query=query, chunks=chunks)

        if not isinstance(result, dict):
            logger.error(f"Tool {action} returned non-dict result: {type(result)}")
            result = {
                "answer": "",
                "success": False,
                "confidence": "low",
                "message": f"Tool {action} returned invalid result type.",
            }

    except Exception:
        logger.exception(f"Tool {action} failed")
        result = {
            "answer": "",
            "success": False,
            "confidence": "low",
            "message": f"Tool execution failed for action: {action}",
        }

    elapsed = round((time.time() - start) * 1000)
    result["action"] = action
    result["latency_ms"] = elapsed

    logger.info(f"Tool: {action} | success={result.get('success')} | {elapsed}ms")
    return result