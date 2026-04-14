from dataclasses import dataclass, field
from typing import Optional

from shared.constants import ALLOWED_ACTIONS_SET, RETRIEVAL_DEPENDENT_ACTIONS
from backend.app.logger import get_logger


logger = get_logger(__name__)


_SIGNAL_MAP = {
    "summarize": [
        "summarize", "summarise", "summary", "key points", "main points", "tldr", "overview", "brief"
    ],
    "explain_simply": [
        "explain simply", "simple explanation", "eli5", "layman", "plain english", "simplify", "for a beginner"
    ],
    "generate_quiz": [
        "generate quiz", "quiz me", "create quiz", "mcq", "multiple choice", "practice questions", "test questions"
    ],
    "generate_viva": [
        "viva", "oral exam", "viva voce", "interview questions", "thesis questions", "defence questions"
    ],
    "answer_question": [
        "what is", "what are", "how does", "how do", "why does", "explain the",
        "tell me about", "define", "describe", "according to", "based on", "in the paper"
    ],
}


_MODE_MAP = {
    "summarize": "summarize",
    "summary": "summarize",
    "explain": "explain_simply",
    "simple": "explain_simply",
    "quiz": "generate_quiz",
    "viva": "generate_viva",
    "answer": "answer_question",
    "question": "answer_question",
    "auto": None,
}


_VAGUE = {"help", "hi", "hello", "hey", "start", "begin", "help me", "can you help", "anything", "something"}


@dataclass
class DecisionResult:
    action: str
    needs_retrieval: bool
    needs_clarification: bool
    confidence: str
    reasoning: str
    original_query: str
    normalised_query: str
    detected_signals: list[str] = field(default_factory=list)


class DecisionEngine:
    def decide(self, query: str, mode: Optional[str] = None, has_documents: bool = True) -> DecisionResult:
        original = query
        normalised = query.strip().lower()

        if not normalised:
            return self._result(
                "ask_clarification",
                "high",
                "Empty query",
                original,
                normalised,
                ["empty_query"],
                True,
            )

        if len(normalised.split()) < 2:
            return self._result(
                "ask_clarification",
                "high",
                "Too short",
                original,
                normalised,
                ["too_short"],
                True,
            )

        if not has_documents:
            return self._result(
                "ask_clarification",
                "high",
                "No documents",
                original,
                normalised,
                ["no_documents"],
                True,
            )

        if normalised in _VAGUE or any(normalised.startswith(v + " ") for v in _VAGUE):
            return self._result(
                "ask_clarification",
                "medium",
                "Vague query",
                original,
                normalised,
                ["vague"],
                True,
            )

        if mode and mode.lower() in _MODE_MAP:
            mapped = _MODE_MAP[mode.lower()]
            if mapped:
                return self._result(
                    mapped,
                    "high",
                    f"Mode hint: {mode}",
                    original,
                    normalised,
                    [f"mode:{mode}"],
                )

        action, signals, confidence = self._detect(normalised)
        return self._result(
            action,
            confidence,
            f"Signals: {signals}",
            original,
            normalised,
            signals,
        )

    def _detect(self, normalised: str):
        scores = {a: 0 for a in _SIGNAL_MAP}
        matched = {a: [] for a in _SIGNAL_MAP}

        for action, signals in _SIGNAL_MAP.items():
            for s in signals:
                if s in normalised:
                    scores[action] += 2 if " " in s else 1
                    matched[action].append(s)

        best_action = max(scores, key=scores.get)
        best_score = scores[best_action]

        if best_score == 0:
            return "retrieve_and_answer", ["fallback-topic-query"], "medium"

        confidence = "high" if best_score >= 2 else "medium"
        return best_action, matched[best_action], confidence

    def _result(self, action, confidence, reasoning, original, normalised, signals, clarify=False):
        # FORCED RETRIEVAL MODE - bypass all clarification and action validation
        forced_action = "retrieve_and_answer"

        result = DecisionResult(
            action=forced_action,
            needs_retrieval=True,
            needs_clarification=False,
            confidence="high",
            reasoning=reasoning or "Forced retrieval mode active",
            original_query=original,
            normalised_query=normalised,
            detected_signals=signals or [],
        )

        logger.info(
            "Decision: %s | retrieval=%s | confidence=%s",
            result.action,
            result.needs_retrieval,
            result.confidence,
        )
        return result