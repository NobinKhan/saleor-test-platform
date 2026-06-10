"""
Build LLM-friendly compatibility reports (Markdown + structured JSON).
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.models import TestRun, TestResult
from app.services.reference_corpus import load_manifest, resolve_corpus_version
from app.services.reference_registry import get_upgrade_hint
from app.services.client_bundles import client_bundle_count
from app.services.run_scope import FULL_SYSTEM_SCOPE
from app.services.reference_compare import tier2_gate_enabled
from app.services.schema_gate import compute_certified, compute_schema_gate
from app.services.response_contract import CONTRACT_SUCCESS

BODY_CAP = 4096


def _truncate(text: str | None, cap: int = BODY_CAP) -> str:
    if not text:
        return ""
    if len(text) <= cap:
        return text
    return text[: cap - 20] + "\n… [truncated]"


def _golden_context(run: TestRun) -> dict[str, Any]:
    target = run.saleor_version or "unknown"
    resolved = resolve_corpus_version(target, settings.golden_corpus_version)
    manifest = load_manifest(resolved) or {}
    diff = run.schema_diff or {}
    return {
        "target_version": target,
        "target_url": run.saleor_url,
        "test_scope": run.test_scope or FULL_SYSTEM_SCOPE,
        "golden_corpus_version": resolved,
        "golden_saleor_url": manifest.get("saleor_url", settings.reference_saleor_url),
        "golden_probe_count": manifest.get("probe_count", 0),
        "l3_dashboard_certified": client_bundle_count(source="dashboard"),
        "l3_storefront_certified": client_bundle_count(source="storefront"),
        "certification_endpoint_count": diff.get("certification_endpoint_count") or run.total_tests,
        "excluded_l3_bundles": diff.get("excluded_l3_bundles") or [],
        "not_counted_note": diff.get("not_counted_note"),
        "upgrade_hint": get_upgrade_hint(target if target != "unknown" else None, resolved),
    }


def _summary_stats(results: list[TestResult]) -> dict[str, Any]:
    gate_on = tier2_gate_enabled()
    matched = sum(
        1 for r in results
        if r.match_status == "match" or (r.match_status == "parity_gap" and not gate_on)
    )
    mismatched = sum(
        1 for r in results
        if r.match_status in ("mismatch", "shape_drift", "tier2_fail")
        or (gate_on and r.match_status == "parity_gap")
    )
    missing = sum(1 for r in results if r.match_status == "missing_golden")
    parity_gaps = sum(
        1 for r in results if r.match_status in ("parity_gap", "tier2_fail") or r.client_parity_note
    )
    with_status = matched + mismatched
    compatibility = round(matched / with_status * 100, 1) if with_status > 0 else None
    return {
        "golden_matched": matched,
        "golden_mismatched": mismatched,
        "golden_missing": missing,
        "client_parity_gaps": parity_gaps,
        "tier2_gate_enabled": gate_on,
        "compatibility_score": compatibility,
    }


def build_ai_report_markdown(run: TestRun, results: list[TestResult]) -> str:
    ctx = _golden_context(run)
    stats = _summary_stats(results)
    total = run.total_tests
    compat_rate = stats["compatibility_score"]
    probe_success = sum(
        1 for r in results
        if r.outcome == CONTRACT_SUCCESS or r.outcome == "success_with_data"
    )
    probe_outcome_rate = round(probe_success / total * 100, 1) if total > 0 else None
    schema_gate = compute_schema_gate(run.schema_diff)
    certified = compute_certified(
        schema_gate_pass=schema_gate["schema_gate_pass"],
        compatibility_score=compat_rate,
        tier2_pass=stats["client_parity_gaps"] == 0,
        parity_gaps=stats["client_parity_gaps"] if stats.get("tier2_gate_enabled") else 0,
    )
    run_meta = (run.schema_diff or {}).get("_run_meta") or {}
    test_mode = run_meta.get("test_mode", "compatibility")

    lines: list[str] = [
        "# Saleor API Compatibility Report",
        "",
        "## Purpose",
        f"This report compares a target GraphQL API against the official Saleor {ctx['golden_corpus_version']} reference.",
        f" Test mode: **{test_mode}** (golden input replay).",
        "",
        "## Version glossary",
        "| Label | Value | Meaning |",
        "|-------|-------|---------|",
        f"| Target API | {ctx['target_version']} @ {ctx['target_url']} | Version from `shop {{ version }}` on server under test |",
        f"| Test scope | {ctx['test_scope']} | Full system: L1 + L3 dashboard + L3 storefront + scenarios + variants |",
        f"| Golden corpus | {ctx['golden_corpus_version']} ({ctx['golden_probe_count']} L1 probes) | Recorded request/response from official Saleor |",
        f"| L3 dashboard bundles | {ctx['l3_dashboard_certified']} | Schema-certified dashboard GraphQL documents |",
        f"| L3 storefront bundles | {ctx['l3_storefront_certified']} | Schema-certified storefront GraphQL documents |",
        "",
        "## Certification denominator",
        f"- **Endpoints executed:** {ctx['certification_endpoint_count']} (compatibility % uses this count only)",
        f"- **Excluded from scoring:** deprecated L1 ops and schema-incompatible L3 bundles are never counted.",
    ]
    if ctx.get("not_counted_note"):
        lines.append(f"- **Note:** {ctx['not_counted_note']}")
    excluded = ctx.get("excluded_l3_bundles") or []
    if excluded:
        lines.append(f"- **Excluded L3 bundles ({len(excluded)}):** " + ", ".join(
            e.get("bundle_id", "?") for e in excluded[:15]
        ) + ("…" if len(excluded) > 15 else ""))
    lines.extend([
        "",
        "## Executive summary",
        f"- **Compatibility score** (primary): **{compat_rate}%**"
        if compat_rate is not None
        else "- **Compatibility score**: N/A",
        f"- Schema gate ({schema_gate.get('schema_gate_source', 'dashboard catalog')}): "
        f"**{'PASS' if schema_gate['schema_gate_pass'] else 'FAIL'}** "
        f"(missing {schema_gate['missing_queries']} queries, {schema_gate['missing_mutations']} mutations)",
        f"- Certified Saleor-compatible: **{'YES' if certified else 'NO'}** (requires schema gate + compatibility 100%)",
        f"- Probe outcome rate (informational): **{probe_outcome_rate}%** returned success-class responses ({probe_success}/{total})",
        f"- Incompatible: {run.failed}, Warnings: {run.warnings}, Compatible: {run.passed}",
        f"- Golden: {stats['golden_matched']} matched, {stats['golden_mismatched']} mismatched, {stats['golden_missing']} missing",
        f"- Client parity gaps (Tier 2, informational): {stats.get('client_parity_gaps', 0)}",
    ])
    if ctx["upgrade_hint"]:
        lines.extend(["", f"**Upgrade recommendation:** {ctx['upgrade_hint']}"])

    parity_rows = [r for r in results if r.match_status == "parity_gap" or r.client_parity_note]
    if parity_rows:
        lines.extend([
            "",
            "## Client parity gaps (SGRC Tier 2 — informational)",
            "Certified = SGRC Tier 1 pass. These probes match semantically but lack optional path/code fields "
            "recommended for Dashboard/Storefront parity.",
            "",
            "| Endpoint | Kind | Note |",
            "|----------|------|------|",
        ])
        for r in parity_rows[:50]:
            note = r.client_parity_note or r.diff_summary or "—"
            lines.append(f"| {r.endpoint_name} | {r.endpoint_kind} | {note} |")

    if run.schema_diff:
        lines.extend(["", "## Schema drift"])
        diff = run.schema_diff
        if isinstance(diff.get("version_warning"), str) and diff["version_warning"]:
            lines.append(f"- {diff['version_warning']}")
        for key, label in [
            ("missing_queries", "Missing queries"),
            ("missing_mutations", "Missing mutations"),
            ("extra_queries", "Extra queries"),
            ("extra_mutations", "Extra mutations"),
        ]:
            items = diff.get(key) or []
            if items:
                preview = ", ".join(items[:10])
                more = f" (+{len(items) - 10} more)" if len(items) > 10 else ""
                lines.append(f"- {label} ({len(items)}): {preview}{more}")

    true_mismatches = [
        r for r in results
        if r.match_status in ("mismatch", "shape_drift")
    ]
    compatible_errors = [
        r for r in results
        if r.match_status == "match" and r.status == "fail"
    ]
    if true_mismatches:
        lines.extend(["", "## Behavioral mismatches (action required)"])
        failures = true_mismatches
    else:
        failures = []
    if compatible_errors:
        lines.extend([
            "",
            f"## Expected error probes (compatible, {len(compatible_errors)} total)",
            "These probes send invalid/minimal input and receive the same error class as golden — not failures.",
        ])
    if failures:
        if not true_mismatches:
            lines.extend(["", "## Failures requiring action (prioritized)"])
        for r in failures[:50]:
            lines.extend([
                "",
                f"### {r.endpoint_name} ({r.endpoint_kind})",
                f"- Status: {r.status}, Match: {r.match_status or '—'}, Outcome: {r.outcome or '—'}",
            ])
            if r.diff_summary:
                lines.append(f"- Diff: {r.diff_summary}")
            if r.input_sent:
                lines.append(f"- **Request:**\n```graphql\n{_truncate(r.input_sent)}\n```")
            if r.expected_response:
                lines.append(f"- **Expected (golden):**\n```json\n{_truncate(r.expected_response)}\n```")
            if r.actual_response:
                lines.append(f"- **Actual:**\n```json\n{_truncate(r.actual_response)}\n```")
            if r.error_message:
                lines.append(f"- Error: {r.error_message}")

    warns = [
        r for r in results
        if r.status == "warn" and r not in failures and r not in true_mismatches
    ]
    if warns:
        lines.extend(["", "## Warnings (summary)", "| Endpoint | Kind | Outcome | Match |", "|----------|------|---------|-------|"])
        for r in warns[:30]:
            lines.append(
                f"| {r.endpoint_name} | {r.endpoint_kind} | {r.outcome or '—'} | {r.match_status or '—'} |"
            )

    lines.extend([
        "",
        "## All results index (compact)",
        "| Endpoint | Kind | Status | Match | Outcome | ms |",
        "|----------|------|--------|-------|---------|-----|",
    ])
    for r in results:
        lines.append(
            f"| {r.endpoint_name} | {r.endpoint_kind} | {r.status} | {r.match_status or '—'} | "
            f"{r.outcome or '—'} | {r.response_time_ms or '—'} |"
        )

    return "\n".join(lines) + "\n"


def build_ai_report_json(run: TestRun, results: list[TestResult]) -> dict[str, Any]:
    ctx = _golden_context(run)
    stats = _summary_stats(results)
    total = run.total_tests
    schema_gate = compute_schema_gate(run.schema_diff)
    certified = compute_certified(
        schema_gate_pass=schema_gate["schema_gate_pass"],
        compatibility_score=stats["compatibility_score"],
        tier2_pass=stats["client_parity_gaps"] == 0,
        parity_gaps=stats["client_parity_gaps"] if stats.get("tier2_gate_enabled") else 0,
    )

    def row(r: TestResult, *, full: bool) -> dict[str, Any]:
        base: dict[str, Any] = {
            "endpoint": r.endpoint_name,
            "kind": r.endpoint_kind,
            "category": r.category,
            "status": r.status,
            "outcome": r.outcome,
            "match_status": r.match_status,
            "diff_summary": r.diff_summary,
            "client_parity_note": r.client_parity_note,
            "response_time_ms": r.response_time_ms,
            "error_message": r.error_message,
        }
        if full:
            base["input_sent"] = r.input_sent
            base["expected_response"] = (
                json.loads(r.expected_response) if r.expected_response else None
            )
            base["actual_response"] = (
                json.loads(r.actual_response) if r.actual_response else None
            )
        return base

    priority = [r for r in results if r.match_status in ("mismatch", "shape_drift")]
    warnings = [r for r in results if r.status == "warn" and r not in priority]
    parity_gaps = [r for r in results if r.match_status == "parity_gap" or r.client_parity_note]

    return {
        "purpose": f"Saleor API compatibility report vs golden {ctx['golden_corpus_version']}",
        "version_glossary": ctx,
        "executive_summary": {
            "compatibility_score": stats["compatibility_score"],
            "schema_gate_pass": schema_gate["schema_gate_pass"],
            "certified": certified,
            "total": total,
            "compatible": run.passed,
            "incompatible": run.failed,
            "warnings": run.warnings,
            "skipped": run.skipped,
            **stats,
        },
        "schema_diff": run.schema_diff,
        "failures": [row(r, full=True) for r in priority[:50]],
        "client_parity_gaps": [row(r, full=False) for r in parity_gaps[:50]],
        "warnings": [row(r, full=False) for r in warnings[:30]],
        "results_index": [row(r, full=False) for r in results],
    }
