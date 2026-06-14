"""
Deprecated type auto-exclusion scanner.

Parses L3 bundle documents and L1 probe strings to detect references
to deprecated/removed Saleor GraphQL types. Auto-excludes them from
compatibility scoring.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.client_bundles import ClientBundle, CLIENT_BUNDLE_KIND


DEPRECATED_TYPES: frozenset[str] = frozenset({
    "Sale",
    "SaleType",
    "SaleTranslatableContent",
    "SaleTranslation",
    "SaleChannelListing",
    "SaleBulkDelete",
    "SaleCreate",
    "SaleUpdate",
    "SaleDelete",
    "SaleAddChannels",
    "SaleRemoveChannels",
    "SaleChannelListingUpdate",
    "DiscountedSubtotal",
    "VoucherDiscountType",
    "sale",
})

DEPRECATED_TYPE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(DEPRECATED_TYPES)) + r")\b"
)


def scan_document_for_deprecated_types(document: str) -> list[str]:
    """Return list of deprecated type names found in a GraphQL document string."""
    matches = DEPRECATED_TYPE_PATTERN.findall(document)
    return sorted(set(matches))


def is_deprecated_bundle(bundle: ClientBundle) -> tuple[bool, list[str]]:
    """Check if a client bundle references deprecated types.

    Returns (is_deprecated, list_of_deprecated_types_found).
    """
    found = scan_document_for_deprecated_types(bundle.document)
    if found:
        return True, found
    return False, []


def filter_deprecated_bundles(
    bundles: list[ClientBundle],
) -> tuple[list[ClientBundle], list[dict[str, Any]]]:
    """Split bundles into compatible and deprecated-excluded lists.

    Returns (compatible_bundles, excluded_with_reason).
    """
    compatible: list[ClientBundle] = []
    excluded: list[dict[str, Any]] = []

    for bundle in bundles:
        is_dep, types_found = is_deprecated_bundle(bundle)
        if is_dep:
            excluded.append({
                "bundle_id": bundle.bundle_id,
                "source": bundle.source,
                "reason": "deprecated_type",
                "deprecated_types": types_found,
                "message": (
                    f"References deprecated type(s): {', '.join(types_found)}. "
                    "Excluded from compatibility scoring."
                ),
            })
        else:
            compatible.append(bundle)

    return compatible, excluded


def scan_l1_probe_for_deprecated(query_input: str) -> tuple[bool, list[str]]:
    """Check if an L1 probe query references deprecated operations.

    Returns (is_deprecated, list_of_deprecated_types_found).
    """
    found = DEPRECATED_TYPE_PATTERN.findall(query_input)
    return bool(found), sorted(set(found))


def get_deprecated_types() -> list[str]:
    """Return sorted list of all deprecated type names."""
    return sorted(DEPRECATED_TYPES)
