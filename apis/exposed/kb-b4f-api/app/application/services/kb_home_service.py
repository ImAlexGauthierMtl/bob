"""Knowledge base home composition service."""

import asyncio
from typing import Any


async def build_kb_home(kb_client, current_user: dict, forward_headers: Any = None) -> dict:
    categories, recent_articles, popular_articles, stats = await asyncio.gather(
        kb_client.list_categories(forward_headers=forward_headers),
        kb_client.list_articles(skip=0, limit=5, visibility="public", forward_headers=forward_headers),
        kb_client.popular_articles(limit=5, forward_headers=forward_headers),
        kb_client.get_stats(forward_headers=forward_headers),
    )

    return {
        "user_id": current_user.get("user_id"),
        "tenant_id": current_user.get("tenant_id"),
        "categories": _items(categories),
        "recent_articles": _items(recent_articles),
        "popular_articles": _items(popular_articles),
        "stats": stats if isinstance(stats, dict) else {},
        "empty_state": _empty_state(recent_articles, popular_articles),
    }


def _items(payload: Any) -> list:
    if isinstance(payload, dict):
        items = payload.get("items", [])
        return items if isinstance(items, list) else []
    return payload if isinstance(payload, list) else []


def _empty_state(recent_articles: Any, popular_articles: Any) -> dict:
    has_content = bool(_items(recent_articles) or _items(popular_articles))
    return {
        "show_create_article_hint": not has_content,
        "message": None if has_content else "No knowledge base content is available yet.",
    }
