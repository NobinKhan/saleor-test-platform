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
