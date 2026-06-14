"""Fixture resolver tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.fixture_resolver import (
    _query_saleor,
    resolve_fixtures,
    resolve_dynamic_probe_support,
    validate_preflight,
)


def _setup_client_mock(mock_cls: MagicMock, post_return=None, post_side_effect=None):
    """Configure httpx.AsyncClient mock to work with async context manager."""
    instance = mock_cls.return_value
    instance.__aenter__.return_value = instance
    instance.__aexit__.return_value = None
    if post_side_effect:
        instance.post = AsyncMock(side_effect=post_side_effect)
    else:
        instance.post = AsyncMock(return_value=post_return)


def _mock_response(resp_data: dict, status_code: int = 200):
    resp = MagicMock(status_code=status_code)
    resp.json = MagicMock(return_value=resp_data)
    return resp


@pytest.mark.asyncio
async def test_query_saleor_success():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_return=_mock_response({"data": {"products": {"edges": []}}}))
        result = await _query_saleor("http://example.com/graphql/", "{ products }", "token")
    assert result == {"products": {"edges": []}}


@pytest.mark.asyncio
async def test_query_saleor_error_status():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_return=_mock_response({}, status_code=500))
        result = await _query_saleor("http://example.com/graphql/", "{ products }", "token")
    assert result is None


@pytest.mark.asyncio
async def test_query_saleor_graphql_errors():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_return=_mock_response({"errors": [{"message": "error"}]}))
        result = await _query_saleor("http://example.com/graphql/", "{ products }", "token")
    assert result is None


@pytest.mark.asyncio
async def test_query_saleor_exception():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_side_effect=Exception("connection failed"))
        result = await _query_saleor("http://example.com/graphql/", "{ products }", "token")
    assert result is None


@pytest.mark.asyncio
async def test_resolve_fixtures_queries_saleor():
    call_count = 0
    responses = [
        {"data": {"products": {"edges": [{"node": {"id": "UHJvZHVjdDox", "slug": "test-product", "productType": {"id": "UHJvZHVjdFR5cGU6MQ=="}}}]}}},
        {"data": {"product": {"variants": [{"id": "VmFyaWFudDox"}]}}},
        {"data": {"channels": {"edges": [{"node": {"id": "Q2hhbm5lbDox", "slug": "default", "name": "Default", "currencyCode": "USD"}}]}}},
        {"data": {"orders": {"edges": [{"node": {"id": "T3JkZXI6MQ=="}}]}}},
        {"data": {"users": {"edges": [{"node": {"id": "VXNlcjox", "email": "harness@test.com"}}]}}},
    ]

    async def mock_post(url, **kw):
        nonlocal call_count
        resp = MagicMock(status_code=200)
        resp.json = MagicMock(return_value=responses[call_count] if call_count < len(responses) else {"data": {}})
        call_count += 1
        return resp

    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_side_effect=mock_post)
        with patch("app.services.fixture_resolver.load_fixtures", return_value={
            "default_product_id": "UHJvZHVjdDox",
            "default_variant_id": "VmFyaWFudDox",
            "default_channel_id": "Q2hhbm5lbDox",
        }):
            result = await resolve_fixtures("http://example.com/graphql/", "token")

    assert result["default_product_id"] == "UHJvZHVjdDox"
    assert result["default_variant_id"] == "VmFyaWFudDox"
    assert result["default_channel_id"] == "Q2hhbm5lbDox"
    assert result.get("default_slug") == "test-product"
    assert result.get("default_product_type_id") == "UHJvZHVjdFR5cGU6MQ=="


@pytest.mark.asyncio
async def test_resolve_dynamic_probe_support():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_return=_mock_response({
            "data": {"productTypes": {"edges": [{"node": {"id": "UHJvZHVjdFR5cGU6MQ=="}}]}}
        }))
        support = await resolve_dynamic_probe_support("http://example.com/graphql/", "token")
    assert support.get("product_type_id") == "UHJvZHVjdFR5cGU6MQ=="


@pytest.mark.asyncio
async def test_resolve_dynamic_probe_support_empty():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_return=_mock_response({"data": {"productTypes": {"edges": []}}}))
        support = await resolve_dynamic_probe_support("http://example.com/graphql/", "token")
    assert support == {}


@pytest.mark.asyncio
async def test_validate_preflight_api_unreachable():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_side_effect=Exception("fail"))
        result = await validate_preflight("http://example.com/graphql/", "token")
    assert not result["api_reachable"]
    assert "unreachable" in result["issues"][0]


@pytest.mark.asyncio
async def test_validate_preflight_checks_version():
    call_count = 0

    async def mock_post(url, **kw):
        nonlocal call_count
        resp = MagicMock(status_code=200)
        if call_count == 0:
            resp.json = MagicMock(return_value={"data": {"shop": {"version": "3.23.7"}}})
        else:
            resp.json = MagicMock(return_value={"data": {"products": {"edges": []}}})
        call_count += 1
        return resp

    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_side_effect=mock_post)
        with patch("app.services.fixture_resolver.load_fixtures", return_value={}):
            result = await validate_preflight("http://example.com/graphql/", "token", corpus_version="3.23.7")

    assert result["api_reachable"]
    assert result["shop_version"] == "3.23.7"


@pytest.mark.asyncio
async def test_validate_preflight_fixture_missing():
    async def mock_post(url, **kw):
        resp = MagicMock(status_code=200)
        resp.json = MagicMock(return_value={"data": {"shop": {"version": "3.23.7"}}})
        return resp

    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(mock_cls, post_side_effect=mock_post)
        with patch("app.services.fixture_resolver.load_fixtures", return_value={}):
            result = await validate_preflight("http://example.com/graphql/", "token")

    assert "fixture_status" in result
    for key, status in result["fixture_status"].items():
        assert status == "missing", f"Expected {key} to be missing"
