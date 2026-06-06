"""
app/models/__init__.py — All database models.
Defined in one file to avoid circular import issues with SQLAlchemy relationships.
"""

from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, Text, ForeignKey, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum


# ── Enums ────────────────────────────────────────────────────────────────────

class TestRunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class TestResultStatus(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    WARN = "warn"


class EndpointKind(str, enum.Enum):
    QUERY = "QUERY"
    MUTATION = "MUTATION"


class EndpointCategory(str, enum.Enum):
    PRODUCTS = "products"
    ORDERS = "orders"
    CHECKOUT = "checkout"
    PAYMENTS = "payments"
    SHIPPING = "shipping"
    DISCOUNTS = "discounts"
    CHANNELS = "channels"
    CATEGORIES = "categories"
    COLLECTIONS = "collections"
    ATTRIBUTES = "attributes"
    ACCOUNT = "account"
    GIFTCARDS = "giftcards"
    PAGES = "pages"
    WAREHOUSE = "warehouse"
    META = "meta"
    SHOP = "shop"
    PLUGINS = "plugins"
    WEBHOOKS = "webhooks"
    UNKNOWN = "unknown"


# ── Models ────────────────────────────────────────────────────────────────────

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    test_runs: Mapped[list["TestRun"]] = relationship(back_populates="user", lazy="selectin", cascade="all, delete-orphan")


class TestRun(Base):
    __tablename__ = "test_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    saleor_url: Mapped[str] = mapped_column(String(500), nullable=False)
    saleor_token: Mapped[str] = mapped_column(Text, nullable=False)
    saleor_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_tests: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    test_scope: Mapped[str] = mapped_column(String(50), default="full+client")
    public_only: Mapped[bool] = mapped_column(Boolean, default=False)
    schema_diff: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    saleor_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    saleor_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_baseline_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_baseline_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    concurrency: Mapped[int] = mapped_column(Integer, default=5)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)

    user: Mapped["User"] = relationship(back_populates="test_runs")
    results: Mapped[list["TestResult"]] = relationship(back_populates="test_run", lazy="selectin", cascade="all, delete-orphan")


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_runs.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    endpoint_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    endpoint_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    input_sent: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saleor_field_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actual_field_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    response_valid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    expected_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_parity_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["TestItem"]] = relationship(back_populates="test_result", lazy="selectin", cascade="all, delete-orphan")
    test_run: Mapped["TestRun"] = relationship(back_populates="results")


# Field-level breakdown rows — populated when introspection field checks exist (deferred).
class ReferenceProbe(Base):
    __tablename__ = "reference_probes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    saleor_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    endpoint_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    endpoint_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    input_sent: Mapped[str] = mapped_column(Text, nullable=False)
    golden_response: Mapped[str] = mapped_column(Text, nullable=False)
    golden_outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    golden_status: Mapped[str] = mapped_column(String(10), nullable=False)
    error_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_shape_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    corpus_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TestItem(Base):
    __tablename__ = "test_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("test_results.id"), nullable=False)
    item_key: Mapped[str] = mapped_column(String(255), nullable=False)
    item_status: Mapped[str] = mapped_column(String(20), nullable=False)
    expected_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actual_type: Mapped[str | None] = mapped_column(String(255), nullable=True)

    test_result: Mapped["TestResult"] = relationship(back_populates="items")


__all__ = [
    "User",
    "TestRun",
    "TestRunStatus",
    "TestResult",
    "TestItem",
    "ReferenceProbe",
    "TestResultStatus",
    "EndpointKind",
    "EndpointCategory",
]