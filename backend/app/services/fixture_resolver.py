"""
Runtime fixture resolver — resolves entity IDs at test-run start.

Queries the target Saleor instance to verify that required fixture entities
(Product, Variant, etc.) exist, and optionally seeds missing ones. Replaces
static fixtures.json IDs with live-resolved IDs per run.

The keys align with the on-disk fixtures.json schema and reference_seed.py
REQUIRED_FIXTURE_KEYS (default_product_id, default_variant_id, etc.) so
that substitute_fixtures() resolves {{fixtures.default_product_id}} correctly.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.services.client_bundles import load_fixtures, resolve_dashboard_bundle_version

logger = logging.getLogger(__name__)


async def _query_saleor(
    saleor_url: str,
    query: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any] | None:
    """Execute a GraphQL query against the target and return data or None."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                saleor_url,
                json={"query": query},
                headers=headers,
            )
            if resp.status_code in (200, 400):
                body = resp.json()
                if not body.get("errors"):
                    return body.get("data")
    except Exception as exc:
        logger.debug("Query failed: %s", exc)
    return None


async def resolve_fixtures(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    source: str = "dashboard",
) -> dict[str, Any]:
    """Query target Saleor to resolve fixture entity IDs at runtime.

    Returns a dict using the standard fixture.json key names (default_product_id,
    default_variant_id, default_channel_id, etc.) so that substitute_fixtures()
    correctly resolves {{fixtures.default_product_id}} placeholders.

    Falls back to static fixtures.json values for any unresolvable keys.
    """
    static_fixtures = load_fixtures(source, resolve_dashboard_bundle_version())
    resolved: dict[str, Any] = dict(static_fixtures)

    product_data = await _query_saleor(
        saleor_url,
        '{ products(first: 1) { edges { node { id slug name productType { id } } } } }',
        token,
        timeout,
    )
    if product_data:
        products = (product_data.get("products") or {}).get("edges") or []
        if products:
            node = products[0]["node"]
            resolved["default_product_id"] = node["id"]
            resolved["default_slug"] = node.get("slug", "test-product")
            product_type = node.get("productType") or {}
            if product_type.get("id"):
                resolved["default_product_type_id"] = product_type["id"]
            product_id = node["id"]
            variants_data = await _query_saleor(
                saleor_url,
                f'{{ product(id: "{product_id}") {{ variants {{ id }} }} }}',
                token,
                timeout,
            )
            if variants_data:
                variants = (variants_data.get("product") or {}).get("variants") or []
                if variants:
                    resolved["default_variant_id"] = variants[0]["id"]
                    resolved["variant_id_for_cart"] = variants[0]["id"]
                else:
                    fallback = await _query_saleor(
                        saleor_url,
                        f'{{ productVariants(first: 1, filter: {{ product: "{product_id}" }}) '
                        f'{{ edges {{ node {{ id }} }} }} }}',
                        token,
                        timeout,
                    )
                    if fallback:
                        edges = (fallback.get("productVariants") or {}).get("edges") or []
                        if edges:
                            resolved["default_variant_id"] = edges[0]["node"]["id"]
                            resolved["variant_id_for_cart"] = edges[0]["node"]["id"]

    channel_data = await _query_saleor(
        saleor_url,
        '{ channels(first: 1) { edges { node { id slug name currencyCode } } } }',
        token,
        timeout,
    )
    if channel_data:
        channels = (channel_data.get("channels") or {}).get("edges") or []
        if channels:
            cnode = channels[0]["node"]
            resolved["default_channel_id"] = cnode["id"]
            resolved["default_channel"] = cnode.get("slug", "default")

    if "default_product_type_id" not in resolved:
        pt_data = await _query_saleor(
            saleor_url,
            '{ productTypes(first: 1) { edges { node { id } } } }',
            token,
            timeout,
        )
        if pt_data:
            pts = (pt_data.get("productTypes") or {}).get("edges") or []
            if pts:
                resolved["default_product_type_id"] = pts[0]["node"]["id"]

    order_data = await _query_saleor(
        saleor_url,
        '{ orders(first: 1) { edges { node { id } } } }',
        token,
        timeout,
    )
    if order_data:
        orders = (order_data.get("orders") or {}).get("edges") or []
        if orders:
            resolved["default_order_id"] = orders[0]["node"]["id"]

    customer_data = await _query_saleor(
        saleor_url,
        '{ users(first: 1, filter: { search: \"harness\" }) { edges { node { id email } } } }',
        token,
        timeout,
    )
    if customer_data:
        users = (customer_data.get("users") or {}).get("edges") or []
        if users:
            resolved["default_customer_id"] = users[0]["node"]["id"]

    return resolved


async def resolve_dynamic_probe_support(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Resolve support data needed for dynamic probes (product type ID)."""
    support: dict[str, Any] = {}
    pt_data = await _query_saleor(
        saleor_url,
        '{ productTypes(first: 1) { edges { node { id } } } }',
        token,
        timeout,
    )
    if pt_data:
        pts = (pt_data.get("productTypes") or {}).get("edges") or []
        if pts:
            support["product_type_id"] = pts[0]["node"]["id"]
    return support


async def validate_preflight(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    corpus_version: str | None = None,
    *,
    allow_patch_drift: bool = False,
) -> dict[str, Any]:
    """Pre-flight validation: check API reachability, version, fixtures.

    Returns a structured result suitable for the validate endpoint.
    Includes the hard version gate check (fails on major/minor mismatch).
    """
    from app.services.version_routing import (
        version_compatibility_warning,
        version_hard_gate_check,
    )

    result: dict[str, Any] = {
        "api_reachable": False,
        "authenticated": False,
        "shop_version": None,
        "version_match": None,
        "version_warning": None,
        "version_gate_pass": None,
        "version_gate_reason": None,
        "fixture_status": {},
        "issues": [],
    }

    shop_data = await _query_saleor(
        saleor_url,
        "{ shop { version } }",
        token,
        timeout,
    )
    if shop_data is None:
        result["issues"].append("API unreachable or authentication failed")
        return result

    result["api_reachable"] = True
    result["authenticated"] = bool(token)
    version = (shop_data.get("shop") or {}).get("version")
    result["shop_version"] = version

    if version and corpus_version:
        warn = version_compatibility_warning(version, corpus_version)
        result["version_warning"] = warn
        result["version_match"] = version == corpus_version
        if warn and "major" in warn.lower():
            result["issues"].append(warn)

        gate = version_hard_gate_check(
            version, corpus_version, allow_patch_drift=allow_patch_drift
        )
        result["version_gate_pass"] = gate["gate_pass"]
        result["version_gate_reason"] = gate["reason"]
        if not gate["gate_pass"] and gate["reason"]:
            result["issues"].append(f"Version gate: {gate['reason']}")

    fixture_keys_to_check = {
        "default_product_id": '{ products(first: 1) { edges { node { id } } } }',
        "default_variant_id": '{ productVariants(first: 1) { edges { node { id } } } }',
        "default_channel_id": '{ channels(first: 1) { edges { node { id } } } }',
        "default_product_type_id": '{ productTypes(first: 1) { edges { node { id } } } }',
    }
    for key, query in fixture_keys_to_check.items():
        data = await _query_saleor(saleor_url, query, token, timeout)
        exists = bool(
            data
            and any(
                (data.get(root) or {}).get("edges")
                for root in data
            )
        )
        result["fixture_status"][key] = "present" if exists else "missing"
        if not exists:
            result["issues"].append(
                f"Fixture entity {key} not found in target database — "
                "seed reference data or set RUNTIME_SEED=true"
            )

    return result
