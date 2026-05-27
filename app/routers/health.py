from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse(
        content={
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
