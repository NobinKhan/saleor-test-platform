"""SSE stream payload formatting tests."""

import json


def _sse_payload(event: dict) -> dict[str, str]:
    """Mirror stream_run helper — single data field for EventSourceResponse."""
    return {"data": json.dumps(event)}


def test_sse_payload_is_json_string_not_prefixed_frame():
    payload = _sse_payload({"type": "connected", "run_id": "abc", "status": "running"})
    assert "data" in payload
    assert not payload["data"].startswith("data:")
    parsed = json.loads(payload["data"])
    assert parsed["type"] == "connected"
    assert parsed["run_id"] == "abc"


def test_sse_result_event_roundtrip():
    event = {
        "type": "result",
        "current": 1,
        "total": 10,
        "current_endpoint": "products",
        "status": "pass",
        "status_counts": {"pass": 1, "fail": 0, "warn": 0, "skip": 0},
    }
    parsed = json.loads(_sse_payload(event)["data"])
    assert parsed["current_endpoint"] == "products"
    assert parsed["status"] == "pass"
