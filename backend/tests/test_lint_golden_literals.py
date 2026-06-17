"""Golden literal linter tests."""

from __future__ import annotations

import json
from pathlib import Path

from app.scripts.lint_golden_literals import lint_golden_files


def test_lint_finds_demo_literal_in_temp_golden(tmp_path: Path):
    golden = tmp_path / "probe.json"
    golden.write_text(
        json.dumps({"golden_response": {"data": {"channel": {"slug": "channel-pln"}}}}),
        encoding="utf-8",
    )
    _ok, findings = lint_golden_files(extra_paths=[golden], blocking=False)
    assert any("channel-pln" in f.message for f in findings)


def test_lint_blocking_fails_on_findings(tmp_path: Path):
    golden = tmp_path / "bundle.graphql.json"
    golden.write_text(
        json.dumps({"golden_response": {"name": "Featured Products"}}),
        encoding="utf-8",
    )
    ok, findings = lint_golden_files(extra_paths=[golden], blocking=True)
    assert not ok
    assert findings
