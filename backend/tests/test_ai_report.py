"""AI report markdown/JSON generation."""

import uuid
from datetime import datetime, timezone

from app.models import TestResult, TestRun
from app.services.ai_report import build_ai_report_json, build_ai_report_markdown


def _minimal_run() -> TestRun:
    return TestRun(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        saleor_url="http://localhost:8000/graphql/",
        saleor_token="token",
        saleor_version="3.23.7",
        status="completed",
        started_at=datetime.now(timezone.utc),
        total_tests=1,
        passed=1,
        failed=0,
        warnings=0,
        skipped=0,
        test_scope="full+scenarios",
        schema_diff={"certification_endpoint_count": 856},
    )


def _minimal_result(run_id: uuid.UUID) -> TestResult:
    return TestResult(
        id=uuid.uuid4(),
        test_run_id=run_id,
        category="shop",
        endpoint_name="shop",
        endpoint_kind="QUERY",
        status="pass",
        is_public=True,
        match_status="match",
        outcome="success_with_data",
        response_time_ms=42,
    )


def test_build_ai_report_markdown():
    run = _minimal_run()
    results = [_minimal_result(run.id)]
    md = build_ai_report_markdown(run, results)
    assert md.startswith("# Saleor API Compatibility Report")
    assert "Certification denominator" in md
    assert "Executive summary" in md
    assert "shop" in md


def test_build_ai_report_json():
    run = _minimal_run()
    results = [_minimal_result(run.id)]
    payload = build_ai_report_json(run, results)
    assert "purpose" in payload
    assert payload["executive_summary"]["compatible"] == 1


def test_latency_by_operation_groups_and_sorts():
    from app.services.ai_report import _latency_by_operation

    run = _minimal_run()
    r1 = _minimal_result(run.id)
    r1.operation_name = "ProductCreate"
    r1.response_time_ms = 50
    r2 = _minimal_result(run.id)
    r2.operation_name = "ProductCreate"
    r2.response_time_ms = 200
    r3 = _minimal_result(run.id)
    r3.operation_name = "CategoryCreate"
    r3.response_time_ms = 10
    ops = _latency_by_operation([r1, r2, r3])
    assert len(ops) == 2
    assert ops[0]["operation_name"] == "ProductCreate"
    assert ops[0]["sample_count"] == 2
    assert ops[0]["max"] == 200
    assert ops[1]["operation_name"] == "CategoryCreate"


def test_latency_by_operation_p99_in_json_report():
    run = _minimal_run()
    r1 = _minimal_result(run.id)
    r1.operation_name = "CheckoutCreate"
    r1.response_time_ms = 30
    payload = build_ai_report_json(run, [r1])
    lat = payload["latency_by_operation"]
    assert len(lat) == 1
    assert lat[0]["operation_name"] == "CheckoutCreate"
    assert "p99" in lat[0]
