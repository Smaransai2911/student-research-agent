from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from backend.app.schemas.responses import UploadResponse
from backend.app.services.knowledge import process_upload
from backend.app.config import settings
from backend.app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    try:
        file_bytes = await file.read(25 * 1024 * 1024)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        await file.close()

    # Clear old index every time — always index only the new file
    faiss_path = settings.vectorstore_path / "faiss.index"
    meta_path  = settings.vectorstore_path / "metadata.json"
    if faiss_path.exists():
        faiss_path.unlink()
    if meta_path.exists():
        meta_path.unlink()
    logger.info(f"Index cleared. Indexing new file: {file.filename}")

    result = process_upload(
        file_bytes=file_bytes,
        filename=file.filename,
        file_size=len(file_bytes),
        content_type=file.content_type or "application/octet-stream",
    )

    if not result["success"]:
        return JSONResponse(status_code=422, content={
            "success":        False,
            "filename":       result["filename"],
            "chunks_created": 0,
            "pages_parsed":   result.get("pages_parsed", 0),
            "message":        result["message"],
            "warnings":       result.get("warnings", []),
        })

    return UploadResponse(
        success=True,
        filename=result["filename"],
        chunks_created=result["chunks_created"],
        pages_parsed=result["pages_parsed"],
        message=result["message"],
        warnings=result.get("warnings", []),
    )
