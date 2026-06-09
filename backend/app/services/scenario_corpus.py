"""
L4 scenario corpus — multi-step chained GraphQL flows with shared context.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCENARIO_KIND = "SCENARIO_STEP"


def _default_scenarios_root() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[3] / "reference" / "scenarios"
    if repo_root.parent.is_dir():
        return repo_root
    return here.parents[2] / "reference" / "scenarios"


SCENARIOS_ROOT = Path(__import__("os").environ.get("SCENARIOS_ROOT", str(_default_scenarios_root())))


@dataclass
class ScenarioStep:
    step_id: str
    scenario_id: str
    order: int
    name: str
    auth_context: str
    input_sent: str
    variables: dict[str, Any] = field(default_factory=dict)
    extract: dict[str, str] = field(default_factory=dict)
    assertions: list[dict[str, Any]] = field(default_factory=list)
    golden_response: dict[str, Any] | None = None
    golden_contract: str | None = None
    golden_status: str | None = None
    semantic_profile: dict[str, Any] | None = None
    cleanup: bool = False

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "step_id": self.step_id,
            "scenario_id": self.scenario_id,
            "order": self.order,
            "name": self.name,
            "auth_context": self.auth_context,
            "input_sent": self.input_sent,
            "variables": self.variables,
            "extract": self.extract,
            "assertions": self.assertions,
            "cleanup": self.cleanup,
        }
        if self.golden_response is not None:
            d["golden_response"] = self.golden_response
        if self.golden_contract:
            d["golden_contract"] = self.golden_contract
        if self.golden_status:
            d["golden_status"] = self.golden_status
        if self.semantic_profile:
            d["semantic_profile"] = self.semantic_profile
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioStep:
        return cls(
            step_id=data["step_id"],
            scenario_id=data.get("scenario_id", ""),
            order=int(data.get("order", 0)),
            name=data.get("name", data["step_id"]),
            auth_context=data.get("auth_context", "staff"),
            input_sent=data["input_sent"],
            variables=data.get("variables") or {},
            extract=data.get("extract") or {},
            assertions=data.get("assertions") or [],
            golden_response=data.get("golden_response"),
            golden_contract=data.get("golden_contract"),
            golden_status=data.get("golden_status"),
            semantic_profile=data.get("semantic_profile"),
            cleanup=bool(data.get("cleanup")),
        )


@dataclass
class ScenarioManifest:
    scenario_id: str
    name: str
    category: str
    auth_context: str
    steps: list[str]
    description: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScenarioManifest:
        return cls(
            scenario_id=data["scenario_id"],
            name=data.get("name", data["scenario_id"]),
            category=data.get("category", "scenarios"),
            auth_context=data.get("auth_context", "staff"),
            steps=list(data.get("steps") or []),
            description=data.get("description", ""),
        )


def scenario_dir(scenario_id: str) -> Path:
    return SCENARIOS_ROOT / scenario_id


def load_scenario_manifest(scenario_id: str) -> ScenarioManifest | None:
    path = scenario_dir(scenario_id) / "manifest.json"
    if not path.is_file():
        return None
    return ScenarioManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_scenario_step(scenario_id: str, step_file: str) -> ScenarioStep | None:
    path = scenario_dir(scenario_id) / "steps" / step_file
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("scenario_id", scenario_id)
    data.setdefault("step_id", step_file.replace(".json", ""))
    return ScenarioStep.from_dict(data)


def load_all_scenarios() -> list[ScenarioManifest]:
    if not SCENARIOS_ROOT.is_dir():
        return []
    manifests: list[ScenarioManifest] = []
    for path in sorted(SCENARIOS_ROOT.iterdir()):
        if path.is_dir() and (path / "manifest.json").is_file():
            manifest = load_scenario_manifest(path.name)
            if manifest:
                manifests.append(manifest)
    return manifests


def load_scenario_steps(manifest: ScenarioManifest) -> list[ScenarioStep]:
    steps: list[ScenarioStep] = []
    for i, step_file in enumerate(manifest.steps):
        step = load_scenario_step(manifest.scenario_id, step_file)
        if step:
            step.order = i + 1
            steps.append(step)
    return steps


def _extract_json_path(obj: Any, path: str) -> Any:
    """Extract value using simple $.data.field.subfield path."""
    if not path.startswith("$."):
        return None
    parts = path[2:].split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def substitute_scenario_variables(
    template: dict[str, Any] | str,
    context: dict[str, Any],
    fixtures: dict[str, Any],
) -> Any:
    """Replace {{context.key}} and {{fixtures.key}} placeholders."""
    if isinstance(template, str):
        result = template
        for key, value in context.items():
            result = result.replace(f"{{{{context.{key}}}}}", str(value))
        for key, value in fixtures.items():
            result = result.replace(f"{{{{fixtures.{key}}}}}", str(value))
        return result
    if isinstance(template, dict):
        return {
            k: substitute_scenario_variables(v, context, fixtures)
            for k, v in template.items()
        }
    if isinstance(template, list):
        return [substitute_scenario_variables(v, context, fixtures) for v in template]
    return template


def run_assertions(
    response: dict[str, Any],
    assertions: list[dict[str, Any]],
    context: dict[str, Any],
) -> list[str]:
    """Return list of failed assertion messages."""
    failures: list[str] = []
    for assertion in assertions:
        kind = assertion.get("kind", "path_exists")
        path = assertion.get("path", "")
        expected = assertion.get("expected")
        actual = _extract_json_path(response, path) if path else None

        if kind == "path_exists":
            if actual is None:
                failures.append(f"Expected path {path} to exist")
        elif kind == "equals":
            if str(actual) != str(expected):
                failures.append(f"Expected {path}={expected!r}, got {actual!r}")
        elif kind == "contains":
            if expected and str(expected) not in str(actual or ""):
                failures.append(f"Expected {path} to contain {expected!r}")
        elif kind == "context_equals":
            ctx_key = assertion.get("context_key", "")
            if str(actual) != str(context.get(ctx_key)):
                failures.append(
                    f"Expected {path} to equal context.{ctx_key}="
                    f"{context.get(ctx_key)!r}, got {actual!r}"
                )
        elif kind == "not_in_list":
            list_path = assertion.get("list_path", "")
            field_name = assertion.get("field", "slug")
            items = _extract_json_path(response, list_path) or []
            values = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        node = item.get("node") or item
                        if isinstance(node, dict):
                            values.append(node.get(field_name))
            if expected in values:
                failures.append(f"Expected {expected!r} absent from {list_path}")
    return failures


def build_scenario_endpoints(
    *,
    scenario_ids: list[str] | None = None,
    fixtures: dict[str, Any] | None = None,
    recorded_only: bool = False,
) -> list[dict]:
    """Flatten scenario steps into sequential test endpoints."""
    endpoints: list[dict] = []
    manifests = load_all_scenarios()
    if scenario_ids:
        manifests = [m for m in manifests if m.scenario_id in scenario_ids]

    for manifest in manifests:
        steps = load_scenario_steps(manifest)
        for step in steps:
            if recorded_only and step.golden_response is None:
                continue
            endpoints.append({
                "name": f"{manifest.scenario_id}/{step.step_id}",
                "kind": SCENARIO_KIND,
                "category": manifest.category,
                "is_public": step.auth_context == "anonymous",
                "auth_context": step.auth_context,
                "golden_input": step.input_sent,
                "scenario_id": manifest.scenario_id,
                "step_id": step.step_id,
                "step_order": step.order,
                "step_variables": step.variables,
                "step_extract": step.extract,
                "step_assertions": step.assertions,
                "step_fixtures": fixtures or {},
                "golden_response": step.golden_response,
                "golden_contract": step.golden_contract,
                "golden_status": step.golden_status,
                "semantic_profile": step.semantic_profile,
            })
    return endpoints
