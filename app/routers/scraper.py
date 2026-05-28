import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings, Settings
from app.services.scraper_service import scrape_all_roadmaps
from app.services.scraper_debug import debug_scrape

router = APIRouter()


@router.post("/scrape")
async def trigger_scrape(
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    try:
        result = await asyncio.to_thread(scrape_all_roadmaps, settings.java_api_url)
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
            "summary": result["summary"],
            "errors": result["errors"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get("/scrape/debug/{slug}")
async def debug_roadmap_scrape(slug: str) -> JSONResponse:
    result = await asyncio.to_thread(debug_scrape, slug)
    return JSONResponse(content=result)


@router.get("/scrape/test/{slug}")
async def test_fetch_nodes(slug: str) -> JSONResponse:
    """
    Testa APENAS o fetch + parse de nós do roadmap.sh (sem Java API, sem salvar).
    Use para isolar se o problema está no fetch ou na integração com o Java.
    """
    from app.services.scraper_service import _fetch_roadmap_json, _parse_react_flow_nodes

    raw = await asyncio.to_thread(_fetch_roadmap_json, slug)
    if not raw:
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "message": f"Failed to fetch https://roadmap.sh/{slug}.json",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    nodes = _parse_react_flow_nodes(raw, roadmap_uuid="test-uuid")
    all_types = list({n.get("type", "") for n in raw.get("nodes", [])})

    return JSONResponse(
        content={
            "slug": slug,
            "total_nodes_in_json": len(raw.get("nodes", [])),
            "content_nodes_after_filter": len(nodes),
            "all_node_types_in_json": all_types,
            "first_5_nodes": nodes[:5],
        }
    )
