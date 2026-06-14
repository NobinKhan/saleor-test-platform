"""
Field-level JSON shape and value comparison for golden vs actual GraphQL responses.
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


def _walk_paths(obj: Any, prefix: str = "") -> tuple[dict[str, str], dict[str, Any]]:
    """Walk JSON tree returning (type_map, value_map) for each path."""
    type_map: dict[str, str] = {}
    value_map: dict[str, Any] = {}
    if isinstance(obj, dict):
        if not obj:
            type_map[prefix or "$"] = "object"
            value_map[prefix or "$"] = {}
            return type_map, value_map
        for key, val in obj.items():
            child = f"{prefix}.{key}" if prefix else key
            if isinstance(val, (dict, list)):
                t, v = _walk_paths(val, child)
                type_map.update(t)
                value_map.update(v)
            else:
                type_map[child] = _type_label(val)
                value_map[child] = val
    elif isinstance(obj, list):
        if not obj:
            type_map[prefix or "$"] = "array"
            value_map[prefix or "$"] = []
            return type_map, value_map
        t, v = _walk_paths(obj[0], f"{prefix}[0]")
        type_map.update(t)
        value_map.update(v)
    else:
        type_map[prefix or "$"] = _type_label(obj)
        value_map[prefix or "$"] = obj
    return type_map, value_map


def _truncate_value(val: Any, max_len: int = 100) -> str:
    """Truncate a value for display."""
    s = str(val)
    if len(s) > max_len:
        return s[:max_len - 20] + f"… [{len(s)} chars]"
    return s


def compare_response_fields(
    golden: dict[str, Any],
    actual: dict[str, Any],
    *,
    max_items: int = 50,
    include_values: bool = True,
) -> list[dict[str, str | None]]:
    """Return TestItem-compatible rows comparing JSON field paths.

    If include_values=True, also includes truncated golden/actual values
    for scalar mismatches.
    """
    golden_types, golden_values = _walk_paths(golden)
    actual_types, actual_values = _walk_paths(actual)
    all_keys = sorted(set(golden_types) | set(actual_types))

    items: list[dict[str, str | None]] = []
    for key in all_keys:
        g_type = golden_types.get(key)
        a_type = actual_types.get(key)
        if g_type is None:
            status = "extra"
        elif a_type is None:
            status = "missing"
        elif g_type == a_type:
            status = "match"
        else:
            status = "type_mismatch"
        item: dict[str, str | None] = {
            "item_key": key,
            "item_status": status,
            "expected_type": g_type,
            "actual_type": a_type,
        }
        if include_values and status in ("type_mismatch", "match"):
            g_val = golden_values.get(key)
            a_val = actual_values.get(key)
            if g_val is not None and not isinstance(g_val, (dict, list)):
                item["expected_value"] = _truncate_value(g_val)
            if a_val is not None and not isinstance(a_val, (dict, list)):
                item["actual_value"] = _truncate_value(a_val)
        items.append(item)
        if len(items) >= max_items:
            break
    return items


def summarize_field_diffs(
    items: list[dict[str, str | None]],
    *,
    top_n: int = 10,
) -> list[str]:
    """Summarize field-level diffs for display in reports.

    Returns human-readable diff lines for the top N mismatched paths.
    """
    mismatches = [i for i in items if i["item_status"] != "match"]
    lines: list[str] = []
    for item in mismatches[:top_n]:
        key = item["item_key"]
        status = item["item_status"]
        g_type = item.get("expected_type", "?")
        a_type = item.get("actual_type", "?")
        g_val = item.get("expected_value")
        a_val = item.get("actual_value")
        if status == "extra":
            lines.append(f"  + {key}: {a_type} (extra in actual)")
        elif status == "missing":
            lines.append(f"  - {key}: {g_type} (missing in actual)")
        elif status == "type_mismatch":
            val_note = ""
            if g_val and a_val:
                val_note = f" [{g_val} → {a_val}]"
            lines.append(f"  ~ {key}: {g_type} → {a_type}{val_note}")
    remaining = len(mismatches) - top_n
    if remaining > 0:
        lines.append(f"  ... +{remaining} more mismatches")
    return lines
