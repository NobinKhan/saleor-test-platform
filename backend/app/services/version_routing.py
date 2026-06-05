"""
Saleor version compatibility routing for golden corpus selection.
"""

from __future__ import annotations


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
