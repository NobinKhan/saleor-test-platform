"""Certification API integration tests.

Tests the certification pipeline: version gating, schema gating,
effective_score computation, and the compute_certified aggregator.
"""

from app.services.version_routing import (
    parse_major_minor,
    parse_version_parts,
    version_compatibility_warning,
    version_hard_gate_check,
)
from app.services.schema_gate import compute_schema_gate, compute_certified


# --- Version routing ---

def test_parse_major_minor_standard():
    assert parse_major_minor("3.23.7") == (3, 23)


def test_parse_major_minor_none():
    assert parse_major_minor(None) is None


def test_parse_major_minor_short():
    assert parse_major_minor("3") is None


def test_parse_version_parts_standard():
    assert parse_version_parts("3.23.7") == (3, 23, 7)


def test_parse_version_parts_none():
    assert parse_version_parts(None) is None


def test_parse_version_parts_short():
    assert parse_version_parts("3.23") is None


def test_version_compat_exact_match():
    assert version_compatibility_warning("3.23.7", "3.23.7") is None


def test_version_compat_patch_drift():
    msg = version_compatibility_warning("3.23.8", "3.23.7")
    assert msg and "patch" in msg.lower()


def test_version_compat_minor_drift():
    msg = version_compatibility_warning("3.24.0", "3.23.7")
    assert msg and "minor" in msg.lower()


def test_version_compat_major_mismatch():
    msg = version_compatibility_warning("4.0.0", "3.23.7")
    assert msg and "major" in msg.lower()


def test_version_compat_none_version():
    assert version_compatibility_warning(None, "3.23.7") is None


# --- Hard gate ---

def test_hard_gate_exact_match():
    result = version_hard_gate_check("3.23.7", "3.23.7")
    assert result["gate_pass"] is True
    assert result["reason"] is None


def test_hard_gate_major_mismatch():
    result = version_hard_gate_check("4.0.0", "3.23.7")
    assert result["gate_pass"] is False
    assert "major" in result["reason"].lower()


def test_hard_gate_minor_mismatch():
    result = version_hard_gate_check("3.24.0", "3.23.7")
    assert result["gate_pass"] is False
    assert "minor" in result["reason"].lower()


def test_hard_gate_patch_drift_default():
    result = version_hard_gate_check("3.23.8", "3.23.7")
    assert result["gate_pass"] is False
    assert "patch" in result["reason"].lower()


def test_hard_gate_patch_drift_allowed():
    result = version_hard_gate_check("3.23.8", "3.23.7", allow_patch_drift=True)
    assert result["gate_pass"] is True


def test_hard_gate_no_version():
    result = version_hard_gate_check(None, "3.23.7")
    assert result["gate_pass"] is False
    assert "detect" in result["reason"].lower()


# --- Schema gate ---

def test_schema_gate_no_diff():
    gate = compute_schema_gate(None)
    assert gate["schema_gate_pass"] is True
    assert gate["schema_score"] == 100.0


def test_schema_gate_clean():
    gate = compute_schema_gate({})
    assert gate["schema_gate_pass"] is True
    assert gate["schema_score"] == 100.0


def test_schema_gate_missing_queries():
    gate = compute_schema_gate({"missing_queries": ["foo", "bar"]})
    assert gate["schema_gate_pass"] is False
    assert gate["schema_score"] < 100.0


def test_schema_gate_missing_mutations():
    gate = compute_schema_gate({"missing_mutations": ["baz"]})
    assert gate["schema_gate_pass"] is False


def test_schema_gate_introspection_error():
    gate = compute_schema_gate({"introspection_error": "timeout"})
    assert gate["schema_gate_pass"] is False
    assert any("introspection" in i.lower() for i in gate["schema_issues"])


def test_schema_gate_client_l3_fail():
    gate = compute_schema_gate({"client_schema_gate_pass": False})
    assert gate["schema_gate_pass"] is False


def test_schema_gate_document_fail():
    gate = compute_schema_gate({"document_schema_gate_pass": False})
    assert gate["schema_gate_pass"] is False


def test_schema_gate_golden_source():
    gate = compute_schema_gate({
        "missing_queries": ["foo"],
        "schema_gate_source": "golden",
    })
    assert "golden" in gate["schema_issues"][0]


def test_schema_gate_major_version_fail():
    gate = compute_schema_gate({"version_warning": "Major version mismatch"})
    assert gate["schema_gate_pass"] is False


def test_schema_gate_minor_version_ok():
    gate = compute_schema_gate({"version_warning": "Minor version drift"})
    assert gate["schema_gate_pass"] is True


# --- compute_certified ---

def test_certified_both_pass():
    assert compute_certified(schema_gate_pass=True, compatibility_score=100.0) is True


def test_certified_schema_fail():
    assert compute_certified(schema_gate_pass=False, compatibility_score=100.0) is False


def test_certified_low_score():
    assert compute_certified(schema_gate_pass=True, compatibility_score=99.9) is False


def test_certified_uses_effective_score():
    assert compute_certified(
        schema_gate_pass=True,
        compatibility_score=90.0,
        effective_score=100.0,
    ) is True


def test_certified_low_effective_score():
    assert compute_certified(
        schema_gate_pass=True,
        compatibility_score=100.0,
        effective_score=90.0,
    ) is False


def test_certified_tier2_fail():
    assert compute_certified(
        schema_gate_pass=True,
        compatibility_score=100.0,
        tier2_pass=False,
    ) is False


def test_certified_parity_gaps():
    assert compute_certified(
        schema_gate_pass=True,
        compatibility_score=100.0,
        parity_gaps=1,
    ) is False


def test_certified_none_score():
    assert compute_certified(schema_gate_pass=True, compatibility_score=None) is False
