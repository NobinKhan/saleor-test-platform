"""Scenario recorder auth context tests."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.scenario_corpus import ScenarioStep
from app.services.scenario_variant_record import _token_for_auth_context, record_scenario_step


@pytest.mark.asyncio
async def test_token_for_auth_context_customer():
    with patch(
        "app.services.saleor_auth.ensure_customer_token",
        new_callable=AsyncMock,
        return_value="customer-jwt",
    ) as mock_customer:
        token = await _token_for_auth_context(
            saleor_url="http://example.com/graphql/",
            auth_context="customer",
            staff_token="staff-jwt",
        )
    assert token == "customer-jwt"
    mock_customer.assert_awaited_once()


@pytest.mark.asyncio
async def test_token_for_auth_context_staff():
    token = await _token_for_auth_context(
        saleor_url="http://example.com/graphql/",
        auth_context="staff",
        staff_token="staff-jwt",
    )
    assert token == "staff-jwt"


@pytest.mark.asyncio
async def test_record_scenario_step_uses_customer_token():
    step = ScenarioStep(
        step_id="04_checkout_customer_attach",
        scenario_id="checkout-lifecycle",
        order=4,
        name="Attach customer",
        auth_context="customer",
        input_sent="mutation { checkoutCustomerAttach { checkout { id } } }",
        variables={},
    )
    with patch(
        "app.services.scenario_variant_record._token_for_auth_context",
        new_callable=AsyncMock,
        return_value="customer-jwt",
    ) as mock_auth, patch(
        "app.services.scenario_variant_record._gql_query",
        new_callable=AsyncMock,
        return_value={"data": {"checkoutCustomerAttach": {"checkout": {"id": "x"}}}},
    ) as mock_gql:
        await record_scenario_step(
            saleor_url="http://example.com/graphql/",
            saleor_token="staff-jwt",
            scenario_id="checkout-lifecycle",
            step=step,
        )
    mock_auth.assert_awaited_once()
    mock_gql.assert_awaited_once()
    assert mock_gql.await_args[0][3] == "customer-jwt"
