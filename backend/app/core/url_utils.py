"""URL helpers for Docker vs host Saleor access."""

from __future__ import annotations

import os

from app.core.config import get_settings
from app.services.introspection import normalize_graphql_url


def resolve_saleor_url_for_runner(saleor_url: str) -> str:
    """
    Normalize GraphQL URL. When the harness runs in Docker and the UI sends
    localhost:8000, rewrite to the in-compose Saleor service.
    """
    normalized = normalize_graphql_url(saleor_url)
    if "localhost" in normalized or "127.0.0.1" in normalized:
        if "@harness-db:" in os.environ.get("DATABASE_URL", ""):
            default = get_settings().saleor_graphql_url_default
            if default:
                return normalize_graphql_url(default)
    return normalized
