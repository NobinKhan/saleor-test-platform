"""Customer JWT provisioning tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.saleor_auth import (
    DeleteCustomerResult,
    RegisterCustomerResult,
    _customer_delete_incompatible_warning,
    delete_harness_customer_by_email,
    ensure_customer_auth,
    ensure_customer_token,
    login_existing_customer,
    per_run_customer_email,
    register_customer_account,
    resolve_storefront_channel,
    try_unified_customer_login,
)


@pytest.mark.asyncio
async def test_register_customer_account_detects_top_level_duplicate():
    with patch(
        "app.services.saleor_auth._post_graphql",
        new_callable=AsyncMock,
        return_value={
            "data": None,
            "errors": [{"message": "customer with this email already exists"}],
        },
    ):
        result = await register_customer_account(
            "http://example.com/graphql/",
            "shopper@example.com",
            "secret",
        )
    assert result.account_exists is True
    assert result.session_token is None
    assert result.ok is False


@pytest.mark.asyncio
async def test_ensure_customer_token_uses_session_token():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        return_value=RegisterCustomerResult(True, "session-jwt", None),
    ) as mock_register:
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            force_refresh=True,
        )
    assert token == "session-jwt"
    mock_register.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_customer_token_logs_in_when_account_exists():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        side_effect=[False, True],
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        return_value=RegisterCustomerResult(
            False, None, "already exists", account_exists=True
        ),
    ), patch(
        "app.services.saleor_auth.login_existing_customer",
        new_callable=AsyncMock,
        return_value="customer-jwt",
    ) as mock_login:
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            staff_token="staff-jwt",
            force_refresh=True,
        )
    assert token == "customer-jwt"
    mock_login.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_customer_token_disables_confirmation_then_registers():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        side_effect=[
            RegisterCustomerResult(True, None, None),
            RegisterCustomerResult(True, None, None),
            RegisterCustomerResult(True, "session-jwt", None),
        ],
    ), patch(
        "app.services.saleor_auth.prepare_storefront_customer_auth",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_prepare:
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            staff_token="staff-jwt",
            force_refresh=True,
        )
    assert token == "session-jwt"
    mock_prepare.assert_awaited()


@pytest.mark.asyncio
async def test_ensure_customer_token_confirms_via_staff_then_login():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        side_effect=[False, True],
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        return_value=RegisterCustomerResult(
            False, None, "already exists", account_exists=True
        ),
    ), patch(
        "app.services.saleor_auth.prepare_storefront_customer_auth",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.saleor_auth.login_existing_customer",
        new_callable=AsyncMock,
        side_effect=[None, "customer-jwt"],
    ) as mock_login, patch(
        "app.services.saleor_auth.confirm_customer_via_staff",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_confirm:
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            staff_token="staff-jwt",
            force_refresh=True,
        )
    assert token == "customer-jwt"
    mock_confirm.assert_awaited_once()
    assert mock_login.await_count == 2


@pytest.mark.asyncio
async def test_ensure_customer_token_deletes_and_reregisters_when_login_fails():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        side_effect=[
            RegisterCustomerResult(
                False, None, "already exists", account_exists=True
            ),
            RegisterCustomerResult(
                False, None, "already exists", account_exists=True
            ),
            RegisterCustomerResult(True, "fresh-session-jwt", None),
        ],
    ), patch(
        "app.services.saleor_auth.login_existing_customer",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.saleor_auth.confirm_customer_via_staff",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.saleor_auth.delete_harness_customer_by_email",
        new_callable=AsyncMock,
        return_value=DeleteCustomerResult(True, None),
    ) as mock_delete:
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            staff_token="staff-jwt",
            force_refresh=True,
        )
    assert token == "fresh-session-jwt"
    mock_delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_customer_token_returns_none_when_delete_fails_without_run_id():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        return_value=RegisterCustomerResult(
            False, None, "already exists", account_exists=True
        ),
    ), patch(
        "app.services.saleor_auth.login_existing_customer",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.saleor_auth.confirm_customer_via_staff",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.saleor_auth.delete_harness_customer_by_email",
        new_callable=AsyncMock,
        return_value=DeleteCustomerResult(
            False, "Invalid ID: VXNlcjoy. Expected: User."
        ),
    ):
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            staff_token="staff-jwt",
            force_refresh=True,
        )
    assert token is None


@pytest.mark.asyncio
async def test_ensure_customer_auth_per_run_fallback_when_delete_fails():
    run_id = "e2052d4c-aaaa-bbbb-cccc-ddddeeeeffff"
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        side_effect=[
            RegisterCustomerResult(
                False, None, "already exists", account_exists=True
            ),
            RegisterCustomerResult(
                False, None, "already exists", account_exists=True
            ),
            RegisterCustomerResult(True, "fallback-session-jwt", None),
        ],
    ), patch(
        "app.services.saleor_auth.login_existing_customer",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.saleor_auth.confirm_customer_via_staff",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.saleor_auth.delete_harness_customer_by_email",
        new_callable=AsyncMock,
        return_value=DeleteCustomerResult(
            False, "Invalid ID: VXNlcjoy. Expected: User."
        ),
    ):
        result = await ensure_customer_auth(
            saleor_url="http://example.com/graphql/",
            token=None,
            email="shopper@example.com",
            password="secret",
            staff_token="staff-jwt",
            force_refresh=True,
            run_id=run_id,
        )
    assert result.token == "fallback-session-jwt"
    assert result.effective_email == per_run_customer_email(run_id)
    assert any("customer_delete_incompatible" in w for w in result.warnings)


def test_customer_delete_incompatible_warning_detects_relay_defect():
    warning = _customer_delete_incompatible_warning(
        "Invalid ID: VXNlcjoy. Expected: User."
    )
    assert warning is not None
    assert "customer_delete_incompatible" in warning


@pytest.mark.asyncio
async def test_delete_harness_customer_by_email_verifies_removal():
    with patch(
        "app.services.saleor_auth._lookup_customer_id_by_email",
        new_callable=AsyncMock,
        return_value="VXNlcjoy",
    ), patch(
        "app.services.saleor_auth._post_graphql",
        new_callable=AsyncMock,
        return_value={
            "data": {
                "customerDelete": {
                    "user": {"id": "VXNlcjoy"},
                    "errors": [],
                }
            }
        },
    ), patch(
        "app.services.saleor_auth.customer_exists_by_email",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await delete_harness_customer_by_email(
            "http://example.com/graphql/",
            "staff-jwt",
            "shopper@example.com",
        )
    assert result.deleted is True


@pytest.mark.asyncio
async def test_try_unified_customer_login_rejects_staff_token():
    with patch(
        "app.services.saleor_auth.fetch_saleor_token",
        new_callable=AsyncMock,
        return_value=("staff-jwt", None),
    ), patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=False,
    ):
        token = await try_unified_customer_login(
            "http://example.com/graphql/",
            "shopper@example.com",
            "secret",
        )
    assert token is None


@pytest.mark.asyncio
async def test_login_existing_customer_uses_set_password_token():
    with patch(
        "app.services.saleor_auth.try_unified_customer_login",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "app.services.saleor_auth.login_via_set_password",
        new_callable=AsyncMock,
        return_value="reset-jwt",
    ) as mock_set_password:
        token = await login_existing_customer(
            "http://example.com/graphql/",
            "shopper@example.com",
            "secret",
            reset_token="reset-token",
        )
    assert token == "reset-jwt"
    mock_set_password.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_storefront_channel_prefers_live_default():
    with patch(
        "app.services.saleor_auth._list_active_channel_slugs",
        new_callable=AsyncMock,
        return_value=["default", "setup-ch-abc"],
    ):
        slug = await resolve_storefront_channel(
            "http://example.com/graphql/",
            "staff-jwt",
            fixtures={"default_channel": "harness-channel"},
        )
    assert slug == "default"


@pytest.mark.asyncio
async def test_ensure_customer_token_returns_none_when_all_paths_fail():
    with patch(
        "app.services.saleor_auth.validate_customer_token",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.saleor_auth.resolve_storefront_channel",
        new_callable=AsyncMock,
        return_value="default",
    ), patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        return_value=RegisterCustomerResult(True, None, None),
    ), patch(
        "app.services.saleor_auth.prepare_storefront_customer_auth",
        new_callable=AsyncMock,
        return_value=False,
    ), patch(
        "app.services.saleor_auth.login_existing_customer",
        new_callable=AsyncMock,
        return_value=None,
    ):
        token = await ensure_customer_token(
            saleor_url="http://example.com/graphql/",
            token=None,
            email=None,
            password=None,
            staff_token=None,
            force_refresh=True,
        )
    assert token is None
