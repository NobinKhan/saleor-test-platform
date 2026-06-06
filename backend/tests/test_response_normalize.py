"""Response normalization for golden comparison."""

from app.services.response_normalize import normalize_response, sanitize_for_sgrc


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
    assert norm["data"]["product"]["id"] == "<id>"


def test_sanitize_for_sgrc_strips_python_debug():
    resp = {
        "errors": [
            {
                "message": "Invalid ID: x. Expected: Checkout.",
                "locations": [{"line": 1, "column": 9}],
                "path": ["checkout"],
                "extensions": {
                    "exception": {"code": "GraphQLError", "stacktrace": ["Traceback..."]},
                    "cost": 1,
                },
            }
        ],
        "data": {"checkout": None},
        "extensions": {"cost": {"requestedQueryCost": 1}},
    }
    clean = sanitize_for_sgrc(resp)
    assert clean["errors"] == [{"message": "Invalid ID: x. Expected: Checkout."}]
    assert "extensions" not in clean
    assert "stacktrace" not in str(clean)


def test_sanitize_for_sgrc_keeps_client_error_code():
    resp = {
        "errors": [{"message": "Not found", "extensions": {"code": "NOT_FOUND"}}],
        "data": {"order": None},
    }
    clean = sanitize_for_sgrc(resp)
    assert clean["errors"][0]["extensions"] == {"code": "NOT_FOUND"}
