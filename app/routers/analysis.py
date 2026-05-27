from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import AnalysisResponse
from app.services import spaced_repetition

router = APIRouter()


@router.get("/analysis/{user_id}", response_model=AnalysisResponse)
async def get_analysis(
    user_id: str,
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    try:
        weak_topics = await spaced_repetition.get_weak_topics(user_id=user_id, db=db)
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
