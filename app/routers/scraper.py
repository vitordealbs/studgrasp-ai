import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings, Settings
from app.services.scraper_service import scrape_all_roadmaps

router = APIRouter()


@router.post("/scrape")
async def trigger_scrape(
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    try:
        summary = await asyncio.to_thread(scrape_all_roadmaps, settings.java_api_url)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
    return JSONResponse(
        content={
            "status": "ok",
            "summary": summary,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
