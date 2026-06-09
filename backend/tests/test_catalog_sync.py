"""Tests for catalog sync from corpus diff."""

from app.services.catalog_sync import sync_catalog_from_diff


def test_sync_catalog_removes_deprecated_query(tmp_path, monkeypatch):
    import app.services.catalog_sync as mod

    sample = '''SALEOR_QUERIES: list[dict] = [
    {"name": "users", "kind": "QUERY", "category": "account", "is_public": False},
    {"name": "shop", "kind": "QUERY", "category": "shop", "is_public": True},
]
'''
    runner = tmp_path / "test_runner.py"
    runner.write_text(sample, encoding="utf-8")
    monkeypatch.setattr(mod, "TEST_RUNNER_PATH", runner)

    removed = sync_catalog_from_diff(["users__QUERY"])
    assert removed == 1
    text = runner.read_text(encoding="utf-8")
    assert "users" not in text
    assert "shop" in text


def test_sync_catalog_noop_on_empty():
    assert sync_catalog_from_diff([]) == 0
