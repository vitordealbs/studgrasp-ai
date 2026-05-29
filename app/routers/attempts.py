from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx

from app.config import get_settings, Settings
from app.services import spaced_repetition

router = APIRouter()


class AttemptRequest(BaseModel):
    flashcardId: str
    quality: int = Field(ge=0, le=5)


@router.post("/attempts")
async def record_attempt(
    body: AttemptRequest,
    settings: Settings = Depends(get_settings),
):
    try:
        return await spaced_repetition.record_attempt(
            flashcard_id=body.flashcardId,
            quality=body.quality,
            java_api_url=settings.java_api_url,
        )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        raise HTTPException(
            status_code=code if code in (400, 404) else 502,
            detail={
                "status": "error",
                "message": exc.response.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
