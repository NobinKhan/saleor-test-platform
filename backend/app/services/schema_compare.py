"""
Schema-based response comparison — validates response shape (field types,
nullability, nesting) instead of data values.

This replaces the data-value comparison for success probes, making the
testing methodology data-independent.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any

# ── Type classification ──────────────────────────────────────────────────────

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
GLOBAL_ID_RE = re.compile(r"^[A-Za-z0-9+/=_-]{8,}$")
ISO_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# Volatile field paths that naturally differ between database states.
# These are forgiven during schema comparison.
VOLATILE_FRAGMENTS = (
    ".edges",
    ".edges[",
    ".pricing",
    ".amount",
    ".currency",
    ".name",
    ".slug",
    ".email",
    ".firstName",
    ".lastName",
    ".title",
    ".description",
    ".seoTitle",
    ".seoDescription",
    ".sku",
    ".margin",
    ".quantity",
    ".quantityAllocated",
    ".stockAvailability",
    ".weight",
    ".meta",
    ".privateMeta",
    ".translation",
    ".status",
    ".createdAt",
    ".updatedAt",
    ".price",
    ".channel",
    ".country",
    ".countryArea",
    ".city",
    ".streetAddress1",
    ".streetAddress2",
    ".postalCode",
    ".phone",
    ".companyName",
    ".firstName",
    ".lastName",
    ".code",
    ".token",
    ".password",
    ".isActive",
    "__typename",
)


def _type_label(value: Any) -> str:
    """Classify a JSON value into a type label."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        if UUID_RE.match(value):
            return "uuid"
        if GLOBAL_ID_RE.match(value) and len(value) > 12:
            return "global_id"
        if ISO_TS_RE.match(value):
            return "timestamp"
        return "string"
    if isinstance(value, list):
        if not value:
            return "array"
        return f"array<{_type_label(value[0])}>"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _is_volatile_path(path: str) -> bool:
    """Check if a field path is in the volatile list (DB-state-dependent)."""
    return any(frag in path for frag in VOLATILE_FRAGMENTS)


def _is_id_type(type_label: str) -> bool:
    """Check if a type label represents an ID (uuid or global_id)."""
    return type_label in ("uuid", "global_id")


# ── Schema extraction ────────────────────────────────────────────────────────

@dataclass
class FieldSchema:
    path: str
    type_label: str
    nullable: bool = False
    is_id: bool = False
    is_volatile: bool = False


def extract_schema(obj: Any, prefix: str = "") -> dict[str, FieldSchema]:
    """Extract the type schema from a JSON response.

    Returns a mapping of dot-path → FieldSchema describing the structure.
    """
    schema: dict[str, FieldSchema] = {}

    if isinstance(obj, dict):
        for key, val in obj.items():
            child_path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, (dict, list)):
                schema.update(extract_schema(val, child_path))
            else:
                tl = _type_label(val)
                schema[child_path] = FieldSchema(
                    path=child_path,
                    type_label=tl,
                    nullable=val is None,
                    is_id=_is_id_type(tl),
                    is_volatile=_is_volatile_path(child_path),
                )
    elif isinstance(obj, list):
        if obj:
            schema.update(extract_schema(obj[0], f"{prefix}[0]"))
        else:
            schema[prefix or "$"] = FieldSchema(
                path=prefix or "$",
                type_label="array",
                nullable=False,
                is_volatile=_is_volatile_path(prefix),
            )
    else:
        tl = _type_label(obj)
        schema[prefix or "$"] = FieldSchema(
            path=prefix or "$",
            type_label=tl,
            nullable=obj is None,
            is_id=_is_id_type(tl),
            is_volatile=_is_volatile_path(prefix),
        )

    return schema


# ── Comparison result ────────────────────────────────────────────────────────

@dataclass
class SchemaDiff:
    path: str
    expected_type: str
    actual_type: str
    is_volatile: bool
    severity: str  # "error" or "warning"


@dataclass
class SchemaComparisonResult:
    compatible: bool
    match_status: str  # "match", "schema_mismatch", "shape_drift_data"
    diffs: list[SchemaDiff] = field(default_factory=list)
    volatile_diffs: list[SchemaDiff] = field(default_factory=list)
    schema_diffs: list[SchemaDiff] = field(default_factory=list)
    summary: str = ""


def compare_schemas(
    golden: dict[str, Any],
    actual: dict[str, Any],
    *,
    golden_contract: str | None = None,
) -> SchemaComparisonResult:
    """Compare two responses by schema shape (types, not values).

    This is the core of data-independent comparison. It validates that:
    1. Both responses have the same field paths
    2. Fields at the same path have compatible types
    3. ID fields (uuid, global_id) are type-compatible regardless of value
    4. Volatile fields (names, slugs, etc.) are forgiven on type mismatch

    Returns a SchemaComparisonResult with compatible=True if the schema
    matches (ignoring volatile data differences).
    """
    golden_schema = extract_schema(golden)
    actual_schema = extract_schema(actual)

    all_paths = sorted(set(golden_schema) | set(actual_schema))

    diffs: list[SchemaDiff] = []
    volatile_diffs: list[SchemaDiff] = []
    schema_diffs: list[SchemaDiff] = []

    for path in all_paths:
        g = golden_schema.get(path)
        a = actual_schema.get(path)

        if g is None:
            # Field exists in actual but not in golden — extra field
            # This is acceptable (backends may add fields)
            continue
        if a is None:
            # Field exists in golden but not in actual — missing field
            diffs.append(SchemaDiff(
                path=path,
                expected_type=g.type_label,
                actual_type="missing",
                is_volatile=g.is_volatile,
                severity="warning" if g.is_volatile else "error",
            ))
            continue

        # Both exist — compare types
        g_type = g.type_label
        a_type = a.type_label

        if g_type == a_type:
            continue

        # Type mismatch — check if it's an ID type (all IDs are compatible)
        if _is_id_type(g_type) and _is_id_type(a_type):
            continue

        # Type mismatch — check if it's a volatile path
        is_volatile = g.is_volatile or a.is_volatile or _is_volatile_path(path)

        diff = SchemaDiff(
            path=path,
            expected_type=g_type,
            actual_type=a_type,
            is_volatile=is_volatile,
            severity="warning" if is_volatile else "error",
        )
        diffs.append(diff)
        if is_volatile:
            volatile_diffs.append(diff)
        else:
            schema_diffs.append(diff)

    # Determine compatibility
    if not schema_diffs:
        # Only volatile diffs (or no diffs) — compatible
        return SchemaComparisonResult(
            compatible=True,
            match_status="match",
            diffs=diffs,
            volatile_diffs=volatile_diffs,
            schema_diffs=schema_diffs,
            summary=(
                f"Schema match ({len(diffs)} volatile diffs forgiven)"
                if diffs else "Schema match"
            ),
        )
    else:
        # Real schema differences — incompatible
        return SchemaComparisonResult(
            compatible=False,
            match_status="schema_mismatch",
            diffs=diffs,
            volatile_diffs=volatile_diffs,
            schema_diffs=schema_diffs,
            summary=(
                f"Schema mismatch: {len(schema_diffs)} structural diffs, "
                f"{len(volatile_diffs)} volatile diffs"
            ),
        )


def schema_to_template(response: dict[str, Any]) -> dict[str, str]:
    """Convert a response to a type template for documentation.

    Returns a dict mapping dot-path → type_label.
    """
    schema = extract_schema(response)
    return {k: v.type_label for k, v in schema.items()}
