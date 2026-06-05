"""
Normalize GraphQL responses for stable golden comparison.
"""

from __future__ import annotations

import copy
import re
from typing import Any

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
SKIP_KEYS = frozenset({"extensions", "__typename"})


def normalize_response(resp: dict[str, Any]) -> dict[str, Any]:
    """Strip volatile fields and placeholder dynamic values for comparison."""
    return _walk(copy.deepcopy(resp))


def _walk(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            out[k] = _walk(v)
        return out
    if isinstance(obj, list):
        if not obj:
            return []
        normalized = [_walk(item) for item in obj]
        if len(normalized) > 1:
            return [normalized[0]]
        return normalized
    if isinstance(obj, str):
        if UUID_RE.match(obj):
            return "<uuid>"
        if len(obj) > 64:
            return obj[:64] + "…"
        return obj
    return obj
