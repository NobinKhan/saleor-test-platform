"""
app/schemas/__init__.py — Pydantic schemas for API request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


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
    id: UUID
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Test Run ───────────────────────────────────────────────────────────────────

class TestRunCreate(BaseModel):
    saleor_url: str = Field(description="GraphQL endpoint URL of Saleor server")
    saleor_token: str | None = Field(default=None, description="Bearer token or API key")
    saleor_email: str | None = Field(default=None, description="Saleor admin email (optional, for auto token fetch)")
    saleor_password: str | None = Field(default=None, description="Saleor admin password (optional, for auto token fetch)")
    test_scope: str = Field(default="full", description="full|queries|mutations|custom")
    public_only: bool = Field(default=False, description="Only test public endpoints")
    categories: list[str] | None = Field(default=None, description="Categories when test_scope=custom")
    concurrency: int = Field(default=5, ge=1, le=20)
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    reference_saleor_url: str | None = Field(default=None, description="Reference Saleor URL for schema compare")
    reference_saleor_token: str | None = Field(default=None, description="Bearer token for reference Saleor")


class TestRunSummary(BaseModel):
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

    class Config:
        from_attributes = True


class TestRunDetail(TestRunSummary):
    user_id: UUID
    saleor_token: str
    saleor_email: str | None = None
    saleor_password: str | None = None
    test_scope: str
    public_only: bool


# ── Test Result ────────────────────────────────────────────────────────────────

class TestResultResponse(BaseModel):
    id: UUID
    category: str
    endpoint_name: str
    endpoint_kind: str
    field_name: str | None
    status: str
    input_sent: str | None
    actual_response: str | None
    error_message: str | None
    response_time_ms: int | None
    saleor_field_type: str | None
    actual_field_type: str | None
    is_public: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TestItemResponse(BaseModel):
    id: UUID
    item_key: str
    item_status: str
    expected_type: str | None
    actual_type: str | None

    class Config:
        from_attributes = True


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


class ReportData(BaseModel):
    summary: ReportSummary
    category_breakdown: list[CategoryBreakdown]
    response_time_distribution: list[ResponseTimeBucket]
    pass_rate: float
    schema_diff: dict[str, Any] | None = None


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