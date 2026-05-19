"""
app/routes/reports.py — Report generation and export (CSV, JSON, PDF).
"""

import csv
import io
import uuid
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_sse
from app.models import User, TestRun, TestResult
from app.schemas import ReportData, ReportSummary, CategoryBreakdown, ResponseTimeBucket

router = APIRouter(prefix="/api/reports", tags=["reports"])

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.units import cm
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


@router.get("/{run_id}", response_model=ReportData)
async def get_report(run_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    run_result = await db.execute(select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")

    total = run.total_tests
    pass_rate = (run.passed / total * 100) if total > 0 else 0.0

    cat_result = await db.execute(
        select(TestResult.category, TestResult.status, func.count())
        .where(TestResult.test_run_id == run_id)
        .group_by(TestResult.category, TestResult.status)
    )
    cat_counts: dict[str, dict] = {}
    for cat, status, cnt in cat_result.all():
        if cat not in cat_counts:
            cat_counts[cat] = {"total": 0, "passed": 0, "failed": 0, "warn": 0, "skip": 0}
        cat_counts[cat]["total"] += cnt
        if status == "pass":
            cat_counts[cat]["passed"] += cnt
        elif status == "fail":
            cat_counts[cat]["failed"] += cnt
        elif status == "warn":
            cat_counts[cat]["warn"] += cnt
        elif status == "skip":
            cat_counts[cat]["skip"] += cnt

    category_breakdown = [
        CategoryBreakdown(category=k, total=v["total"], passed=v["passed"], failed=v["failed"], warn=v["warn"], skip=v["skip"])
        for k, v in cat_counts.items()
    ]

    time_result = await db.execute(
        select(TestResult.response_time_ms).where(TestResult.test_run_id == run_id, TestResult.response_time_ms.isnot(None))
    )
    times = [r[0] for r in time_result.all() if r[0]]
    buckets = {"0-50ms": 0, "50-100ms": 0, "100-500ms": 0, "500ms+": 0}
    for t in times:
        if t < 50: buckets["0-50ms"] += 1
        elif t < 100: buckets["50-100ms"] += 1
        elif t < 500: buckets["100-500ms"] += 1
        else: buckets["500ms+"] += 1
    response_time_dist = [ResponseTimeBucket(bucket=k, count=v) for k, v in buckets.items()]
    avg_time = sum(times) / len(times) if times else 0

    summary = ReportSummary(
        test_run_id=run.id,
        total=total,
        passed=run.passed,
        failed=run.failed,
        warnings=run.warnings,
        skipped=run.skipped,
        pass_rate=round(pass_rate, 1),
        avg_response_time_ms=round(avg_time, 1),
        saleor_version=run.saleor_version or "unknown",
        saleor_url=run.saleor_url,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )
    return ReportData(
        summary=summary,
        category_breakdown=category_breakdown,
        response_time_distribution=response_time_dist,
        pass_rate=pass_rate,
        schema_diff=run.schema_diff,
    )


@router.get("/{run_id}/export/csv")
async def export_csv(run_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user_sse)):
    run_result = await db.execute(select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")

    results = await db.execute(select(TestResult).where(TestResult.test_run_id == run_id).order_by(TestResult.created_at))
    results = results.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Endpoint", "Kind", "Category", "Is Public", "Status", "Response Time (ms)", "Error Message", "Input Sent", "Actual Response", "Created At"])

    for r in results:
        writer.writerow([
            r.endpoint_name,
            r.endpoint_kind,
            r.category,
            r.is_public,
            r.status,
            r.response_time_ms,
            r.error_message or "",
            r.input_sent or "",
            r.actual_response or "",
            r.created_at.isoformat() if r.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=saleor-test-{run_id}.csv"},
    )


@router.get("/{run_id}/export/json")
async def export_json(run_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user_sse)):
    run_result = await db.execute(select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")

    results = await db.execute(select(TestResult).where(TestResult.test_run_id == run_id).order_by(TestResult.created_at))
    results = results.scalars().all()

    data = {
        "test_run": {
            "id": str(run.id),
            "saleor_url": run.saleor_url,
            "saleor_version": run.saleor_version,
            "status": run.status,
            "total": run.total_tests,
            "passed": run.passed,
            "failed": run.failed,
            "warnings": run.warnings,
            "skipped": run.skipped,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        },
        "results": [
            {
                "endpoint": r.endpoint_name,
                "kind": r.endpoint_kind,
                "category": r.category,
                "is_public": r.is_public,
                "status": r.status,
                "response_time_ms": r.response_time_ms,
                "error_message": r.error_message,
                "input_sent": r.input_sent,
                "actual_response": r.actual_response,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
    }

    return StreamingResponse(
        iter([json.dumps(data, indent=2)]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=saleor-test-{run_id}.json"},
    )


@router.get("/{run_id}/export/pdf")
async def export_pdf(run_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user_sse)):
    if not HAS_REPORTLAB:
        raise HTTPException(500, "PDF export requires reportlab: pip install reportlab")

    run_result = await db.execute(select(TestRun).where(TestRun.id == run_id, TestRun.user_id == user.id))
    run = run_result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Test run not found")

    results = await db.execute(select(TestResult).where(TestResult.test_run_id == run_id).order_by(TestResult.created_at))
    results = results.scalars().all()

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=16)
    story = []

    story.append(Paragraph(f"Saleor API Test Report", title_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Server: {run.saleor_url}", styles["Normal"]))
    story.append(Paragraph(f"Version: {run.saleor_version or 'unknown'}", styles["Normal"]))
    story.append(Paragraph(f"Date: {run.started_at.strftime('%Y-%m-%d %H:%M UTC') if run.started_at else 'N/A'}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))

    # Summary table
    total = run.total_tests
    pass_rate = (run.passed / total * 100) if total > 0 else 0.0
    summary_data = [
        ["Metric", "Value"],
        ["Total Tests", str(total)],
        ["Passed", str(run.passed)],
        ["Failed", str(run.failed)],
        ["Warnings", str(run.warnings)],
        ["Skipped", str(run.skipped)],
        ["Pass Rate", f"{pass_rate:.1f}%"],
    ]
    summary_table = Table(summary_data, colWidths=[6*cm, 8*cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#16213e")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#16213e"), colors.HexColor("#0f3460")]),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5*cm))

    # Failures table
    failures = [r for r in results if r.status == "fail"]
    if failures:
        story.append(Paragraph("Failures", styles["Heading2"]))
        fail_data = [["Endpoint", "Kind", "Category", "Error"]]
        for r in failures[:50]:
            msg = (r.error_message or "")[:80]
            fail_data.append([r.endpoint_name, r.endpoint_kind, r.category, msg])
        fail_table = Table(fail_data, colWidths=[3.5*cm, 1.5*cm, 2.5*cm, 7*cm])
        fail_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7f1d1d")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#1c1c1c"), colors.HexColor("#272727")]),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(fail_table)

    doc.build(story)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=saleor-test-{run_id}.pdf"},
    )
