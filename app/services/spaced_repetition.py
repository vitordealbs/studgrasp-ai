import os
from typing import List

import httpx

from app.schemas.analysis import WeakTopic

_SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")


def _auth_headers() -> dict:
    return {"X-API-Key": _SCRAPER_API_KEY}


async def get_due_flashcards(user_id: str, java_api_url: str) -> List[dict]:
    async with httpx.AsyncClient(base_url=java_api_url, headers=_auth_headers()) as client:
        resp = await client.get(f"/api/attempts/due/{user_id}")
        resp.raise_for_status()
        return resp.json()


async def get_weak_topics(user_id: str, java_api_url: str) -> List[WeakTopic]:
    async with httpx.AsyncClient(base_url=java_api_url, headers=_auth_headers()) as client:
        resp = await client.get(f"/api/attempts/analysis/{user_id}")
        resp.raise_for_status()
        data = resp.json()
        return [WeakTopic(**t) for t in data.get("weakTopics", [])]


async def record_attempt(flashcard_id: str, quality: int, java_api_url: str) -> dict:
    async with httpx.AsyncClient(base_url=java_api_url, headers=_auth_headers()) as client:
        resp = await client.post(
            "/api/attempts",
            json={"flashcardId": flashcard_id, "quality": quality},
        )
        resp.raise_for_status()
        return resp.json()
