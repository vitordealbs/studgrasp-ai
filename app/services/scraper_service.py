import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx
from playwright.sync_api import sync_playwright, Page

logger = logging.getLogger(__name__)

BASE_URL = "https://roadmap.sh"

# Tipos de nós que são tópicos reais (clicáveis, com conteúdo)
_CONTENT_NODE_TYPES = {"topic", "subtopic", "section", "link-group"}

# Tipos visuais/conectores que não representam conteúdo
_VISUAL_NODE_TYPES = {
    "vertical", "horizontal", "column", "divider", "label",
    "button-group", "container", "junction", "spacer", "edge",
    "roadmap", "simple-horizontal", "simple-vertical",
    "button", "legend",
}

# Labels de parágrafos que são textos instrucionais, não tópicos reais
_INSTRUCTIONAL_LABELS = {
    "have a look at the following relevant tracks",
    "or pick a role specific roadmap",
    "visit the following resources to learn more",
    "see the following resources",
}

_EXCLUDED_SLUGS = {
    "blog", "guides", "videos", "account", "login", "signup",
    "about", "team", "discord", "github", "twitter", "youtube",
    "sitemap", "terms", "privacy", "advertise", "sponsor",
    "profile", "settings", "roadmaps", "best-practices",
    "questions", "projects", "ai", "friends",
}


def _slug_to_title(slug: str) -> str:
    acronyms = {"ai", "ml", "api", "ios", "sql", "aws", "gcp", "qa"}
    return " ".join(
        word.upper() if word in acronyms else word.capitalize()
        for word in slug.split("-")
    )


# ── Descoberta dinâmica de trilhas ────────────────────────────────────────────

def _parse_slugs_from_listing(data: Dict[str, Any]) -> List[str]:
    page_props = data.get("props", {}).get("pageProps", {})
    for key in ("roadmaps", "featuredRoadmaps", "items", "groups"):
        items = page_props.get(key, [])
        if not items:
            continue
        slugs: List[str] = []
        for item in items:
            if isinstance(item, dict):
                slug = item.get("id") or item.get("slug")
                if slug:
                    slugs.append(slug)
                for nested in item.get("items", []):
                    if isinstance(nested, dict):
                        s = nested.get("id") or nested.get("slug")
                        if s:
                            slugs.append(s)
        if slugs:
            return slugs
    return []


def _extract_next_data(page: Page) -> Optional[Dict[str, Any]]:
    try:
        raw = page.evaluate("() => JSON.stringify(window.__NEXT_DATA__)")
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _discover_roadmap_slugs(page: Page) -> List[str]:
    page.goto(BASE_URL, wait_until="networkidle", timeout=60_000)

    next_data = _extract_next_data(page)
    if next_data:
        slugs = _parse_slugs_from_listing(next_data)
        if slugs:
            logger.info("Discovered %d roadmap slugs via __NEXT_DATA__", len(slugs))
            return slugs

    logger.info("Falling back to DOM link extraction for slug discovery")
    hrefs: List[str] = page.eval_on_selector_all(
        "a[href]",
        "els => els.map(el => el.getAttribute('href'))",
    )
    seen: set = set()
    slugs = []
    for href in hrefs or []:
        match = re.match(r"^/([a-z][a-z0-9-]+)$", href or "")
        if not match:
            continue
        slug = match.group(1)
        if slug in _EXCLUDED_SLUGS or slug in seen:
            continue
        seen.add(slug)
        slugs.append(slug)

    logger.info("Discovered %d roadmap slugs via DOM", len(slugs))
    return slugs


# ── Java API ──────────────────────────────────────────────────────────────────

def _get_or_create_roadmap(slug: str, java_api_url: str) -> str:
    with httpx.Client(base_url=java_api_url, timeout=30) as client:
        # Tenta match exato primeiro
        resp = client.get(f"/api/roadmaps/career/{slug}")
        if resp.status_code == 200:
            return resp.json()["id"]

        # Fallback: busca todos e faz match case-insensitive
        # (evita duplicatas quando o banco tem careerType em maiúsculo)
        if resp.status_code == 404:
            all_resp = client.get("/api/roadmaps")
            if all_resp.status_code == 200:
                for roadmap in all_resp.json():
                    if roadmap.get("careerType", "").lower() == slug.lower():
                        return roadmap["id"]

            # Não existe de jeito nenhum — cria
            payload = {
                "title": _slug_to_title(slug),
                "careerType": slug,
                "sourceUrl": f"{BASE_URL}/{slug}",
            }
            create_resp = client.post("/api/roadmaps", json=payload)
            create_resp.raise_for_status()
            return create_resp.json()["id"]

        resp.raise_for_status()


# ── Busca e parse dos nós ─────────────────────────────────────────────────────

def _fetch_roadmap_json(slug: str) -> Optional[Dict[str, Any]]:
    """
    Busca o JSON do roadmap diretamente via HTTP.
    roadmap.sh serve arquivos estáticos em /{slug}.json.
    """
    url = f"{BASE_URL}/{slug}.json"
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)

    # Fallback: API oficial
    api_url = f"{BASE_URL}/api/v1-official-roadmap/{slug}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(api_url)
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", api_url, exc)

    return None


def _parse_react_flow_nodes(data: Dict[str, Any], roadmap_uuid: str) -> List[Dict]:
    """
    Extrai os nós de conteúdo do formato React Flow usado pelo roadmap.sh.
    Filtra conectores visuais (vertical, horizontal, column, etc.)
    e mantém apenas os nós de tópico real.
    """
    raw_nodes = data.get("nodes") or []
    if not raw_nodes:
        return []

    result = []
    for order, node in enumerate(raw_nodes):
        node_type = (node.get("type") or "").strip()

        # Pula conectores e elementos visuais
        if node_type in _VISUAL_NODE_TYPES:
            continue

        node_data = node.get("data") or {}
        label = (
            node_data.get("label")
            or node.get("label")
            or node_data.get("title")
            or ""
        ).strip()

        # Pula nós sem label significativo
        if not label or len(label) < 2:
            continue

        # Pula labels genéricas de elementos visuais e textos instrucionais
        if label.lower() in {"vertical node", "horizontal node", "column", "edge", "divider"}:
            continue
        if label.lower() in _INSTRUCTIONAL_LABELS:
            continue

        description = (
            node_data.get("description")
            or node_data.get("body")
            or node_data.get("content")
            or ""
        )

        result.append(
            {
                "title": label,
                "description": description,
                "parentId": None,
                "nodeType": node_type or "topic",
                "nodeOrder": order,
                "roadmapId": roadmap_uuid,
            }
        )

    return result


def _scrape_roadmap(slug: str, roadmap_uuid: str) -> List[Dict]:
    """Busca e parseia os nós de um roadmap via HTTP (sem Playwright)."""
    data = _fetch_roadmap_json(slug)
    if not data:
        logger.warning("Could not fetch roadmap JSON for '%s'", slug)
        return []

    nodes = _parse_react_flow_nodes(data, roadmap_uuid)
    logger.info("Parsed %d content nodes from '%s'", len(nodes), slug)
    return nodes


# ── Save ──────────────────────────────────────────────────────────────────────

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


# ── Entry point ───────────────────────────────────────────────────────────────

def scrape_all_roadmaps(java_api_url: str) -> Dict[str, int]:
    summary: Dict[str, int] = {}

    # Playwright apenas para descoberta de slugs na homepage
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        slugs = _discover_roadmap_slugs(page)
        browser.close()

    if not slugs:
        logger.error("No roadmap slugs discovered — aborting")
        return summary

    logger.info("Starting scrape for %d roadmaps", len(slugs))

    # Nodes são buscados via HTTP puro, sem Playwright
    errors: Dict[str, str] = {}

    for slug in slugs:
        try:
            roadmap_uuid = _get_or_create_roadmap(slug, java_api_url)
        except Exception as exc:
            msg = f"Java API error: {exc}"
            logger.error("'%s' — %s", slug, msg)
            errors[slug] = msg
            summary[slug] = 0
            continue

        try:
            nodes = _scrape_roadmap(slug, roadmap_uuid)
            _save_nodes(nodes, java_api_url)
            summary[slug] = len(nodes)
            logger.info("Scraped %d nodes from '%s'", len(nodes), slug)
        except Exception as exc:
            msg = f"Scrape/save error: {exc}"
            logger.error("'%s' — %s", slug, msg)
            errors[slug] = msg
            summary[slug] = 0

    return {"summary": summary, "errors": errors}