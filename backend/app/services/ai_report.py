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
        if r.match_status in ("mismatch", "shape_drift", "tier2_fail", "assertion_fail")
        or (gate_on and r.match_status == "parity_gap")
    )
    missing = sum(1 for r in results if r.match_status == "missing_golden")
    assertion_fail_count = sum(1 for r in results if r.match_status == "assertion_fail")
    parity_gaps = sum(
        1 for r in results if r.match_status in ("parity_gap", "tier2_fail") or r.client_parity_note
    )
    with_status = matched + mismatched
    compatibility = round(matched / with_status * 100, 1) if with_status > 0 else None

    category_counts: dict[str, int] = {}
    for r in results:
        cat = r.failure_category or "unknown"
        category_counts[cat] = category_counts.get(cat, 0) + 1

    deprecated_count = category_counts.get("deprecated_excluded", 0)
    data_prereq_count = category_counts.get("data_prerequisite", 0)
    seed_prereq_count = category_counts.get("seed_prerequisite", 0)
    real_bug_count = category_counts.get("real_bug", 0)
    compatible_count = category_counts.get("compatible", 0)
    missing_golden_count = category_counts.get("missing_golden", 0)
    schema_mismatch_count = category_counts.get("schema_mismatch", 0)
    data_drift_count = category_counts.get("data_drift", 0)

    effective_denominator = with_status - deprecated_count - data_prereq_count - seed_prereq_count
    effective_score = (
        round(matched / effective_denominator * 100, 1)
        if effective_denominator > 0
        else compatibility
    )

    return {
        "golden_matched": matched,
        "golden_mismatched": mismatched,
        "golden_missing": missing,
        "client_parity_gaps": parity_gaps,
        "tier2_gate_enabled": gate_on,
        "compatibility_score": compatibility,
        "effective_score": effective_score,
        "deprecated_excluded": deprecated_count,
        "data_prerequisite": data_prereq_count,
        "seed_prerequisite": seed_prereq_count,
        "real_bugs": real_bug_count,
        "schema_mismatch": schema_mismatch_count,
        "data_drift": data_drift_count,
        "effective_compatible": compatible_count,
        "effective_incompatible": real_bug_count,
        "assertion_fail_count": assertion_fail_count,
        "failure_category_counts": category_counts,
    }


def _latency_by_operation(results: list[TestResult]) -> list[dict[str, Any]]:
    """Group response times by operation_name; return sorted by p95 desc."""
    groups: dict[str, list[int]] = {}
    kinds: dict[str, str] = {}
    for r in results:
        op = getattr(r, "operation_name", None) or "unknown"
        rt = r.response_time_ms
        if rt is None:
            continue
        groups.setdefault(op, []).append(rt)
        if op not in kinds:
            kinds[op] = r.endpoint_kind or ""
    out = []
    for op, vals in groups.items():
        st = sorted(vals)
        n = len(st)
        out.append({
            "operation_name": op,
            "endpoint_kind": kinds[op],
            "sample_count": n,
            "avg": round(sum(vals) / n, 1),
            "p50": float(st[min(n - 1, int(n * 0.50))]),
            "p95": float(st[min(n - 1, int(n * 0.95))]),
            "p99": float(st[min(n - 1, int(n * 0.99))]),
            "max": st[-1],
            "latency_outlier": st[min(n - 1, int(n * 0.95))] > 100,
        })
    out.sort(key=lambda x: x["p95"], reverse=True)
    return out


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
        effective_score=stats.get("effective_score"),
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
        f"- **Effective score** (excludes deprecated + data-prerequisite): **{stats.get('effective_score', 'N/A')}%**",
        f"- Schema gate ({schema_gate.get('schema_gate_source', 'dashboard catalog')}): "
        f"**{'PASS' if schema_gate['schema_gate_pass'] else 'FAIL'}** "
        f"(missing {schema_gate['missing_queries']} queries, {schema_gate['missing_mutations']} mutations)",
        f"- Certified Saleor-compatible: **{'YES' if certified else 'NO'}** (requires schema gate + compatibility 100%)",
        f"- Probe outcome rate (informational): **{probe_outcome_rate}%** returned success-class responses ({probe_success}/{total})",
        f"- Incompatible: {run.failed}, Warnings: {run.warnings}, Compatible: {run.passed}",
        f"- Golden: {stats['golden_matched']} matched, {stats['golden_mismatched']} mismatched, {stats['golden_missing']} missing",
        f"- Scenario assertion failures: {stats.get('assertion_fail_count', 0)}",
        f"- Client parity gaps (Tier 2, informational): {stats.get('client_parity_gaps', 0)}",
    ])
    dep_count = stats.get("deprecated_excluded", 0)
    prereq_count = stats.get("data_prerequisite", 0)
    seed_prereq_count = stats.get("seed_prerequisite", 0)
    real_bugs = stats.get("real_bugs", 0)
    schema_mismatch = stats.get("schema_mismatch", 0)
    data_drift = stats.get("data_drift", 0)
    if dep_count or prereq_count or seed_prereq_count or real_bugs or schema_mismatch or data_drift:
        lines.extend([
            "",
            "### Failure category breakdown",
            f"- Deprecated (excluded from denominator): {dep_count}",
            f"- Data-dependent (missing fixture, excluded): {prereq_count}",
            f"- Seed-dependent (demo topology, excluded): {seed_prereq_count}",
            f"- Schema mismatch (structural API defect): {schema_mismatch}",
            f"- Data drift (data differs, not API bug): {data_drift}",
            f"- Real bugs (confirmed API defects): {real_bugs}",
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
                f"- Failure category: {r.failure_category or '—'}",
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

    latency_ops = _latency_by_operation(results)
    if latency_ops:
        lines.extend([
            "",
            "## Latency by operation (Top 20 by p95)",
            "| Operation | Kind | n | avg | p50 | p95 | p99 | max |",
            "|-----------|------|---|-----|-----|-----|-----|-----|",
        ])
        for op in latency_ops[:20]:
            lines.append(
                f"| {op['operation_name']} | {op['endpoint_kind']} | {op['sample_count']} | "
                f"{op['avg']:.0f} | {op['p50']:.0f} | {op['p95']:.0f} | {op['p99']:.0f} | {op['max']} |"
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
        effective_score=stats.get("effective_score"),
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
            "operation_name": getattr(r, "operation_name", None),
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
            "effective_score": stats.get("effective_score"),
            "schema_gate_pass": schema_gate["schema_gate_pass"],
            "certified": certified,
            "total": total,
            "compatible": run.passed,
            "incompatible": run.failed,
            "warnings": run.warnings,
            "skipped": run.skipped,
            "deprecated_excluded": stats.get("deprecated_excluded", 0),
            "data_prerequisite": stats.get("data_prerequisite", 0),
            "real_bugs": stats.get("real_bugs", 0),
            **stats,
        },
        "schema_diff": run.schema_diff,
        "latency_by_operation": _latency_by_operation(results),
        "failures": [row(r, full=True) for r in priority[:50]],
        "client_parity_gaps": [row(r, full=False) for r in parity_gaps[:50]],
        "warnings": [row(r, full=False) for r in warnings[:30]],
        "results_index": [row(r, full=False) for r in results],
    }
