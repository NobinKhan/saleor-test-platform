"""
app/services/saleor_auth.py — Fetch JWT from Saleor using admin credentials.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.url_utils import resolve_saleor_url_for_runner
from app.services.reference_seed import REFERENCE_CHANNEL_SLUG

TOKEN_CREATE_MUTATION = """
mutation TokenCreate($email: String!, $password: String!) {
  tokenCreate(email: $email, password: $password) {
    token
    errors { field message code }
  }
}
"""

ME_QUERY = "query { me { email } }"

ACCOUNT_REGISTER_MUTATION = """
mutation AccountRegister($input: AccountRegisterInput!) {
  accountRegister(input: $input) {
    user { id email }
    errors { field message code }
  }
}
"""

CUSTOMER_DEFAULT_EMAIL = "harness-storefront-customer@example.com"
CUSTOMER_DEFAULT_PASSWORD = "HarnessCustomer123!"
HARNESS_DEFAULT_CHANNEL = "harness-channel"


def _format_saleor_auth_error(message: str) -> str:
    if 'relation "' in message and '" does not exist' in message:
        return (
            "Saleor database not migrated — run `just fresh` or wait for "
            "stack migrations to complete after `just up`."
        )
    return message


async def validate_saleor_token(
    saleor_url: str,
    token: str | None,
    timeout: int = 30,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Return True when the token resolves a staff user via the me query."""
    if not token:
        return False
    graphql_url = resolve_saleor_url_for_runner(saleor_url)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=timeout)
    try:
        resp = await http.post(graphql_url, json={"query": ME_QUERY}, headers=headers)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return bool((data.get("data") or {}).get("me"))
    except Exception:
        return False
    finally:
        if own_client:
            await http.aclose()


async def refresh_saleor_token(
    saleor_url: str,
    email: str,
    password: str,
    timeout: int = 30,
) -> tuple[Optional[str], Optional[str]]:
    """Re-authenticate with Saleor and return a fresh JWT."""
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
    """Validate token via me; refresh with credentials when invalid or forced."""
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
    """
    Call Saleor's tokenCreate mutation with admin credentials.
    Returns (token, error_message).
    """
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
) -> tuple[bool, str | None]:
    """Register a customer account (idempotent — ignores duplicate email errors)."""
    graphql_url = resolve_saleor_url_for_runner(saleor_url)
    payload = {
        "query": ACCOUNT_REGISTER_MUTATION,
        "variables": {
            "input": {
                "email": email,
                "password": password,
                "channel": channel,
                "redirectUrl": "http://localhost:3000/account/confirm",
            }
        },
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(graphql_url, json=payload)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"
        data = resp.json()
        result = (data.get("data") or {}).get("accountRegister") or {}
        errors = result.get("errors") or []
        if errors:
            code = (errors[0].get("code") or "").upper()
            if code in ("UNIQUE", "ALREADY_EXISTS", "UNIQUE_VIOLATION"):
                return True, None
            return False, errors[0].get("message", "Registration failed")
        return True, None
    except Exception as exc:
        return False, str(exc)


async def fetch_customer_token(
    saleor_url: str,
    email: str,
    password: str,
    timeout: int = 15,
) -> tuple[Optional[str], Optional[str]]:
    """Obtain a customer JWT via tokenCreate."""
    return await fetch_saleor_token(saleor_url, email, password, timeout)


async def confirm_customer_via_staff(
    saleor_url: str,
    staff_token: str,
    email: str,
    timeout: int = 15,
) -> bool:
    """Confirm an unconfirmed customer account using staff credentials."""
    graphql_url = resolve_saleor_url_for_runner(saleor_url)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {staff_token}",
    }
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
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            lookup = await client.post(
                graphql_url,
                json={"query": lookup_query, "variables": {"email": email}},
                headers=headers,
            )
            if lookup.status_code != 200:
                return False
            edges = (
                ((lookup.json().get("data") or {}).get("customers") or {}).get("edges")
                or []
            )
            if not edges:
                return False
            user_id = (edges[0].get("node") or {}).get("id")
            if not user_id:
                return False
            update = await client.post(
                graphql_url,
                json={
                    "query": update_mutation,
                    "variables": {"id": user_id, "input": {"isConfirmed": True}},
                },
                headers=headers,
            )
            if update.status_code != 200:
                return False
            payload = (update.json().get("data") or {}).get("customerUpdate") or {}
            if payload.get("errors"):
                return False
            return bool((payload.get("user") or {}).get("isConfirmed"))
    except Exception:
        return False


def _needs_email_confirmation(error: str | None) -> bool:
    if not error:
        return False
    lowered = error.lower()
    return "confirm" in lowered or "confirmed" in lowered


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
) -> str | None:
    """Ensure a valid customer JWT, registering the account if needed."""
    if not force_refresh and token and await validate_saleor_token(
        saleor_url, token, timeout, client
    ):
        return token
    cust_email = email or CUSTOMER_DEFAULT_EMAIL
    cust_password = password or CUSTOMER_DEFAULT_PASSWORD
    await register_customer_account(
        saleor_url, cust_email, cust_password, timeout=timeout, channel=channel
    )
    new_token, err = await fetch_customer_token(
        saleor_url, cust_email, cust_password, timeout
    )
    if new_token:
        return new_token
    if staff_token and _needs_email_confirmation(err):
        if await confirm_customer_via_staff(
            saleor_url, staff_token, cust_email, timeout=timeout
        ):
            new_token, _err = await fetch_customer_token(
                saleor_url, cust_email, cust_password, timeout
            )
            if new_token:
                return new_token
    return token
