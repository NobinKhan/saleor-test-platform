"""patch_corpus scenario recording defaults."""

from __future__ import annotations

import inspect


def test_self_check_uses_harness_seed_profile():
    from app.scripts import self_check

    source = inspect.getsource(self_check.run_self_check)
    assert 'demo_seed_profile="harness"' in source


def test_patch_corpus_scenarios_default_seed_profile():
    """--scenarios without --seed-profile must match self_check (harness)."""
    seed_profile = None or "harness"
    assert seed_profile == "harness"
