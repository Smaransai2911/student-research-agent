from fastapi import APIRouter, HTTPException
from backend.app.schemas.requests import QueryRequest
from backend.app.schemas.responses import AgentResponse
from backend.app.services.orchestrator import run_agent
from backend.app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["query"])


@router.post("/query", response_model=AgentResponse)
async def query_agent(request: QueryRequest) -> AgentResponse:
    try:
        return run_agent(
            session_id=request.session_id,
            query=request.query,
            mode=request.mode,
        )
    except Exception as e:
        logger.error(f"Unhandled error in /query: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error. Check server logs.")
