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
GLOBAL_ID_RE = re.compile(r"^[A-Za-z0-9+/=_-]{8,}$")
SKIP_KEYS = frozenset({"extensions", "__typename", "stacktrace", "locations", "path"})
ERROR_STRIP_KEYS = frozenset({"extensions", "locations", "path"})
ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def sanitize_for_sgrc(resp: dict[str, Any]) -> dict[str, Any]:
    """SGRC contract view — message + data only; no Python debug fields."""
    out = copy.deepcopy(resp)
    top_ext = out.get("extensions")
    if isinstance(top_ext, dict) and ("cost" in top_ext or not top_ext):
        out.pop("extensions", None)

    errors = out.get("errors")
    if isinstance(errors, list):
        cleaned: list[Any] = []
        for err in errors:
            if not isinstance(err, dict):
                cleaned.append(err)
                continue
            clean_err: dict[str, Any] = {}
            if "message" in err:
                clean_err["message"] = err["message"]
            ext = err.get("extensions")
            if isinstance(ext, dict) and ext.get("code") and "exception" not in ext:
                clean_err["extensions"] = {"code": ext["code"]}
            cleaned.append(clean_err)
        out["errors"] = cleaned
    return out


def normalize_response(resp: dict[str, Any]) -> dict[str, Any]:
    """Strip volatile fields and placeholder dynamic values for comparison."""
    return _walk(copy.deepcopy(resp))


def normalize_error_message(msg: str) -> str:
    """Reduce error messages to category keys for comparison."""
    lower = msg.lower()
    if "invalid id" in lower and "expected" in lower:
        return "<invalid_id>"
    if "invalid value" in lower or ("expected" in lower and "found" in lower):
        return "<validation>"
    if "not found" in lower or "does not exist" in lower:
        return "<not_found>"
    if "permission" in lower or "authenticate" in lower or "token" in lower:
        return "<auth>"
    if "required" in lower:
        return "<required>"
    return msg[:80] if len(msg) > 80 else msg


def _walk(obj: Any, *, in_errors: bool = False) -> Any:
    if isinstance(obj, dict):
        if in_errors and "message" in obj and isinstance(obj["message"], str):
            out: dict[str, Any] = {"message": normalize_error_message(obj["message"])}
            return out
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k in SKIP_KEYS:
                continue
            if k == "exception" and isinstance(v, dict):
                continue
            child_in_errors = in_errors or k == "errors"
            out[k] = _walk(v, in_errors=child_in_errors)
        return out
    if isinstance(obj, list):
        if not obj:
            return []
        normalized = [_walk(item, in_errors=in_errors) for item in obj]
        if len(normalized) > 1:
            return [normalized[0], "<more>"]
        return normalized
    if isinstance(obj, str):
        if UUID_RE.match(obj):
            return "<id>"
        if GLOBAL_ID_RE.match(obj) and len(obj) > 12:
            return "<gid>"
        if ISO_TS_RE.match(obj):
            return "<ts>"
        if len(obj) > 64:
            return obj[:64] + "…"
        return obj
    return obj
