"""
L1 input variant matrix — multiple valid/invalid probes per operation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VARIANT_KIND = "VARIANT_PROBE"


def _default_variants_root() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[3] / "reference" / "variants"
    if repo_root.parent.is_dir():
        return repo_root
    return here.parents[2] / "reference" / "variants"


VARIANTS_ROOT = Path(__import__("os").environ.get("VARIANTS_ROOT", str(_default_variants_root())))


@dataclass
class InputVariant:
    variant_id: str
    operation_name: str
    operation_kind: str
    category: str
    input_sent: str
    tags: list[str]
    golden_response: dict[str, Any] | None = None
    golden_contract: str | None = None
    golden_status: str | None = None
    golden_outcome: str | None = None
    semantic_profile: dict[str, Any] | None = None
    http_status: int | None = None
    variables: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "variant_id": self.variant_id,
            "operation_name": self.operation_name,
            "operation_kind": self.operation_kind,
            "category": self.category,
            "input_sent": self.input_sent,
            "tags": self.tags,
        }
        if self.golden_response is not None:
            d["golden_response"] = self.golden_response
        if self.golden_contract:
            d["golden_contract"] = self.golden_contract
        if self.golden_status:
            d["golden_status"] = self.golden_status
        if self.golden_outcome:
            d["golden_outcome"] = self.golden_outcome
        if self.semantic_profile:
            d["semantic_profile"] = self.semantic_profile
        if self.http_status is not None:
            d["http_status"] = self.http_status
        if self.variables:
            d["variables"] = self.variables
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InputVariant:
        return cls(
            variant_id=data["variant_id"],
            operation_name=data["operation_name"],
            operation_kind=data.get("operation_kind", "MUTATION"),
            category=data.get("category", "products"),
            input_sent=data["input_sent"],
            tags=list(data.get("tags") or []),
            golden_response=data.get("golden_response"),
            golden_contract=data.get("golden_contract"),
            golden_status=data.get("golden_status"),
            golden_outcome=data.get("golden_outcome"),
            semantic_profile=data.get("semantic_profile"),
            http_status=data.get("http_status"),
            variables=data.get("variables"),
        )

    def has_golden(self) -> bool:
        return self.golden_response is not None


def variant_dir(operation_name: str) -> Path:
    return VARIANTS_ROOT / operation_name


def load_variant_matrix(operation_name: str) -> list[InputVariant]:
    directory = variant_dir(operation_name)
    if not directory.is_dir():
        return []
    variants: list[InputVariant] = []
    matrix_path = directory / "matrix.json"
    if matrix_path.is_file():
        data = json.loads(matrix_path.read_text(encoding="utf-8"))
        for entry in data.get("variants") or []:
            entry.setdefault("operation_name", operation_name)
            variants.append(InputVariant.from_dict(entry))
    for path in sorted(directory.glob("*.json")):
        if path.name == "matrix.json":
            continue
        variants.append(InputVariant.from_dict(json.loads(path.read_text(encoding="utf-8"))))
    return variants


def load_all_variants(
    *,
    operation_names: list[str] | None = None,
    recorded_only: bool = False,
) -> list[InputVariant]:
    if not VARIANTS_ROOT.is_dir():
        return []
    all_variants: list[InputVariant] = []
    for path in sorted(VARIANTS_ROOT.iterdir()):
        if not path.is_dir():
            continue
        if operation_names and path.name not in operation_names:
            continue
        for variant in load_variant_matrix(path.name):
            if recorded_only and not variant.has_golden():
                continue
            all_variants.append(variant)
    return all_variants


def build_variant_endpoints(
    *,
    operation_names: list[str] | None = None,
    recorded_only: bool = True,
) -> list[dict]:
    variants = load_all_variants(operation_names=operation_names, recorded_only=recorded_only)
    endpoints: list[dict] = []
    for variant in variants:
        endpoints.append({
            "name": f"{variant.operation_name}__{variant.variant_id}",
            "kind": VARIANT_KIND,
            "category": variant.category,
            "is_public": False,
            "golden_input": variant.input_sent,
            "variant_id": variant.variant_id,
            "operation_name": variant.operation_name,
            "operation_kind": variant.operation_kind,
            "golden_response": variant.golden_response,
            "golden_contract": variant.golden_contract,
            "golden_status": variant.golden_status,
            "semantic_profile": variant.semantic_profile,
            "tags": variant.tags,
            "bundle_variables": variant.variables or {},
        })
    return endpoints
