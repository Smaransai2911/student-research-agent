from backend.app.tools import (
    answer,
    summarize,
    explain_simply,
    generate_quiz,
    generate_viva,
    ask_clarification,
    refuse,
    retrieve_documents,
)

TOOL_REGISTRY = {
    "answer_question": answer.run,
    "summarize": summarize.run,
    "explain_simply": explain_simply.run,
    "generate_quiz": generate_quiz.run,
    "generate_viva": generate_viva.run,
    "ask_clarification": ask_clarification.run,
    "refuse_if_no_evidence": refuse.run,
    "retrieve_documents": retrieve_documents.run,
}