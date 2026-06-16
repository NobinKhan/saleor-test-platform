"""Fixture resolver tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.fixture_resolver import (
    FixtureResolution,
    _query_saleor,
    resolve_fixtures,
    resolve_dynamic_probe_support,
    validate_preflight,
)
from app.services.reference_seed import SeedResult


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
async def test_resolve_fixtures_uses_capture():
    captured = {
        "default_product_id": "UHJvZHVjdDox",
        "default_variant_id": "VmFyaWFudDox",
        "default_channel_id": "Q2hhbm5lbDox",
        "default_product_type_id": "UHJvZHVjdFR5cGU6MQ==",
        "default_slug": "test-product",
    }
    with patch(
        "app.services.fixture_resolver.capture_live_fixtures",
        new_callable=AsyncMock,
        return_value=captured,
    ):
        with patch("app.services.fixture_resolver.load_fixtures", return_value={}):
            with patch("app.services.fixture_resolver.settings") as mock_settings:
                mock_settings.runtime_seed = False
                result = await resolve_fixtures("http://example.com/graphql/", "token")

    assert result.fixtures["default_product_id"] == "UHJvZHVjdDox"
    assert "default_variant_id" in result.live_keys
    assert "default_channel_id" in result.live_keys
    assert not result.seeded_keys


@pytest.mark.asyncio
async def test_resolve_fixtures_runtime_seed_when_missing():
    with patch(
        "app.services.fixture_resolver.capture_live_fixtures",
        new_callable=AsyncMock,
        return_value={"default_channel_id": "Q2hhbm5lbDox", "default_channel": "default"},
    ):
        with patch(
            "app.services.fixture_resolver.ensure_certification_topology",
            new_callable=AsyncMock,
            return_value=SeedResult(
                fixtures={
                    "default_channel_id": "Q2hhbm5lbDox",
                    "default_product_id": "UHJvZHVjdDox",
                    "default_variant_id": "VmFyaWFudDox",
                    "default_product_type_id": "UHJvZHVjdFR5cGU6MQ==",
                },
                live_keys=frozenset(
                    {
                        "default_channel_id",
                        "default_product_id",
                        "default_variant_id",
                        "default_product_type_id",
                    }
                ),
                seeded_keys=frozenset({"default_product_id", "default_variant_id"}),
            ),
        ) as mock_ensure:
            with patch("app.services.fixture_resolver.load_fixtures", return_value={}):
                with patch("app.services.fixture_resolver.settings") as mock_settings:
                    mock_settings.runtime_seed = True
                    mock_settings.demo_seed_profile = "harness"
                    result = await resolve_fixtures("http://example.com/graphql/", "token")

    mock_ensure.assert_awaited_once()
    assert mock_ensure.await_args.kwargs.get("full_topology") is False
    assert result.fixtures["default_product_id"] == "UHJvZHVjdDox"
    assert "default_product_id" in result.seeded_keys


@pytest.mark.asyncio
async def test_validate_preflight_rewrites_localhost_url():
    with patch(
        "app.services.fixture_resolver.resolve_harness_saleor_url",
        return_value=(
            "http://localhost:8000/graphql/",
            "http://host.docker.internal:8000/graphql/",
        ),
    ):
        with patch(
            "app.services.fixture_resolver._query_saleor",
            new_callable=AsyncMock,
            return_value={"shop": {"version": "3.23.7"}},
        ) as mock_query:
            with patch(
                "app.services.fixture_resolver.resolve_fixtures",
                new_callable=AsyncMock,
                return_value=FixtureResolution(
                    fixtures={},
                    live_keys=frozenset(
                        {
                            "default_product_id",
                            "default_variant_id",
                            "default_channel_id",
                            "default_product_type_id",
                        }
                    ),
                ),
            ):
                result = await validate_preflight(
                    "http://localhost:8000/graphql/",
                    "token",
                    corpus_version="3.23.7",
                )

    mock_query.assert_awaited_once()
    assert mock_query.await_args.args[0] == "http://host.docker.internal:8000/graphql/"
    assert result["requested_saleor_url"] == "http://localhost:8000/graphql/"
    assert result["resolved_saleor_url"] == "http://host.docker.internal:8000/graphql/"
    assert result["blocking_issues"] == []


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
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(
            mock_cls,
            post_return=_mock_response({"data": {"shop": {"version": "3.23.7"}}}),
        )
        with patch(
            "app.services.fixture_resolver.resolve_fixtures",
            new_callable=AsyncMock,
            return_value=FixtureResolution(
                fixtures={},
                live_keys=frozenset(),
                seeded_keys=frozenset(),
            ),
        ):
            result = await validate_preflight(
                "http://example.com/graphql/", "token", corpus_version="3.23.7"
            )

    assert result["api_reachable"]
    assert result["shop_version"] == "3.23.7"


@pytest.mark.asyncio
async def test_validate_preflight_fixture_missing():
    with patch.object(httpx, "AsyncClient") as mock_cls:
        _setup_client_mock(
            mock_cls,
            post_return=_mock_response({"data": {"shop": {"version": "3.23.7"}}}),
        )
        with patch(
            "app.services.fixture_resolver.resolve_fixtures",
            new_callable=AsyncMock,
            return_value=FixtureResolution(
                fixtures={},
                live_keys=frozenset(),
                seeded_keys=frozenset(),
            ),
        ):
            with patch("app.services.fixture_resolver.settings") as mock_settings:
                mock_settings.runtime_seed = True
                result = await validate_preflight("http://example.com/graphql/", "token")

    assert "fixture_status" in result
    for key, status in result["fixture_status"].items():
        assert status == "missing", f"Expected {key} to be missing"
    assert len(result["warning_issues"]) >= 1
    assert result["blocking_issues"] == []


@pytest.mark.asyncio
async def test_resolve_fixtures_saleor_demo_profile():
    with patch(
        "app.services.fixture_resolver.capture_live_fixtures",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "app.services.demo_seed.ensure_saleor_demo_topology",
        new_callable=AsyncMock,
        return_value=SeedResult(
            fixtures={"default_channel_id": "Q2hhbm5lbDox"},
            live_keys=frozenset({"default_channel_id"}),
            seeded_keys=frozenset({"default_channel_id"}),
        ),
    ) as mock_demo, patch(
        "app.services.fixture_resolver._resolve_storefront_customer",
        new_callable=AsyncMock,
        return_value=(None, None),
    ), patch(
        "app.services.storefront_session.ensure_storefront_session",
        new_callable=AsyncMock,
        return_value=({"default_channel_id": "Q2hhbm5lbDox"}, set(), []),
    ):
        resolution = await resolve_fixtures(
            "http://example.com/graphql/",
            "token",
            seed_profile="saleor_demo",
        )
    mock_demo.assert_awaited_once()
    assert resolution.seed_profile == "saleor_demo"
    assert resolution.fixtures.get("default_channel_id") == "Q2hhbm5lbDox"
