"""
Saleor version compatibility routing for golden corpus selection.
"""

from __future__ import annotations

from typing import Any


def parse_major_minor(version: str | None) -> tuple[int, int] | None:
    if not version:
        return None
    parts = version.strip().split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def parse_version_parts(version: str | None) -> tuple[int, int, int] | None:
    """Parse full version into (major, minor, patch)."""
    if not version:
        return None
    parts = version.strip().split(".")
    if len(parts) < 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None


def version_compatibility_warning(
    target_version: str | None,
    corpus_version: str,
) -> str | None:
    """Return a human warning when target and corpus versions may not align."""
    target_mm = parse_major_minor(target_version)
    corpus_mm = parse_major_minor(corpus_version)
    if not target_mm or not corpus_mm:
        return None
    if target_mm[0] != corpus_mm[0]:
        return (
            f"Major version mismatch: target Saleor {target_version} "
            f"vs golden corpus {corpus_version}"
        )
    if target_mm != corpus_mm:
        return (
            f"Minor version drift: target Saleor {target_version} "
            f"vs golden corpus {corpus_version} — comparisons may differ"
        )
    if target_version != corpus_version:
        return (
            f"Patch version drift: target Saleor {target_version} "
            f"vs golden corpus {corpus_version} — comparisons may differ"
        )
    return None


def version_hard_gate_check(
    target_version: str | None,
    corpus_version: str,
    *,
    allow_patch_drift: bool = False,
) -> dict[str, Any]:
    """Hard gate: fail certification if target version is incompatible.

    Returns a dict with:
      - gate_pass: bool
      - reason: str or None
      - severity: "error" | "warning" | None
    """
    if not target_version:
        return {
            "gate_pass": False,
            "reason": "Could not detect target Saleor version",
            "severity": "error",
        }

    target_parts = parse_version_parts(target_version)
    corpus_parts = parse_version_parts(corpus_version)

    if target_parts and corpus_parts:
        if target_parts[0] != corpus_parts[0]:
            return {
                "gate_pass": False,
                "reason": (
                    f"Major version mismatch: target {target_version} "
                    f"vs corpus {corpus_version}. Run upgrade workflow first."
                ),
                "severity": "error",
            }
        if target_parts[1] != corpus_parts[1]:
            return {
                "gate_pass": False,
                "reason": (
                    f"Minor version mismatch: target {target_version} "
                    f"vs corpus {corpus_version}. Corpus must be updated."
                ),
                "severity": "error",
            }
        if not allow_patch_drift and target_parts[2] != corpus_parts[2]:
            return {
                "gate_pass": False,
                "reason": (
                    f"Patch version drift: target {target_version} "
                    f"vs corpus {corpus_version}. "
                    "Set ALLOW_PATCH_DRIFT=true to override."
                ),
                "severity": "error",
            }

    return {
        "gate_pass": True,
        "reason": None,
        "severity": None,
    }


def detect_golden_staleness(
    target_version: str | None,
    corpus_version: str,
    *,
    recorded_date: str | None = None,
) -> dict[str, Any]:
    """Detect if golden data might be stale.

    Checks if the target version is newer than the corpus version,
    which means the golden responses may not reflect the latest
    Saleor API behavior.

    Returns a dict with:
      - stale: bool
      - warning: str or None
      - severity: "info" | "warning" | None
    """
    if not target_version:
        return {"stale": False, "warning": None, "severity": None}

    target_parts = parse_version_parts(target_version)
    corpus_parts = parse_version_parts(corpus_version)

    if not target_parts or not corpus_parts:
        return {"stale": False, "warning": None, "severity": None}

    # Target is newer than corpus
    if target_parts > corpus_parts:
        return {
            "stale": True,
            "warning": (
                f"Golden data may be stale: target Saleor {target_version} is newer "
                f"than golden corpus {corpus_version}. "
                f"Consider re-recording golden data with `just record-reference`."
            ),
            "severity": "warning",
        }

    # Target is older than corpus (unusual but possible)
    if target_parts < corpus_parts:
        return {
            "stale": True,
            "warning": (
                f"Target Saleor {target_version} is older than golden corpus {corpus_version}. "
                f"Some golden responses may reference newer API features."
            ),
            "severity": "info",
        }

    return {"stale": False, "warning": None, "severity": None}
