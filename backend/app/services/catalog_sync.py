"""
Sync static SALEOR_QUERIES / SALEOR_MUTATIONS catalog with corpus diff removals.
"""

from __future__ import annotations

import re
from pathlib import Path

TEST_RUNNER_PATH = Path(__file__).resolve().parent / "test_runner.py"


def _parse_removed_ops(removed_keys: list[str]) -> set[tuple[str, str]]:
    """Parse diff keys like orderCreate__MUTATION into (name, kind) pairs."""
    ops: set[tuple[str, str]] = set()
    for key in removed_keys:
        if "__" not in key:
            continue
        name, kind = key.rsplit("__", 1)
        ops.add((name, kind))
    return ops


def sync_catalog_from_diff(removed_keys: list[str]) -> int:
    """
    Remove deprecated ops from SALEOR_QUERIES / SALEOR_MUTATIONS in test_runner.py.
    Returns count of catalog entries removed.
    """
    if not removed_keys:
        return 0

    removed = _parse_removed_ops(removed_keys)
    if not removed:
        return 0

    text = TEST_RUNNER_PATH.read_text(encoding="utf-8")
    count = 0

    for name, kind in removed:
        # Match catalog dict entries: {"name": "opName", "kind": "QUERY", ...}
        pattern = (
            rf'\s*\{{"name": "{re.escape(name)}", "kind": "{kind}"[^}}]*\}},?\n'
        )
        new_text, n = re.subn(pattern, "", text)
        if n:
            text = new_text
            count += n

    if count:
        TEST_RUNNER_PATH.write_text(text, encoding="utf-8")

    return count
