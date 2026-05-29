from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
import httpx

from app.config import get_settings, Settings
from app.schemas.flashcard import (
    FlashcardGenerateRequest,
    FlashcardGenerateResponse,
    FlashcardItem,
)
from app.services import llm_service, spaced_repetition

router = APIRouter()


@router.post("/flashcards/generate", response_model=FlashcardGenerateResponse)
async def generate_flashcards(
    request: FlashcardGenerateRequest,
    settings: Settings = Depends(get_settings),
) -> FlashcardGenerateResponse:
    try:
        items: list[FlashcardItem] = await llm_service.generate_flashcards(
            node_title=request.nodeTitle,
            node_description=request.nodeDescription,
            quantity=request.quantity,
            settings=settings,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "message": f"Failed to generate flashcards: {exc}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    payload = [
        {
            "nodeId": request.nodeId,
            "question": item.question,
            "answer": item.answer,
            "difficulty": item.difficulty.value,
            "aiGenerated": True,
        }
        for item in items
    ]

    async with httpx.AsyncClient(base_url=settings.java_api_url) as client:
        for card in payload:
            resp = await client.post("/api/flashcards", json=card)
            if resp.status_code not in (200, 201):
                raise HTTPException(
                    status_code=502,
                    detail={
                        "status": "error",
                        "message": f"Java API error: {resp.text}",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

    return FlashcardGenerateResponse(nodeId=request.nodeId, flashcards=items)


@router.get("/review/{user_id}")
async def get_review_flashcards(
    user_id: str,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    try:
        cards = await spaced_repetition.get_due_flashcards(
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
    return JSONResponse(content={"userId": user_id, "cards": cards})
