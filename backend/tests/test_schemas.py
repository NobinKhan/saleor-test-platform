"""Schema validation tests."""

import pytest
from pydantic import ValidationError

from app.schemas import TestRunCreate


def _minimal_run(**overrides):
    base = {
        "saleor_url": "http://localhost:8000/graphql/",
        "saleor_email": "admin@example.com",
        "saleor_password": "secret",
    }
    base.update(overrides)
    return TestRunCreate(**base)


def test_saleor_email_accepts_local_domain():
    run = _minimal_run(saleor_email="merchant@demo.basmalahub.local")
    assert run.saleor_email == "merchant@demo.basmalahub.local"


def test_saleor_email_accepts_standard_domain():
    run = _minimal_run(saleor_email="admin@example.com")
    assert run.saleor_email == "admin@example.com"


def test_saleor_email_strips_whitespace():
    run = _minimal_run(saleor_email="  user@host.local  ")
    assert run.saleor_email == "user@host.local"


def test_saleor_email_rejects_invalid():
    with pytest.raises(ValidationError):
        _minimal_run(saleor_email="not-an-email")
