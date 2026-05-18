"""
app/services/saleor_auth.py — Fetch JWT from Saleor using admin credentials.
"""

import urllib.request
import urllib.error
import json
from typing import Optional


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
    payload = json.dumps({
        "operationName": "TokenCreate",
        "query": "mutation TokenCreate($email: String!, $password: String!) { tokenCreate(email: $email, password: $password) { token errors { field message code } } }",
        "variables": {"email": email, "password": password}
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        req = urllib.request.Request(saleor_url.rstrip("/") + "/graphql/", data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())

        result = data.get("data", {}).get("tokenCreate", {})
        errors = result.get("errors", [])

        if errors:
            return None, errors[0].get("message", "Authentication failed")

        token = result.get("token")
        if not token:
            return None, "No token returned from Saleor"

        return token, None

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(body)
            msg = err_json.get("errors", [{}])[0].get("message", str(e))
        except Exception:
            msg = f"HTTP {e.code}: {str(e)}"
        return None, msg

    except urllib.error.URLError as e:
        return None, f"Connection error: {e.reason}"

    except Exception as e:
        return None, f"Unexpected error: {str(e)}"