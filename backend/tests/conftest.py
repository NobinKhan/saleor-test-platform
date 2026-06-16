"""
Shared test configuration — suppresses pytest collection warnings for
model/schema classes whose names start with 'Test' but are not tests.
"""

from __future__ import annotations

import warnings

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Suppress PytestCollectionWarning for model/schema classes named Test*."""
    # Add filter early in configuration to suppress collection warnings
    for attr in ("TestResult", "TestRun", "TestRunCreate", "TestRunner",
                 "TestRunSummary", "TestRunDetail", "TestResultResponse"):
        warnings.filterwarnings(
            "ignore",
            message=f".*{attr}.*",
            category=pytest.PytestCollectionWarning,
        )
