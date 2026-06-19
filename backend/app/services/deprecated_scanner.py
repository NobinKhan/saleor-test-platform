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

DEPRECATED_MUTATIONS: frozenset[str] = frozenset({
    "saleBulkDelete",
    "saleCreate",
    "saleUpdate",
    "saleDelete",
    "saleAddChannels",
    "saleRemoveChannels",
    "saleChannelListingUpdate",
})

DEPRECATED_TYPE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted(DEPRECATED_TYPES)) + r")\b"
)

DEPRECATED_MUTATION_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(m) for m in sorted(DEPRECATED_MUTATIONS)) + r")\b"
)


def is_deprecated_mutation(name: str) -> bool:
    """True when an introspected mutation field is legacy/removed from certification."""
    return name in DEPRECATED_MUTATIONS


def filter_deprecated_schema_ops(ops: list[str]) -> list[str]:
    """Drop deprecated mutation names from schema gate reference lists."""
    return [op for op in ops if not is_deprecated_mutation(op)]


def find_deprecated_mutations_in_list(ops: list[str]) -> list[str]:
    """Return deprecated mutation field names present in a list."""
    return sorted(m for m in ops if is_deprecated_mutation(m))


def check_corpus_deprecated(
    *,
    manifest_mutations: list[str] | None,
    probes: list[Any],
) -> list[str]:
    """Return error messages if legacy Sale API appears in corpus or manifest."""
    errors: list[str] = []
    if manifest_mutations:
        found = find_deprecated_mutations_in_list(manifest_mutations)
        if found:
            errors.append(
                "manifest reference_mutations contains legacy Sale API: "
                + ", ".join(found)
            )
    for probe in probes:
        is_dep, types_found = scan_l1_probe_for_deprecated(probe.input_sent)
        if is_dep:
            errors.append(
                f"probe {probe.endpoint_name}__{probe.endpoint_kind} references "
                f"deprecated: {', '.join(types_found)}"
            )
    return errors


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
    type_found = DEPRECATED_TYPE_PATTERN.findall(query_input)
    mutation_found = DEPRECATED_MUTATION_PATTERN.findall(query_input)
    found = sorted(set(type_found + mutation_found))
    return bool(found), found


def get_deprecated_types() -> list[str]:
    """Return sorted list of all deprecated type names."""
    return sorted(DEPRECATED_TYPES)
