def run(query, chunks, signal="default", **kwargs):
    messages = {
        "no_documents": (
            "No documents have been uploaded yet.\n\n"
            "Please upload a PDF using the sidebar, then ask your question."
        ),
        "too_short": (
            "Your query is too short. Please be more specific.\n\n"
            "Examples:\n"
            "• 'Summarise this paper'\n"
            "• 'What is the main hypothesis?'\n"
            "• 'Generate quiz questions'"
        ),
        "empty_query": "Please type a question or choose a task mode.",
        "vague": (
            "I can help you with your uploaded documents. Try:\n\n"
            "• **Summarise** — 'Give me a summary'\n"
            "• **Answer** — 'What is the main finding?'\n"
            "• **Explain** — 'Explain this simply'\n"
            "• **Quiz** — 'Generate quiz questions'\n"
            "• **Viva** — 'Create viva questions'"
        ),
        "default": (
            "Could you be more specific?\n\n"
            "Try: 'Summarise this paper' or 'What does the paper say about X?'"
        ),
    }
    return {
        "answer":     messages.get(signal, messages["default"]),
        "success":    True,
        "confidence": "high",
    }
