import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.spaced_repetition import (
    get_due_flashcards,
    get_weak_topics,
    record_attempt,
)

_JAVA_URL = "http://localhost:8080"


def _mock_async_client(get_return=None, post_return=None):
    mock_http = AsyncMock()
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    if get_return is not None:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = get_return
        mock_http.get = AsyncMock(return_value=resp)
    if post_return is not None:
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = post_return
        mock_http.post = AsyncMock(return_value=resp)
    return mock_http


@pytest.mark.asyncio
@patch("app.services.spaced_repetition.httpx.AsyncClient")
async def test_get_due_flashcards_returns_list(mock_cls):
    payload = [
        {
            "id": "fc-1",
            "nodeId": "node-1",
            "question": "Q?",
            "answer": "A",
            "difficulty": "EASY",
            "nextReviewAt": "2026-01-01T00:00:00",
            "easeFactor": 2.5,
            "intervalDays": 1,
            "repetitions": 0,
        }
    ]
    mock_cls.return_value = _mock_async_client(get_return=payload)

    result = await get_due_flashcards("user-1", _JAVA_URL)

    assert len(result) == 1
    assert result[0]["id"] == "fc-1"
    assert result[0]["easeFactor"] == 2.5
    mock_cls.return_value.get.assert_called_once_with("/api/attempts/due/user-1")


@pytest.mark.asyncio
@patch("app.services.spaced_repetition.httpx.AsyncClient")
async def test_get_due_flashcards_empty(mock_cls):
    mock_cls.return_value = _mock_async_client(get_return=[])

    result = await get_due_flashcards("user-1", _JAVA_URL)

    assert result == []


@pytest.mark.asyncio
@patch("app.services.spaced_repetition.httpx.AsyncClient")
async def test_get_weak_topics_parses_response(mock_cls):
    payload = {
        "userId": "user-1",
        "weakTopics": [
            {"nodeId": "node-1", "nodeTitle": "HTTP", "errorRate": 0.7}
        ],
    }
    mock_cls.return_value = _mock_async_client(get_return=payload)

    result = await get_weak_topics("user-1", _JAVA_URL)

    assert len(result) == 1
    assert result[0].nodeTitle == "HTTP"
    assert result[0].errorRate == 0.7
    mock_cls.return_value.get.assert_called_once_with("/api/attempts/analysis/user-1")


@pytest.mark.asyncio
@patch("app.services.spaced_repetition.httpx.AsyncClient")
async def test_get_weak_topics_empty(mock_cls):
    mock_cls.return_value = _mock_async_client(get_return={"userId": "user-1", "weakTopics": []})

    result = await get_weak_topics("user-1", _JAVA_URL)

    assert result == []


@pytest.mark.asyncio
@patch("app.services.spaced_repetition.httpx.AsyncClient")
async def test_record_attempt_posts_and_returns(mock_cls):
    payload = {
        "id": "fc-1",
        "nodeId": "node-1",
        "question": "Q?",
        "answer": "A",
        "difficulty": "EASY",
        "nextReviewAt": "2026-06-01T00:00:00",
        "easeFactor": 2.6,
        "intervalDays": 1,
        "repetitions": 1,
    }
    mock_cls.return_value = _mock_async_client(post_return=payload)

    result = await record_attempt("fc-1", 4, _JAVA_URL)

    assert result["id"] == "fc-1"
    assert result["repetitions"] == 1
    mock_cls.return_value.post.assert_called_once_with(
        "/api/attempts", json={"flashcardId": "fc-1", "quality": 4}
    )
