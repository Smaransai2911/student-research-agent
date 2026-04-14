from backend.app.services.generator import generate

def run(query: str, chunks: list, **kwargs) -> dict:
    if not chunks:
        return {"answer": "", "success": False, "confidence": "low"}
    context = "\n\n".join(c.get('text','') for c in chunks[:4])
    prompt = f"Explain this in very simple plain English for a beginner. Use short sentences and simple words.\n\nCONTENT:\n{context}\n\nSIMPLE EXPLANATION:"
    answer = generate(prompt)
    return {"answer": answer.strip(), "success": bool(answer and len(answer) > 10), "confidence": "high"}
