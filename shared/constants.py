ALLOWED_ACTIONS = [
    "retrieve_documents",
    "answer_question",
    "summarize",
    "explain_simply",
    "generate_quiz",
    "generate_viva",
    "ask_clarification",
    "refuse_if_no_evidence",
]

ALLOWED_ACTIONS_SET = set(ALLOWED_ACTIONS)

RETRIEVAL_DEPENDENT_ACTIONS = {
    "answer_question",
    "summarize",
    "explain_simply",
    "generate_quiz",
    "generate_viva",
}

DIRECT_CONTROL_ACTIONS = {
    "ask_clarification",
    "refuse_if_no_evidence",
}

CONFIDENCE_HIGH   = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW    = "low"

DEFAULT_TOP_K           = 5
DEFAULT_SCORE_THRESHOLD = 0.35
ALLOWED_EXTENSIONS      = {".pdf"}
MAX_FILE_SIZE_BYTES     = 20 * 1024 * 1024
MAX_SESSION_HISTORY     = 10
