"""Customer JWT provisioning tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.saleor_auth import (
    _needs_email_confirmation,
    ensure_customer_token,
)


def test_needs_email_confirmation():
    assert _needs_email_confirmation("Account needs to be confirmed via email.")
    assert not _needs_email_confirmation("Invalid credentials")


@pytest.mark.asyncio
async def test_ensure_customer_token_confirms_via_staff():
    with patch(
        "app.services.saleor_auth.register_customer_account",
        new_callable=AsyncMock,
        return_value=(True, None),
    ), patch(
        "app.services.saleor_auth.fetch_customer_token",
        new_callable=AsyncMock,
        side_effect=[
            (None, "Account needs to be confirmed via email."),
            ("customer-jwt", None),
        ],
    ), patch(
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
    mock_confirm.assert_awaited_once_with(
        "http://example.com/graphql/",
        "staff-jwt",
        "shopper@example.com",
        timeout=30,
    )
