"""
Compare live probe responses against golden reference records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.client_bundles import (
    CLIENT_BUNDLE_KIND,
    CLIENT_SOURCES,
    load_bundle_from_disk,
    resolve_dashboard_bundle_version,
    resolve_storefront_bundle_version,
)
from app.services.scenario_corpus import SCENARIO_KIND
from app.services.variant_corpus import VARIANT_KIND
from app.services.field_compare import compare_response_fields
from app.services.reference_corpus import GoldenProbe, load_probe_from_disk, resolve_corpus_version, response_shape_hash
from app.services.response_contract import (
    classify_response_contract,
    contract_family,
    contract_to_legacy_outcome,
    contract_to_status,
    infer_probe_stability,
)
from app.services.response_normalize import normalize_response, sanitize_for_sgrc
from app.services.semantic_compare import compare_semantic_error, is_error_contract


def tier2_gate_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    return settings.sgrc_tier2_gate


L3_VOLATILE_PATH_FRAGMENTS = (
    ".edges",
    ".edges[",
    ".pricing",
    ".amount",
    ".currency",
    ".name",
    ".slug",
    "__typename",
)


def _connection_volatile_drift(mismatches: list[dict[str, str | None]]) -> bool:
    """True when all field mismatches are in DB-volatile list/connection paths."""
    if not mismatches:
        return False
    for item in mismatches:
        key = item.get("item_key") or ""
        if item.get("item_status") == "type_mismatch":
            return False
        if not any(frag in key for frag in L3_VOLATILE_PATH_FRAGMENTS):
            return False
    return True


@dataclass
class ComparisonResult:
    match_status: str
    expected_response: str | None
    diff_summary: str | None
    recommended_status: str
    golden_outcome: str | None = None
    golden_contract: str | None = None
    actual_contract: str | None = None
    field_items: list[dict[str, str | None]] | None = None
    resolved_corpus_version: str | None = None
    compatible: bool = False
    client_parity_note: str | None = None


def _normalized_hash(resp: dict[str, Any]) -> str:
    return response_shape_hash(normalize_response(resp))


def _resolve_golden_contract(golden: GoldenProbe) -> str:
    if golden.golden_contract:
        return golden.golden_contract
    return classify_response_contract(
        golden.golden_response,
        http_status=golden.http_status or 200,
    )


def compare_probe_to_actual(
    golden: GoldenProbe,
    actual_response_json: dict[str, Any],
    *,
    http_status: int = 200,
    resolved_corpus_version: str | None = None,
    tier2_required: bool | None = None,
    input_sent: str | None = None,
) -> ComparisonResult:
    endpoint_name = golden.endpoint_name
    endpoint_kind = golden.endpoint_kind
    query_input = input_sent or golden.input_sent
    gate_on = tier2_gate_enabled(tier2_required)

    expected_str = json.dumps(sanitize_for_sgrc(golden.golden_response), indent=2)
    golden_contract = _resolve_golden_contract(golden)
    actual_contract = classify_response_contract(actual_response_json, http_status=http_status)

    golden_family = contract_family(golden_contract)
    actual_family = contract_family(actual_contract)

    if golden_family != actual_family:
        return ComparisonResult(
            match_status="mismatch",
            expected_response=expected_str,
            diff_summary=(
                f"Expected family {golden_family} ({golden_contract}), "
                f"got {actual_family} ({actual_contract})"
            ),
            recommended_status="fail",
            golden_outcome=golden.golden_outcome,
            golden_contract=golden_contract,
            actual_contract=actual_contract,
            resolved_corpus_version=resolved_corpus_version,
            compatible=False,
        )

    strict_contract_note = None
    if golden_contract != actual_contract:
        strict_contract_note = f"Contract detail: golden {golden_contract}, actual {actual_contract}"

    if is_error_contract(golden_contract):
        semantic_profile = getattr(golden, "semantic_profile", None) or {}
        stability = golden.probe_stability or infer_probe_stability(golden_contract, endpoint_kind)
        semantic_profile_with_stability = dict(semantic_profile)
        semantic_profile_with_stability["probe_stability"] = stability
        semantic = compare_semantic_error(
            golden.golden_response,
            actual_response_json,
            golden_contract=golden_contract,
            endpoint_name=endpoint_name,
            endpoint_kind=endpoint_kind,
            input_sent=query_input,
            semantic_profile=semantic_profile_with_stability,
            tier2_required=gate_on,
        )
        if not semantic.tier1_match:
            return ComparisonResult(
                match_status="mismatch",
                expected_response=expected_str,
                diff_summary=semantic.diff_summary or "SGRC Tier 1 semantic mismatch",
                recommended_status="fail",
                golden_outcome=golden.golden_outcome,
                golden_contract=golden_contract,
                actual_contract=actual_contract,
                resolved_corpus_version=resolved_corpus_version,
                compatible=False,
            )
        parity_note = "; ".join(semantic.client_parity_notes) if semantic.client_parity_notes else None
        diff_parts = [p for p in (strict_contract_note, parity_note) if p]
        if gate_on and not semantic.tier2_match:
            return ComparisonResult(
                match_status="tier2_fail",
                expected_response=expected_str,
                diff_summary="; ".join(diff_parts) if diff_parts else "SGRC Tier 2 parity failure",
                recommended_status="fail",
                golden_outcome=golden.golden_outcome,
                golden_contract=golden_contract,
                actual_contract=actual_contract,
                resolved_corpus_version=resolved_corpus_version,
                compatible=False,
                client_parity_note=parity_note,
            )
        match_status = "parity_gap" if parity_note else "match"
        return ComparisonResult(
            match_status=match_status,
            expected_response=expected_str,
            diff_summary="; ".join(diff_parts) if diff_parts else None,
            recommended_status="pass",
            golden_outcome=contract_to_legacy_outcome(golden_contract),
            golden_contract=golden_contract,
            actual_contract=actual_contract,
            resolved_corpus_version=resolved_corpus_version,
            compatible=True,
            client_parity_note=parity_note,
        )

    norm_golden = normalize_response(golden.golden_response)
    norm_actual = normalize_response(actual_response_json)
    golden_hash = golden.response_shape_hash or _normalized_hash(golden.golden_response)
    actual_hash = _normalized_hash(actual_response_json)

    if golden_hash.replace("sha256:", "") != actual_hash.replace("sha256:", ""):
        field_items = compare_response_fields(norm_golden, norm_actual)
        mismatches = [i for i in field_items if i["item_status"] != "match"]
        stability = golden.probe_stability or infer_probe_stability(golden_contract, endpoint_kind)

        is_client_bundle = endpoint_kind == CLIENT_BUNDLE_KIND
        is_error_probe = is_error_contract(golden_contract)

        if is_error_probe:
            allow_stateful_drift = False
        elif is_client_bundle and not is_error_probe and _connection_volatile_drift(mismatches):
            allow_stateful_drift = True
        elif stability == "stateful" and mismatches and _connection_volatile_drift(mismatches):
            allow_stateful_drift = True
        elif is_client_bundle:
            allow_stateful_drift = False
        elif stability == "stateful" and not mismatches:
            allow_stateful_drift = True
        elif stability == "stateful" and mismatches:
            allow_stateful_drift = False
        else:
            allow_stateful_drift = False

        if mismatches and allow_stateful_drift:
            return ComparisonResult(
                match_status="match",
                expected_response=expected_str,
                diff_summary=f"Stateful probe shape differs ({len(mismatches)} paths) — DB state may differ",
                recommended_status="pass",
                golden_outcome=golden.golden_outcome,
                golden_contract=golden_contract,
                actual_contract=actual_contract,
                field_items=field_items,
                resolved_corpus_version=resolved_corpus_version,
                compatible=True,
            )
        if mismatches:
            return ComparisonResult(
                match_status="shape_drift",
                expected_response=expected_str,
                diff_summary=f"Normalized shape differs ({len(mismatches)} field paths)",
                recommended_status="fail",
                golden_outcome=golden.golden_outcome,
                golden_contract=golden_contract,
                actual_contract=actual_contract,
                field_items=field_items,
                resolved_corpus_version=resolved_corpus_version,
                compatible=False,
            )

    field_items = compare_response_fields(norm_golden, norm_actual)
    return ComparisonResult(
        match_status="match",
        expected_response=expected_str,
        diff_summary=None,
        recommended_status=contract_to_status(actual_contract, compatible=True),
        golden_outcome=contract_to_legacy_outcome(golden_contract),
        golden_contract=golden_contract,
        actual_contract=actual_contract,
        field_items=field_items,
        resolved_corpus_version=resolved_corpus_version,
        compatible=True,
    )


def _load_client_bundle_golden(endpoint_name: str):
    for source in CLIENT_SOURCES:
        ver = (
            resolve_storefront_bundle_version()
            if source == "storefront"
            else resolve_dashboard_bundle_version()
        )
        bundle = load_bundle_from_disk(source, ver, endpoint_name)
        if bundle is not None and bundle.has_golden():
            return bundle, ver
    return None, None


def compare_to_golden(
    saleor_version: str | None,
    endpoint_name: str,
    endpoint_kind: str,
    actual_response_json: dict[str, Any],
    classified: dict[str, Any],
    *,
    http_status: int = 200,
    baseline_version: str | None = None,
    tier2_required: bool | None = None,
    endpoint_meta: dict[str, Any] | None = None,
) -> ComparisonResult:
    baseline = baseline_version or settings.golden_corpus_version
    corpus_version = resolve_corpus_version(saleor_version, baseline)
    meta = endpoint_meta or {}

    if endpoint_kind in (VARIANT_KIND, SCENARIO_KIND):
        golden_response = meta.get("golden_response")
        if golden_response is None:
            return ComparisonResult(
                match_status="missing_golden",
                expected_response=None,
                diff_summary=f"No golden reference recorded for this {endpoint_kind}",
                recommended_status="warn",
                golden_outcome=None,
                resolved_corpus_version=corpus_version,
                compatible=False,
            )
        inline = GoldenProbe(
            endpoint_name=endpoint_name,
            endpoint_kind=endpoint_kind,
            category=meta.get("category", "unknown"),
            input_sent=meta.get("golden_input") or "",
            golden_response=golden_response,
            golden_outcome=meta.get("golden_outcome") or "unknown",
            golden_status=meta.get("golden_status") or "warn",
            golden_contract=meta.get("golden_contract"),
            semantic_profile=meta.get("semantic_profile"),
            probe_stability="stateful" if endpoint_kind == SCENARIO_KIND else "stateless",
        )
        return compare_probe_to_actual(
            inline,
            actual_response_json,
            http_status=http_status,
            resolved_corpus_version=corpus_version,
            tier2_required=tier2_required,
            input_sent=inline.input_sent,
        )

    if endpoint_kind == CLIENT_BUNDLE_KIND:
        bundle, ver = _load_client_bundle_golden(endpoint_name)
        if bundle is None:
            return ComparisonResult(
                match_status="missing_golden",
                expected_response=None,
                diff_summary="No golden reference recorded for this client bundle",
                recommended_status="warn",
                golden_outcome=None,
                resolved_corpus_version=resolve_dashboard_bundle_version(),
                compatible=False,
            )
        return compare_probe_to_actual(
            bundle.to_golden_probe(),
            actual_response_json,
            http_status=http_status,
            resolved_corpus_version=ver,
            tier2_required=tier2_required,
            input_sent=bundle.document,
        )

    golden = load_probe_from_disk(corpus_version, endpoint_name, endpoint_kind)
    if golden is None:
        return ComparisonResult(
            match_status="missing_golden",
            expected_response=None,
            diff_summary="No golden reference recorded for this endpoint",
            recommended_status="warn",
            golden_outcome=None,
            resolved_corpus_version=corpus_version,
            compatible=False,
        )

    return compare_probe_to_actual(
        golden,
        actual_response_json,
        http_status=http_status,
        resolved_corpus_version=corpus_version,
        tier2_required=tier2_required,
    )


def probe_from_capture(
    endpoint: dict[str, Any],
    query: str,
    resp_json: dict[str, Any],
    classified: dict[str, Any],
    *,
    http_status: int = 200,
) -> GoldenProbe:
    from app.services.reference_corpus import GoldenProbe
    from app.services.semantic_compare import build_semantic_profile

    contract = classify_response_contract(resp_json, http_status=http_status)
    stability = infer_probe_stability(contract, endpoint["kind"])

    semantic_profile = build_semantic_profile(
        golden_response=resp_json,
        golden_contract=contract,
        input_sent=query,
        endpoint_name=endpoint["name"],
    )

    sanitized = sanitize_for_sgrc(resp_json)

    return GoldenProbe(
        endpoint_name=endpoint["name"],
        endpoint_kind=endpoint["kind"],
        category=endpoint.get("category", "unknown"),
        input_sent=query,
        golden_response=sanitized,
        golden_outcome=contract_to_legacy_outcome(contract),
        golden_status="pass" if contract == "success" else "warn",
        error_pattern=None,
        response_shape_hash=_normalized_hash(sanitized),
        golden_contract=contract,
        http_status=http_status,
        probe_stability=stability,
        semantic_profile=semantic_profile,
    )
