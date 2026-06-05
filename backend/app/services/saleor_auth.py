"""
app/services/saleor_auth.py — Fetch JWT from Saleor using admin credentials.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.url_utils import resolve_saleor_url_for_runner

TOKEN_CREATE_MUTATION = """
mutation TokenCreate($email: String!, $password: String!) {
  tokenCreate(email: $email, password: $password) {
    token
    errors { field message code }
  }
}
"""

ME_QUERY = "query { me { email } }"


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
            return None, top_errors[0].get("message", "Saleor GraphQL error")

        result = (data.get("data") or {}).get("tokenCreate") or {}
        errors = result.get("errors") or []

        if errors:
            return None, errors[0].get("message", "Authentication failed")

        token = result.get("token")
        if not token:
            return None, "No token returned from Saleor"

        return token, None

    except httpx.TimeoutException:
        return None, "Connection timed out"
    except httpx.HTTPError as e:
        return None, f"HTTP error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"
