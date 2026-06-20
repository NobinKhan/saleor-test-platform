"""
Record golden responses for L3 dashboard client bundles.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings
from app.services.client_bundle_fixtures import substitute_fixtures
from app.services.client_bundles import (
    ClientBundle,
    bundle_dir_for_version,
    load_all_bundles_from_disk,
    load_fixtures,
    save_fixtures,
    update_bundle_manifest,
    write_bundle,
)
from app.services.reference_compare import _normalized_hash
from app.services.response_contract import classify_response_contract, contract_to_legacy_outcome
from app.services.semantic_compare import build_semantic_profile


async def capture_dashboard_fixtures(
    saleor_url: str,
    token: str,
    *,
    timeout: int = 30,
) -> dict[str, Any]:
    """Capture common fixture IDs from a fresh Saleor instance."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    fixtures: dict[str, Any] = {
        "default_channel": "default-channel",
        "default_slug": "test-product",
        "placeholder_id": "00000000-0000-0000-0000-000000000000",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            saleor_url,
            json={"query": "query { channels { id slug } }"},
            headers=headers,
        )
        data = resp.json().get("data") or {}
        channels = data.get("channels") or []
        if channels:
            node = channels[0]
            fixtures["default_channel"] = node.get("slug") or fixtures["default_channel"]
            fixtures["default_channel_id"] = node.get("id")

        resp = await client.post(
            saleor_url,
            json={
                "query": (
                    "query($ch: String!) { products(first: 1, channel: $ch) "
                    "{ edges { node { id slug variants { id } } } } }"
                ),
                "variables": {"ch": fixtures["default_channel"]},
            },
            headers=headers,
        )
        data = resp.json().get("data") or {}
        edges = (data.get("products") or {}).get("edges") or []
        if edges:
            node = edges[0].get("node") or {}
            fixtures["default_slug"] = node.get("slug") or fixtures["default_slug"]
            fixtures["default_product_id"] = node.get("id")
            variants = node.get("variants") or []
            if variants:
                fixtures["default_variant_id"] = variants[0].get("id")

        resp = await client.post(
            saleor_url,
            json={"query": "query { orders(first: 1) { edges { node { id } } } }"},
            headers=headers,
        )
        data = resp.json().get("data") or {}
        edges = (data.get("orders") or {}).get("edges") or []
        if edges:
            fixtures["default_order_id"] = (edges[0].get("node") or {}).get("id")

        resp = await client.post(
            saleor_url,
            json={"query": "query { customers(first: 1) { edges { node { id } } } }"},
            headers=headers,
        )
        data = resp.json().get("data") or {}
        edges = (data.get("customers") or {}).get("edges") or []
        if edges:
            fixtures["default_customer_id"] = (edges[0].get("node") or {}).get("id")

        resp = await client.post(
            saleor_url,
            json={"query": "query { warehouses(first: 1) { edges { node { id } } } }"},
            headers=headers,
        )
        data = resp.json().get("data") or {}
        edges = (data.get("warehouses") or {}).get("edges") or []
        if edges:
            fixtures["default_warehouse_id"] = (edges[0].get("node") or {}).get("id")

        resp = await client.post(
            saleor_url,
            json={
                "query": (
                    "query($ch: String!) { collections(first: 1, channel: $ch) "
                    "{ edges { node { id } } } }"
                ),
                "variables": {"ch": fixtures["default_channel"]},
            },
            headers=headers,
        )
        data = resp.json().get("data") or {}
        edges = (data.get("collections") or {}).get("edges") or []
        if edges:
            fixtures["default_collection_id"] = (edges[0].get("node") or {}).get("id")

        resp = await client.post(
            saleor_url,
            json={"query": "query { categories(first: 1) { edges { node { id } } } }"},
            headers=headers,
        )
        data = resp.json().get("data") or {}
        edges = (data.get("categories") or {}).get("edges") or []
        if edges:
            fixtures["default_category_id"] = (edges[0].get("node") or {}).get("id")

    return fixtures


def save_record_failures(source: str, version: str, errors: list[str]) -> None:
    path = bundle_dir_for_version(source, version) / "record_failures.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"errors": errors}, indent=2), encoding="utf-8")


async def record_client_bundles(
    *,
    source: str,
    saleor_url: str,
    saleor_token: str,
    version: str | None = None,
    bundle_ids: list[str] | None = None,
    priority: str | None = None,
    timeout: int = 30,
    capture_fixtures: bool = True,
    customer_token: str | None = None,
) -> dict[str, Any]:
    from app.services.saleor_auth import ensure_customer_token

    ver = version or settings.reference_baseline_version
    if capture_fixtures:
        from app.services.reference_seed import seed_reference_data

        try:
            fixtures = await seed_reference_data(
                saleor_url,
                saleor_token,
                timeout=timeout,
                dashboard_version=ver,
                storefront_version=ver,
            )
        except Exception:
            fixtures = await capture_dashboard_fixtures(saleor_url, saleor_token, timeout=timeout)
            save_fixtures(source, ver, fixtures)
    else:
        fixtures = load_fixtures(source, ver) or load_fixtures("dashboard", ver)

    # Resolve staff_user_id via me { id } for bundles that need it
    # (saveonboardingstate-success, updatemetadata-success)
    if not fixtures.get("staff_user_id"):
        try:
            async with httpx.AsyncClient(timeout=timeout) as me_client:
                me_resp = await me_client.post(
                    saleor_url,
                    json={"query": "query { me { id } }"},
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {saleor_token.removeprefix('Bearer ')}",
                    },
                )
                me_data = me_resp.json().get("data", {})
                staff_id = (me_data.get("me") or {}).get("id")
                if staff_id:
                    fixtures["staff_user_id"] = staff_id
        except Exception:
            pass

    # Inject a recording-scoped run_id so bundles with unique-SKU fixtures
    # (e.g. productvariantbulkcreate-success) don't collide on re-runs.
    import uuid as _uuid
    fixtures["_run_id"] = str(_uuid.uuid4())[:8]

    bundles = load_all_bundles_from_disk(source, ver, priority=priority)
    if bundle_ids:
        wanted = set(bundle_ids)
        bundles = [b for b in bundles if b.bundle_id in wanted]
    if not bundles:
        raise ValueError(f"No bundles to record for {source}-{ver}")

    staff_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {saleor_token.removeprefix('Bearer ')}",
    }

    # Run BUNDLE_SETUP chains for bundles that need prerequisite entities
    from app.services.bundle_setup import get_bundle_setup

    async with httpx.AsyncClient(timeout=timeout) as setup_client:
        for bundle in bundles:
            setup_steps = get_bundle_setup(bundle.bundle_id)
            for step in setup_steps:
                fixture_key = step.get("fixture_key")
                if fixture_key and fixtures.get(fixture_key):
                    continue  # Already resolved
                mutation = step.get("mutation")
                if not mutation:
                    # Copy-from-key step (no mutation to run)
                    from_key = step.get("_from_key")
                    if from_key and from_key in fixtures and fixture_key:
                        fixtures[fixture_key] = fixtures[from_key]
                    continue
                variables_fn = step.get("variables")
                step_vars = variables_fn(fixtures) if callable(variables_fn) else variables_fn
                step_auth = step.get("auth", "staff")
                step_headers = {"Content-Type": "application/json"}
                if step_auth == "staff":
                    step_headers["Authorization"] = f"Bearer {saleor_token.removeprefix('Bearer ')}"
                try:
                    step_resp = await setup_client.post(
                        saleor_url,
                        json={"query": mutation, "variables": step_vars},
                        headers=step_headers,
                    )
                    step_json = step_resp.json()
                    extract_path = step.get("extract")
                    if extract_path:
                        from app.services.scenario_corpus import _extract_json_path
                        entity_id = _extract_json_path(step_json, extract_path)
                        if entity_id:
                            fixtures[fixture_key] = str(entity_id)
                except Exception:
                    pass

    recorded = 0
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=timeout) as client:
        cust_token = customer_token
        for bundle in bundles:
            try:
                variables = substitute_fixtures(bundle.variables, fixtures)
            except KeyError as exc:
                errors.append(f"{bundle.bundle_id}: missing fixture {exc}")
                continue
            auth_context = bundle.auth_context or "staff"
            if auth_context == "customer" and not cust_token:
                from app.services.reference_seed import REFERENCE_CHANNEL_SLUG

                cust_token = await ensure_customer_token(
                    saleor_url=saleor_url,
                    token=None,
                    email=None,
                    password=None,
                    timeout=timeout,
                    client=client,
                    channel=fixtures.get("default_channel") or REFERENCE_CHANNEL_SLUG,
                )
            headers = dict(staff_headers)
            if auth_context == "customer" and cust_token:
                headers["Authorization"] = f"Bearer {cust_token}"
            elif auth_context == "anonymous":
                headers.pop("Authorization", None)
            try:
                resp = await client.post(
                    saleor_url,
                    json={"query": bundle.document, "variables": variables},
                    headers=headers,
                )
                resp_json = resp.json()
            except Exception as exc:
                errors.append(f"{bundle.bundle_id}: request failed: {exc}")
                continue
            contract = classify_response_contract(resp_json, http_status=resp.status_code)
            profile = build_semantic_profile(
                golden_response=resp_json,
                golden_contract=contract,
                input_sent=bundle.document,
                endpoint_name=bundle.bundle_id,
            )
            from app.services.response_normalize import sanitize_for_sgrc

            sanitized = sanitize_for_sgrc(resp_json)
            bundle.golden_response = sanitized
            bundle.golden_contract = contract
            bundle.golden_outcome = contract_to_legacy_outcome(contract)
            bundle.golden_status = "pass" if contract == "success" else "warn"
            bundle.http_status = resp.status_code
            bundle.response_shape_hash = _normalized_hash(sanitized)
            bundle.semantic_profile = profile
            write_bundle(source, ver, bundle)
            recorded += 1

    update_bundle_manifest(source, ver)
    save_record_failures(source, ver, errors)
    return {
        "version": ver,
        "recorded": recorded,
        "errors": errors,
        "source": source,
    }


async def record_dashboard_bundles(
    *,
    saleor_url: str,
    saleor_token: str,
    version: str | None = None,
    bundle_ids: list[str] | None = None,
    priority: str | None = None,
    timeout: int = 30,
    capture_fixtures: bool = True,
) -> dict[str, Any]:
    return await record_client_bundles(
        source="dashboard",
        saleor_url=saleor_url,
        saleor_token=saleor_token,
        version=version,
        bundle_ids=bundle_ids,
        priority=priority,
        timeout=timeout,
        capture_fixtures=capture_fixtures,
    )


async def record_storefront_bundles(
    *,
    saleor_url: str,
    saleor_token: str,
    version: str | None = None,
    bundle_ids: list[str] | None = None,
    priority: str | None = None,
    timeout: int = 30,
    capture_fixtures: bool = True,
) -> dict[str, Any]:
    return await record_client_bundles(
        source="storefront",
        saleor_url=saleor_url,
        saleor_token=saleor_token,
        version=version,
        bundle_ids=bundle_ids,
        priority=priority,
        timeout=timeout,
        capture_fixtures=capture_fixtures,
    )
