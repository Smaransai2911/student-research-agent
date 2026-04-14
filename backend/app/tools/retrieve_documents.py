from backend.app.services.knowledge import retrieve


def run(query, top_k=None, threshold=None, **kwargs):
    chunks = retrieve(query=query, top_k=top_k, threshold=threshold)
    return {
        "chunks": chunks,
        "count": len(chunks),
        "success": len(chunks) > 0,
    }