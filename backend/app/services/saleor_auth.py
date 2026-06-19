"""
app/services/saleor_auth.py — Staff and customer JWT helpers for Saleor replay.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings
from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.reference_seed import REFERENCE_CHANNEL_SLUG

logger = logging.getLogger(__name__)

TOKEN_CREATE_MUTATION = """
mutation TokenCreate($email: String!, $password: String!) {
  tokenCreate(email: $email, password: $password) {
    token
    errors { field message code }
  }
}
"""

ME_QUERY = "query { me { id email } }"

ACCOUNT_REGISTER_MUTATION = """
mutation AccountRegister($input: AccountRegisterInput!) {
  accountRegister(input: $input) {
    user { id email }
    sessionToken
    errors { field message code }
  }
}
"""

SHOP_SETTINGS_UPDATE_MUTATION = """
mutation HarnessShopSettings($input: ShopSettingsInput!) {
  shopSettingsUpdate(input: $input) {
    shop { enableAccountConfirmationByEmail }
    errors { field message code }
  }
}
"""

REQUEST_PASSWORD_RESET_MUTATION = """
mutation RequestPasswordReset($email: String!, $redirectUrl: String!) {
  requestPasswordReset(email: $email, redirectUrl: $redirectUrl) {
    errors { field message code }
  }
}
"""

SET_PASSWORD_MUTATION = """
mutation SetPassword($email: String!, $password: String!, $token: String!) {
  setPassword(email: $email, password: $password, token: $token) {
    token
    refreshToken
    errors { field message code }
  }
}
"""

CHANNELS_QUERY = "query { channels { slug isActive } }"

CUSTOMER_DEFAULT_EMAIL = "harness-storefront-customer@example.com"
CUSTOMER_DEFAULT_PASSWORD = "HarnessCustomer123!"
HARNESS_DEFAULT_CHANNEL = "harness-channel"

_ACCOUNT_EXISTS_CODES = frozenset({"UNIQUE", "ALREADY_EXISTS", "UNIQUE_VIOLATION"})
_ACCOUNT_EXISTS_PHRASES = (
    "already exists",
    "unique constraint",
    "duplicate",
)


@dataclass(frozen=True)
class RegisterCustomerResult:
    ok: bool
    session_token: str | None
    error: str | None
    account_exists: bool = False


@dataclass(frozen=True)
class CustomerAuthResult:
    token: str | None
    effective_email: str
    warnings: tuple[str, ...] = ()


def per_run_customer_email(run_id: str) -> str:
    """Unique storefront customer email for a certification run."""
    slug = str(run_id).replace("-", "")[:8]
    return f"harness-customer-{slug}@example.com"


def _customer_delete_incompatible_warning(delete_error: str | None) -> str | None:
    if not delete_error:
        return None
    lower = delete_error.lower()
    if "invalid id" in lower and "expected" in lower:
        return (
            "customer_delete_incompatible: staff customerDelete rejects relay ID "
            "from customers query (target API defect vs Saleor)"
        )
    return None


def _format_saleor_auth_error(message: str) -> str:
    if 'relation "' in message and '" does not exist' in message:
        return (
            "Saleor database not migrated — run `just fresh` or wait for "
            "stack migrations to complete after `just up`."
        )
    return message


def _message_indicates_account_exists(message: str) -> bool:
    lower = (message or "").lower()
    return any(phrase in lower for phrase in _ACCOUNT_EXISTS_PHRASES)


def _top_level_errors_indicate_account_exists(data: dict) -> bool:
    for err in data.get("errors") or []:
        if _message_indicates_account_exists(err.get("message", "")):
            return True
        code = (err.get("extensions") or {}).get("code", "")
        if isinstance(code, str) and code.lower() in {"unique", "already_exists"}:
            return True
    return False


async def _post_graphql(
    saleor_url: str,
    query: str,
    *,
    variables: dict | None = None,
    token: str | None = None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
) -> dict | None:
    graphql_url = resolve_saleor_url_for_runner(saleor_url)
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload: dict = {"query": query}
    if variables is not None:
        payload["variables"] = variables
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        resp = await http.post(graphql_url, json=payload, headers=headers)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None
    finally:
        if own_client:
            await http.aclose()


async def _list_active_channel_slugs(
    saleor_url: str,
    staff_token: str | None,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> list[str]:
    data = await _post_graphql(
        saleor_url,
        CHANNELS_QUERY,
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    if not data:
        return []
    channels = (data.get("data") or {}).get("channels") or []
    slugs: list[str] = []
    for ch in channels:
        if not isinstance(ch, dict):
            continue
        slug = ch.get("slug")
        if slug and ch.get("isActive", True):
            slugs.append(str(slug))
    return slugs


async def resolve_storefront_channel(
    saleor_url: str,
    staff_token: str | None,
    *,
    fixtures: dict | None = None,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Pick a channel slug that exists on the target for accountRegister."""
    fixtures = fixtures or {}
    slugs = await _list_active_channel_slugs(
        saleor_url, staff_token, timeout=timeout, client=client
    )
    slug_set = set(slugs)

    for candidate in (
        fixtures.get("default_channel"),
        REFERENCE_CHANNEL_SLUG,
        HARNESS_DEFAULT_CHANNEL,
        "default",
        "default-channel",
    ):
        if candidate and candidate in slug_set:
            return str(candidate)

    if slugs:
        return slugs[0]

    return str(fixtures.get("default_channel") or REFERENCE_CHANNEL_SLUG)


async def validate_customer_token(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Return True when Bearer resolves a logged-in user via me."""
    if not token:
        return False
    data = await _post_graphql(
        saleor_url, ME_QUERY, token=token, timeout=timeout, client=client
    )
    if not data:
        return False
    me = (data.get("data") or {}).get("me")
    return isinstance(me, dict) and bool(me.get("id"))


async def validate_saleor_token(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Return True when the token resolves a user via me (staff or customer)."""
    return await validate_customer_token(saleor_url, token, timeout, client)


async def refresh_saleor_token(
    saleor_url: str,
    email: str,
    password: str,
    timeout: int = 30,
) -> tuple[Optional[str], Optional[str]]:
    """Re-authenticate with Saleor staff credentials and return a fresh JWT."""
    return await fetch_saleor_token(saleor_url, email, password, timeout)


async def ensure_valid_token(
    *,
    saleor_url: str,
    token: str | None,
    email: str | None,
    password: str | None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
    force_refresh: bool = False,
) -> str | None:
    """Validate staff token via me; refresh with credentials when invalid or forced."""
    if not force_refresh and token and await validate_saleor_token(
        saleor_url, token, timeout, client
    ):
        return token
    if email and password:
        new_token, _err = await refresh_saleor_token(
            saleor_url, email, password, timeout
        )
        if new_token:
            return new_token
    return token


async def fetch_saleor_token(
    saleor_url: str,
    email: str,
    password: str,
    timeout: int = 15,
) -> tuple[Optional[str], Optional[str]]:
    """Staff/dashboard login via tokenCreate. Not for customer auth_context replay."""
    graphql_url = resolve_saleor_url_for_runner(saleor_url)
    payload = {
        "operationName": "TokenCreate",
        "query": TOKEN_CREATE_MUTATION,
        "variables": {"email": email, "password": password},
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(graphql_url, json=payload, headers=headers)

        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"

        data = resp.json()
        top_errors = data.get("errors") or []
        if top_errors:
            msg = top_errors[0].get("message", "Saleor GraphQL error")
            return None, _format_saleor_auth_error(msg)

        result = (data.get("data") or {}).get("tokenCreate") or {}
        errors = result.get("errors") or []

        if errors:
            msg = errors[0].get("message", "Authentication failed")
            return None, _format_saleor_auth_error(msg)

        token = result.get("token")
        if not token:
            body_text = resp.text[:300]
            if "suspended" in body_text.lower():
                return None, "Saleor login rate-limited — wait and retry or restart saleor-cache"
            return None, "No token returned from Saleor"

        return token, None

    except httpx.TimeoutException:
        return None, "Connection timed out"
    except httpx.HTTPError as e:
        return None, f"HTTP error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


async def register_customer_account(
    saleor_url: str,
    email: str,
    password: str,
    *,
    timeout: int = 15,
    channel: str = HARNESS_DEFAULT_CHANNEL,
    client: httpx.AsyncClient | None = None,
) -> RegisterCustomerResult:
    """Register a customer account.

    Returns RegisterCustomerResult with account_exists=True when the email is
    already registered (including top-level GraphQL duplicate errors).
    """
    data = await _post_graphql(
        saleor_url,
        ACCOUNT_REGISTER_MUTATION,
        variables={
            "input": {
                "email": email,
                "password": password,
                "channel": channel,
                "redirectUrl": "http://localhost:3000/account/confirm",
            }
        },
        timeout=timeout,
        client=client,
    )
    if not data:
        return RegisterCustomerResult(False, None, "Registration request failed")

    if _top_level_errors_indicate_account_exists(data):
        return RegisterCustomerResult(
            False, None, "Customer account already exists", account_exists=True
        )

    top_errors = data.get("errors") or []
    if top_errors and not (data.get("data") or {}).get("accountRegister"):
        msg = top_errors[0].get("message", "Registration failed")
        exists = _message_indicates_account_exists(msg)
        return RegisterCustomerResult(False, None, msg, account_exists=exists)

    result = (data.get("data") or {}).get("accountRegister") or {}
    errors = result.get("errors") or []
    if errors:
        code = (errors[0].get("code") or "").upper()
        msg = errors[0].get("message", "Registration failed")
        if code in _ACCOUNT_EXISTS_CODES or _message_indicates_account_exists(msg):
            return RegisterCustomerResult(
                False, None, msg or "Customer account already exists", account_exists=True
            )
        return RegisterCustomerResult(False, None, msg)

    session_token = result.get("sessionToken")
    return RegisterCustomerResult(True, session_token, None)


@dataclass(frozen=True)
class DeleteCustomerResult:
    deleted: bool
    error: str | None = None


CUSTOMER_DELETE_MUTATION = """
mutation DeleteCustomer($id: ID!) {
  customerDelete(id: $id) {
    user { id }
    errors { field message code }
  }
}
"""

CUSTOMER_BULK_DELETE_MUTATION = """
mutation BulkDeleteCustomers($ids: [ID!]!) {
  customerBulkDelete(ids: $ids) {
    count
    errors { field message code }
  }
}
"""


async def _lookup_customer_id_by_email(
    saleor_url: str,
    staff_token: str,
    email: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    lookup_query = """
query CustomerByEmail($email: String!) {
  customers(first: 1, filter: { search: $email }) {
    edges { node { id email } }
  }
}
"""
    lookup = await _post_graphql(
        saleor_url,
        lookup_query,
        variables={"email": email},
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    if not lookup:
        return None
    edges = (
        ((lookup.get("data") or {}).get("customers") or {}).get("edges") or []
    )
    if not edges:
        return None
    return (edges[0].get("node") or {}).get("id")


async def delete_harness_customer_by_email(
    saleor_url: str,
    staff_token: str,
    email: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> DeleteCustomerResult:
    """Delete a storefront customer by email so accountRegister can recreate it."""
    customer_id = await _lookup_customer_id_by_email(
        saleor_url, staff_token, email, timeout=timeout, client=client
    )
    if not customer_id:
        return DeleteCustomerResult(True, None)

    delete = await _post_graphql(
        saleor_url,
        CUSTOMER_DELETE_MUTATION,
        variables={"id": customer_id},
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    delete_errors: list[str] = []
    if delete:
        payload = (delete.get("data") or {}).get("customerDelete") or {}
        for err in payload.get("errors") or []:
            delete_errors.append(err.get("message") or "customerDelete failed")
        if not delete_errors and not (payload.get("user") or {}).get("id"):
            delete_errors.append("customerDelete returned no user")

    if delete_errors:
        bulk = await _post_graphql(
            saleor_url,
            CUSTOMER_BULK_DELETE_MUTATION,
            variables={"ids": [customer_id]},
            token=staff_token,
            timeout=timeout,
            client=client,
        )
        bulk_count = 0
        if bulk:
            bulk_payload = (bulk.get("data") or {}).get("customerBulkDelete") or {}
            bulk_count = int(bulk_payload.get("count") or 0)
            for err in bulk_payload.get("errors") or []:
                delete_errors.append(err.get("message") or "customerBulkDelete failed")
            if bulk_count <= 0 and not bulk_payload.get("errors"):
                delete_errors.append("customerBulkDelete removed 0 customers")

    still_exists = await customer_exists_by_email(
        saleor_url, staff_token, email, timeout=timeout, client=client
    )
    if not still_exists:
        return DeleteCustomerResult(True, None)

    err_msg = "; ".join(delete_errors) if delete_errors else "customer still exists after delete"
    logger.warning(
        "Could not delete harness customer %s (id=%s): %s",
        email,
        customer_id,
        err_msg,
    )
    return DeleteCustomerResult(False, err_msg)


async def customer_exists_by_email(
    saleor_url: str,
    staff_token: str,
    email: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Return True when staff can find a customer with the given email."""
    lookup_query = """
query CustomerByEmail($email: String!) {
  customers(first: 1, filter: { search: $email }) {
    edges { node { id email } }
  }
}
"""
    lookup = await _post_graphql(
        saleor_url,
        lookup_query,
        variables={"email": email},
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    if not lookup:
        return False
    edges = (
        ((lookup.get("data") or {}).get("customers") or {}).get("edges") or []
    )
    return bool(edges)


async def request_password_reset(
    saleor_url: str,
    email: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Trigger password reset email for an existing customer account."""
    data = await _post_graphql(
        saleor_url,
        REQUEST_PASSWORD_RESET_MUTATION,
        variables={
            "email": email,
            "redirectUrl": "http://localhost:3000/account/reset-password",
        },
        timeout=timeout,
        client=client,
    )
    if not data:
        return False
    if data.get("errors"):
        return False
    payload = (data.get("data") or {}).get("requestPasswordReset") or {}
    return not payload.get("errors")


async def login_via_set_password(
    saleor_url: str,
    email: str,
    password: str,
    reset_token: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Obtain customer JWT via setPassword when a reset token is available."""
    data = await _post_graphql(
        saleor_url,
        SET_PASSWORD_MUTATION,
        variables={"email": email, "password": password, "token": reset_token},
        timeout=timeout,
        client=client,
    )
    if not data:
        return None
    payload = (data.get("data") or {}).get("setPassword") or {}
    if payload.get("errors"):
        return None
    token = payload.get("token")
    if token and await validate_customer_token(saleor_url, token, timeout, client):
        return token
    return None


async def login_existing_customer(
    saleor_url: str,
    email: str,
    password: str,
    *,
    reset_token: str | None = None,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
    staff_token: str | None = None,
) -> str | None:
    """Log in an existing storefront customer (no accountRegister sessionToken)."""
    unified = await try_unified_customer_login(
        saleor_url, email, password, timeout=timeout, client=client
    )
    if unified:
        return unified

    token_value = (reset_token or settings.harness_customer_reset_token or "").strip()
    if not token_value and staff_token:
        await request_password_reset(saleor_url, email, timeout=timeout, client=client)
        token_value = (settings.harness_customer_reset_token or "").strip()

    if token_value:
        session = await login_via_set_password(
            saleor_url,
            email,
            password,
            token_value,
            timeout=timeout,
            client=client,
        )
        if session:
            return session

    return None


async def disable_account_confirmation_for_harness(
    saleor_url: str,
    staff_token: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Disable email confirmation so accountRegister returns sessionToken."""
    data = await _post_graphql(
        saleor_url,
        SHOP_SETTINGS_UPDATE_MUTATION,
        variables={"input": {"enableAccountConfirmationByEmail": False}},
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    if not data:
        return False
    payload = (data.get("data") or {}).get("shopSettingsUpdate") or {}
    if payload.get("errors"):
        return False
    shop = payload.get("shop") or {}
    return shop.get("enableAccountConfirmationByEmail") is False


async def prepare_storefront_customer_auth(
    saleor_url: str,
    staff_token: str | None,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Prepare target for harness customer registration (disable confirmation when possible)."""
    if not staff_token:
        return False
    return await disable_account_confirmation_for_harness(
        saleor_url, staff_token, timeout=timeout, client=client
    )


async def fetch_customer_token(
    saleor_url: str,
    email: str,
    password: str,
    timeout: int = 15,
) -> tuple[Optional[str], Optional[str]]:
    """Legacy alias — uses staff tokenCreate; do not use for customer auth_context."""
    return await fetch_saleor_token(saleor_url, email, password, timeout)


async def try_unified_customer_login(
    saleor_url: str,
    email: str,
    password: str,
    *,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Attempt tokenCreate for customer credentials (official Saleor only).

    Returns JWT only when me succeeds with that token — never returns staff JWT
    mistaken for customer session on split-login backends.
    """
    token, _err = await fetch_saleor_token(saleor_url, email, password, timeout)
    if not token:
        return None
    if await validate_customer_token(saleor_url, token, timeout, client):
        return token
    return None


async def confirm_customer_via_staff(
    saleor_url: str,
    staff_token: str,
    email: str,
    timeout: int = 15,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Confirm an unconfirmed customer account using staff credentials."""
    lookup_query = """
query CustomerByEmail($email: String!) {
  customers(first: 1, filter: { search: $email }) {
    edges { node { id } }
  }
}
"""
    update_mutation = """
mutation ConfirmCustomer($id: ID!, $input: CustomerInput!) {
  customerUpdate(id: $id, input: $input) {
    user { id isConfirmed }
    errors { field message code }
  }
}
"""
    lookup = await _post_graphql(
        saleor_url,
        lookup_query,
        variables={"email": email},
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    if not lookup:
        return False
    edges = (
        ((lookup.get("data") or {}).get("customers") or {}).get("edges") or []
    )
    if not edges:
        return False
    user_id = (edges[0].get("node") or {}).get("id")
    if not user_id:
        return False
    update = await _post_graphql(
        saleor_url,
        update_mutation,
        variables={"id": user_id, "input": {"isConfirmed": True}},
        token=staff_token,
        timeout=timeout,
        client=client,
    )
    if not update:
        return False
    payload = (update.get("data") or {}).get("customerUpdate") or {}
    if payload.get("errors"):
        return False
    return bool((payload.get("user") or {}).get("isConfirmed"))


async def _session_from_register_result(
    saleor_url: str,
    result: RegisterCustomerResult,
    *,
    timeout: int,
    client: httpx.AsyncClient | None,
) -> str | None:
    if result.session_token and await validate_customer_token(
        saleor_url, result.session_token, timeout, client
    ):
        return result.session_token
    return None


async def ensure_customer_auth(
    *,
    saleor_url: str,
    token: str | None,
    email: str | None,
    password: str | None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
    force_refresh: bool = False,
    channel: str = HARNESS_DEFAULT_CHANNEL,
    staff_token: str | None = None,
    fixtures: dict | None = None,
    run_id: str | None = None,
) -> CustomerAuthResult:
    """Ensure a valid customer access JWT; may use per-run email when delete/login fail."""
    warnings: list[str] = []
    cust_email = email or CUSTOMER_DEFAULT_EMAIL
    cust_password = password or CUSTOMER_DEFAULT_PASSWORD

    if not force_refresh and token and await validate_customer_token(
        saleor_url, token, timeout, client
    ):
        return CustomerAuthResult(token=token, effective_email=cust_email)

    channel_slug = await resolve_storefront_channel(
        saleor_url,
        staff_token,
        fixtures={"default_channel": channel, **(fixtures or {})},
        timeout=timeout,
        client=client,
    )

    if staff_token:
        await prepare_storefront_customer_auth(
            saleor_url, staff_token, timeout=timeout, client=client
        )

    async def _try_register(email_to_use: str) -> str | None:
        result = await register_customer_account(
            saleor_url,
            email_to_use,
            cust_password,
            timeout=timeout,
            channel=channel_slug,
            client=client,
        )
        return await _session_from_register_result(
            saleor_url, result, timeout=timeout, client=client
        )

    async def _try_fallback_email(fallback_email: str) -> CustomerAuthResult | None:
        session = await _try_register(fallback_email)
        if session:
            return CustomerAuthResult(
                token=session,
                effective_email=fallback_email,
                warnings=tuple(warnings),
            )
        logged_in = await login_existing_customer(
            saleor_url,
            fallback_email,
            cust_password,
            timeout=timeout,
            client=client,
            staff_token=staff_token,
        )
        if logged_in:
            return CustomerAuthResult(
                token=logged_in,
                effective_email=fallback_email,
                warnings=tuple(warnings),
            )
        return None

    session = await _try_register(cust_email)
    if session:
        return CustomerAuthResult(token=session, effective_email=cust_email)

    register_result = await register_customer_account(
        saleor_url,
        cust_email,
        cust_password,
        timeout=timeout,
        channel=channel_slug,
        client=client,
    )
    account_exists = register_result.account_exists
    if not account_exists and staff_token:
        account_exists = await customer_exists_by_email(
            saleor_url, staff_token, cust_email, timeout=timeout, client=client
        )

    if account_exists:
        logger.debug("Customer %s already exists — attempting login", cust_email)
        logged_in = await login_existing_customer(
            saleor_url,
            cust_email,
            cust_password,
            timeout=timeout,
            client=client,
            staff_token=staff_token,
        )
        if logged_in:
            return CustomerAuthResult(token=logged_in, effective_email=cust_email)

        if staff_token and await confirm_customer_via_staff(
            saleor_url, staff_token, cust_email, timeout=timeout, client=client
        ):
            logged_in = await login_existing_customer(
                saleor_url,
                cust_email,
                cust_password,
                timeout=timeout,
                client=client,
                staff_token=staff_token,
            )
            if logged_in:
                return CustomerAuthResult(token=logged_in, effective_email=cust_email)

        if staff_token:
            delete_result = await delete_harness_customer_by_email(
                saleor_url,
                staff_token,
                cust_email,
                timeout=timeout,
                client=client,
            )
            if delete_result.deleted:
                session = await _try_register(cust_email)
                if session:
                    return CustomerAuthResult(token=session, effective_email=cust_email)
            else:
                defect = _customer_delete_incompatible_warning(delete_result.error)
                if defect:
                    warnings.append(defect)

        if run_id:
            fallback_email = per_run_customer_email(run_id)
            logger.info(
                "Registering per-run storefront customer %s after fixed-email paths failed",
                fallback_email,
            )
            fallback = await _try_fallback_email(fallback_email)
            if fallback:
                return fallback

        if warnings:
            logger.warning("; ".join(warnings))
        logger.warning(
            "Could not obtain customer JWT for %s — login/delete/fallback failed",
            cust_email,
        )
        return CustomerAuthResult(
            token=None,
            effective_email=cust_email,
            warnings=tuple(warnings),
        )

    session = await _try_register(cust_email)
    if session:
        return CustomerAuthResult(token=session, effective_email=cust_email)

    logged_in = await login_existing_customer(
        saleor_url,
        cust_email,
        cust_password,
        timeout=timeout,
        client=client,
        staff_token=staff_token,
    )
    if logged_in:
        return CustomerAuthResult(token=logged_in, effective_email=cust_email)

    if run_id:
        fallback_email = per_run_customer_email(run_id)
        fallback = await _try_fallback_email(fallback_email)
        if fallback:
            return fallback

    if token and await validate_customer_token(saleor_url, token, timeout, client):
        return CustomerAuthResult(token=token, effective_email=cust_email)
    return CustomerAuthResult(
        token=None,
        effective_email=cust_email,
        warnings=tuple(warnings),
    )


async def ensure_customer_token(
    *,
    saleor_url: str,
    token: str | None,
    email: str | None,
    password: str | None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
    force_refresh: bool = False,
    channel: str = HARNESS_DEFAULT_CHANNEL,
    staff_token: str | None = None,
    fixtures: dict | None = None,
    run_id: str | None = None,
) -> str | None:
    """Ensure a valid customer access JWT for auth_context=customer replay."""
    result = await ensure_customer_auth(
        saleor_url=saleor_url,
        token=token,
        email=email,
        password=password,
        timeout=timeout,
        client=client,
        force_refresh=force_refresh,
        channel=channel,
        staff_token=staff_token,
        fixtures=fixtures,
        run_id=run_id,
    )
    return result.token
