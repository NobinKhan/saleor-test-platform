"""patch_corpus scenario recording uses harness mutation-first topology."""

from pathlib import Path


def test_patch_corpus_scenarios_resolve_fixtures_before_record():
    source = Path(__file__).resolve().parents[1] / "app" / "scripts" / "patch_corpus.py"
    text = source.read_text(encoding="utf-8")
    assert "resolve_fixtures(args.url, token" in text
    assert "--seed-profile" not in text


def test_self_check_uses_concurrency_one():
    source = Path(__file__).resolve().parents[1] / "app" / "scripts" / "self_check.py"
    assert "concurrency=1" in source.read_text(encoding="utf-8")
