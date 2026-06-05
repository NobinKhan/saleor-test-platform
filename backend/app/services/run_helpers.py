"""Shared helpers for creating and summarizing test runs."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token
from app.services.saleor_auth import fetch_saleor_token
from app.services.test_runner import SALEOR_MUTATIONS, SALEOR_QUERIES

if TYPE_CHECKING:
    from app.models import TestRun


def catalog_counts() -> tuple[int, int]:
    return len(SALEOR_QUERIES), len(SALEOR_MUTATIONS)


def decrypt_saleor_email(run: TestRun) -> str | None:
    raw = run.saleor_email
    if not raw:
        return None
    return decrypt_token(raw)


async def authenticate_saleor(
    saleor_url: str,
    saleor_email: str,
    saleor_password: str,
) -> tuple[str | None, str | None]:
    return await fetch_saleor_token(saleor_url, saleor_email, saleor_password)


def build_test_run_row(
    *,
    user_id: uuid.UUID,
    saleor_url: str,
    saleor_email: str,
    saleor_password: str,
    saleor_token: str,
    test_scope: str,
    public_only: bool,
    concurrency: int,
    timeout_seconds: int,
) -> dict:
    settings = get_settings()
    q_count, m_count = catalog_counts()
    return {
        "user_id": user_id,
        "saleor_url": saleor_url,
        "saleor_token": encrypt_token(saleor_token),
        "saleor_email": encrypt_token(saleor_email),
        "saleor_password": encrypt_token(saleor_password),
        "test_scope": test_scope,
        "public_only": public_only,
        "concurrency": concurrency,
        "timeout_seconds": timeout_seconds,
        "reference_baseline_version": settings.reference_baseline_version,
        "reference_baseline_source": settings.reference_baseline_source,
        "status": "running",
    }


def run_detail_fields(run: TestRun) -> dict:
    q_count, m_count = catalog_counts()
    return {
        "saleor_email": decrypt_saleor_email(run),
        "saleor_password_masked": "••••••••",
        "concurrency": run.concurrency or 5,
        "timeout_seconds": run.timeout_seconds or 30,
        "reference_baseline_version": run.reference_baseline_version,
        "reference_baseline_source": run.reference_baseline_source,
        "reference_catalog_queries": q_count,
        "reference_catalog_mutations": m_count,
    }
