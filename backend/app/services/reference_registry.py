"""
Golden corpus version registry — tracks supported Saleor reference versions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.reference_corpus import CORPUS_ROOT, corpus_hash, load_manifest


def registry_path() -> Path:
    return CORPUS_ROOT / "registry.json"


def load_registry() -> dict[str, Any]:
    path = registry_path()
    if not path.is_file():
        return {
            "default_version": settings.golden_corpus_version,
            "supported": [],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def save_registry(data: dict[str, Any]) -> None:
    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    registry_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def register_corpus_version(
    version: str,
    *,
    probe_count: int,
    saleor_url: str = "",
    set_default: bool | None = None,
) -> dict[str, Any]:
    registry = load_registry()
    manifest = load_manifest(version) or {}
    entry = {
        "version": version,
        "captured_at": manifest.get("captured_at") or datetime.now(timezone.utc).isoformat(),
        "probe_count": probe_count or manifest.get("probe_count", 0),
        "saleor_url": saleor_url or manifest.get("saleor_url", ""),
        "corpus_hash": corpus_hash(version),
    }
    supported = [s for s in registry.get("supported", []) if s.get("version") != version]
    supported.append(entry)
    supported.sort(key=lambda x: x.get("version", ""), reverse=True)
    registry["supported"] = supported
    if set_default or version == settings.golden_corpus_version:
        registry["default_version"] = version
    save_registry(registry)
    return registry


def get_upgrade_hint(target_version: str | None, resolved_corpus: str | None) -> str | None:
    if not target_version or not resolved_corpus:
        return None
    if target_version == resolved_corpus:
        return None
    parts_t = target_version.split(".")
    parts_c = resolved_corpus.split(".")
    if len(parts_t) >= 2 and len(parts_c) >= 2:
        if parts_t[0] != parts_c[0]:
            return f"Major mismatch: record golden for Saleor {target_version} (`bash scripts/upgrade-reference.sh {target_version}`)"
        if f"{parts_t[0]}.{parts_t[1]}" != f"{parts_c[0]}.{parts_c[1]}":
            return f"Minor drift: upgrade golden to {target_version} (`bash scripts/upgrade-reference.sh {target_version}`)"
        if target_version != resolved_corpus:
            return f"Patch drift: consider re-recording {target_version} if GraphQL changed"
    return None
