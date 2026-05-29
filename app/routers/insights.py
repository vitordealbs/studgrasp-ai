from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from app.config import get_settings, Settings
from app.schemas.insights import (
    InsightRequest,
    InsightResponse,
    ClassInsightRequest,
    ClassInsightResponse,
)
from app.services import llm_service

router = APIRouter()


@router.post("/insights/class/{class_id}", response_model=ClassInsightResponse)
async def generate_class_insights(
    class_id: str,
    body: ClassInsightRequest,
    settings: Settings = Depends(get_settings),
) -> ClassInsightResponse:
    try:
        insights = await llm_service.generate_class_insights(context=body, settings=settings)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": f"LLM error: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return ClassInsightResponse(classId=class_id, insights=insights)


@router.post("/insights/{user_id}", response_model=InsightResponse)
async def generate_insights(
    user_id: str,
    body: InsightRequest,
    settings: Settings = Depends(get_settings),
) -> InsightResponse:
    try:
        insights = await llm_service.generate_insights(context=body, settings=settings)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": f"LLM error: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return InsightResponse(userId=user_id, insights=insights)
