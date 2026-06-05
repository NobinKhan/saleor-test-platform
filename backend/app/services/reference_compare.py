"""
Compare live probe responses against golden reference records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.field_compare import compare_response_fields
from app.services.reference_corpus import GoldenProbe, load_probe_from_disk, response_shape_hash
from app.services.response_contract import (
    classify_response_contract,
    contract_family,
    contract_to_legacy_outcome,
    contract_to_status,
    infer_probe_stability,
)
from app.services.response_normalize import normalize_response


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


def _normalized_hash(resp: dict[str, Any]) -> str:
    return response_shape_hash(normalize_response(resp))


def _resolve_golden_contract(golden: GoldenProbe) -> str:
    if golden.golden_contract:
        return golden.golden_contract
    return classify_response_contract(
        golden.golden_response,
        http_status=golden.http_status or 200,
    )


def compare_to_golden(
    saleor_version: str | None,
    endpoint_name: str,
    endpoint_kind: str,
    actual_response_json: dict[str, Any],
    classified: dict[str, Any],
    *,
    http_status: int = 200,
    baseline_version: str | None = None,
) -> ComparisonResult:
    from app.services.reference_corpus import resolve_corpus_version

    baseline = baseline_version or settings.golden_corpus_version
    corpus_version = resolve_corpus_version(saleor_version, baseline)
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

    expected_str = json.dumps(golden.golden_response, indent=2)
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
            resolved_corpus_version=corpus_version,
            compatible=False,
        )

    strict_contract_note = None
    if golden_contract != actual_contract:
        strict_contract_note = f"Contract detail: golden {golden_contract}, actual {actual_contract}"

    if golden_family == "rejection":
        return ComparisonResult(
            match_status="match",
            expected_response=expected_str,
            diff_summary=strict_contract_note,
            recommended_status="pass",
            golden_outcome=contract_to_legacy_outcome(golden_contract),
            golden_contract=golden_contract,
            actual_contract=actual_contract,
            resolved_corpus_version=corpus_version,
            compatible=True,
        )

    norm_golden = normalize_response(golden.golden_response)
    norm_actual = normalize_response(actual_response_json)
    golden_hash = golden.response_shape_hash or _normalized_hash(golden.golden_response)
    actual_hash = _normalized_hash(actual_response_json)

    if golden_hash.replace("sha256:", "") != actual_hash.replace("sha256:", ""):
        field_items = compare_response_fields(norm_golden, norm_actual)
        mismatches = [i for i in field_items if i["item_status"] != "match"]
        stability = golden.probe_stability or infer_probe_stability(golden_contract, endpoint_kind)
        if mismatches and stability == "stateful":
            return ComparisonResult(
                match_status="match",
                expected_response=expected_str,
                diff_summary=f"Stateful probe shape differs ({len(mismatches)} paths) — DB state may differ",
                recommended_status="pass",
                golden_outcome=golden.golden_outcome,
                golden_contract=golden_contract,
                actual_contract=actual_contract,
                field_items=field_items,
                resolved_corpus_version=corpus_version,
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
                resolved_corpus_version=corpus_version,
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
        resolved_corpus_version=corpus_version,
        compatible=True,
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

    contract = classify_response_contract(resp_json, http_status=http_status)
    stability = infer_probe_stability(contract, endpoint["kind"])

    return GoldenProbe(
        endpoint_name=endpoint["name"],
        endpoint_kind=endpoint["kind"],
        category=endpoint.get("category", "unknown"),
        input_sent=query,
        golden_response=resp_json,
        golden_outcome=contract_to_legacy_outcome(contract),
        golden_status="pass" if contract == "success" else "warn",
        error_pattern=None,
        response_shape_hash=_normalized_hash(resp_json),
        golden_contract=contract,
        http_status=http_status,
        probe_stability=stability,
    )
