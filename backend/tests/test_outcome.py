"""Outcome classification tests."""

from app.services.outcome import classify_graphql_response, classify_transport_error


def test_success_with_data():
    meta = classify_graphql_response(
        {"data": {"products": {"edges": []}}},
        http_status=200,
        endpoint_kind="QUERY",
    )
    assert meta["outcome"] == "success_with_data"
    assert meta["status"] == "pass"
    assert meta["response_valid"] is True


def test_schema_error():
    meta = classify_graphql_response(
        {"errors": [{"message": "Cannot query field 'foo' on type Query"}]},
        http_status=200,
        endpoint_kind="QUERY",
    )
    assert meta["outcome"] == "schema_error"
    assert meta["status"] == "fail"


def test_mutation_validation_warn():
    meta = classify_graphql_response(
        {"errors": [{"message": "Invalid value", "extensions": {"code": "INVALID"}}]},
        http_status=200,
        endpoint_kind="MUTATION",
    )
    assert meta["outcome"] == "validation_error"
    assert meta["status"] == "warn"


def test_transport_timeout():
    meta = classify_transport_error(kind="timeout", message="Timeout after 30s")
    assert meta["outcome"] == "timeout"
    assert meta["status"] == "fail"


def test_unknown_field_schema_error():
    meta = classify_graphql_response(
        {
            "errors": [
                {
                    "message": 'Unknown field "shippingMethodUpdate" on type "MutationRoot". '
                    'Did you mean "shippingPriceUpdate"?',
                }
            ]
        },
        http_status=200,
        endpoint_kind="MUTATION",
    )
    assert meta["outcome"] == "schema_error"
    assert meta["status"] == "fail"


def test_missing_required_argument_schema_error():
    meta = classify_graphql_response(
        {
            "errors": [
                {
                    "message": 'Field "webhook" argument "id" of type "QueryRoot" is required but not provided',
                }
            ]
        },
        http_status=200,
        endpoint_kind="QUERY",
    )
    assert meta["outcome"] == "schema_error"
    assert meta["status"] == "fail"


def test_unexpected_error_is_warn_not_pass():
    meta = classify_graphql_response(
        {"errors": [{"message": "Something completely unexpected happened"}]},
        http_status=200,
        endpoint_kind="QUERY",
    )
    assert meta["outcome"] == "unexpected_error"
    assert meta["status"] == "warn"
