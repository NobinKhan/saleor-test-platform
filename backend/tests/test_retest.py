"""Retest and credential storage tests."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.crypto import decrypt_token, encrypt_token
from app.models import TestRun, User
from app.routes.tests import retest_run
from app.services.run_helpers import build_test_run_row


def test_build_test_run_row_roundtrips_local_email():
    user_id = uuid.uuid4()
    row = build_test_run_row(
        user_id=user_id,
        saleor_url="http://192.168.1.1:8000/graphql/",
        saleor_email="merchant@demo.basmalahub.local",
        saleor_password="changeme",
        saleor_token="jwt-token",
        test_scope="queries",
        public_only=False,
        concurrency=3,
        timeout_seconds=15,
    )
    assert decrypt_token(row["saleor_email"]) == "merchant@demo.basmalahub.local"
    assert decrypt_token(row["saleor_password"]) == "changeme"
    assert row["test_scope"] == "queries"
    assert row["concurrency"] == 3


@pytest.mark.asyncio
async def test_retest_run_clones_config_and_starts_runner():
    user_id = uuid.uuid4()
    run_id = uuid.uuid4()
    user = User(id=user_id, email="test@example.com", name="Test", password_hash="x")

    source = TestRun(
        id=run_id,
        user_id=user_id,
        saleor_url="http://saleor.local/graphql/",
        saleor_token=encrypt_token("old-jwt"),
        saleor_email=encrypt_token("merchant@demo.basmalahub.local"),
        saleor_password=encrypt_token("changeme"),
        test_scope="mutations",
        public_only=True,
        concurrency=7,
        timeout_seconds=45,
        status="completed",
    )

    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = source
    db.execute = AsyncMock(return_value=result_mock)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    new_run_holder: list[TestRun] = []

    def capture_add(run: TestRun):
        run.id = uuid.uuid4()
        run.total_tests = 0
        run.passed = 0
        run.failed = 0
        run.warnings = 0
        run.skipped = 0
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        new_run_holder.append(run)

    db.add.side_effect = capture_add

    with patch("app.routes.tests.authenticate_saleor", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = ("new-jwt", None)
        with patch("app.routes.tests._start_runner") as mock_start:
            summary = await retest_run(run_id, db=db, user=user)

    mock_auth.assert_awaited_once_with(
        "http://saleor.local/graphql/",
        "merchant@demo.basmalahub.local",
        "changeme",
    )
    mock_start.assert_called_once()
    assert len(new_run_holder) == 1
    assert new_run_holder[0].saleor_url == source.saleor_url
    assert new_run_holder[0].test_scope == "mutations"
    assert new_run_holder[0].public_only is True
    assert new_run_holder[0].concurrency == 7
    assert summary.saleor_url == source.saleor_url
    assert summary.id == new_run_holder[0].id
