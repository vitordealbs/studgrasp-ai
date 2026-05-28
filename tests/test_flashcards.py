import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.flashcard import Difficulty, FlashcardItem


GENERATE_PAYLOAD = {
    "nodeId": "node-1",
    "nodeTitle": "REST APIs",
    "nodeDescription": "Understanding RESTful API design",
    "quantity": 2,
}


@pytest.fixture
def mock_flashcard_items():
    return [
        FlashcardItem(question="What is REST?", answer="Representational State Transfer", difficulty=Difficulty.EASY),
        FlashcardItem(question="What is a resource?", answer="An entity accessible via URI", difficulty=Difficulty.MEDIUM),
    ]


@patch("app.routers.flashcards.llm_service.generate_flashcards", new_callable=AsyncMock)
@patch("app.routers.flashcards.httpx.AsyncClient")
def test_generate_flashcards_success(mock_httpx_cls, mock_generate, client, mock_flashcard_items):
    mock_generate.return_value = mock_flashcard_items

    mock_resp = MagicMock()
    mock_resp.status_code = 201

    mock_http_client = AsyncMock()
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=False)
    mock_http_client.post = AsyncMock(return_value=mock_resp)
    mock_httpx_cls.return_value = mock_http_client

    response = client.post("/ai/flashcards/generate", json=GENERATE_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["nodeId"] == "node-1"
    assert len(body["flashcards"]) == 2


@patch("app.routers.flashcards.llm_service.generate_flashcards", new_callable=AsyncMock)
def test_generate_flashcards_anthropic_error(mock_generate, client):
    mock_generate.side_effect = RuntimeError("Claude unavailable")

    response = client.post("/ai/flashcards/generate", json=GENERATE_PAYLOAD)

    assert response.status_code == 502


@patch("app.routers.flashcards.spaced_repetition.get_due_flashcards", new_callable=AsyncMock)
def test_get_review_flashcards(mock_due, client):
    mock_due.return_value = [
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

    response = client.get("/ai/review/user-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == "user-abc"
    assert len(body["cards"]) == 1
