"""Run creation with credential clone from previous run."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.crypto import decrypt_token, encrypt_token
from app.models import TestRun, User
from app.routes.tests import create_run
from app.schemas import TestRunCreate
from app.services.run_helpers import build_test_run_row


def test_build_test_run_row_roundtrips_local_email():
    user_id = uuid.uuid4()
    row = build_test_run_row(
        user_id=user_id,
        saleor_url="http://192.168.1.1:8000/graphql/",
        saleor_email="merchant@demo.basmalahub.local",
        saleor_password="changeme",
        saleor_token="jwt-token",
        test_scope="full+client",
        public_only=False,
        concurrency=3,
        timeout_seconds=15,
    )
    assert decrypt_token(row["saleor_email"]) == "merchant@demo.basmalahub.local"
    assert decrypt_token(row["saleor_password"]) == "changeme"
    assert row["test_scope"] == "full+client"
    assert row["concurrency"] == 3


def test_create_run_rejects_non_certification_scope():
    with pytest.raises(ValueError, match="full\\+client"):
        TestRunCreate(
            saleor_url="http://saleor.local/graphql/",
            saleor_email="admin@example.com",
            saleor_password="secret",
            test_scope="full",
        )


@pytest.mark.asyncio
async def test_create_run_clones_password_from_source_run():
    user_id = uuid.uuid4()
    source_id = uuid.uuid4()
    user = User(id=user_id, email="test@example.com", name="Test", password_hash="x")

    source = TestRun(
        id=source_id,
        user_id=user_id,
        saleor_url="http://saleor.local/graphql/",
        saleor_token=encrypt_token("old-jwt"),
        saleor_email=encrypt_token("merchant@demo.basmalahub.local"),
        saleor_password=encrypt_token("changeme"),
        test_scope="full+client",
        public_only=False,
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

    data = TestRunCreate(
        saleor_url=source.saleor_url,
        saleor_email="merchant@demo.basmalahub.local",
        clone_from_run_id=source_id,
        concurrency=7,
        timeout_seconds=45,
    )

    with patch("app.routes.tests.authenticate_saleor", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = ("new-jwt", None)
        with patch("app.routes.tests._start_runner") as mock_start:
            summary = await create_run(data, db=db, user=user)

    mock_auth.assert_awaited_once_with(
        "http://saleor.local/graphql/",
        "merchant@demo.basmalahub.local",
        "changeme",
    )
    mock_start.assert_called_once()
    assert len(new_run_holder) == 1
    assert new_run_holder[0].saleor_url == source.saleor_url
    assert new_run_holder[0].test_scope == "full+client"
    assert new_run_holder[0].concurrency == 7
    assert summary.saleor_url == source.saleor_url
    assert summary.id == new_run_holder[0].id
