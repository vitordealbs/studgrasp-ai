import pytest
from unittest.mock import MagicMock, patch

from app.services.scraper_service import (
    _parse_nodes_from_next_data,
    _parse_nodes_from_dom,
    _save_nodes,
    _get_or_create_roadmap,
)

ROADMAP_UUID = "550e8400-e29b-41d4-a716-446655440000"

MOCK_NEXT_DATA = {
    "props": {
        "pageProps": {
            "roadmap": {
                "topics": [
                    {"id": "t1", "title": "HTTP", "description": "HTTP basics", "parentId": None, "type": "topic"},
                    {"id": "t2", "title": "REST", "description": "REST principles", "parentId": "t1", "type": "topic"},
                ]
            }
        }
    }
}


# --- _get_or_create_roadmap ---

@patch("app.services.scraper_service.httpx.Client")
def test_get_or_create_roadmap_existing(mock_client_cls):
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"id": ROADMAP_UUID, "careerType": "backend"}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_get_resp
    mock_client_cls.return_value = mock_client

    result = _get_or_create_roadmap("backend", "http://localhost:8080")

    assert result == ROADMAP_UUID
    mock_client.post.assert_not_called()


@patch("app.services.scraper_service.httpx.Client")
def test_get_or_create_roadmap_creates_when_not_found(mock_client_cls):
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 404

    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"id": ROADMAP_UUID}
    mock_post_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_get_resp
    mock_client.post.return_value = mock_post_resp
    mock_client_cls.return_value = mock_client

    result = _get_or_create_roadmap("backend", "http://localhost:8080")

    assert result == ROADMAP_UUID
    mock_client.post.assert_called_once_with(
        "/api/roadmaps",
        json={
            "title": "Backend",
            "careerType": "backend",
            "sourceUrl": "https://roadmap.sh/backend",
        },
    )


# --- Parsing ---

def test_parse_nodes_from_next_data():
    nodes = _parse_nodes_from_next_data(MOCK_NEXT_DATA, ROADMAP_UUID)
    assert len(nodes) == 2
    assert nodes[0]["title"] == "HTTP"
    assert nodes[0]["roadmapId"] == ROADMAP_UUID
    assert nodes[1]["parentId"] == "t1"
    assert "externalId" not in nodes[0]


def test_parse_nodes_from_next_data_missing_topics():
    nodes = _parse_nodes_from_next_data({}, ROADMAP_UUID)
    assert nodes == []


def test_parse_nodes_from_dom():
    mock_page = MagicMock()
    el1 = MagicMock()
    el1.get_attribute.side_effect = lambda attr: "node-1" if attr == "data-id" else "HTTP"
    el1.inner_text.return_value = "HTTP"

    el2 = MagicMock()
    el2.get_attribute.side_effect = lambda attr: "node-2" if attr == "data-id" else "REST"
    el2.inner_text.return_value = "REST"

    mock_page.query_selector_all.return_value = [el1, el2]

    nodes = _parse_nodes_from_dom(mock_page, ROADMAP_UUID)
    assert len(nodes) == 2
    assert nodes[0]["roadmapId"] == ROADMAP_UUID
    assert nodes[1]["nodeOrder"] == 1
    assert "externalId" not in nodes[0]


# --- Saving ---

@patch("app.services.scraper_service.httpx.Client")
def test_save_nodes_success(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.status_code = 201

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    nodes = [{"title": "HTTP", "roadmapId": ROADMAP_UUID, "nodeOrder": 0}]
    _save_nodes(nodes, "http://localhost:8080")

    mock_client.post.assert_called_once_with("/api/roadmap-nodes", json=nodes[0])


@patch("app.services.scraper_service.httpx.Client")
def test_save_nodes_logs_failure(mock_client_cls, caplog):
    import logging
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    nodes = [{"title": "HTTP", "roadmapId": ROADMAP_UUID}]
    with caplog.at_level(logging.WARNING, logger="app.services.scraper_service"):
        _save_nodes(nodes, "http://localhost:8080")

    assert any("Failed to save node" in r.message for r in caplog.records)
