"""
app/schemas/__init__.py — Pydantic schemas for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.services.run_scope import FULL_SYSTEM_SCOPE


def _validate_saleor_email(value: str) -> str:
    """Allow internal/dev domains (.local, etc.) that strict EmailStr rejects."""
    email = value.strip()
    if email.count("@") != 1:
        raise ValueError("Invalid email format")
    local, domain = email.split("@", 1)
    if not local or not domain:
        raise ValueError("Invalid email format")
    return email


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    created_at: datetime


# ── Test Run ───────────────────────────────────────────────────────────────────

class TestRunCreate(BaseModel):
    saleor_url: str = Field(description="GraphQL endpoint URL of Saleor server")
    saleor_email: str = Field(min_length=3, max_length=255, description="Saleor admin email")
    saleor_password: str | None = Field(
        default=None,
        description="Saleor admin password (omit when clone_from_run_id reuses stored password)",
    )
    clone_from_run_id: UUID | None = Field(
        default=None,
        description="Copy stored password from a previous run when saleor_password is omitted",
    )

    @field_validator("saleor_email")
    @classmethod
    def validate_saleor_email(cls, value: str) -> str:
        return _validate_saleor_email(value)

    @model_validator(mode="after")
    def password_or_clone(self) -> TestRunCreate:
        if not self.saleor_password and not self.clone_from_run_id:
            raise ValueError("saleor_password is required unless clone_from_run_id is set")
        return self

    compare_run_id: UUID | None = Field(
        default=None,
        description="Optional prior run UUID for side-by-side comparison on report",
    )
    concurrency: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    demo_seed_profile: str = Field(
        default="harness",
        description="Fixture seed profile: harness (minimal) or saleor_demo (full topology)",
    )


class TestRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    saleor_url: str
    saleor_version: str | None
    status: str
    started_at: datetime
    completed_at: datetime | None
    total_tests: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    pass_rate: float = 0.0


class TestRunDetail(TestRunSummary):
    user_id: UUID
    saleor_email: str | None = None
    saleor_password_masked: str = "••••••••"
    test_scope: str
    public_only: bool
    concurrency: int = 5
    timeout_seconds: int = 30
    reference_baseline_version: str | None = None
    reference_baseline_source: str | None = None
    reference_catalog_queries: int = 0
    reference_catalog_mutations: int = 0


# ── Test Result ────────────────────────────────────────────────────────────────

class TestResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    endpoint_name: str
    endpoint_kind: str
    field_name: str | None
    status: str
    outcome: str | None = None
    response_valid: bool | None = None
    expected: str | None = None
    expected_response: str | None = None
    match_status: str | None = None
    diff_summary: str | None = None
    client_parity_note: str | None = None
    failure_category: str | None = None
    input_sent: str | None
    actual_response: str | None
    error_message: str | None
    response_time_ms: int | None
    saleor_field_type: str | None
    actual_field_type: str | None
    is_public: bool
    created_at: datetime
    items: list["TestItemResponse"] = []


class TestItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_key: str
    item_status: str
    expected_type: str | None
    actual_type: str | None
    expected_value: str | None = None
    actual_value: str | None = None


# ── Report ─────────────────────────────────────────────────────────────────────

class ReportSummary(BaseModel):
    test_run_id: UUID
    total: int
    passed: int
    failed: int
    warnings: int
    skipped: int
    pass_rate: float
    avg_response_time_ms: float
    saleor_version: str | None
    saleor_url: str
    started_at: datetime
    completed_at: datetime | None
    saleor_email: str | None = None
    saleor_password_masked: str = "••••••••"
    test_scope: str = FULL_SYSTEM_SCOPE
    public_only: bool = False
    concurrency: int = 5
    timeout_seconds: int = 30
    reference_baseline_version: str | None = None
    reference_baseline_source: str | None = None
    reference_catalog_queries: int = 0
    reference_catalog_mutations: int = 0
    golden_corpus_version: str | None = None
    golden_corpus_url: str | None = None
    golden_probe_count: int = 0
    golden_match_rate: float | None = None
    compatibility_score: float | None = None
    golden_matched: int = 0
    golden_mismatched: int = 0
    golden_missing: int = 0
    client_parity_gaps: int = 0
    client_bundle_count: int = 0
    storefront_bundle_count: int = 0
    document_schema_gate_pass: bool | None = None
    tier2_gate_enabled: bool = False
    upgrade_hint: str | None = None
    probe_outcome_rate: float | None = None
    probe_success_count: int = 0
    schema_gate_pass: bool | None = None
    schema_gate_source: str | None = None
    schema_score: float | None = None
    certified: bool | None = None
    test_mode: str | None = None
    deprecated_queries: list[str] = []
    deprecated_mutations: list[str] = []
    extra_queries: list[str] = []
    extra_mutations: list[str] = []
    deprecation_note: str | None = None
    sgrc_note: str | None = None
    certification_endpoint_count: int = 0
    l3_dashboard_certified: int = 0
    l3_dashboard_recorded: int = 0
    excluded_l3_bundles: list[dict[str, str]] = []
    not_counted_note: str | None = None
    effective_score: float | None = None
    effective_compatible: int = 0
    effective_incompatible: int = 0
    deprecated_excluded: int = 0
    data_prerequisite: int = 0
    seed_prerequisite: int = 0
    real_bugs: int = 0


class LatencySummary(BaseModel):
    avg: float
    min: int
    max: int
    p50: float
    p95: float
    sample_count: int


class SlowEndpoint(BaseModel):
    endpoint_name: str
    endpoint_kind: str
    category: str
    status: str
    response_time_ms: int
    outcome: str | None = None


class CategoryBreakdown(BaseModel):
    category: str
    total: int
    passed: int
    failed: int
    warn: int
    skip: int


class ResponseTimeBucket(BaseModel):
    bucket: str
    count: int


class CompareRunSummary(BaseModel):
    compare_run_id: UUID
    saleor_url: str
    saleor_version: str | None
    pass_rate: float
    compatibility_score: float | None = None
    certified: bool | None = None
    total: int
    passed: int
    failed: int
    scope: str
    regressions: int = 0
    improvements: int = 0


class ReportData(BaseModel):
    summary: ReportSummary
    category_breakdown: list[CategoryBreakdown]
    response_time_distribution: list[ResponseTimeBucket]
    latency_summary: LatencySummary
    slowest_endpoints: list[SlowEndpoint]
    results: list[TestResultResponse]
    pass_rate: float
    schema_diff: dict[str, Any] | None = None
    compare_summary: CompareRunSummary | None = None


# ── Live Progress (SSE) ────────────────────────────────────────────────────────

class LiveProgress(BaseModel):
    type: str  # "progress" | "result" | "complete" | "error"
    run_id: UUID
    current: int
    total: int
    current_endpoint: str | None = None
    status_counts: dict[str, int] = {}
    result: dict | None = None
    message: str | None = None