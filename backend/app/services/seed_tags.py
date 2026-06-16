"""
Per-probe seed requirement tags for L3 client bundles.

Seed-tagged probes may fail with shape_drift when the target DB lacks Saleor
populatedb topology — classify as seed_prerequisite, not real_bug.
"""

from __future__ import annotations

from typing import Any

# Legacy seed tags — mutation-first topology in reference_seed handles these at run start.
# Kept for explicit bundle metadata only; empty registry means no seed_prerequisite bypass.
SEED_TAGGED_BUNDLES: dict[str, frozenset[str]] = {}


def resolve_seed_tags(
    bundle_id: str,
    endpoint: dict[str, Any] | None = None,
) -> frozenset[str]:
    """Return seed tags for a bundle from endpoint metadata or static registry."""
    endpoint = endpoint or {}
    explicit = endpoint.get("seed_tags")
    if explicit:
        return frozenset(explicit)
    return SEED_TAGGED_BUNDLES.get(bundle_id, frozenset())


def merge_seed_tags_into_bundle(bundle_id: str, existing: list[str] | None = None) -> list[str]:
    """Combine registry tags with any tags stored on the bundle JSON."""
    tags = set(existing or [])
    tags.update(SEED_TAGGED_BUNDLES.get(bundle_id, ()))
    return sorted(tags)
