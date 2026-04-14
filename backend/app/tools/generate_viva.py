from backend.app.services.generator import generate

def run(query: str, chunks: list, **kwargs) -> dict:
    if not chunks:
        return {"answer": "", "success": False, "confidence": "low"}
    context = "\n\n".join(f"[{c.get('document','?')}, Page {c.get('page','?')}]\n{c.get('text','')}" for c in chunks[:4])
    prompt = f"Generate 5 viva voce examination questions from this content.\nFormat:\nQ1. [question]\nFollow-up: [probe question]\nExpected points: [2-3 key points]\n\nCONTENT:\n{context}\n\nVIVA QUESTIONS:"
    answer = generate(prompt, max_tokens=800)
    return {"answer": answer.strip(), "success": bool(answer and len(answer) > 10), "confidence": "high"}
