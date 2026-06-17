"""
Per-bundle L3 setup mutations (mutation-first L3 extension).
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

RunSetupFn = Callable[[dict[str, Any], str], Awaitable[str | None]]

# Bundles needing extra fixture keys beyond global runtime seed.
_SECONDARY_VARIANT_STEP: dict[str, Any] = {
    "mutation": """mutation($input: ProductVariantCreateInput!) {
        productVariantCreate(input: $input) {
            productVariant { id }
            errors { field message }
        }
    }""",
    "variables": lambda fixtures: {
        "input": {
            "product": fixtures.get("default_product_id"),
            "sku": "harness-second-variant",
            "attributes": [],
            "channelListings": [
                {
                    "channelId": fixtures.get("default_channel_id"),
                    "price": "12.00",
                }
            ],
        }
    },
    "extract": "$.data.productVariantCreate.productVariant.id",
    "fixture_key": "secondary_variant_id",
    "auth": "staff",
}

BUNDLE_SETUP: dict[str, list[dict[str, Any]]] = {
    "productvariantsetdefault": [_SECONDARY_VARIANT_STEP],
    "productvariantreorder": [_SECONDARY_VARIANT_STEP],
}


def get_bundle_setup(bundle_id: str) -> list[dict[str, Any]]:
    """Return setup chain for bundle_id, if any."""
    return BUNDLE_SETUP.get(bundle_id, [])


async def apply_bundle_setup(
    *,
    bundle_id: str,
    fixtures: dict[str, Any],
    run_setup_mutation: RunSetupFn,
) -> dict[str, Any]:
    """Run per-bundle setup mutations; return fixture overlay to merge."""
    overlay: dict[str, Any] = {}
    for step in get_bundle_setup(bundle_id):
        variables_fn = step.get("variables")
        if callable(variables_fn):
            variables = variables_fn({**fixtures, **overlay})
        else:
            variables = variables_fn or {}
        if not variables.get("input", variables):
            continue
        setup = {
            "mutation": step["mutation"],
            "variables": variables,
            "extract": step.get("extract"),
        }
        entity_id = await run_setup_mutation(setup, step.get("auth", "staff"))
        key = step.get("fixture_key")
        if entity_id and key:
            overlay[key] = entity_id
    return overlay
