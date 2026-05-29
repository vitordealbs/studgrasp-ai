import pytest
from unittest.mock import AsyncMock, patch
import httpx


@patch("app.routers.attempts.spaced_repetition.record_attempt", new_callable=AsyncMock)
def test_record_attempt_success(mock_record, client):
    mock_record.return_value = {
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

    response = client.post("/ai/attempts", json={"flashcardId": "fc-1", "quality": 4})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "fc-1"
    assert body["repetitions"] == 1
    mock_record.assert_called_once_with(
        flashcard_id="fc-1", quality=4, java_api_url="http://localhost:8080"
    )


def test_record_attempt_quality_too_high(client):
    response = client.post("/ai/attempts", json={"flashcardId": "fc-1", "quality": 6})
    assert response.status_code == 422


def test_record_attempt_quality_negative(client):
    response = client.post("/ai/attempts", json={"flashcardId": "fc-1", "quality": -1})
    assert response.status_code == 422


@patch("app.routers.attempts.spaced_repetition.record_attempt", new_callable=AsyncMock)
def test_record_attempt_flashcard_not_found(mock_record, client):
    mock_resp = AsyncMock()
    mock_resp.status_code = 404
    mock_resp.text = "Flashcard not found"
    mock_record.side_effect = httpx.HTTPStatusError(
        "404", request=None, response=mock_resp
    )

    response = client.post("/ai/attempts", json={"flashcardId": "bad-id", "quality": 3})

    assert response.status_code == 404


@patch("app.routers.attempts.spaced_repetition.record_attempt", new_callable=AsyncMock)
def test_record_attempt_java_unavailable(mock_record, client):
    mock_record.side_effect = RuntimeError("Connection refused")

    response = client.post("/ai/attempts", json={"flashcardId": "fc-1", "quality": 3})

    assert response.status_code == 502
