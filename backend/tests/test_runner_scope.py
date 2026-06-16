"""Tests for L1 golden corpus endpoint building."""

from app.core.config import settings
from app.services.auth_visibility import infer_is_public
from app.services.test_runner import build_golden_endpoints


def test_build_golden_endpoints_returns_l1_corpus():
    version = settings.golden_corpus_version
    endpoints = build_golden_endpoints(version)
    assert len(endpoints) >= 380
    assert all(e.get("golden_input") for e in endpoints)
    kinds = {e["kind"] for e in endpoints}
    assert "QUERY" in kinds
    assert "MUTATION" in kinds


def test_infer_is_public_staff_queries():
    assert infer_is_public("orders", "QUERY") is False
    assert infer_is_public("products", "QUERY") is True
    assert infer_is_public("checkoutCreate", "MUTATION") is True
    assert infer_is_public("productCreate", "MUTATION") is False
