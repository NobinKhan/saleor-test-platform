"""E2E certification API test — requires full stack (SALEOR_E2E=1)."""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.skipif(
    os.environ.get("SALEOR_E2E") != "1",
    reason="Set SALEOR_E2E=1 with harness + Saleor running",
)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@pytest.mark.asyncio
async def test_certification_api_validate_and_run():
    from app.main import app

    harness_email = _env("HARNESS_TEST_EMAIL", "test@example.com")
    harness_password = _env("HARNESS_TEST_PASSWORD", "testpass123")
    saleor_url = _env("SALEOR_E2E_URL", "http://host.docker.internal:8000/graphql/")
    saleor_email = _env("SALEOR_E2E_EMAIL", "admin@example.com")
    saleor_password = _env("SALEOR_E2E_PASSWORD", "admin123456")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": harness_email, "password": harness_password},
        )
        if login.status_code == 401:
            reg = await client.post(
                "/api/auth/register",
                json={
                    "email": harness_email,
                    "password": harness_password,
                    "name": "E2E Test",
                },
            )
            assert reg.status_code in (201, 400), reg.text
            login = await client.post(
                "/api/auth/login",
                json={"email": harness_email, "password": harness_password},
            )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        validate_payload = {
            "saleor_url": saleor_url,
            "saleor_email": saleor_email,
            "saleor_password": saleor_password,
        }
        validate_resp = await client.post(
            "/api/runs/validate", json=validate_payload, headers=headers
        )
        assert validate_resp.status_code == 200, validate_resp.text
        validate_body = validate_resp.json()
        assert validate_body.get("api_reachable") is True
        assert validate_body.get("version_gate_pass") is not False

        run_resp = await client.post(
            "/api/runs",
            json={
                **validate_payload,
                "concurrency": 3,
                "timeout_seconds": 60,
            },
            headers=headers,
        )
        assert run_resp.status_code == 200, run_resp.text
        run_id = run_resp.json()["id"]

        deadline = asyncio.get_event_loop().time() + 900
        status = "running"
        while asyncio.get_event_loop().time() < deadline:
            detail = await client.get(f"/api/runs/{run_id}", headers=headers)
            assert detail.status_code == 200
            status = detail.json()["status"]
            if status in ("completed", "failed", "stopped"):
                break
            await asyncio.sleep(5)

        assert status == "completed", f"Run ended with status {status}"

        report = await client.get(f"/api/reports/{run_id}", headers=headers)
        assert report.status_code == 200, report.text
        summary = report.json()["summary"]
        assert summary.get("schema_gate_pass") is True
        assert summary.get("certified") is True
        assert summary.get("effective_score") == 100.0
