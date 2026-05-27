import json
import logging
from typing import Any, Dict, List, Optional

import httpx
from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)

ROADMAPS: List[str] = [
    "backend",
    "frontend",
    "devops",
    "full-stack",
    "android",
    "ai-data-scientist",
]

ROADMAP_TITLES: Dict[str, str] = {
    "backend": "Backend",
    "frontend": "Frontend",
    "devops": "DevOps",
    "full-stack": "Full Stack",
    "android": "Android",
    "ai-data-scientist": "AI / Data Scientist",
}

BASE_URL = "https://roadmap.sh"


def _get_or_create_roadmap(slug: str, java_api_url: str) -> str:
    """
    Returns the UUID of the Roadmap for the given careerType slug.
    Creates it via POST /api/roadmaps if it does not exist yet.
    """
    with httpx.Client(base_url=java_api_url, timeout=30) as client:
        resp = client.get(f"/api/roadmaps/career/{slug}")

        if resp.status_code == 200:
            return resp.json()["id"]

        if resp.status_code == 404:
            payload = {
                "title": ROADMAP_TITLES.get(slug, slug.title()),
                "careerType": slug,
                "sourceUrl": f"{BASE_URL}/{slug}",
            }
            create_resp = client.post("/api/roadmaps", json=payload)
            create_resp.raise_for_status()
            return create_resp.json()["id"]

        resp.raise_for_status()


def _extract_next_data(page: Page) -> Optional[Dict[str, Any]]:
    try:
        raw = page.evaluate("() => JSON.stringify(window.__NEXT_DATA__)")
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _parse_nodes_from_next_data(data: Dict[str, Any], roadmap_uuid: str) -> List[Dict]:
    nodes: List[Dict] = []
    try:
        topics = (
            data.get("props", {})
            .get("pageProps", {})
            .get("roadmap", {})
            .get("topics", [])
        )
        for order, topic in enumerate(topics):
            nodes.append(
                {
                    "title": topic.get("title", ""),
                    "description": topic.get("description", ""),
                    "parentId": topic.get("parentId"),
                    "nodeType": topic.get("type", "topic"),
                    "nodeOrder": order,
                    "roadmapId": roadmap_uuid,
                }
            )
    except (KeyError, TypeError) as exc:
        logger.warning("Could not parse __NEXT_DATA__: %s", exc)
    return nodes


def _parse_nodes_from_dom(page: Page, roadmap_uuid: str) -> List[Dict]:
    nodes: List[Dict] = []
    elements = page.query_selector_all("[data-id]")
    for order, el in enumerate(elements):
        node_id = el.get_attribute("data-id") or ""
        title = el.get_attribute("data-title") or el.inner_text() or node_id
        nodes.append(
            {
                "title": title,
                "description": "",
                "parentId": None,
                "nodeType": "topic",
                "nodeOrder": order,
                "roadmapId": roadmap_uuid,
            }
        )
    return nodes


def _scrape_roadmap(page: Page, slug: str, roadmap_uuid: str) -> List[Dict]:
    url = f"{BASE_URL}/{slug}"
    page.goto(url, wait_until="networkidle", timeout=60_000)

    next_data = _extract_next_data(page)
    if next_data:
        nodes = _parse_nodes_from_next_data(next_data, roadmap_uuid)
        if nodes:
            return nodes

    logger.info("Falling back to DOM scraping for %s", slug)
    return _parse_nodes_from_dom(page, roadmap_uuid)


def _save_nodes(nodes: List[Dict], java_api_url: str) -> None:
    with httpx.Client(base_url=java_api_url, timeout=30) as client:
        for node in nodes:
            try:
                resp = client.post("/api/roadmap-nodes", json=node)
                if resp.status_code not in (200, 201):
                    logger.warning(
                        "Failed to save node '%s': %s", node.get("title"), resp.text
                    )
            except Exception as exc:
                logger.error("Error saving node '%s': %s", node.get("title"), exc)


def scrape_all_roadmaps(java_api_url: str) -> Dict[str, int]:
    summary: Dict[str, int] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        for slug in ROADMAPS:
            try:
                roadmap_uuid = _get_or_create_roadmap(slug, java_api_url)
                nodes = _scrape_roadmap(page, slug, roadmap_uuid)
                _save_nodes(nodes, java_api_url)
                summary[slug] = len(nodes)
                logger.info("Scraped %d nodes from '%s'", len(nodes), slug)
            except Exception as exc:
                logger.error("Error scraping '%s': %s", slug, exc)
                summary[slug] = 0

        browser.close()

    return summary
