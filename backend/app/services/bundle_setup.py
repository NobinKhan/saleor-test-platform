"""
Per-bundle L3 setup mutations (mutation-first L3 extension).

Each bundle_setup entry defines a chain of mutations to run BEFORE the probe,
creating the exact prerequisite state needed for the probe to hit its golden
response path. The returned entity IDs are stored in the overlay and merged
into bundle_fixtures, so {{fixtures.*}} substitutions in probe variables
resolve to the newly-created IDs rather than stale static fixture IDs.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.services.saleor_auth import CUSTOMER_DEFAULT_EMAIL, CUSTOMER_DEFAULT_PASSWORD

RunSetupFn = Callable[[dict[str, Any], str], Awaitable[str | None]]

# Shared step: create a second variant on the harness reference product.
# Stored as secondary_variant_id; see usage in productvariantsetdefault etc.
_SECONDARY_VARIANT_STEP: dict[str, Any] = {
    "mutation": """mutation($input: ProductVariantCreateInput!) {
        productVariantCreate(input: $input) {
            productVariant { id }
            errors { field message }
        }
    }""",
    "variables": lambda fixtures: {
        "input": {
            "product": fixtures.get("default_product_id"),
            "sku": "harness-second-variant",
            "attributes": [],
            "channelListings": [
                {
                    "channelId": fixtures.get("default_channel_id"),
                    "price": "12.00",
                }
            ],
        }
    },
    "extract": "$.data.productVariantCreate.productVariant.id",
    "fixture_key": "secondary_variant_id",
    "auth": "staff",
}


def _customer_step(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Return a step that registers + confirms a customer account, returning user id."""
    return {
        "mutation": """mutation($input: AccountRegisterInput!) {
            accountRegister(input: $input) {
                user { id email }
                errors { field message code }
            }
        }""",
        "variables": lambda f: {
            "input": {
                "email": CUSTOMER_DEFAULT_EMAIL,
                "password": CUSTOMER_DEFAULT_PASSWORD,
                "channel": f.get("default_channel", "harness-channel"),
                "redirectUrl": "http://localhost:3000/account/confirm",
            }
        },
        "extract": "$.data.accountRegister.user.id",
        "fixture_key": "_setup_customer_id",
        "auth": "anonymous",
    }


def _checkout_create_step(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Return a step that creates an anonymous checkout, returning checkout id."""
    return {
        "mutation": """mutation($input: CheckoutCreateInput!) {
            checkoutCreate(input: $input) {
                checkout { id token }
                errors { field message }
            }
        }""",
        "variables": lambda f: {
            "input": {
                "channel": f.get("default_channel", "harness-channel"),
                "lines": [
                    {
                        "quantity": 1,
                        "variantId": f.get("variant_id_for_cart") or f.get("default_variant_id"),
                    }
                ],
            }
        },
        "extract": "$.data.checkoutCreate.checkout.id",
        "fixture_key": "_setup_checkout_id",
        "auth": "anonymous",
    }


def _checkout_attach_customer_step(fixtures: dict[str, Any]) -> dict[str, Any]:
    """Return a step that attaches a customer to the checkout, returning checkout id."""
    return {
        "mutation": """mutation($id: ID!, $customerId: ID!) {
            checkoutCustomerAttach(id: $id, customerId: $customerId) {
                checkout { id user { id } }
                errors { field message code }
            }
        }""",
        "variables": lambda f: {
            "id": f.get("_setup_checkout_id") or f.get("default_checkout_id"),
            "customerId": f.get("_setup_customer_id") or f.get("storefront_customer_id"),
        },
        "extract": "$.data.checkoutCustomerAttach.checkout.id",
        "fixture_key": "_setup_checkout_id",
        "auth": "customer",
    }


BUNDLE_SETUP: dict[str, list[dict[str, Any]]] = {
    # ── Dashboard variants ────────────────────────────────────────────────────
    # These need a second variant on the harness reference product so the
    # probe (which operates on the DEFAULT variant) has a valid product.
    # The secondary variant is stored as default_variant_id so the probe's
    # {{fixtures.default_variant_id}} substitution resolves correctly.
    "productvariantsetdefault": [
        _SECONDARY_VARIANT_STEP,
        {
            # Copy the created secondary variant id into the key the probe reads.
            "mutation": None,
            "variables": lambda fixtures: {},
            "extract": None,
            "fixture_key": "default_variant_id",
            "auth": "staff",
            "_from_key": "secondary_variant_id",
        },
    ],
    "productvariantreorder": [_SECONDARY_VARIANT_STEP],
    "productvariantbulkdelete": [_SECONDARY_VARIANT_STEP],
    "productvariantbulkupdate": [_SECONDARY_VARIANT_STEP],
    # ── Storefront: accountUpdate ──────────────────────────────────────────
    # Probe: accountUpdate (auth: customer)
    # Golden: success_with_data — the customer already has profile "Harness Updated"
    # Fix: register customer + update profile BEFORE the probe runs so the
    # customer session has the expected data and the mutation returns success.
    "sf-accountupdate": [
        _customer_step({}),
        {
            "mutation": """mutation($input: AccountInput!) {
                accountUpdate(input: $input) {
                    user { id firstName lastName }
                    errors { field message code }
                }
            }""",
            "variables": lambda fixtures: {
                "input": {
                    "firstName": "Harness",
                    "lastName": "Updated",
                }
            },
            "extract": "$.data.accountUpdate.user.id",
            "fixture_key": "account_update_user_id",
            "auth": "customer",
            "_from_key": None,  # use current user token, not a fixture key
        },
    ],
    # ── Storefront: checkoutCreate ──────────────────────────────────────────
    # Probe: checkoutCreate (auth: anonymous) → creates a new checkout
    # Golden: success_with_data with a specific checkout+variant from recording
    # Fix: create a variant so the checkoutCreate succeeds; the returned
    # variant id is stored as variant_id_for_cart so the probe uses it.
    "sf-checkoutcreate": [
        _SECONDARY_VARIANT_STEP,
        {
            # Store the created secondary variant as variant_id_for_cart.
            "mutation": None,
            "variables": lambda fixtures: {},
            "extract": None,
            "fixture_key": "variant_id_for_cart",
            "auth": "staff",
            "_from_key": "secondary_variant_id",
        },
    ],
    # ── Storefront: checkoutCustomerAttach ─────────────────────────────────
    # Probe: checkoutCustomerAttach (auth: customer) → expects PermissionDenied
    #   ("cannot reassign a checkout already attached to a user")
    # Golden: graphql_error — already attached
    # Fix: create a customer, create a checkout, attach the customer to it,
    # then the probe tries to attach the same customer again → PermissionDenied.
    "categorydetails-aftercreate": [
        {
            "mutation": "mutation($input: CategoryInput!) { categoryCreate(input: $input) { category { id slug } errors { field message code } } }",
            "variables": lambda f: {"input": {"name": "Harness Smoke Category", "slug": ""}},
            "extract": "$.data.categoryCreate.category.id",
            "fixture_key": "_smoke_category_id",
            "auth": "staff",
        },
    ],
    "externalrefresh-success": [
        {
            "mutation": "mutation($email: String!, $password: String!) { tokenCreate(email: $email, password: $password) { token refreshToken errors { field message code } } }",
            "variables": lambda f: {
                "email": f.get("staff_email") or "admin@example.com",
                "password": f.get("staff_password") or "admin123456",
            },
            "extract": "$.data.tokenCreate.refreshToken",
            "fixture_key": "refresh_token",
            "auth": "staff",
        },
    ],
    "sf-checkoutcustomerattach": [
        _customer_step({}),
        _checkout_create_step({}),
        _checkout_attach_customer_step({}),
        {
            # Ensure downstream probes (sf-checkoutshippingmethods, etc.) share
            # the same preamble checkout that has a customer attached.
            "mutation": None,
            "variables": lambda fixtures: {},
            "extract": None,
            "fixture_key": "default_checkout_id",
            "auth": "staff",
            "_from_key": "_setup_checkout_id",
        },
    ],
    # ── Storefront: checkout lines/add ─────────────────────────────────────
    # Probe: checkoutLinesAdd (auth: anonymous) → adds lines to an existing checkout
    # Golden: success_with_data
    # Shares the preamble checkout via storefront_fixture_overlay (Fix 1).
    # No bundle_setup needed here; the overlay propagates default_checkout_id.
    # ── Storefront: remaining checkout probes ────────────────────────────────
    # sf-checkoutshippingmethods, sf-checkoutbytoken, sf-checkoutemailupdate:
    # all use {{fixtures.default_checkout_id}} — this is now propagated from the
    # preamble via _storefront_fixture_overlay (Fix 1).
}


def get_bundle_setup(bundle_id: str) -> list[dict[str, Any]]:
    """Return the setup chain for bundle_id, if any."""
    return BUNDLE_SETUP.get(bundle_id, [])


async def apply_bundle_setup(
    *,
    bundle_id: str,
    fixtures: dict[str, Any],
    run_setup_mutation: RunSetupFn,
) -> dict[str, Any]:
    """Run the per-bundle setup mutation chain; return a fixture overlay.

    The overlay maps fixture keys (e.g. default_checkout_id) to the IDs of
    entities created during setup. After the overlay is merged into
    bundle_fixtures, {{fixtures.*}} substitutions in probe variables resolve
    to the newly-created IDs instead of stale static fixture IDs.
    """
    overlay: dict[str, Any] = {}
    steps = get_bundle_setup(bundle_id)
    for step in steps:
        # No-op step used to copy one fixture key into another (e.g.
        # secondary_variant_id → default_variant_id).
        if step.get("mutation") is None and step.get("_from_key"):
            from_key = step["_from_key"]
            to_key = step["fixture_key"]
            value = overlay.get(from_key) or fixtures.get(from_key)
            if value:
                overlay[to_key] = value
            continue

        variables_fn = step.get("variables")
        if callable(variables_fn):
            variables = variables_fn({**fixtures, **overlay})
        else:
            variables = variables_fn or {}
        if not variables.get("input", variables):
            continue
        setup = {
            "mutation": step["mutation"],
            "variables": variables,
            "extract": step.get("extract"),
        }
        entity_id = await run_setup_mutation(setup, step.get("auth", "staff"))
        key = step.get("fixture_key")
        if entity_id and key:
            overlay[key] = entity_id
    return overlay
