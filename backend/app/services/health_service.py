import json
import time
from backend.app.config import settings
from backend.app.logger import get_logger

logger = get_logger(__name__)


def run_health_check() -> dict:
    start  = time.time()
    upload = _check_upload()
    vstore = _check_vectorstore()
    embed  = _check_embedding()
    gen    = _check_generation()
    critical = any(c["status"] == "error" for c in [upload, vstore, embed, gen])
    warnings = any(c.get("status") in ("warning", "empty") for c in [upload, vstore, embed, gen])
    status   = "unhealthy" if critical else ("degraded" if warnings else "healthy")
    return {
        "healthy": not critical,
        "status":  status,
        "app":     settings.app_name,
        "version": settings.app_version,
        "response_time_ms": round((time.time() - start) * 1000, 2),
        "checks": {"upload_directory": upload, "vectorstore": vstore,
                   "embedding_model": embed, "generation": gen},
    }


def _check_upload():
    path = settings.upload_path
    try:
        path.mkdir(parents=True, exist_ok=True)
        test = path / ".write_test"
        test.touch()
        test.unlink()
        return {"status": "ok", "path": str(path), "pdf_count": len(list(path.glob("*.pdf"))), "writable": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_vectorstore():
    vpath = settings.vectorstore_path
    fpath = vpath / "faiss.index"
    mpath = vpath / "metadata.json"
    try:
        vpath.mkdir(parents=True, exist_ok=True)
        if not fpath.exists():
            return {"status": "empty", "message": "No index yet", "faiss_index": False,
                    "metadata": False, "chunks_indexed": 0}
        chunks = 0
        if mpath.exists():
            with open(mpath) as f:
                chunks = len(json.load(f))
        return {"status": "ok", "faiss_index": True, "metadata": mpath.exists(), "chunks_indexed": chunks}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_embedding():
    try:
        import sentence_transformers  # noqa
        return {"status": "ok", "model": settings.embedding_model}
    except ImportError as e:
        return {"status": "error", "error": str(e)}


def _check_generation():
    if settings.generation_strategy == "hf_inference_api":
        ok = bool(settings.hf_api_token)
        return {"status": "ok" if ok else "warning", "strategy": "hf_inference_api",
                "token_present": ok, "model": settings.hf_model_id}
    return {"status": "ok", "strategy": settings.generation_strategy}
