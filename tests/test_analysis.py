import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.analysis import WeakTopic


@patch("app.routers.analysis.spaced_repetition.get_weak_topics", new_callable=AsyncMock)
def test_get_analysis_success(mock_weak, client):
    mock_weak.return_value = [
        WeakTopic(nodeId="node-1", nodeTitle="REST APIs", errorRate=0.75),
        WeakTopic(nodeId="node-2", nodeTitle="SQL Basics", errorRate=0.50),
    ]

    response = client.get("/ai/analysis/user-abc")

    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == "user-abc"
    assert len(body["weakTopics"]) == 2
    assert body["weakTopics"][0]["errorRate"] == 0.75


@patch("app.routers.analysis.spaced_repetition.get_weak_topics", new_callable=AsyncMock)
def test_get_analysis_empty(mock_weak, client):
    mock_weak.return_value = []

    response = client.get("/ai/analysis/user-xyz")

    assert response.status_code == 200
    assert response.json()["weakTopics"] == []


@patch("app.routers.analysis.spaced_repetition.get_weak_topics", new_callable=AsyncMock)
def test_get_analysis_db_error(mock_weak, client):
    mock_weak.side_effect = RuntimeError("DB connection failed")

    response = client.get("/ai/analysis/user-err")

    assert response.status_code == 500