"""TestRunner auth header and customer JWT replay tests."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.test_runner import TestRunner


def test_auth_headers_customer_never_uses_staff_token():
    runner = TestRunner(
        run_id=uuid.uuid4(),
        saleor_url="http://example.com/graphql/",
        saleor_token="staff-jwt",
    )
    runner._customer_token = None
    headers = runner._auth_headers("customer")
    assert "Authorization" not in headers


def test_auth_headers_staff_uses_staff_token():
    runner = TestRunner(
        run_id=uuid.uuid4(),
        saleor_url="http://example.com/graphql/",
        saleor_token="staff-jwt",
    )
    headers = runner._auth_headers("staff")
    assert headers["Authorization"] == "Bearer staff-jwt"


def test_auth_headers_customer_uses_customer_token():
    runner = TestRunner(
        run_id=uuid.uuid4(),
        saleor_url="http://example.com/graphql/",
        saleor_token="staff-jwt",
    )
    runner._customer_token = "customer-jwt"
    headers = runner._auth_headers("customer")
    assert headers["Authorization"] == "Bearer customer-jwt"


@pytest.mark.asyncio
async def test_customer_bundle_skips_without_customer_jwt():
    runner = TestRunner(
        run_id=uuid.uuid4(),
        saleor_url="http://example.com/graphql/",
        saleor_token="staff-jwt",
    )
    endpoint = {
        "name": "sf-accountupdate",
        "kind": "CLIENT_BUNDLE",
        "category": "storefront",
        "is_public": False,
        "auth_context": "customer",
        "bundle_document": "mutation { accountUpdate(input: {}) { user { id } } }",
        "bundle_variables": {"input": {}},
        "bundle_fixtures": {},
        "bundle_id": "sf-accountupdate",
        "golden_contract": "success_with_data",
    }
    with patch.object(runner, "_ensure_auth_for_context", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = None
        runner._customer_token = None
        result = await runner._test_endpoint(endpoint, 0, 1, http_client=MagicMock())
    assert result["failure_category"] == "auth_prerequisite"
    assert result["status"] == "skip"


def test_runner_uses_fixture_customer_jwt_without_force_refresh():
    """Bootstrap should keep JWT from resolve_fixtures and not force-refresh when set."""
    runner = TestRunner(
        run_id=uuid.uuid4(),
        saleor_url="http://example.com/graphql/",
        saleor_token="staff-jwt",
    )
    runner._customer_token = "fixture-customer-jwt"
    assert runner._customer_token == "fixture-customer-jwt"
