"""
Storefront customer + checkout session preamble before sf-* CLIENT_BUNDLE replay.

Establishes customer profile and an anonymous checkout chain so checkout probes
do not hit "checkout access denied" on a staff-created guest checkout.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.services.reference_seed import _append_mutation_errors, _gql

logger = logging.getLogger(__name__)

US_SHIPPING_ADDRESS = {
    "firstName": "Harness",
    "lastName": "Checkout",
    "streetAddress1": "1 Checkout St",
    "city": "San Francisco",
    "countryArea": "CA",
    "postalCode": "94102",
    "country": "US",
}


def _anonymous_headers() -> dict[str, str]:
    return {"Content-Type": "application/json", "Accept": "application/json"}


def _customer_headers(token: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token.removeprefix('Bearer ')}",
    }


def _checkout_channel_slug(fixtures: dict[str, Any]) -> str:
    return (
        fixtures.get("storefront_channel")
        or fixtures.get("default_channel")
        or "default-channel"
    )


async def _update_customer_profile(
    client: httpx.AsyncClient,
    *,
    url: str,
    customer_token: str,
    error_log: list[str],
) -> bool:
    data = await _gql(
        client,
        url=url,
        headers=_customer_headers(customer_token),
        query=(
            "mutation($input: AccountInput!) { "
            "accountUpdate(input: $input) { user { id firstName lastName } "
            "errors { field message code } } }"
        ),
        variables={"input": {"firstName": "Harness", "lastName": "Updated"}},
        allow_errors=True,
        error_log=error_log,
        operation="accountUpdate",
    )
    payload = data.get("accountUpdate")
    user = (payload or {}).get("user")
    if user:
        return True
    _append_mutation_errors(error_log, "accountUpdate", payload)
    return False


async def _resolve_delivery_method_id(
    client: httpx.AsyncClient,
    *,
    url: str,
    checkout_id: str,
    fixtures: dict[str, Any],
) -> None:
    """Capture a shipping method id for scenario step 05 without setting delivery on checkout."""
    methods_data = await _gql(
        client,
        url=url,
        headers=_anonymous_headers(),
        query=(
            "query($id: ID!) { checkout(id: $id) { "
            "availableShippingMethods { id name } } }"
        ),
        variables={"id": checkout_id},
        allow_errors=True,
    )
    methods = ((methods_data.get("checkout") or {}).get("availableShippingMethods")) or []
    if methods and methods[0].get("id"):
        fixtures["delivery_method_id"] = methods[0]["id"]


async def _attach_customer_to_checkout(
    client: httpx.AsyncClient,
    *,
    url: str,
    customer_token: str,
    checkout_id: str,
    customer_id: str,
    error_log: list[str],
) -> bool:
    data = await _gql(
        client,
        url=url,
        headers=_customer_headers(customer_token),
        query=(
            "mutation($id: ID!, $customerId: ID!) { "
            "checkoutCustomerAttach(id: $id, customerId: $customerId) { "
            "checkout { id user { id } } errors { field message code } } }"
        ),
        variables={"id": checkout_id, "customerId": customer_id},
        allow_errors=True,
        error_log=error_log,
        operation="checkoutCustomerAttach",
    )
    payload = data.get("checkoutCustomerAttach")
    checkout = (payload or {}).get("checkout")
    if checkout:
        return True
    _append_mutation_errors(error_log, "checkoutCustomerAttach", payload)
    return False


async def _create_checkout_chain(
    client: httpx.AsyncClient,
    *,
    url: str,
    fixtures: dict[str, Any],
    error_log: list[str],
) -> dict[str, Any]:
    """Anonymous checkout: create → lines → shipping address (no delivery method)."""
    headers = _anonymous_headers()
    channel_slug = _checkout_channel_slug(fixtures)
    variant_id = fixtures.get("variant_id_for_cart") or fixtures.get("default_variant_id")
    if not variant_id:
        return fixtures

    create_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($input: CheckoutCreateInput!) { "
            "checkoutCreate(input: $input) { checkout { id token } "
            "errors { field message code } } }"
        ),
        variables={
            "input": {
                "channel": channel_slug,
                "lines": [{"quantity": 1, "variantId": variant_id}],
            }
        },
        allow_errors=True,
        error_log=error_log,
        operation="checkoutCreate",
    )
    checkout = (create_data.get("checkoutCreate") or {}).get("checkout")
    if not checkout:
        _append_mutation_errors(error_log, "checkoutCreate", create_data.get("checkoutCreate"))
        return fixtures

    checkout_id = checkout["id"]
    fixtures["default_checkout_id"] = checkout_id
    fixtures["default_checkout_token"] = checkout.get("token")
    fixtures["variant_id_for_cart"] = variant_id

    line_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $lines: [CheckoutLineInput!]!) { "
            "checkoutLinesAdd(id: $id, lines: $lines) { checkout { id } "
            "errors { field message code } } }"
        ),
        variables={
            "id": checkout_id,
            "lines": [{"quantity": 1, "variantId": variant_id}],
        },
        allow_errors=True,
        error_log=error_log,
        operation="checkoutLinesAdd",
    )
    if not (line_data.get("checkoutLinesAdd") or {}).get("checkout"):
        _append_mutation_errors(error_log, "checkoutLinesAdd", line_data.get("checkoutLinesAdd"))

    ship_data = await _gql(
        client,
        url=url,
        headers=headers,
        query=(
            "mutation($id: ID!, $shippingAddress: AddressInput!) { "
            "checkoutShippingAddressUpdate(id: $id, shippingAddress: $shippingAddress) { "
            "checkout { id } errors { field message code } } }"
        ),
        variables={"id": checkout_id, "shippingAddress": US_SHIPPING_ADDRESS},
        allow_errors=True,
        error_log=error_log,
        operation="checkoutShippingAddressUpdate",
    )
    if not (ship_data.get("checkoutShippingAddressUpdate") or {}).get("checkout"):
        _append_mutation_errors(
            error_log, "checkoutShippingAddressUpdate", ship_data.get("checkoutShippingAddressUpdate")
        )

    await _resolve_delivery_method_id(
        client, url=url, checkout_id=checkout_id, fixtures=fixtures
    )

    return fixtures


async def ensure_storefront_session(
    saleor_url: str,
    *,
    customer_token: str | None,
    fixtures: dict[str, Any],
    timeout: int = 60,
) -> tuple[dict[str, Any], set[str], list[str]]:
    """Run customer profile + anonymous checkout preamble; return updated fixtures."""
    seeded: set[str] = set()
    error_log: list[str] = []
    updated = dict(fixtures)

    async with httpx.AsyncClient(timeout=timeout) as client:
        if customer_token:
            if await _update_customer_profile(
                client, url=saleor_url, customer_token=customer_token, error_log=error_log
            ):
                seeded.add("storefront_customer_profile")

        existing_checkout = updated.get("default_checkout_id")
        if existing_checkout:
            await _resolve_delivery_method_id(
                client,
                url=saleor_url,
                checkout_id=existing_checkout,
                fixtures=updated,
            )
            if updated.get("delivery_method_id"):
                seeded.add("storefront_checkout_session")
            return updated, seeded, error_log

        updated = await _create_checkout_chain(
            client, url=saleor_url, fixtures=updated, error_log=error_log
        )
        if updated.get("default_checkout_id"):
            seeded.add("storefront_checkout_session")

        customer_id = updated.get("storefront_customer_id")
        checkout_id = updated.get("default_checkout_id")
        if customer_token and customer_id and checkout_id:
            if await _attach_customer_to_checkout(
                client,
                url=saleor_url,
                customer_token=customer_token,
                checkout_id=checkout_id,
                customer_id=customer_id,
                error_log=error_log,
            ):
                seeded.add("storefront_checkout_customer_attach")

    return updated, seeded, error_log
