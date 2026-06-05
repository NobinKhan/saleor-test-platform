"""Response contract classification tests."""

from app.services.response_contract import (
    CONTRACT_BUSINESS_ERROR,
    CONTRACT_GRAPHQL_ERROR,
    CONTRACT_SUCCESS,
    classify_response_contract,
)


def test_graphql_error_on_http_400():
    resp = {
        "errors": [{"message": "Argument \"input\" has invalid value {}.", "extensions": {}}],
    }
    assert classify_response_contract(resp, http_status=400) == CONTRACT_GRAPHQL_ERROR


def test_business_error_in_data():
    resp = {
        "data": {
            "checkoutComplete": {
                "errors": [{"field": None, "message": "At least one of arguments is required."}],
            }
        },
    }
    assert classify_response_contract(resp, http_status=200) == CONTRACT_BUSINESS_ERROR


def test_success_with_data():
    resp = {"data": {"products": {"edges": []}}}
    assert classify_response_contract(resp, http_status=200) == CONTRACT_SUCCESS
