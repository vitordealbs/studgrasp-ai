import pytest
from unittest.mock import MagicMock, patch

from app.services.scraper_service import (
    _parse_react_flow_nodes,
    _fetch_roadmap_json,
    _save_nodes,
    _get_or_create_roadmap,
    _parse_slugs_from_listing,
    _discover_roadmap_slugs,
    _slug_to_title,
)

ROADMAP_UUID = "550e8400-e29b-41d4-a716-446655440000"

MOCK_NEXT_DATA_LISTING = {
    "props": {
        "pageProps": {
            "roadmaps": [
                {"id": "backend", "title": "Backend"},
                {"id": "frontend", "title": "Frontend"},
                {"id": "devops", "title": "DevOps"},
            ]
        }
    }
}

MOCK_NEXT_DATA_LISTING_GROUPED = {
    "props": {
        "pageProps": {
            "groups": [
                {
                    "title": "Role-based",
                    "items": [{"id": "backend"}, {"id": "frontend"}],
                },
                {
                    "title": "Skill-based",
                    "items": [{"id": "docker"}, {"id": "kubernetes"}],
                },
            ]
        }
    }
}

MOCK_REACT_FLOW_DATA = {
    "nodes": [
        {"type": "topic",    "data": {"label": "HTTP",  "description": "HTTP basics"}},
        {"type": "subtopic", "data": {"label": "REST",  "description": "REST principles"}},
        {"type": "vertical", "data": {"label": "Vertical Node"}},   # visual — filtrado
        {"type": "topic",    "data": {"label": ""}},                # sem label — filtrado
        {"type": "topic",    "data": {"label": "X"}},               # label curto — filtrado
        {"type": "topic",    "data": {
            "label": "Visit the following resources to learn more"  # instrucional — filtrado
        }},
    ]
}


# ── _slug_to_title ────────────────────────────────────────────────────────────

def test_slug_to_title_simple():
    assert _slug_to_title("backend") == "Backend"


def test_slug_to_title_hyphenated():
    assert _slug_to_title("full-stack") == "Full Stack"


def test_slug_to_title_acronym():
    assert _slug_to_title("ai-data-scientist") == "AI Data Scientist"


# ── _parse_slugs_from_listing ─────────────────────────────────────────────────

def test_parse_slugs_from_listing_flat():
    slugs = _parse_slugs_from_listing(MOCK_NEXT_DATA_LISTING)
    assert slugs == ["backend", "frontend", "devops"]


def test_parse_slugs_from_listing_grouped():
    slugs = _parse_slugs_from_listing(MOCK_NEXT_DATA_LISTING_GROUPED)
    assert "backend" in slugs
    assert "docker" in slugs
    assert len(slugs) == 4


def test_parse_slugs_from_listing_empty():
    assert _parse_slugs_from_listing({}) == []


# ── _discover_roadmap_slugs ───────────────────────────────────────────────────

def test_discover_roadmap_slugs_via_next_data():
    mock_page = MagicMock()
    mock_page.evaluate.return_value = (
        '{"props":{"pageProps":{"roadmaps":[{"id":"backend"},{"id":"frontend"}]}}}'
    )

    slugs = _discover_roadmap_slugs(mock_page)

    assert slugs == ["backend", "frontend"]
    mock_page.eval_on_selector_all.assert_not_called()


def test_discover_roadmap_slugs_via_dom_fallback():
    mock_page = MagicMock()
    mock_page.evaluate.return_value = None
    mock_page.eval_on_selector_all.return_value = [
        "/backend", "/frontend", "/devops",
        "/blog",     # excluído
        "/login",    # excluído
        "/backend",  # duplicado
    ]

    slugs = _discover_roadmap_slugs(mock_page)

    assert "backend" in slugs
    assert "frontend" in slugs
    assert "blog" not in slugs
    assert "login" not in slugs
    assert slugs.count("backend") == 1


# ── _parse_react_flow_nodes ───────────────────────────────────────────────────

def test_parse_react_flow_nodes_filters_and_maps():
    nodes = _parse_react_flow_nodes(MOCK_REACT_FLOW_DATA, ROADMAP_UUID)

    assert len(nodes) == 2
    assert nodes[0]["title"] == "HTTP"
    assert nodes[0]["roadmapId"] == ROADMAP_UUID
    assert nodes[0]["description"] == "HTTP basics"
    assert nodes[0]["nodeType"] == "topic"
    assert nodes[1]["title"] == "REST"


def test_parse_react_flow_nodes_order_preserved():
    nodes = _parse_react_flow_nodes(MOCK_REACT_FLOW_DATA, ROADMAP_UUID)
    assert nodes[0]["nodeOrder"] == 0
    assert nodes[1]["nodeOrder"] == 1


def test_parse_react_flow_nodes_empty_data():
    assert _parse_react_flow_nodes({}, ROADMAP_UUID) == []


def test_parse_react_flow_nodes_all_visual():
    data = {
        "nodes": [
            {"type": "vertical",   "data": {"label": "Line"}},
            {"type": "horizontal", "data": {"label": "Row"}},
            {"type": "divider",    "data": {"label": "---"}},
        ]
    }
    assert _parse_react_flow_nodes(data, ROADMAP_UUID) == []


# ── _fetch_roadmap_json ───────────────────────────────────────────────────────

@patch("app.services.scraper_service.httpx.Client")
def test_fetch_roadmap_json_primary_success(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"nodes": []}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    result = _fetch_roadmap_json("backend")

    assert result == {"nodes": []}


@patch("app.services.scraper_service.httpx.Client")
def test_fetch_roadmap_json_falls_back_to_api(mock_client_cls):
    mock_404 = MagicMock()
    mock_404.status_code = 404

    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.json.return_value = {"nodes": [{"type": "topic"}]}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = [mock_404, mock_200]
    mock_client_cls.return_value = mock_client

    result = _fetch_roadmap_json("backend")

    assert result is not None
    assert "nodes" in result


@patch("app.services.scraper_service.httpx.Client")
def test_fetch_roadmap_json_returns_none_when_both_fail(mock_client_cls):
    mock_404 = MagicMock()
    mock_404.status_code = 404

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_404
    mock_client_cls.return_value = mock_client

    result = _fetch_roadmap_json("nonexistent-slug")

    assert result is None


# ── _get_or_create_roadmap ────────────────────────────────────────────────────

@patch("app.services.scraper_service.httpx.Client")
def test_get_or_create_roadmap_existing(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": ROADMAP_UUID}

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp
    mock_client_cls.return_value = mock_client

    result = _get_or_create_roadmap("backend", "http://localhost:8080")

    assert result == ROADMAP_UUID
    mock_client.post.assert_not_called()


@patch("app.services.scraper_service.httpx.Client")
def test_get_or_create_roadmap_creates_when_not_found(mock_client_cls):
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 404
    mock_get_resp.json.return_value = []

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


# ── _save_nodes ───────────────────────────────────────────────────────────────

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

    with caplog.at_level(logging.WARNING, logger="app.services.scraper_service"):
        _save_nodes([{"title": "HTTP", "roadmapId": ROADMAP_UUID}], "http://localhost:8080")

    assert any("Failed to save node" in r.message for r in caplog.records)
