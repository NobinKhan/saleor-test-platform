"""
Substitute {{fixtures.key}} placeholders in bundle variables.
"""

from __future__ import annotations

import copy
import re
from typing import Any

FIXTURE_PATTERN = re.compile(r"^\{\{fixtures\.(\w+)\}\}$")
FIXTURE_EMBED_PATTERN = re.compile(r"\{\{fixtures\.(\w+)\}\}")


def _resolve_value(value: Any, fixtures: dict[str, Any]) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        m = FIXTURE_PATTERN.match(stripped)
        if m:
            key = m.group(1)
            if key not in fixtures:
                raise KeyError(f"Missing fixture: {key}")
            return fixtures[key]
        if FIXTURE_EMBED_PATTERN.search(stripped):
            def _replace(match: re.Match) -> str:
                key = match.group(1)
                if key not in fixtures:
                    raise KeyError(f"Missing fixture: {key}")
                return str(fixtures[key])
            return FIXTURE_EMBED_PATTERN.sub(_replace, stripped)
        return value
    if isinstance(value, dict):
        return {k: _resolve_value(v, fixtures) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_value(v, fixtures) for v in value]
    return value


def substitute_fixtures(variables: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    return _resolve_value(copy.deepcopy(variables), fixtures)
