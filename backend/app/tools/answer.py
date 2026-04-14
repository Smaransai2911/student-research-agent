from backend.app.services.generator import generate


def run(query: str, chunks: list, **kwargs) -> dict:
    if not chunks:
        return {
            "answer":     "No relevant content found in uploaded documents.",
            "success":    False,
            "confidence": "low",
        }

    context = "\n\n---\n\n".join(
        f"[Source: {c.get('document','?')}, Page {c.get('page','?')}]\n{c.get('text','')}"
        for c in chunks[:4]
    )

    prompt = (
        f"You are an academic research assistant.\n"
        f"Answer the question using ONLY the document context below.\n"
        f"If the answer is not in the context, say: "
        f"'I cannot find this in the uploaded documents.'\n\n"
        f"DOCUMENT CONTEXT:\n{context}\n\n"
        f"QUESTION: {query}\n\n"
        f"ANSWER:"
    )

    answer = generate(prompt)

    if not answer or len(answer.strip()) < 5:
        return {
            "answer":     "Generation failed. Please try again.",
            "success":    False,
            "confidence": "low",
        }

    refusal = ["cannot find", "not enough", "not mentioned", "not provided", "does not contain"]
    confidence = "low" if any(p in answer.lower() for p in refusal) else "high"

    return {
        "answer":     answer.strip(),
        "success":    True,
        "confidence": confidence,
    }
