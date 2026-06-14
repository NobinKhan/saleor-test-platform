"""
Probe execution tier classification for parallel-safe execution.

Classifies endpoints into dependency tiers:
  Tier 0: read-only, parallel-safe (default concurrency 4)
  Tier 1: mutating, isolated (sequential)
  Tier 2: scenario steps (strict order, shared context)
  Tier 3: dynamic probes (sequential per group)
"""

from __future__ import annotations

import os
import re
from typing import Any

PROBE_CONCURRENCY = int(os.environ.get("PROBE_CONCURRENCY", "4"))

_MUTATION_RE = re.compile(r"\bmutation\b", re.IGNORECASE)


TIER_0_CATEGORIES = frozenset({
    "products", "categories", "collections", "channels",
    "attributes", "shipping", "discounts", "shop", "pages",
    "client-dashboard", "client-storefront",
})


def is_mutating_document(document: str) -> bool:
    """True when a GraphQL document performs mutations (not read-only)."""
    text = (document or "").lstrip()
    if not text:
        return False
    return bool(_MUTATION_RE.search(text))


def classify_probe_tier(endpoint: dict[str, Any]) -> int:
    """Classify an endpoint into an execution tier."""
    kind = endpoint.get("kind", "")
    category = endpoint.get("category", "")

    if kind in ("SCENARIO_KIND", "SCENARIO", "SCENARIO_STEP"):
        return 2

    if kind == "DYNAMIC_PROBE":
        return 3

    if kind == "VARIANT_PROBE":
        return 1

    if kind == "CLIENT_BUNDLE":
        doc = endpoint.get("bundle_document") or endpoint.get("golden_input") or ""
        return 1 if is_mutating_document(doc) else 0

    if kind == "QUERY":
        return 0

    if kind == "MUTATION":
        if category in TIER_0_CATEGORIES:
            return 0
        return 1

    return 1


def tier_label(tier: int) -> str:
    """Human-readable tier label."""
    labels = {
        0: "parallel-read",
        1: "sequential-mutate",
        2: "scenario-ordered",
        3: "dynamic-sequential",
    }
    return labels.get(tier, f"tier-{tier}")


def tier_concurrency(tier: int) -> int:
    """Max concurrency for a tier."""
    if tier == 0:
        return PROBE_CONCURRENCY
    return 1
