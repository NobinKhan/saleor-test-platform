"""Schema gate tests."""

from app.services.schema_gate import compute_certified, compute_schema_gate


def test_schema_gate_pass_clean():
    gate = compute_schema_gate({})
    assert gate["schema_gate_pass"] is True


def test_schema_gate_fail_missing():
    gate = compute_schema_gate({
        "missing_queries": ["foo"],
        "missing_mutations": ["bar"],
    })
    assert gate["schema_gate_pass"] is False


def test_schema_gate_golden_source_label():
    gate = compute_schema_gate({
        "missing_queries": ["foo"],
        "schema_gate_source": "golden",
    })
    assert gate["schema_gate_source"] == "golden"
    assert "golden schema" in gate["schema_issues"][0]


def test_certified_requires_both():
    assert compute_certified(schema_gate_pass=True, compatibility_score=100.0) is True
    assert compute_certified(schema_gate_pass=False, compatibility_score=100.0) is False
    assert compute_certified(schema_gate_pass=True, compatibility_score=99.9) is False


def test_certified_requires_tier2_when_gaps():
    assert compute_certified(
        schema_gate_pass=True,
        compatibility_score=100.0,
        tier2_pass=False,
        parity_gaps=3,
    ) is False
    assert compute_certified(
        schema_gate_pass=True,
        compatibility_score=100.0,
        tier2_pass=True,
        parity_gaps=0,
    ) is True
