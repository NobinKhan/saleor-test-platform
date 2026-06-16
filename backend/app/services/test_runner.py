"""
app/services/test_runner.py — Core GraphQL testing engine.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import httpx

from app.core.config import settings
from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.version_routing import version_compatibility_warning
from app.services.reference_corpus import (
    load_all_probes_from_disk,
    load_manifest,
    resolve_corpus_version,
)
from app.services.introspection import compare_schema, introspect_saleor, schema_gate_diff
from app.services.saleor_auth import (
    CUSTOMER_DEFAULT_EMAIL,
    CUSTOMER_DEFAULT_PASSWORD,
    ensure_customer_token,
    ensure_valid_token,
    refresh_saleor_token,
)
from app.services.outcome import classify_graphql_response, classify_transport_error
from app.services.query_builder import introspect_field_args
from app.services.client_bundle_fixtures import substitute_fixtures
from app.services.client_bundles import (
    build_all_client_bundle_endpoints,
    build_client_bundle_endpoints,
    bundles_compatible_with_schema,
    CLIENT_BUNDLE_KIND,
    CLIENT_SOURCES,
    load_all_bundles_from_disk,
    load_fixtures,
    resolve_dashboard_bundle_version,
    resolve_storefront_bundle_version,
)
from app.services.client_bundle_schema_gate import (
    compute_client_bundle_schema_gate,
    merge_client_schema_into_diff,
)
from app.services.document_schema_gate import (
    compute_document_schema_gate,
    merge_document_schema_into_diff,
)
from app.services.introspection import introspect_full_schema
from app.services.scenario_corpus import (
    SCENARIO_KIND,
    build_scenario_endpoints,
    run_assertions,
    substitute_scenario_variables,
    enrich_checkout_delivery_fixture,
)
from app.services.variant_corpus import VARIANT_KIND, build_variant_endpoints
from app.services.dynamic_corpus import DYNAMIC_PROBE_KIND, build_dynamic_probe_endpoints, compare_dynamic_response
from app.services.reference_compare import compare_to_golden, tier2_gate_enabled
from app.services.response_contract import CONTRACT_AUTH_ERROR, CONTRACT_SUCCESS, classify_response_contract

from app.services.auth_visibility import infer_is_public

TEST_MODE_COMPATIBILITY = "compatibility"


async def detect_saleor_version(url: str, token: str | None, timeout: int) -> str | None:
    """Try to detect Saleor version from shop query."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                json={"query": "query { shop { version } }"},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                version = data.get("data", {}).get("shop", {}).get("version")
                return version
    except Exception:
        pass
    return None


def build_golden_endpoints(corpus_version: str) -> list[dict]:
    """Build endpoint list from golden corpus probes for compatibility replay.

    Probes referencing deprecated Saleor types are auto-excluded.
    """
    from app.services.deprecated_scanner import scan_l1_probe_for_deprecated

    probes = load_all_probes_from_disk(corpus_version)
    endpoints: list[dict] = []
    for probe in probes:
        is_deprecated, _deprecated_types = scan_l1_probe_for_deprecated(probe.input_sent)
        if is_deprecated:
            continue
        endpoints.append({
            "name": probe.endpoint_name,
            "kind": probe.endpoint_kind,
            "category": probe.category,
            "is_public": infer_is_public(probe.endpoint_name, probe.endpoint_kind),
            "golden_input": probe.input_sent,
            "golden_contract": probe.golden_contract,
        })
    return endpoints


def load_reference_schema(corpus_version: str) -> dict[str, list[str]]:
    """Reference schema from manifest or golden probe names."""
    manifest = load_manifest(corpus_version)
    if manifest:
        rq = manifest.get("reference_queries")
        rm = manifest.get("reference_mutations")
        if rq is not None and rm is not None:
            return {"queries": list(rq), "mutations": list(rm)}
    probes = load_all_probes_from_disk(corpus_version)
    return {
        "queries": sorted({p.endpoint_name for p in probes if p.endpoint_kind == "QUERY"}),
        "mutations": sorted({p.endpoint_name for p in probes if p.endpoint_kind == "MUTATION"}),
    }


class TestRunner:
    """
    Core testing engine. Runs all tests against a Saleor endpoint
    and yields live progress events via an async generator.
    """

    def __init__(
        self,
        run_id: uuid.UUID,
        saleor_url: str,
        saleor_token: str | None,
        test_scope: str | None = None,
        public_only: bool = False,
        concurrency: int = 5,
        timeout: int = 30,
        use_introspection: bool = True,
        saleor_email: str | None = None,
        saleor_password: str | None = None,
        tier2_required: bool | None = None,
        demo_seed_profile: str | None = None,
    ):
        from app.services.run_scope import FULL_SYSTEM_SCOPE
        from app.core.config import settings as _settings

        self.run_id = run_id
        self.saleor_url = resolve_saleor_url_for_runner(saleor_url)
        self.saleor_token = saleor_token
        self.saleor_email = saleor_email
        self.saleor_password = saleor_password
        self.saleor_customer_email = CUSTOMER_DEFAULT_EMAIL
        self.saleor_customer_password = CUSTOMER_DEFAULT_PASSWORD
        self.test_scope = test_scope or FULL_SYSTEM_SCOPE
        self._scenario_context: dict[str, Any] = {}
        self._last_scenario_id: str | None = None
        self._customer_token: str | None = None
        self.public_only = public_only
        self.concurrency = concurrency
        self.timeout = timeout
        self.use_introspection = use_introspection
        self.tier2_required = tier2_required
        self._stopped = False
        self.saleor_version: str | None = None
        self.schema_fields: dict[str, list[dict]] | None = None
        self.corpus_version: str | None = None
        self._resolved_fixtures: dict[str, Any] | None = None
        self._dynamic_support: dict[str, Any] | None = None
        self.demo_seed_profile: str = demo_seed_profile or _settings.demo_seed_profile

    def stop(self):
        self._stopped = True

    def _auth_headers(self, auth_context: str = "staff") -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        token = self.saleor_token
        if auth_context == "customer":
            token = self._customer_token
        elif auth_context == "anonymous":
            token = None
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _ensure_auth_for_context(
        self,
        http_client: httpx.AsyncClient | None = None,
        *,
        auth_context: str = "staff",
        force_refresh: bool = False,
    ) -> str | None:
        if auth_context == "anonymous":
            return None
        if auth_context == "customer":
            self._customer_token = await ensure_customer_token(
                saleor_url=self.saleor_url,
                token=self._customer_token,
                email=self.saleor_customer_email,
                password=self.saleor_customer_password,
                timeout=self.timeout,
                client=http_client,
                force_refresh=force_refresh,
                staff_token=self.saleor_token,
            )
            return self._customer_token
        refreshed = await ensure_valid_token(
            saleor_url=self.saleor_url,
            token=self.saleor_token,
            email=self.saleor_email,
            password=self.saleor_password,
            timeout=self.timeout,
            client=http_client,
            force_refresh=force_refresh,
        )
        if refreshed:
            self.saleor_token = refreshed
        return self.saleor_token

    async def _ensure_valid_token(
        self,
        http_client: httpx.AsyncClient | None = None,
        *,
        force_refresh: bool = False,
    ) -> str | None:
        refreshed = await ensure_valid_token(
            saleor_url=self.saleor_url,
            token=self.saleor_token,
            email=self.saleor_email,
            password=self.saleor_password,
            timeout=self.timeout,
            client=http_client,
            force_refresh=force_refresh,
        )
        if refreshed:
            self.saleor_token = refreshed
        return self.saleor_token

    async def _force_refresh_token(self) -> str | None:
        if self.saleor_email and self.saleor_password:
            fresh, _err = await refresh_saleor_token(
                self.saleor_url,
                self.saleor_email,
                self.saleor_password,
                self.timeout,
            )
            if fresh:
                self.saleor_token = fresh
        return self.saleor_token

    async def run(self) -> AsyncGenerator[dict, None]:
        """Run all tests and yield progress events."""

        yield {"type": "progress", "message": "Detecting Saleor version…"}
        version = await detect_saleor_version(self.saleor_url, self.saleor_token, self.timeout)
        self.saleor_version = version
        yield {"type": "version", "version": version}

        corpus_ver = resolve_corpus_version(version, settings.golden_corpus_version)
        self.corpus_version = corpus_ver
        self._scenario_context["run_slug"] = f"harness-scenario-{str(self.run_id)[:8]}"
        passed = failed = warnings = skipped = 0
        counts = {"pass": 0, "fail": 0, "warn": 0, "skip": 0}
        ver_warn = version_compatibility_warning(version, corpus_ver)
        if ver_warn:
            yield {"type": "schema_diff", "diff": {"version_warning": ver_warn}}

        from app.services.version_routing import version_hard_gate_check, detect_golden_staleness
        import os

        # Check if golden data may be stale
        staleness = detect_golden_staleness(version, corpus_ver)
        if staleness.get("stale") and staleness.get("warning"):
            yield {"type": "schema_diff", "diff": {"golden_staleness": staleness["warning"]}}

        allow_patch_drift = os.environ.get("ALLOW_PATCH_DRIFT", "").lower() in ("1", "true", "yes")
        gate = version_hard_gate_check(
            version, corpus_ver, allow_patch_drift=allow_patch_drift
        )
        if not gate["gate_pass"]:
            yield {
                "type": "schema_diff",
                "diff": {
                    "version_gate_fail": gate["reason"],
                    "version_gate_severity": gate["severity"],
                },
            }
            if gate["severity"] == "error" and not allow_patch_drift:
                yield {
                    "type": "complete",
                    "run_id": str(self.run_id),
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "warnings": 0,
                    "skipped": 0,
                    "status_counts": counts,
                    "test_mode": TEST_MODE_COMPATIBILITY,
                    "error": gate["reason"],
                }
                return

        certification_schema = load_reference_schema(corpus_ver)
        endpoints = build_golden_endpoints(corpus_ver)
        endpoints.extend(
            build_all_client_bundle_endpoints(
                recorded_only=True,
                schema_intro=certification_schema,
            )
        )
        scenario_fixtures = load_fixtures("dashboard", resolve_dashboard_bundle_version())
        endpoints.extend(
            build_scenario_endpoints(recorded_only=False, fixtures=scenario_fixtures)
        )
        endpoints.extend(build_variant_endpoints(recorded_only=False))
        endpoints.extend(
            build_dynamic_probe_endpoints(str(self.run_id), recorded_only=False)
        )

        defer_schema = self.use_introspection

        total = len(endpoints)
        yield {
            "type": "progress",
            "message": f"Running {total} endpoint{'s' if total != 1 else ''}…",
            "total": total,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as http_client:
            yield {"type": "progress", "message": "Validating staff authentication…"}
            force = bool(self.saleor_email and self.saleor_password)
            await self._ensure_valid_token(http_client, force_refresh=force)
            if not self.saleor_token and force:
                yield {
                    "type": "schema_diff",
                    "diff": {"introspection_error": "Staff authentication failed"},
                }
            yield {"type": "progress", "message": "Provisioning customer account…"}
            await self._ensure_auth_for_context(
                http_client, auth_context="customer", force_refresh=True
            )

            yield {"type": "progress", "message": "Resolving runtime fixtures…"}
            try:
                from app.services.fixture_resolver import (
                    resolve_fixtures,
                    resolve_dynamic_probe_support,
                )
                resolution = await resolve_fixtures(
                    self.saleor_url,
                    self.saleor_token,
                    timeout=self.timeout,
                    seed_profile=self.demo_seed_profile,
                )
                self._resolved_fixtures = resolution.fixtures
                self.demo_seed_profile = resolution.seed_profile
                if resolution.seeded_keys:
                    yield {
                        "type": "progress",
                        "message": (
                            "Created harness fixture data on target ("
                            + ", ".join(sorted(resolution.seeded_keys)[:4])
                            + ("…" if len(resolution.seeded_keys) > 4 else "")
                            + ")"
                        ),
                    }
                self._dynamic_support = await resolve_dynamic_probe_support(
                    self.saleor_url,
                    self.saleor_token,
                    timeout=self.timeout,
                )
                endpoints = self._attach_resolved_fixtures(endpoints)
            except Exception as exc:
                self._resolved_fixtures = scenario_fixtures
                self._dynamic_support = {}
                yield {
                    "type": "schema_diff",
                    "diff": {"fixture_resolver_error": str(exc)},
                }

            async def test_one(idx: int, endpoint: dict) -> dict:
                if self._stopped:
                    return {
                        "status": "skip",
                        "outcome": "skipped",
                        "expected": "Run stopped by user",
                        "response_valid": None,
                        "endpoint": endpoint["name"],
                        "kind": endpoint["kind"],
                        "category": endpoint["category"],
                        "is_public": endpoint["is_public"],
                        "skipped": True,
                    }
                return await self._test_endpoint(endpoint, idx, total, http_client)

            async def emit_result(result: dict) -> dict:
                nonlocal passed, failed, warnings, skipped
                status = result.get("status", "skip")
                if result.get("compatible"):
                    passed += 1
                    counts["pass"] += 1
                elif result.get("match_status") == "missing_golden":
                    failed += 1
                    counts["fail"] += 1
                elif status == "skip":
                    skipped += 1
                    counts["skip"] += 1
                else:
                    failed += 1
                    counts["fail"] += 1

                current = passed + failed + warnings + skipped
                return {
                    "type": "result",
                    "run_id": str(self.run_id),
                    "current": current,
                    "total": total,
                    "current_endpoint": result.get("endpoint", ""),
                    "status": status,
                    "endpoint_kind": result.get("kind", ""),
                    "category": result.get("category", ""),
                    "is_public": result.get("is_public", False),
                    "response_time_ms": result.get("response_time_ms"),
                    "error_message": result.get("error_message"),
                    "input_sent": result.get("input_sent"),
                    "actual_response": result.get("actual_response"),
                    "outcome": result.get("outcome"),
                    "expected": result.get("expected"),
                    "expected_response": result.get("expected_response"),
                    "match_status": result.get("match_status"),
                    "diff_summary": result.get("diff_summary"),
                    "client_parity_note": result.get("client_parity_note"),
                    "field_items": result.get("field_items"),
                    "compatible": result.get("compatible"),
                    "response_contract": result.get("response_contract"),
                    "response_valid": result.get("response_valid"),
                    "saleor_field_type": result.get("saleor_field_type"),
                    "actual_field_type": result.get("actual_field_type"),
                    "failure_category": result.get("failure_category"),
                    "status_counts": counts,
                }

            tier_buckets: dict[int, list[tuple[int, dict]]] = {0: [], 1: [], 2: [], 3: []}
            for idx, endpoint in enumerate(endpoints):
                from app.services.probe_tiers import classify_probe_tier
                tier = classify_probe_tier(endpoint)
                tier_buckets.setdefault(tier, []).append((idx, endpoint))

            for tier in (0, 1, 2, 3):
                items = tier_buckets.get(tier, [])
                if not items:
                    continue
                from app.services.probe_tiers import tier_concurrency, tier_label
                concurrency = tier_concurrency(tier)
                yield {
                    "type": "progress",
                    "message": (
                        f"Tier {tier} ({tier_label(tier)}): "
                        f"{len(items)} endpoints, concurrency={concurrency}"
                    ),
                }

                if concurrency <= 1 or len(items) == 1:
                    for idx, endpoint in items:
                        if self._stopped:
                            break
                        yield await emit_result(await test_one(idx, endpoint))
                else:
                    sem = asyncio.Semaphore(concurrency)

                    async def run_with_sem(idx: int, endpoint: dict) -> dict:
                        async with sem:
                            return await test_one(idx, endpoint)

                    tasks = [
                        asyncio.create_task(run_with_sem(idx, endpoint))
                        for idx, endpoint in items
                    ]
                    for fut in asyncio.as_completed(tasks):
                        if self._stopped:
                            for t in tasks:
                                if not t.done():
                                    t.cancel()
                            break
                        result = await fut
                        yield await emit_result(result)

        if defer_schema:
            yield {"type": "progress", "message": "Introspecting GraphQL schema (post-replay)…"}
            try:
                await self._ensure_valid_token(
                    force_refresh=bool(self.saleor_email and self.saleor_password),
                )
                intro = await introspect_saleor(
                    self.saleor_url, self.saleor_token, self.timeout
                )
                ref_schema = load_reference_schema(corpus_ver)
                diff = schema_gate_diff(intro, ref_schema, source="golden")
                all_bundles = []
                for source in CLIENT_SOURCES:
                    ver = (
                        resolve_storefront_bundle_version()
                        if source == "storefront"
                        else resolve_dashboard_bundle_version()
                    )
                    all_bundles.extend(
                        load_all_bundles_from_disk(source, ver, recorded_only=True)
                    )
                compatible, excluded = bundles_compatible_with_schema(all_bundles, intro)
                client_gate = compute_client_bundle_schema_gate(
                    compatible, intro, recorded_only=True
                )
                diff = merge_client_schema_into_diff(diff, client_gate)
                diff["excluded_l3_bundles"] = excluded
                diff["certification_endpoint_count"] = total
                diff["l3_dashboard_recorded"] = sum(
                    1 for b in all_bundles if b.source == "dashboard"
                )
                diff["l3_dashboard_certified"] = sum(
                    1 for b in compatible if b.source == "dashboard"
                )
                if excluded:
                    diff["not_counted_note"] = (
                        f"{len(excluded)} deprecated or schema-incompatible L3 bundle(s) "
                        "are excluded from compatibility scoring and certification."
                    )
                try:
                    full_intro = await introspect_full_schema(
                        self.saleor_url, self.saleor_token, self.timeout
                    )
                    doc_gate = compute_document_schema_gate(
                        compatible, full_intro, recorded_only=True
                    )
                    diff = merge_document_schema_into_diff(diff, doc_gate)
                except Exception:
                    pass
                yield {"type": "schema_diff", "diff": diff}
            except Exception as exc:
                yield {"type": "schema_diff", "diff": {"introspection_error": str(exc)}}

        yield {
            "type": "schema_diff",
            "diff": {"_run_meta": {"test_mode": TEST_MODE_COMPATIBILITY}},
        }
        yield {
            "type": "complete",
            "run_id": str(self.run_id),
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "skipped": skipped,
            "status_counts": counts,
            "test_mode": TEST_MODE_COMPATIBILITY,
        }

    def _storefront_fixture_overlay(self, resolved: dict[str, Any]) -> dict[str, Any]:
        """Map storefront L3 bundles to channel-pln while dashboard keeps USD."""
        fixtures = dict(resolved)
        if resolved.get("storefront_channel"):
            fixtures["default_channel"] = resolved["storefront_channel"]
        if resolved.get("storefront_channel_id"):
            fixtures["default_channel_id"] = resolved["storefront_channel_id"]
        return fixtures

    def _attach_resolved_fixtures(self, endpoints: list[dict]) -> list[dict]:
        """Substitute live-resolved fixture IDs into endpoint dicts.

        Replaces the static fixtures.json with the live-resolved fixture map
        for L3 bundles, scenarios, and dynamic probes. The resolver queried
        the target Saleor at run start, so entity IDs match the actual DB.
        """
        resolved = getattr(self, "_resolved_fixtures", None)
        if not resolved:
            return endpoints
        for ep in endpoints:
            if ep.get("bundle_fixtures") is not None:
                fixtures = dict(resolved)
                if ep.get("client_source") == "storefront":
                    fixtures = self._storefront_fixture_overlay(resolved)
                ep["bundle_fixtures"] = fixtures
            if ep.get("step_fixtures") is not None:
                ep["step_fixtures"] = dict(resolved)
        for ep in endpoints:
            if ep.get("kind") == DYNAMIC_PROBE_KIND:
                pt_id = (getattr(self, "_dynamic_support", {}) or {}).get("product_type_id")
                probe = ep.get("dynamic_probe")
                if probe and probe.requires_product_type and pt_id:
                    document = ep.get("bundle_document") or ep.get("golden_input", "")
                    if document and "{{product_type_id}}" in document:
                        document = document.replace("{{product_type_id}}", pt_id)
                        ep["bundle_document"] = document
                        ep["golden_input"] = document
                    variables = ep.get("bundle_variables") or {}
                    if variables and "input" in variables:
                        for k, v in list(variables["input"].items()):
                            if isinstance(v, str) and "{{product_type_id}}" in v:
                                variables["input"][k] = v.replace("{{product_type_id}}", pt_id)
                        ep["bundle_variables"] = variables
        return endpoints

    async def _test_endpoint(
        self,
        endpoint: dict,
        idx: int,
        total: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> dict:
        """Test a single endpoint."""
        name = endpoint["name"]
        kind = endpoint["kind"]
        category = endpoint["category"]
        is_public = endpoint["is_public"]

        auth_context = endpoint.get("auth_context", "staff")
        if kind == SCENARIO_KIND:
            auth_context = endpoint.get("auth_context", "staff")
            scenario_id = endpoint.get("scenario_id") or ""
            if scenario_id and scenario_id != self._last_scenario_id:
                run_slug = self._scenario_context.get("run_slug")
                self._scenario_context = {"run_slug": run_slug} if run_slug else {}
                self._last_scenario_id = scenario_id

        golden_input = endpoint.get("golden_input")
        bundle_document = endpoint.get("bundle_document")
        if kind in (SCENARIO_KIND, VARIANT_KIND, DYNAMIC_PROBE_KIND):
            if not golden_input:
                return {
                    "status": "skip",
                    "outcome": "skipped",
                    "expected": "Missing golden input for probe",
                    "response_valid": None,
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "match_status": "missing_golden",
                    "compatible": False,
                    "failure_category": "missing_golden",
                }
            query = golden_input
        elif kind == CLIENT_BUNDLE_KIND:
            if not bundle_document:
                return {
                    "status": "skip",
                    "outcome": "skipped",
                    "expected": "Missing L3 bundle document",
                    "response_valid": None,
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "match_status": "missing_golden",
                    "compatible": False,
                    "failure_category": "missing_golden",
                }
            query = bundle_document
        elif kind in ("QUERY", "MUTATION"):
            if not golden_input:
                return {
                    "status": "skip",
                    "outcome": "skipped",
                    "expected": "Missing golden input for L1 probe",
                    "response_valid": None,
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "match_status": "missing_golden",
                    "compatible": False,
                    "failure_category": "missing_golden",
                }
            query = golden_input
        else:
            query = golden_input or bundle_document or ""
        payload: dict[str, Any] = {"query": query}
        if bundle_document:
            payload["query"] = bundle_document
            variables = endpoint.get("bundle_variables") or {}
            fixtures = dict(endpoint.get("bundle_fixtures") or {})
            bundle_id = endpoint.get("bundle_id") or name
            from app.services.bundle_setup import apply_bundle_setup

            setup_overlay = await apply_bundle_setup(
                bundle_id=bundle_id,
                fixtures=fixtures,
                run_setup_mutation=lambda setup, auth: self._run_setup_mutation(
                    client=http_client, setup=setup, auth_context=auth
                ),
            )
            fixtures.update(setup_overlay)
            try:
                payload["variables"] = substitute_fixtures(variables, fixtures)
            except KeyError as e:
                payload["variables"] = variables
                return {
                    "status": "skip",
                    "outcome": "skipped",
                    "expected": f"Fixture key not resolved: {e}",
                    "response_valid": None,
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "failure_category": "data_prerequisite",
                    "error_message": f"Fixture substitution failed: {e}",
                }
        elif kind == VARIANT_KIND and endpoint.get("bundle_variables"):
            payload["variables"] = endpoint["bundle_variables"]
        elif kind == SCENARIO_KIND:
            payload["query"] = endpoint["golden_input"]
            raw_vars = endpoint.get("step_variables") or {}
            fixtures = dict(endpoint.get("step_fixtures") or {})
            await enrich_checkout_delivery_fixture(
                self.saleor_url,
                step_id=endpoint.get("step_id", ""),
                context=self._scenario_context,
                fixtures=fixtures,
                token=self.saleor_token,
                timeout=self.timeout,
            )
            payload["variables"] = substitute_scenario_variables(
                raw_vars, self._scenario_context, fixtures
            )

        # ── Mutation-first setup for L1 probes ───────────────────────────
        # For L1 success probes, create the required entity first, then
        # substitute the created ID into the query. This eliminates the
        # dependency on hardcoded Saleor demo data.
        created_entity_id: str | None = None
        if (
            kind in ("QUERY", "MUTATION")
            and not endpoint.get("bundle_document")
            and not endpoint.get("dynamic_probe")
        ):
            from app.services.probe_setup import get_setup_for_operation, needs_setup
            golden_contract_check = endpoint.get("golden_contract")
            if needs_setup(name, golden_contract_check):
                setup = get_setup_for_operation(name)
                if setup and setup.get("mutation"):
                    try:
                        created_entity_id = await self._run_setup_mutation(
                            client=http_client,
                            setup=setup,
                            auth_context=setup.get("auth", "staff"),
                        )
                        if created_entity_id:
                            # Substitute the created ID into the query
                            query = payload.get("query", "")
                            # Replace common ID patterns in the query
                            # The golden query may reference specific entity IDs
                            # that we replace with our dynamically created entity
                            payload["query"] = self._inject_created_id(
                                query, created_entity_id, name
                            )
                    except Exception:
                        # Setup failed — proceed without it (golden may still pass)
                        pass

        start = time.time()

        try:
            client = http_client or httpx.AsyncClient(timeout=self.timeout)
            own_client = http_client is None
            try:
                resp_json = {}
                resp_status = 500
                for attempt in range(3):
                    if (
                        auth_context != "anonymous"
                        or kind in (CLIENT_BUNDLE_KIND, SCENARIO_KIND, VARIANT_KIND)
                    ):
                        await self._ensure_auth_for_context(
                            client, auth_context=auth_context
                        )
                    headers = self._auth_headers(auth_context)
                    resp = await client.post(
                        self.saleor_url,
                        json=payload,
                        headers=headers,
                    )
                    resp_status = resp.status_code
                    resp_json = resp.json()
                    contract = classify_response_contract(resp_json, http_status=resp_status)
                    if contract != CONTRACT_AUTH_ERROR:
                        break
                    if attempt < 2:
                        from app.services.saleor_auth import validate_saleor_token

                        if auth_context == "customer":
                            cust = self._customer_token
                            if not cust or not await validate_saleor_token(
                                self.saleor_url, cust, self.timeout, client
                            ):
                                await self._ensure_auth_for_context(
                                    client, auth_context="customer", force_refresh=True
                                )
                        elif not await validate_saleor_token(
                            self.saleor_url, self.saleor_token, self.timeout, client
                        ):
                            await self._force_refresh_token()
                        await asyncio.sleep(0.25 * (attempt + 1))
                elapsed_ms = int((time.time() - start) * 1000)

                assertion_failures: list[str] = []
                if kind == SCENARIO_KIND:
                    for extract_key, json_path in (endpoint.get("step_extract") or {}).items():
                        from app.services.scenario_corpus import _extract_json_path
                        value = _extract_json_path(resp_json, json_path)
                        if value is not None:
                            self._scenario_context[extract_key] = value
                    assertion_failures = run_assertions(
                        resp_json,
                        endpoint.get("step_assertions") or [],
                        self._scenario_context,
                    )

                meta = classify_graphql_response(
                    resp_json,
                    http_status=resp_status,
                    endpoint_kind=kind,
                )
                comparison = compare_to_golden(
                    self.saleor_version,
                    name,
                    kind,
                    resp_json,
                    meta,
                    http_status=resp_status,
                    tier2_required=tier2_gate_enabled(self.tier2_required),
                    endpoint_meta=endpoint,
                )
                if assertion_failures:
                    comparison = type(comparison)(
                        match_status="assertion_fail",
                        expected_response=comparison.expected_response,
                        diff_summary="; ".join(assertion_failures),
                        recommended_status="fail",
                        golden_outcome=comparison.golden_outcome,
                        golden_contract=comparison.golden_contract,
                        actual_contract=comparison.actual_contract,
                        field_items=comparison.field_items,
                        resolved_corpus_version=comparison.resolved_corpus_version,
                        compatible=False,
                        client_parity_note=comparison.client_parity_note,
                    )
                elif kind == DYNAMIC_PROBE_KIND:
                    dynamic_probe = endpoint.get("dynamic_probe")
                    if dynamic_probe:
                        generated_values = endpoint.get("generated_values") or {}
                        dynamic_ok, dynamic_msg = compare_dynamic_response(
                            dynamic_probe, resp_json, generated_values
                        )
                        if not dynamic_ok:
                            comparison = type(comparison)(
                                match_status="mismatch",
                                expected_response=comparison.expected_response,
                                diff_summary=f"Dynamic probe failed: {dynamic_msg}",
                                recommended_status="fail",
                                golden_outcome=comparison.golden_outcome,
                                golden_contract=comparison.golden_contract,
                                actual_contract=comparison.actual_contract,
                                field_items=comparison.field_items,
                                resolved_corpus_version=comparison.resolved_corpus_version,
                                compatible=False,
                                client_parity_note=comparison.client_parity_note,
                            )
                        else:
                            comparison = type(comparison)(
                                match_status="match",
                                expected_response=comparison.expected_response,
                                diff_summary=f"Dynamic probe: {dynamic_msg}",
                                recommended_status="pass",
                                golden_outcome=comparison.golden_outcome,
                                golden_contract=comparison.golden_contract,
                                actual_contract=comparison.actual_contract,
                                field_items=comparison.field_items,
                                resolved_corpus_version=comparison.resolved_corpus_version,
                                compatible=True,
                                client_parity_note=comparison.client_parity_note,
                            )
                if comparison.compatible:
                    status = "pass"
                elif comparison.match_status == "missing_golden":
                    status = "fail"
                else:
                    status = "fail"
                contract = meta.get("response_contract") or comparison.actual_contract
                expected_label = (
                    f"Contract: {comparison.golden_contract or '?'} → {comparison.actual_contract or contract}"
                    if comparison.golden_contract
                    else meta["expected"]
                )

                binding_failures: list[str] = []
                if (
                    comparison.compatible
                    and comparison.actual_contract == "success"
                    and contract == "success"
                    and kind in (DYNAMIC_PROBE_KIND, "MUTATION", "QUERY", "CLIENT_BUNDLE")
                ):
                    from app.services.input_binding import check_input_bindings
                    op_name = endpoint.get("operation_name") or name
                    if op_name and "input" in (endpoint.get("bundle_variables") or {}):
                        binding_ok, binding_msgs = check_input_bindings(
                            response=resp_json,
                            variables=endpoint.get("bundle_variables") or {},
                            binding_rules=[],
                        )
                        if not binding_ok:
                            binding_failures = binding_msgs
                    elif op_name:
                        from app.services.input_binding import BINDING_RULES as _B
                        rules = _B.get(op_name, [])
                        if rules:
                            binding_ok, binding_msgs = check_input_bindings(
                                response=resp_json,
                                variables={"input": endpoint.get("golden_input") or ""},
                                binding_rules=rules,
                            )
                            if not binding_ok:
                                binding_failures = binding_msgs

                if binding_failures:
                    comparison = type(comparison)(
                        match_status="binding_fail",
                        expected_response=comparison.expected_response,
                        diff_summary="; ".join(binding_failures),
                        recommended_status="fail",
                        golden_outcome=comparison.golden_outcome,
                        golden_contract=comparison.golden_contract,
                        actual_contract=comparison.actual_contract,
                        field_items=comparison.field_items,
                        resolved_corpus_version=comparison.resolved_corpus_version,
                        compatible=False,
                        client_parity_note=comparison.client_parity_note,
                    )
                    status = "fail"

                failure_category = _classify_failure_category(
                    comparison=comparison,
                    kind=kind,
                    endpoint_name=name,
                    meta=meta,
                    assertion_failures=assertion_failures,
                    endpoint=endpoint,
                    demo_seed_profile=self.demo_seed_profile,
                )
                return {
                    "status": status,
                    "outcome": comparison.actual_contract or meta.get("response_contract") or meta["outcome"],
                    "expected": expected_label,
                    "expected_response": comparison.expected_response,
                    "match_status": comparison.match_status,
                    "diff_summary": comparison.diff_summary,
                    "client_parity_note": comparison.client_parity_note,
                    "field_items": comparison.field_items,
                    "compatible": comparison.compatible,
                    "response_contract": contract,
                    "response_valid": meta["response_valid"],
                    "endpoint": name,
                    "kind": kind,
                    "category": category,
                    "is_public": is_public,
                    "response_time_ms": elapsed_ms,
                    "error_message": meta.get("error_message"),
                    "input_sent": json.dumps(payload) if (
                        endpoint.get("bundle_document") or kind == SCENARIO_KIND
                    ) else query,
                    "actual_response": json.dumps(resp_json),
                    "failure_category": failure_category,
                }
            finally:
                if own_client:
                    await client.aclose()

        except httpx.TimeoutException:
            elapsed_ms = int((time.time() - start) * 1000)
            meta = classify_transport_error(
                kind="timeout",
                message=f"Timeout after {self.timeout}s",
            )
            return _result_from_meta(meta, name, kind, category, is_public, elapsed_ms, query)
        except httpx.HTTPStatusError as e:
            elapsed_ms = int((time.time() - start) * 1000)
            meta = classify_transport_error(
                kind="http",
                message=f"HTTP {e.response.status_code}",
            )
            return _result_from_meta(
                meta, name, kind, category, is_public, elapsed_ms, query,
                actual_response=e.response.text[:500],
            )
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            meta = classify_transport_error(kind="error", message=str(e))
            return _result_from_meta(meta, name, kind, category, is_public, elapsed_ms, query)

    async def _run_setup_mutation(
        self,
        client: httpx.AsyncClient | None,
        setup: dict[str, Any],
        auth_context: str = "staff",
    ) -> str | None:
        """Execute a setup mutation and return the created entity's Relay ID.

        Returns None if the mutation fails or returns no ID.
        """
        mutation = setup["mutation"]
        variables_fn = setup["variables"]
        variables = variables_fn() if callable(variables_fn) else variables_fn
        extract_path = setup.get("extract")

        # Resolve product_type_id placeholder if needed
        if self._resolved_fixtures:
            pt_id = self._resolved_fixtures.get("default_product_type_id") or (
                getattr(self, "_dynamic_support", {}) or {}
            ).get("product_type_id")
            if pt_id:
                # Replace in mutation text
                mutation = mutation.replace("{{product_type_id}}", pt_id)
                # Replace in variables
                for key, val in variables.get("input", {}).items():
                    if isinstance(val, str) and "{{product_type_id}}" in val:
                        variables["input"][key] = val.replace("{{product_type_id}}", pt_id)

        payload = {"query": mutation, "variables": variables}
        use_client = client or httpx.AsyncClient(timeout=self.timeout)
        own_client = client is None
        try:
            await self._ensure_valid_token(use_client, force_refresh=False)
            headers = self._auth_headers(auth_context)
            resp = await use_client.post(self.saleor_url, json=payload, headers=headers)
            resp_json = resp.json()

            # Check for errors
            if resp_json.get("errors"):
                return None

            # Extract entity ID from response
            if extract_path:
                from app.services.scenario_corpus import _extract_json_path
                entity_id = _extract_json_path(resp_json, extract_path)
                if entity_id:
                    return str(entity_id)
            return None
        except Exception:
            return None
        finally:
            if own_client:
                await use_client.aclose()

    def _inject_created_id(
        self,
        query: str,
        entity_id: str,
        operation_name: str,
    ) -> str:
        """Inject a dynamically created entity ID into a golden query.

        The golden query may contain hardcoded Saleor demo IDs. This method
        replaces common ID patterns with the dynamically created entity ID.
        """
        import base64
        import re

        # Map operation name → Relay entity type prefix
        _ENTITY_TYPES = {
            "product": "Product",
            "products": "Product",
            "productType": "ProductType",
            "productTypes": "ProductType",
            "category": "Category",
            "categories": "Category",
            "collection": "Collection",
            "collections": "Collection",
            "channel": "Channel",
            "channels": "Channel",
            "attribute": "Attribute",
            "attributes": "Attribute",
            "page": "Page",
            "pages": "Page",
            "shippingZone": "ShippingZone",
            "shippingZones": "ShippingZone",
            "warehouse": "Warehouse",
            "warehouses": "Warehouse",
            "staffUser": "User",
            "staffUsers": "User",
            "customer": "User",
            "customers": "User",
            "user": "User",
            "users": "User",
            "giftCard": "GiftCard",
            "giftCards": "GiftCard",
            "menu": "Menu",
            "menus": "Menu",
            "voucher": "Voucher",
            "vouchers": "Voucher",
            "draftOrder": "Order",
            "draftOrders": "Order",
            "order": "Order",
            "orders": "Order",
            "permissionGroup": "Group",
            "permissionGroups": "Group",
            "webhook": "Webhook",
            "webhooks": "Webhook",
            "taxClass": "TaxClass",
            "taxClasses": "TaxClass",
        }

        entity_type = _ENTITY_TYPES.get(operation_name, "Product")

        # Encode the entity ID as a Relay global ID if it's a plain UUID or numeric ID
        if entity_id.isdigit():
            relay_id = base64.b64encode(f"{entity_type}:{entity_id}".encode()).decode()
        elif re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", entity_id, re.I):
            relay_id = base64.b64encode(f"{entity_type}:{entity_id}".encode()).decode()
        else:
            relay_id = entity_id

        # Replace the null UUID placeholder (used in L1 probes for not-found queries)
        # with the created entity ID for success probes
        null_uuid = "00000000-0000-0000-0000-000000000000"
        null_gid = base64.b64encode(f"{entity_type}:{null_uuid}".encode()).decode()

        # Only replace if the query uses the null UUID (indicating a not-found probe)
        # Don't replace if the query has a specific real ID
        if null_uuid in query:
            query = query.replace(null_uuid, entity_id)
        if null_gid in query:
            query = query.replace(null_gid, relay_id)

        return query


def _result_from_meta(
    meta: dict,
    name: str,
    kind: str,
    category: str,
    is_public: bool,
    elapsed_ms: int,
    query: str,
    actual_response: str | None = None,
) -> dict:
    return {
        "status": meta["status"],
        "outcome": meta["outcome"],
        "expected": meta["expected"],
        "response_valid": meta["response_valid"],
        "endpoint": name,
        "kind": kind,
        "category": category,
        "is_public": is_public,
        "response_time_ms": elapsed_ms,
        "error_message": meta.get("error_message"),
        "input_sent": query,
        "actual_response": actual_response,
    }


def _client_bundle_setup_prerequisite(
    endpoint_name: str,
    comparison: Any,
    match_status: str,
) -> bool:
    """Detect runner setup/session gaps (not API parity bugs)."""
    diff = (comparison.diff_summary or "").lower()
    raw_diff = comparison.diff_summary or ""

    if endpoint_name.startswith("sf-checkout") and "checkout access denied" in diff:
        return True

    if endpoint_name in ("sf-me", "sf-accountupdate", "sf-accountaddresscreate"):
        if "account not found" in diff:
            return True

    if match_status == "shape_drift":
        if 'edges: []' in raw_diff or '"edges": []' in raw_diff or "edges=[]" in raw_diff:
            return True
        if "null" in diff and any(
            token in diff for token in ("categories", "collections", "search", "product")
        ):
            return True

    if endpoint_name.startswith("sf-checkout") and match_status in ("mismatch", "shape_drift"):
        if "access denied" in diff or "checkout" in diff and "not found" in diff:
            return True

    return False


def _classify_failure_category(
    *,
    comparison: Any,
    kind: str,
    endpoint_name: str,
    meta: dict[str, Any],
    assertion_failures: list[str],
    endpoint: dict[str, Any] | None = None,
    demo_seed_profile: str = "saleor_demo",
) -> str:
    """Classify the failure category for structured reporting.

    Scans the actual GraphQL document (not the bundle_id string) for
    deprecated types. Seed-tagged L3 bundles that shape_drift against
    populatedb golden are seed_prerequisite, not real_bug.
    """
    from app.services.deprecated_scanner import (
        scan_document_for_deprecated_types,
        scan_l1_probe_for_deprecated,
    )
    from app.services.seed_tags import resolve_seed_tags

    if comparison.compatible:
        return "compatible"

    match_status = comparison.match_status or ""

    if match_status == "missing_golden":
        return "missing_golden"

    if match_status == "binding_fail":
        return "static_response_suspected"

    if assertion_failures:
        return "assertion_fail"

    if match_status == "tier2_fail":
        return "parity_gap"

    endpoint = endpoint or {}
    document_to_check = (
        endpoint.get("bundle_document")
        or endpoint.get("golden_input")
        or ""
    )

    if kind in ("CLIENT_BUNDLE", "DYNAMIC_PROBE"):
        deprecated_in_doc = scan_document_for_deprecated_types(document_to_check)
        if deprecated_in_doc:
            return "deprecated_excluded"
    elif kind in ("QUERY", "MUTATION"):
        is_dep, _types = scan_l1_probe_for_deprecated(document_to_check)
        if is_dep:
            return "deprecated_excluded"

    if match_status in ("mismatch", "shape_drift"):
        if kind in ("VARIANT_PROBE", "SCENARIO_KIND", "SCENARIO_STEP"):
            is_data_prereq = (
                comparison.actual_contract in ("not_found", "graphql_error")
                and "not found" in (comparison.diff_summary or "").lower()
            )
            if is_data_prereq:
                return "data_prerequisite"
        if kind == "CLIENT_BUNDLE":
            seed_tags = resolve_seed_tags(endpoint_name, endpoint)
            if seed_tags and match_status in ("shape_drift", "mismatch"):
                return "seed_prerequisite"
            if _client_bundle_setup_prerequisite(endpoint_name, comparison, match_status):
                return "data_prerequisite"

        # Distinguish schema mismatch (structural) from data drift (data differs)
        diff_summary = (comparison.diff_summary or "").lower()
        if match_status == "shape_drift":
            # shape_drift means normalized shape differs — check if it's structural
            if "schema" in diff_summary or "structural" in diff_summary:
                return "schema_mismatch"
            # Check if the diff summary mentions type mismatches (structural)
            if "type_mismatch" in diff_summary or "missing" in diff_summary:
                return "schema_mismatch"
            # Otherwise it's likely data drift (values differ but types match)
            return "data_drift"
        return "real_bug"

    return "real_bug"
