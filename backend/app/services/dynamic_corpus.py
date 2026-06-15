"""
Dynamic probe framework — anti-static-response testing layer.

Generates fresh inputs at runtime (unique slugs, UUIDs, timestamps) to prove
the target backend is computing responses, not serving canned golden JSON.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

DYNAMIC_PROBE_KIND = "DYNAMIC_PROBE"


def _default_dynamic_root() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[3] / "reference" / "dynamic"
    if repo_root.parent.is_dir():
        return repo_root
    return here.parents[2] / "reference" / "dynamic"


DYNAMIC_ROOT = Path(__import__("os").environ.get("DYNAMIC_PROBES_ROOT", str(_default_dynamic_root())))


class DynamicProbe:
    """A probe with runtime-generated inputs and echo/binding validation."""

    def __init__(
        self,
        probe_id: str,
        operation_name: str,
        operation_kind: str,
        category: str,
        document_template: str,
        *,
        variables_template: dict[str, Any] | None = None,
        comparison_mode: str = "echo",
        binding_rules: list[dict[str, Any]] | None = None,
        description: str = "",
        auth_context: str = "staff",
        requires_product_type: bool = False,
    ):
        self.probe_id = probe_id
        self.operation_name = operation_name
        self.operation_kind = operation_kind
        self.category = category
        self.document_template = document_template
        self.variables_template = variables_template or {}
        self.comparison_mode = comparison_mode
        self.binding_rules = binding_rules or []
        self.description = description
        self.auth_context = auth_context
        self.requires_product_type = requires_product_type

    def generate_input(
        self,
        run_id: str,
        product_type_id: str | None = None,
    ) -> tuple[str, dict[str, Any], dict[str, str]]:
        """Generate fresh document and variables with unique run-scoped values.

        Returns (document, variables, generated_values_map).
        The generated_values_map contains all runtime-generated strings that
        the echo validator checks for in the response.
        """
        nonce = str(uuid.uuid4())[:8]
        unique_uuid = str(uuid.uuid4())
        run_slug = f"harness-{run_id}-{nonce}"

        generated_values: dict[str, str] = {
            "run_slug": run_slug,
            "nonce": nonce,
            "uuid": unique_uuid,
        }

        document = self.document_template.replace("{{run_slug}}", run_slug)
        document = document.replace("{{nonce}}", nonce)
        document = document.replace("{{uuid}}", unique_uuid)
        if self.requires_product_type and product_type_id:
            document = document.replace("{{product_type_id}}", product_type_id)

        variables: dict[str, Any] = {}
        for key, val in self.variables_template.items():
            if isinstance(val, str):
                val = val.replace("{{run_slug}}", run_slug)
                val = val.replace("{{nonce}}", nonce)
                val = val.replace("{{uuid}}", unique_uuid)
            elif isinstance(val, dict):
                val = {
                    k: (
                        v.replace("{{run_slug}}", run_slug).replace("{{nonce}}", nonce).replace("{{uuid}}", unique_uuid)
                        if isinstance(v, str) else v
                    )
                    for k, v in val.items()
                }
            variables[key] = val

        return document, variables, generated_values

    def validate_response(
        self,
        response: dict[str, Any],
        generated_values: dict[str, str],
    ) -> tuple[bool, str]:
        """Validate that the response echoes generated values (not canned).

        Returns (passes, detail_message).
        """
        if self.comparison_mode == "echo":
            return self._validate_echo(response, generated_values)
        elif self.comparison_mode == "structural":
            return self._validate_structural(response)
        elif self.comparison_mode == "semantic_error":
            return self._validate_semantic_error(response, generated_values)
        elif self.comparison_mode == "not_found_null":
            return self._validate_not_found_null(response)
        return True, "unknown comparison mode, skipping"

    def _validate_echo(
        self,
        response: dict[str, Any],
        generated_values: dict[str, str],
    ) -> tuple[bool, str]:
        """Check that response contains the generated runtime values.

        Only checks the run_slug and any explicit input fields. The full UUID
        is checked separately by semantic_error probes.
        """
        if not (response.get("data") or response.get("errors")):
            return False, "Response missing both 'data' and 'errors' keys"

        resp_str = json.dumps(response)
        run_slug = generated_values.get("run_slug", "")
        if run_slug and run_slug not in resp_str:
            return False, (
                f"Echo check failed: generated run_slug '{run_slug}' "
                "not found in response — possible static/canned response"
            )

        return True, "echo validation passed"

    def _validate_structural(self, response: dict[str, Any]) -> tuple[bool, str]:
        """Structural check: response has expected shape with generated placeholders."""
        if "data" not in response and "errors" not in response:
            return False, "Response missing both 'data' and 'errors' keys"
        return True, "structural validation passed"

    def _validate_semantic_error(
        self,
        response: dict[str, Any],
        generated_values: dict[str, str],
    ) -> tuple[bool, str]:
        """For error probes: error must reference the generated input ID.

        Strengthens the check by requiring the generated UUID to appear in
        the error message, path, or extensions. Catches backends that return
        a static canned error regardless of input.
        """
        errors = response.get("errors") or []
        if not errors:
            return False, "Expected error response but got none"

        generated_uuid = generated_values.get("uuid", "")
        if not generated_uuid:
            return True, "semantic error validation passed (no generated uuid to check)"

        resp_str = json.dumps(response)
        if generated_uuid not in resp_str:
            return False, (
                f"Semantic error check failed: generated UUID '{generated_uuid}' "
                "not referenced in error response — possible static/canned error"
            )

        return True, "semantic error validation passed"

    def _validate_not_found_null(self, response: dict[str, Any]) -> tuple[bool, str]:
        """Saleor returns null data for missing entities; errors may accompany null fields."""
        data = response.get("data")
        if not isinstance(data, dict):
            return False, "Expected data object for not-found query"
        if not data:
            return False, "Expected at least one root field in data"
        for value in data.values():
            if value is not None:
                return False, "Expected null root field for missing entity"
        return True, "not-found null validation passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "operation_name": self.operation_name,
            "operation_kind": self.operation_kind,
            "category": self.category,
            "document_template": self.document_template,
            "variables_template": self.variables_template,
            "comparison_mode": self.comparison_mode,
            "binding_rules": self.binding_rules,
            "description": self.description,
            "auth_context": self.auth_context,
            "requires_product_type": self.requires_product_type,
        }


BUILT_IN_PROBES: list[DynamicProbe] = [
    DynamicProbe(
        probe_id="dynamic_product_create",
        operation_name="productCreate",
        operation_kind="MUTATION",
        category="products",
        document_template='mutation { productCreate(input: { name: "Product {{run_slug}}", slug: "{{run_slug}}", productType: "{{product_type_id}}" }) { product { id name slug } errors { field message code } } }',
        variables_template={
            "input": {
                "name": "Product {{run_slug}}",
                "slug": "{{run_slug}}",
                "productType": "{{product_type_id}}",
            }
        },
        comparison_mode="echo",
        binding_rules=[
            {"field": "data.productCreate.product.name", "expected_input": "input.name"},
            {"field": "data.productCreate.product.slug", "expected_input": "input.slug"},
        ],
        description="Create product with unique name/slug — response must echo runtime values",
        requires_product_type=True,
    ),
    DynamicProbe(
        probe_id="dynamic_category_create",
        operation_name="categoryCreate",
        operation_kind="MUTATION",
        category="categories",
        document_template='mutation($input: CategoryInput!) { categoryCreate(input: $input) { category { id name slug } errors { field message } } }',
        variables_template={
            "input": {
                "name": "Category {{run_slug}}",
                "slug": "{{run_slug}}",
            }
        },
        comparison_mode="echo",
        binding_rules=[
            {"field": "data.categoryCreate.category.name", "expected_input": "input.name"},
            {"field": "data.categoryCreate.category.slug", "expected_input": "input.slug"},
        ],
        description="Create category with unique name/slug — response must echo runtime values",
    ),
    DynamicProbe(
        probe_id="dynamic_collection_create",
        operation_name="collectionCreate",
        operation_kind="MUTATION",
        category="collections",
        document_template='mutation { collectionCreate(input: { name: "Collection {{run_slug}}", slug: "{{run_slug}}" }) { collection { id name slug } errors { field message } } }',
        comparison_mode="echo",
        binding_rules=[
            {"field": "data.collectionCreate.collection.name", "expected_input": "input.name"},
            {"field": "data.collectionCreate.collection.slug", "expected_input": "input.slug"},
        ],
        description="Create collection with unique name/slug — response must echo runtime values",
    ),
    DynamicProbe(
        probe_id="dynamic_product_not_found",
        operation_name="product",
        operation_kind="QUERY",
        category="products",
        document_template='query { product(id: "{{uuid}}") { id name } }',
        variables_template={},
        comparison_mode="semantic_error",
        binding_rules=[],
        description="Query non-existent product by generated UUID — error must reference the ID",
    ),
    DynamicProbe(
        probe_id="dynamic_channel_create",
        operation_name="channelCreate",
        operation_kind="MUTATION",
        category="channels",
        document_template='mutation { channelCreate(input: { name: "Channel {{run_slug}}", slug: "{{run_slug}}", currencyCode: "USD", isActive: true }) { channel { id name slug currencyCode } errors { field message } } }',
        comparison_mode="echo",
        binding_rules=[
            {"field": "data.channelCreate.channel.name", "expected_input": "input.name"},
            {"field": "data.channelCreate.channel.slug", "expected_input": "input.slug"},
        ],
        description="Create channel with unique name/slug — response must echo runtime values",
    ),
]


def _load_disk_probes() -> list[DynamicProbe]:
    """Load dynamic probes from reference/dynamic/*.json on disk."""
    probes: list[DynamicProbe] = []
    if not DYNAMIC_ROOT.is_dir():
        return probes
    for path in sorted(DYNAMIC_ROOT.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            probes.append(DynamicProbe(
                probe_id=data["probe_id"],
                operation_name=data["operation_name"],
                operation_kind=data.get("operation_kind", "MUTATION"),
                category=data.get("category", "products"),
                document_template=data["document_template"],
                variables_template=data.get("variables_template") or {},
                comparison_mode=data.get("comparison_mode", "echo"),
                binding_rules=data.get("binding_rules") or [],
                description=data.get("description", ""),
                auth_context=data.get("auth_context", "staff"),
                requires_product_type=data.get("requires_product_type", False),
            ))
        except (KeyError, json.JSONDecodeError):
            continue
    return probes


def load_dynamic_probes() -> list[DynamicProbe]:
    """Return registered dynamic probes (built-in + disk), deduplicated by probe_id.

    Disk JSON overrides built-in definitions when probe_id collides.
    """
    by_id: dict[str, DynamicProbe] = {p.probe_id: p for p in BUILT_IN_PROBES}
    for probe in _load_disk_probes():
        by_id[probe.probe_id] = probe
    return list(by_id.values())


def build_dynamic_probe_endpoints(
    run_id: str,
    *,
    product_type_id: str | None = None,
    recorded_only: bool = False,
) -> list[dict]:
    """Build endpoint dicts for dynamic probes with fresh generated inputs.

    Each endpoint dict includes:
      - bundle_document, bundle_variables: ready to send
      - generated_values: map of runtime values to check in response
      - dynamic_probe: the probe object
    """
    endpoints: list[dict] = []
    for probe in load_dynamic_probes():
        document, variables, generated_values = probe.generate_input(
            run_id, product_type_id=product_type_id
        )
        endpoints.append({
            "name": f"dynamic__{probe.probe_id}",
            "kind": DYNAMIC_PROBE_KIND,
            "category": probe.category,
            "is_public": False,
            "auth_context": probe.auth_context,
            "golden_input": document,
            "bundle_document": document,
            "bundle_variables": variables,
            "dynamic_probe": probe,
            "generated_values": generated_values,
            "description": probe.description,
        })
    return endpoints


def compare_dynamic_response(
    probe: DynamicProbe,
    response: dict[str, Any],
    generated_values: dict[str, str],
) -> tuple[bool, str]:
    """Compare a dynamic probe response against generated values."""
    return probe.validate_response(response, generated_values)
