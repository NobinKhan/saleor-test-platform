"""Tests for operation_name extraction and latency telemetry."""

from app.routes.reports import _latency_stats, _latency_by_operation
from app.schemas import OperationLatency
from app.services.test_runner import _extract_operation_name


def test_extract_operation_name_from_query():
    doc = "query ProductList { products { edges { node { id } } } }"
    assert _extract_operation_name(doc) == "ProductList"


def test_extract_operation_name_from_mutation():
    doc = "mutation CategoryCreate($input: CategoryCreateInput!) { categoryCreate(input: $input) { id } }"
    assert _extract_operation_name(doc) == "CategoryCreate"


def test_extract_operation_name_none_for_anonymous():
    assert _extract_operation_name("{ me { id } }") is None
    assert _extract_operation_name(None) is None
    assert _extract_operation_name("") is None


def test_latency_stats_p99():
    times = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    stats = _latency_stats(times)
    assert stats.sample_count == 10
    assert stats.p50 > 0
    assert stats.p95 >= stats.p50
    assert stats.p99 >= stats.p95
    assert stats.max == 100


def test_latency_stats_empty():
    stats = _latency_stats([])
    assert stats.sample_count == 0
    assert stats.p99 == 0


class _MockResult:
    """Lightweight stand-in for TestResult/TestResultResponse for latency grouping."""

    def __init__(self, operation_name, response_time_ms, endpoint_kind="QUERY"):
        self.operation_name = operation_name
        self.response_time_ms = response_time_ms
        self.endpoint_kind = endpoint_kind


def test_latency_by_operation_groups_by_op_name():
    results = [
        _MockResult("ProductCreate", 50),
        _MockResult("ProductCreate", 150),
        _MockResult("CategoryCreate", 10),
        _MockResult(None, 5),
    ]
    ops = _latency_by_operation(results)
    # None operation_name is grouped as "unknown"
    assert len(ops) == 3
    by_name = {op.operation_name: op for op in ops}
    assert by_name["ProductCreate"].sample_count == 2
    assert by_name["ProductCreate"].max == 150
    assert by_name["CategoryCreate"].sample_count == 1
    assert by_name["unknown"].sample_count == 1


def test_latency_by_operation_sorted_by_p95_desc():
    results = [
        _MockResult("SlowOp", 200),
        _MockResult("SlowOp", 300),
        _MockResult("FastOp", 5),
        _MockResult("FastOp", 10),
    ]
    ops = _latency_by_operation(results)
    assert ops[0].operation_name == "SlowOp"
    assert ops[1].operation_name == "FastOp"
    assert ops[0].p95 >= ops[1].p95


def test_latency_by_operation_returns_operation_latency_instances():
    results = [_MockResult("Op", 42)]
    ops = _latency_by_operation(results)
    assert len(ops) == 1
    assert isinstance(ops[0], OperationLatency)


def test_latency_by_operation_skips_none_response_time():
    results = [
        _MockResult("Op", None),
        _MockResult("Op", 20),
    ]
    ops = _latency_by_operation(results)
    assert len(ops) == 1
    assert ops[0].sample_count == 1