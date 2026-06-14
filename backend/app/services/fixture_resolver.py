"""
Runtime fixture resolver — resolves entity IDs at test-run start.

Queries the target Saleor instance to verify that required fixture entities
(Product, Variant, etc.) exist, and optionally seeds missing ones via admin
mutations when RUNTIME_SEED=true (default). Replaces static fixtures.json IDs
with live-resolved IDs per run.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from app.core.config import settings
from app.core.url_utils import resolve_harness_saleor_url, resolve_saleor_url_for_runner
from app.services.client_bundles import load_fixtures, resolve_dashboard_bundle_version
from app.services.reference_seed import (
    capture_live_fixtures,
    ensure_runtime_fixture_entities,
)

logger = logging.getLogger(__name__)

PREFLIGHT_REQUIRED_FIXTURE_KEYS = (
    "default_product_id",
    "default_variant_id",
    "default_channel_id",
    "default_product_type_id",
)

IssueSeverity = Literal["blocking", "warning"]


@dataclass(frozen=True)
class PreflightIssue:
    message: str
    severity: IssueSeverity


@dataclass(frozen=True)
class FixtureResolution:
    fixtures: dict[str, Any]
    live_keys: frozenset[str] = field(default_factory=frozenset)
    seeded_keys: frozenset[str] = field(default_factory=frozenset)
    seed_errors: tuple[str, ...] = ()
    seed_profile: str = "harness"


def _apply_captured(
    resolved: dict[str, Any],
    live_keys: set[str],
    captured: dict[str, Any],
) -> None:
    for key, value in captured.items():
        if value and key != "placeholder_id":
            resolved[key] = value
            live_keys.add(key)


async def _query_saleor(
    saleor_url: str,
    query: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any] | None:
    """Execute a GraphQL query against the target and return data or None."""
    import httpx

    saleor_url = resolve_saleor_url_for_runner(saleor_url)
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
                data = body.get("data")
                if isinstance(data, dict):
                    return data
                if not body.get("errors"):
                    return data
    except Exception as exc:
        logger.debug("Query failed: %s", exc)
    return None


async def _resolve_storefront_customer_id(
    saleor_url: str,
    staff_token: str,
    timeout: int = 30,
) -> str | None:
    """Resolve the harness storefront JWT customer ID (distinct from reference customer)."""
    from app.services.saleor_auth import ensure_customer_token

    customer_token = await ensure_customer_token(
        saleor_url=saleor_url,
        token=None,
        email=None,
        password=None,
        timeout=timeout,
        staff_token=staff_token,
    )
    if not customer_token:
        return None
    me_data = await _query_saleor(
        saleor_url,
        "query { me { id } }",
        customer_token,
        timeout,
    )
    me = (me_data or {}).get("me") if isinstance(me_data, dict) else None
    if isinstance(me, dict):
        return me.get("id")
    return None


async def resolve_fixtures(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    source: str = "dashboard",
    *,
    seed_profile: str | None = None,
) -> FixtureResolution:
    """Resolve fixture IDs from target Saleor; optionally create missing entities."""
    saleor_url = resolve_saleor_url_for_runner(saleor_url)
    profile = seed_profile or settings.demo_seed_profile
    static_fixtures = load_fixtures(source, resolve_dashboard_bundle_version())
    resolved: dict[str, Any] = dict(static_fixtures)
    live_keys: set[str] = set()
    seeded_keys: set[str] = set()
    seed_errors: list[str] = []

    if not token:
        return FixtureResolution(fixtures=resolved, live_keys=frozenset(), seed_profile=profile)

    captured = await capture_live_fixtures(saleor_url, token, timeout=timeout)
    _apply_captured(resolved, live_keys, captured)

    missing_required = [
        k for k in PREFLIGHT_REQUIRED_FIXTURE_KEYS if k not in live_keys
    ]
    if settings.runtime_seed or profile == "saleor_demo":
        if profile == "saleor_demo":
            logger.info("Runtime seed: saleor_demo topology on target")
            from app.services.demo_seed import ensure_saleor_demo_topology

            seed_result = await ensure_saleor_demo_topology(
                saleor_url, token, timeout=max(timeout, 120)
            )
        elif missing_required:
            logger.info(
                "Runtime seed: creating missing fixture entities on target: %s",
                ", ".join(missing_required),
            )
            seed_result = await ensure_runtime_fixture_entities(
                saleor_url, token, timeout=timeout
            )
        else:
            seed_result = None
        if seed_result:
            _apply_captured(resolved, live_keys, seed_result.fixtures)
            seeded_keys.update(seed_result.seeded_keys)
            seed_errors.extend(seed_result.errors)

    storefront_customer_id = await _resolve_storefront_customer_id(
        saleor_url, token, timeout=timeout
    )
    if storefront_customer_id:
        resolved["storefront_customer_id"] = storefront_customer_id
        live_keys.add("storefront_customer_id")

    return FixtureResolution(
        fixtures=resolved,
        live_keys=frozenset(live_keys),
        seeded_keys=frozenset(seeded_keys),
        seed_errors=tuple(seed_errors),
        seed_profile=profile,
    )


async def resolve_dynamic_probe_support(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Resolve support data needed for dynamic probes (product type ID)."""
    saleor_url = resolve_saleor_url_for_runner(saleor_url)
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


def _classify_preflight_issues(issues: list[PreflightIssue]) -> dict[str, Any]:
    blocking = [i.message for i in issues if i.severity == "blocking"]
    warnings = [i.message for i in issues if i.severity == "warning"]
    return {
        "issues": [i.message for i in issues],
        "blocking_issues": blocking,
        "warning_issues": warnings,
        "issue_details": [{"message": i.message, "severity": i.severity} for i in issues],
    }


async def validate_preflight(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    corpus_version: str | None = None,
    *,
    allow_patch_drift: bool = False,
    seed_profile: str | None = None,
) -> dict[str, Any]:
    """Pre-flight validation: check API reachability, version match, fixtures."""
    from app.services.version_routing import (
        version_compatibility_warning,
        version_hard_gate_check,
    )

    requested_url, resolved_url = resolve_harness_saleor_url(saleor_url)
    issues: list[PreflightIssue] = []

    result: dict[str, Any] = {
        "api_reachable": False,
        "authenticated": False,
        "shop_version": None,
        "version_match": None,
        "version_warning": None,
        "version_gate_pass": None,
        "version_gate_reason": None,
        "fixture_status": {},
        "runtime_seed_enabled": settings.runtime_seed,
        "demo_seed_profile": settings.demo_seed_profile,
        "requested_saleor_url": requested_url,
        "resolved_saleor_url": resolved_url,
        "issues": [],
        "blocking_issues": [],
        "warning_issues": [],
        "issue_details": [],
    }

    shop_data = await _query_saleor(
        resolved_url,
        "{ shop { version } }",
        token,
        timeout,
    )
    if shop_data is None:
        issues.append(
            PreflightIssue(
                message="API unreachable or authentication failed",
                severity="blocking",
            )
        )
        result.update(_classify_preflight_issues(issues))
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
            issues.append(PreflightIssue(message=warn, severity="blocking"))

        gate = version_hard_gate_check(
            version, corpus_version, allow_patch_drift=allow_patch_drift
        )
        result["version_gate_pass"] = gate["gate_pass"]
        result["version_gate_reason"] = gate["reason"]
        if not gate["gate_pass"] and gate["reason"]:
            issues.append(
                PreflightIssue(
                    message=f"Version gate: {gate['reason']}",
                    severity="blocking",
                )
            )

    resolution = await resolve_fixtures(
        resolved_url, token, timeout=timeout, seed_profile=seed_profile
    )
    result["demo_seed_profile"] = resolution.seed_profile
    for key in PREFLIGHT_REQUIRED_FIXTURE_KEYS:
        present = key in resolution.live_keys
        result["fixture_status"][key] = "present" if present else "missing"
        if not present:
            detail = f"Could not resolve or create {key} on target"
            if resolution.seed_errors:
                detail += f" — {'; '.join(resolution.seed_errors[:3])}"
            elif settings.runtime_seed:
                detail += " — check admin permissions for channel/product mutations"
            else:
                detail += " — set RUNTIME_SEED=true to auto-create harness fixture entities"
            issues.append(PreflightIssue(message=detail, severity="warning"))

    if resolution.seeded_keys:
        result["seeded_fixture_keys"] = sorted(resolution.seeded_keys)
    if resolution.seed_errors:
        result["seed_errors"] = list(resolution.seed_errors)

    result.update(_classify_preflight_issues(issues))
    return result
