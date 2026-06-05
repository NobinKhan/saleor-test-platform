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
from app.services.response_normalize import normalize_response


@dataclass
class ComparisonResult:
    match_status: str
    expected_response: str | None
    diff_summary: str | None
    recommended_status: str
    golden_outcome: str | None = None
    field_items: list[dict[str, str | None]] | None = None
    resolved_corpus_version: str | None = None


def _first_error_message(resp: dict[str, Any]) -> str | None:
    errors = resp.get("errors") or []
    if not errors:
        return None
    return errors[0].get("message")


def _has_data(resp: dict[str, Any]) -> bool:
    data = resp.get("data")
    return data is not None and data != {}


def _has_errors(resp: dict[str, Any]) -> bool:
    return bool(resp.get("errors"))


def _normalized_hash(resp: dict[str, Any]) -> str:
    return response_shape_hash(normalize_response(resp))


def compare_to_golden(
    saleor_version: str | None,
    endpoint_name: str,
    endpoint_kind: str,
    actual_response_json: dict[str, Any],
    classified: dict[str, Any],
    *,
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
            recommended_status=classified.get("status", "warn"),
            golden_outcome=None,
            resolved_corpus_version=corpus_version,
        )

    expected_str = json.dumps(golden.golden_response, indent=2)
    actual_outcome = classified.get("outcome", "")
    golden_outcome = golden.golden_outcome

    norm_golden = normalize_response(golden.golden_response)
    norm_actual = normalize_response(actual_response_json)

    if actual_outcome != golden_outcome:
        return ComparisonResult(
            match_status="mismatch",
            expected_response=expected_str,
            diff_summary=f"Expected outcome {golden_outcome}, got {actual_outcome}",
            recommended_status=_status_from_golden_mismatch(golden.golden_status),
            golden_outcome=golden_outcome,
            resolved_corpus_version=corpus_version,
        )

    golden_has_err = _has_errors(norm_golden)
    actual_has_err = _has_errors(norm_actual)
    golden_has_data = _has_data(norm_golden)
    actual_has_data = _has_data(norm_actual)

    if golden_has_err != actual_has_err or golden_has_data != actual_has_data:
        return ComparisonResult(
            match_status="mismatch",
            expected_response=expected_str,
            diff_summary=(
                f"Response shape differs "
                f"(golden errors={golden_has_err} data={golden_has_data}, "
                f"actual errors={actual_has_err} data={actual_has_data})"
            ),
            recommended_status=_status_from_golden_mismatch(golden.golden_status),
            golden_outcome=golden_outcome,
            resolved_corpus_version=corpus_version,
        )

    golden_hash = golden.response_shape_hash or _normalized_hash(golden.golden_response)
    actual_hash = _normalized_hash(actual_response_json)
    if golden_hash.replace("sha256:", "") != actual_hash.replace("sha256:", ""):
        # Recompute golden with normalized hash for legacy corpora
        if _normalized_hash(golden.golden_response) != actual_hash:
            field_items = compare_response_fields(norm_golden, norm_actual)
            mismatches = [i for i in field_items if i["item_status"] != "match"]
            return ComparisonResult(
                match_status="shape_drift",
                expected_response=expected_str,
                diff_summary=(
                    f"Normalized response shape differs"
                    + (f" ({len(mismatches)} field paths)" if mismatches else "")
                ),
                recommended_status="warn",
                golden_outcome=golden_outcome,
                field_items=field_items,
                resolved_corpus_version=corpus_version,
            )

    field_items = compare_response_fields(norm_golden, norm_actual)
    field_mismatches = [i for i in field_items if i["item_status"] != "match"]
    diff = None
    if field_mismatches:
        diff = f"{len(field_mismatches)} normalized field path(s) differ"

    return ComparisonResult(
        match_status="match",
        expected_response=expected_str,
        diff_summary=diff,
        recommended_status=golden.golden_status,
        golden_outcome=golden_outcome,
        field_items=field_items,
        resolved_corpus_version=corpus_version,
    )


def _status_from_golden_mismatch(golden_status: str) -> str:
    if golden_status == "pass":
        return "fail"
    return "warn"


def probe_from_capture(
    endpoint: dict[str, Any],
    query: str,
    resp_json: dict[str, Any],
    classified: dict[str, Any],
) -> GoldenProbe:
    from app.services.reference_corpus import GoldenProbe

    return GoldenProbe(
        endpoint_name=endpoint["name"],
        endpoint_kind=endpoint["kind"],
        category=endpoint.get("category", "unknown"),
        input_sent=query,
        golden_response=resp_json,
        golden_outcome=classified["outcome"],
        golden_status=classified["status"],
        error_pattern=None,
        response_shape_hash=_normalized_hash(resp_json),
    )
