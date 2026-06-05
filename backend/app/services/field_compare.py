"""
Field-level JSON shape comparison for golden vs actual GraphQL responses.
"""

from __future__ import annotations

from typing import Any


def _type_label(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        if not value:
            return "array"
        return f"array<{_type_label(value[0])}>"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _walk_paths(obj: Any, prefix: str = "") -> dict[str, str]:
    paths: dict[str, str] = {}
    if isinstance(obj, dict):
        if not obj:
            paths[prefix or "$"] = "object"
            return paths
        for key, val in obj.items():
            child = f"{prefix}.{key}" if prefix else key
            if isinstance(val, (dict, list)):
                paths.update(_walk_paths(val, child))
            else:
                paths[child] = _type_label(val)
    elif isinstance(obj, list):
        if not obj:
            paths[prefix or "$"] = "array"
            return paths
        paths.update(_walk_paths(obj[0], f"{prefix}[0]"))
    else:
        paths[prefix or "$"] = _type_label(obj)
    return paths


def compare_response_fields(
    golden: dict[str, Any],
    actual: dict[str, Any],
    *,
    max_items: int = 50,
) -> list[dict[str, str | None]]:
    """Return TestItem-compatible rows comparing JSON field paths."""
    golden_paths = _walk_paths(golden)
    actual_paths = _walk_paths(actual)
    all_keys = sorted(set(golden_paths) | set(actual_paths))

    items: list[dict[str, str | None]] = []
    for key in all_keys:
        g_type = golden_paths.get(key)
        a_type = actual_paths.get(key)
        if g_type is None:
            status = "extra"
        elif a_type is None:
            status = "missing"
        elif g_type == a_type:
            status = "match"
        else:
            status = "type_mismatch"
        items.append(
            {
                "item_key": key,
                "item_status": status,
                "expected_type": g_type,
                "actual_type": a_type,
            }
        )
        if len(items) >= max_items:
            break
    return items
