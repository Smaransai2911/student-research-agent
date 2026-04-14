from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.app.services.health_service import run_health_check

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    report = run_health_check()
    return JSONResponse(content=report, status_code=200 if report["healthy"] else 503)
