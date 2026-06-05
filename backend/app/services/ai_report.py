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
from app.services.run_helpers import catalog_counts

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
    q_count, m_count = catalog_counts()
    return {
        "target_version": target,
        "target_url": run.saleor_url,
        "catalog_source": run.reference_baseline_source or settings.reference_baseline_source,
        "catalog_version": run.reference_baseline_version or settings.reference_baseline_version,
        "catalog_queries": q_count,
        "catalog_mutations": m_count,
        "golden_corpus_version": resolved,
        "golden_saleor_url": manifest.get("saleor_url", settings.reference_saleor_url),
        "golden_probe_count": manifest.get("probe_count", 0),
        "upgrade_hint": get_upgrade_hint(target if target != "unknown" else None, resolved),
    }


def _summary_stats(results: list[TestResult]) -> dict[str, Any]:
    matched = sum(1 for r in results if r.match_status == "match")
    mismatched = sum(1 for r in results if r.match_status in ("mismatch", "shape_drift"))
    missing = sum(1 for r in results if r.match_status == "missing_golden")
    with_status = matched + mismatched
    compatibility = round(matched / with_status * 100, 1) if with_status > 0 else None
    return {
        "golden_matched": matched,
        "golden_mismatched": mismatched,
        "golden_missing": missing,
        "compatibility_score": compatibility,
    }


def build_ai_report_markdown(run: TestRun, results: list[TestResult]) -> str:
    ctx = _golden_context(run)
    stats = _summary_stats(results)
    total = run.total_tests
    pass_rate = round(run.passed / total * 100, 1) if total > 0 else 0.0

    lines: list[str] = [
        "# Saleor API Compatibility Report",
        "",
        "## Purpose",
        f"This report compares a target GraphQL API against the official Saleor {ctx['golden_corpus_version']} reference.",
        "",
        "## Version glossary",
        "| Label | Value | Meaning |",
        "|-------|-------|---------|",
        f"| Target API | {ctx['target_version']} @ {ctx['target_url']} | Version from `shop {{ version }}` on server under test |",
        f"| Catalog baseline | {ctx['catalog_source']} {ctx['catalog_version']} | Static list of operation names we probe |",
        f"| Golden corpus | {ctx['golden_corpus_version']} ({ctx['golden_probe_count']} probes) | Recorded request/response from official Saleor |",
        "",
        "## Executive summary",
        f"- Pass rate: **{pass_rate}%** ({run.passed}/{total})",
        f"- Compatibility score (golden match): **{stats['compatibility_score']}%**"
        if stats["compatibility_score"] is not None
        else "- Compatibility score: **N/A** (no golden comparisons)",
        f"- Failed: {run.failed}, Warnings: {run.warnings}, Skipped: {run.skipped}",
        f"- Golden: {stats['golden_matched']} matched, {stats['golden_mismatched']} mismatched, {stats['golden_missing']} missing",
    ]
    if ctx["upgrade_hint"]:
        lines.extend(["", f"**Upgrade recommendation:** {ctx['upgrade_hint']}"])

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

    failures = [
        r for r in results
        if r.status == "fail" or r.match_status in ("mismatch", "shape_drift")
    ]
    if failures:
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

    warns = [r for r in results if r.status == "warn" and r not in failures]
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
    pass_rate = round(run.passed / total * 100, 1) if total > 0 else 0.0

    def row(r: TestResult, *, full: bool) -> dict[str, Any]:
        base: dict[str, Any] = {
            "endpoint": r.endpoint_name,
            "kind": r.endpoint_kind,
            "category": r.category,
            "status": r.status,
            "outcome": r.outcome,
            "match_status": r.match_status,
            "diff_summary": r.diff_summary,
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

    priority = [
        r for r in results
        if r.status == "fail" or r.match_status in ("mismatch", "shape_drift")
    ]
    warnings = [r for r in results if r.status == "warn" and r not in priority]

    return {
        "purpose": f"Saleor API compatibility report vs golden {ctx['golden_corpus_version']}",
        "version_glossary": ctx,
        "executive_summary": {
            "pass_rate": pass_rate,
            "compatibility_score": stats["compatibility_score"],
            "total": total,
            "passed": run.passed,
            "failed": run.failed,
            "warnings": run.warnings,
            "skipped": run.skipped,
            **stats,
        },
        "schema_diff": run.schema_diff,
        "failures": [row(r, full=True) for r in priority[:50]],
        "warnings": [row(r, full=False) for r in warnings[:30]],
        "results_index": [row(r, full=False) for r in results],
    }
