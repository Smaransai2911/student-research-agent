from backend.app.logger import get_logger

logger = get_logger(__name__)


def run(query, chunks, reason="", **kwargs):
    logger.warning(f"Refusing: '{query[:80]}' | reason: {reason}")
    return {
        "answer": (
            "I could not find sufficient evidence in your uploaded documents "
            "to answer this question.\n\n"
            "What you can try:\n"
            "• Rephrase your question to match the document content\n"
            "• Upload a document that covers this topic\n"
            "• Lower the specificity of your question"
        ),
        "success":    False,
        "confidence": "low",
    }
