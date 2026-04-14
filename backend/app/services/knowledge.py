import json
import re
import unicodedata
from pathlib import Path
import faiss
import numpy as np
from backend.app.config import settings
from backend.app.logger import get_logger

logger = get_logger(__name__)
_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embedding_model = SentenceTransformer(settings.embedding_model)
        logger.info("Embedding model loaded on CPU")
    return _embedding_model


def validate_file(filename, file_size, content_type):
    errors = []
    if Path(filename).suffix.lower() not in {".pdf"}:
        errors.append(f"Only PDF files accepted.")
    if file_size > settings.max_file_size_bytes:
        errors.append(f"File too large. Max {settings.max_file_size_mb} MB.")
    if ".." in filename or "/" in filename or "\\" in filename:
        errors.append("Filename contains illegal characters.")
    return errors


def sanitise_filename(filename):
    name = Path(filename).name
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w.\-]", "_", name)
    name = re.sub(r"_+", "_", name)
    return name or "uploaded_document.pdf"


def save_file(file_bytes, safe_filename):
    path = settings.upload_path
    path.mkdir(parents=True, exist_ok=True)
    dest = path / safe_filename
    dest.write_bytes(file_bytes)
    logger.info(f"Saved: {dest} ({len(file_bytes)//1024} KB)")
    return dest


def extract_text(file_path):
    import fitz
    pages = []
    doc = fitz.open(str(file_path))
    if doc.is_encrypted:
        doc.close()
        raise ValueError("PDF is password-protected.")
    for i in range(len(doc)):
        try:
            text = doc[i].get_text("text")
            if len(text.strip()) >= 20:
                pages.append({"page": i + 1, "text": text})
        except Exception as e:
            logger.warning(f"Page {i+1} skip: {e}")
    doc.close()
    if not pages:
        raise ValueError("No readable text found. May be a scanned PDF.")
    logger.info(f"Extracted {len(pages)} pages from {file_path.name}")
    return pages


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\x00", "").replace("\x0c", "\n")
    text = re.sub(r"-\n(\w)", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_text(pages, chunk_size=300, chunk_overlap=50):
    chunks = []
    chunk_id = 0
    for page_info in pages:
        clean = clean_text(page_info["text"])
        words = clean.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            if len(chunk_words) >= 15:
                chunks.append({
                    "chunk_id": chunk_id,
                    "page":     page_info["page"],
                    "text":     " ".join(chunk_words),
                })
                chunk_id += 1
            start += chunk_size - chunk_overlap
            if chunk_size <= chunk_overlap:
                break
    logger.info(f"Created {len(chunks)} chunks")
    return chunks


def embed_chunks(chunks):
    model  = get_embedding_model()
    texts  = [c["text"] for c in chunks]
    vecs   = model.encode(texts, batch_size=16, show_progress_bar=False, convert_to_numpy=True)
    return vecs.astype(np.float32)


def build_or_update_index(vectors):
    index_path = settings.vectorstore_path / "faiss.index"
    faiss.normalize_L2(vectors)
    dim = vectors.shape[1]
    if index_path.exists():
        index = faiss.read_index(str(index_path))
        if index.d != dim:
            index = faiss.IndexFlatIP(dim)
    else:
        logger.info(f"Creating new FAISS IndexFlatIP dim={dim}")
        index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    settings.vectorstore_path.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_path))
    logger.info(f"FAISS index saved: {index_path} | total={index.ntotal}")
    return index


def save_metadata(chunks, filename, existing_count=0):
    meta_path = settings.vectorstore_path / "metadata.json"
    metadata  = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    for i, chunk in enumerate(chunks):
        metadata[str(existing_count + i)] = {
            "document": filename,
            "page":     chunk["page"],
            "text":     chunk["text"],
        }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"Metadata saved: {len(metadata)} total entries")


def retrieve(query, top_k=None, threshold=None):
    # Always return top_k results — no threshold filtering
    # Let the LLM decide if the content answers the question
    top_k = top_k or settings.retrieval_top_k

    index_path = settings.vectorstore_path / "faiss.index"
    meta_path  = settings.vectorstore_path / "metadata.json"

    if not index_path.exists():
        logger.warning("No FAISS index found")
        return []

    try:
        index = faiss.read_index(str(index_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        model = get_embedding_model()
        qvec  = model.encode([query], convert_to_numpy=True).astype(np.float32)
        faiss.normalize_L2(qvec)

        k = min(top_k, index.ntotal)
        scores, indices = index.search(qvec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            meta = metadata.get(str(idx))
            if meta:
                results.append({
                    "chunk_id": int(idx),
                    "document": meta["document"],
                    "page":     meta["page"],
                    "text":     meta["text"],
                    "score":    round(float(score), 4),
                })

        logger.info(f"Retrieval: '{query[:50]}' → {len(results)} chunks")
        return results

    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        return []


def process_upload(file_bytes, filename, file_size, content_type):
    errors = validate_file(filename, file_size, content_type)
    if errors:
        return {"success": False, "filename": filename, "chunks_created": 0,
                "pages_parsed": 0, "message": "; ".join(errors), "warnings": [], "errors": errors}

    safe = sanitise_filename(filename)

    try:
        path = save_file(file_bytes, safe)
    except Exception as e:
        return {"success": False, "filename": safe, "chunks_created": 0,
                "pages_parsed": 0, "message": f"Save failed: {e}", "warnings": [], "errors": [str(e)]}

    try:
        pages = extract_text(path)
    except ValueError as e:
        path.unlink(missing_ok=True)
        return {"success": False, "filename": safe, "chunks_created": 0,
                "pages_parsed": 0, "message": str(e), "warnings": [], "errors": [str(e)]}

    chunks = chunk_text(pages)
    if not chunks:
        return {"success": False, "filename": safe, "chunks_created": 0,
                "pages_parsed": len(pages), "message": "No chunks created.",
                "warnings": [], "errors": ["zero chunks"]}

    index_path     = settings.vectorstore_path / "faiss.index"
    existing_count = faiss.read_index(str(index_path)).ntotal if index_path.exists() else 0

    try:
        vectors = embed_chunks(chunks)
        build_or_update_index(vectors)
        save_metadata(chunks, safe, existing_count)
    except Exception as e:
        return {"success": False, "filename": safe, "chunks_created": 0,
                "pages_parsed": len(pages), "message": f"Indexing failed: {e}",
                "warnings": [], "errors": [str(e)]}

    return {
        "success":        True,
        "filename":       safe,
        "chunks_created": len(chunks),
        "pages_parsed":   len(pages),
        "message":        f"Indexed '{safe}': {len(pages)} pages, {len(chunks)} chunks.",
        "warnings":       [],
        "errors":         [],
    }
