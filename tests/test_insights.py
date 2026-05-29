import pytest
from unittest.mock import AsyncMock, patch

from app.schemas.analysis import WeakTopic


_CLASS_BODY = {
    "classId": "class-1",
    "totalStudents": 25,
    "avgRetentionRate": 0.72,
    "totalReviewedToday": 45,
    "weakTopics": [
        {"nodeId": "n1", "nodeTitle": "Ponteiros", "errorRate": 0.65},
        {"nodeId": "n2", "nodeTitle": "Recursão", "errorRate": 0.50},
    ],
    "students": [
        {"userId": "u1", "userName": "João", "reviewedToday": 12, "retentionRate": 0.80},
        {"userId": "u2", "userName": "Maria", "reviewedToday": 0, "retentionRate": None},
    ],
}

_BODY = {
    "userId": "user-1",
    "weakTopics": [{"nodeId": "n1", "nodeTitle": "HTTP", "errorRate": 0.7}],
    "streak": 3,
    "reviewedToday": 10,
    "correctToday": 7,
    "dueNow": 5,
    "retentionRate": 0.65,
}


@patch("app.routers.insights.llm_service.generate_insights", new_callable=AsyncMock)
def test_generate_insights_success(mock_gen, client):
    mock_gen.return_value = [
        "Você está errando 70% das questões de HTTP.",
        "Revise os cards pendentes antes de dormir.",
    ]

    response = client.post("/ai/insights/user-1", json=_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["userId"] == "user-1"
    assert len(body["insights"]) == 2
    assert "HTTP" in body["insights"][0]


@patch("app.routers.insights.llm_service.generate_insights", new_callable=AsyncMock)
def test_generate_insights_llm_error(mock_gen, client):
    mock_gen.side_effect = RuntimeError("LLM timeout")

    response = client.post("/ai/insights/user-1", json=_BODY)

    assert response.status_code == 502


def test_generate_insights_missing_required_fields(client):
    response = client.post("/ai/insights/user-1", json={"userId": "user-1"})
    assert response.status_code == 422


@patch("app.routers.insights.llm_service.generate_class_insights", new_callable=AsyncMock)
def test_generate_class_insights_success(mock_gen, client):
    mock_gen.return_value = [
        "Ponteiros tem 65% de erro — priorize uma aula revisional.",
        "Maria não realizou nenhuma revisão hoje.",
        "A turma tem retenção média de 72%.",
    ]

    response = client.post("/ai/insights/class/class-1", json=_CLASS_BODY)

    assert response.status_code == 200
    body = response.json()
    assert body["classId"] == "class-1"
    assert len(body["insights"]) == 3
    mock_gen.assert_called_once()


@patch("app.routers.insights.llm_service.generate_class_insights", new_callable=AsyncMock)
def test_generate_class_insights_no_retention_history(mock_gen, client):
    body = {**_CLASS_BODY, "avgRetentionRate": None}
    mock_gen.return_value = ["A turma ainda não tem histórico suficiente."]

    response = client.post("/ai/insights/class/class-1", json=body)

    assert response.status_code == 200
    assert response.json()["classId"] == "class-1"


@patch("app.routers.insights.llm_service.generate_class_insights", new_callable=AsyncMock)
def test_generate_class_insights_llm_error(mock_gen, client):
    mock_gen.side_effect = RuntimeError("LLM timeout")

    response = client.post("/ai/insights/class/class-1", json=_CLASS_BODY)

    assert response.status_code == 502


def test_generate_class_insights_missing_required_fields(client):
    response = client.post("/ai/insights/class/class-1", json={"classId": "class-1"})
    assert response.status_code == 422
