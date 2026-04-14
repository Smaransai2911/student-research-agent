from backend.app.services.generator import generate


def run(query: str, chunks: list, **kwargs) -> dict:
    if not chunks:
        return {"answer": "", "success": False, "confidence": "low"}
    context = "\n\n---\n\n".join(
        f"[{c.get('document','?')}, Page {c.get('page','?')}]\n{c.get('text','')}"
        for c in chunks[:5]
    )
    prompt = (
        "Summarise the following document content clearly.\n"
        "Structure your response as:\n"
        "1. Main Topic:\n"
        "2. Key Points:\n"
        "3. Conclusion:\n\n"
        f"CONTENT:\n{context}\n\nSUMMARY:"
    )
    answer = generate(prompt)
    if not answer or len(answer.strip()) < 10:
        return {"answer": "", "success": False, "confidence": "low"}
    return {"answer": answer.strip(), "success": True, "confidence": "high"}
