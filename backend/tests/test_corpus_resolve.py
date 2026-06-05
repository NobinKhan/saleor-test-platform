"""Corpus version resolution tests."""

from app.services.reference_corpus import resolve_corpus_version


def test_resolve_prefers_exact_version_with_probes(monkeypatch):
    monkeypatch.setattr(
        "app.services.reference_corpus._has_probes",
        lambda v: v == "3.23.8",
    )
    assert resolve_corpus_version("3.23.8", "3.23.7") == "3.23.8"
