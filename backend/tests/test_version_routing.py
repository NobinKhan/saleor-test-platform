"""Version routing tests."""

from app.services.version_routing import version_compatibility_warning


def test_same_minor_no_warning():
    assert version_compatibility_warning("3.23.7", "3.23.7") is None


def test_patch_drift_warning():
    msg = version_compatibility_warning("3.23.8", "3.23.7")
    assert msg and "Patch version drift" in msg


def test_minor_drift_warning():
    msg = version_compatibility_warning("3.24.0", "3.23.7")
    assert msg and "Minor version drift" in msg


def test_major_mismatch_warning():
    msg = version_compatibility_warning("4.0.0", "3.23.7")
    assert msg and "Major version mismatch" in msg
