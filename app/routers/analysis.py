from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings, Settings
from app.schemas.analysis import AnalysisResponse
from app.services import spaced_repetition

router = APIRouter()


@router.get("/analysis/{user_id}", response_model=AnalysisResponse)
async def get_analysis(
    user_id: str,
    settings: Settings = Depends(get_settings),
) -> AnalysisResponse:
    try:
        weak_topics = await spaced_repetition.get_weak_topics(
            user_id=user_id, java_api_url=settings.java_api_url
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return AnalysisResponse(userId=user_id, weakTopics=weak_topics)
