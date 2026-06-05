"""Response normalization for golden comparison."""

from app.services.response_normalize import normalize_response


def test_strips_extensions():
    resp = {
        "data": {"shop": {"version": "3.23.7"}},
        "extensions": {"cost": 42},
    }
    norm = normalize_response(resp)
    assert "extensions" not in norm
    assert norm["data"]["shop"]["version"] == "3.23.7"


def test_normalizes_uuids():
    uid = "550e8400-e29b-41d4-a716-446655440000"
    resp = {"data": {"product": {"id": uid}}}
    norm = normalize_response(resp)
    assert norm["data"]["product"]["id"] == "<uuid>"
