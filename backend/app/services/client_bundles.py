"""
L3 client query bundles — real Dashboard/Storefront GraphQL documents on disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.reference_corpus import GoldenProbe, response_shape_hash


def _default_bundles_root() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[3] / "reference" / "client-bundles"
    if repo_root.parent.is_dir():
        return repo_root
    return here.parents[2] / "reference" / "client-bundles"


def _default_vendor_root() -> Path:
    here = Path(__file__).resolve()
    repo_root = here.parents[3] / "reference" / "vendor"
    if repo_root.parent.is_dir():
        return repo_root
    return here.parents[2] / "reference" / "vendor"


VENDOR_ROOT = Path(os.environ.get("DASHBOARD_VENDOR_ROOT", str(_default_vendor_root())))


def dashboard_vendor_path(version: str) -> Path:
    safe = re.sub(r"[^\w.\-]", "-", version.strip())
    return VENDOR_ROOT / f"saleor-dashboard-{safe}"


def storefront_vendor_path(version: str) -> Path:
    safe = re.sub(r"[^\w.\-]", "-", version.strip())
    return VENDOR_ROOT / f"saleor-storefront-{safe}"


CLIENT_SOURCES = ("dashboard", "storefront")


BUNDLES_ROOT = Path(os.environ.get("CLIENT_BUNDLES_ROOT", str(_default_bundles_root())))

CLIENT_BUNDLE_KIND = "CLIENT_BUNDLE"


def bundle_dir_for_version(source: str, version: str) -> Path:
    safe = re.sub(r"[^\w.\-]", "-", version.strip())
    return BUNDLES_ROOT / f"{source}-{safe}"


def bundle_filename(bundle_id: str) -> str:
    safe = re.sub(r"[^\w.\-]", "-", bundle_id.strip())
    return f"{safe}.graphql.json"


@dataclass
class ClientBundle:
    bundle_id: str
    source: str
    source_path: str
    operation_names: list[str]
    document: str
    variables: dict[str, Any]
    auth_context: str = "staff"
    priority: str = "P1"
    golden_response: dict[str, Any] | None = None
    golden_outcome: str | None = None
    golden_status: str | None = None
    golden_contract: str | None = None
    http_status: int | None = None
    response_shape_hash: str | None = None
    semantic_profile: dict[str, Any] | None = None
    document_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "bundle_id": self.bundle_id,
            "source": self.source,
            "source_path": self.source_path,
            "operation_names": self.operation_names,
            "document": self.document,
            "variables": self.variables,
            "auth_context": self.auth_context,
            "priority": self.priority,
        }
        if self.golden_response is not None:
            d["golden_response"] = self.golden_response
        if self.golden_outcome:
            d["golden_outcome"] = self.golden_outcome
        if self.golden_status:
            d["golden_status"] = self.golden_status
        if self.golden_contract:
            d["golden_contract"] = self.golden_contract
        if self.http_status is not None:
            d["http_status"] = self.http_status
        if self.response_shape_hash:
            d["response_shape_hash"] = self.response_shape_hash
        if self.semantic_profile:
            d["semantic_profile"] = self.semantic_profile
        if self.document_hash:
            d["document_hash"] = self.document_hash
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClientBundle:
        return cls(
            bundle_id=data["bundle_id"],
            source=data.get("source", "saleor-dashboard"),
            source_path=data.get("source_path", ""),
            operation_names=data.get("operation_names") or [],
            document=data["document"],
            variables=data.get("variables") or {},
            auth_context=data.get("auth_context", "staff"),
            priority=data.get("priority", "P1"),
            golden_response=data.get("golden_response"),
            golden_outcome=data.get("golden_outcome"),
            golden_status=data.get("golden_status"),
            golden_contract=data.get("golden_contract"),
            http_status=data.get("http_status"),
            response_shape_hash=data.get("response_shape_hash"),
            semantic_profile=data.get("semantic_profile"),
            document_hash=data.get("document_hash"),
        )

    def client_category(self) -> str:
        if self.source == "saleor-storefront" or "storefront" in (self.source or ""):
            return "client-storefront"
        return "client-dashboard"

    def to_golden_probe(self) -> GoldenProbe:
        """Adapt bundle for existing comparison pipeline."""
        root = self.operation_names[0] if self.operation_names else self.bundle_id
        return GoldenProbe(
            endpoint_name=self.bundle_id,
            endpoint_kind=CLIENT_BUNDLE_KIND,
            category=self.client_category(),
            input_sent=self.document,
            golden_response=self.golden_response or {},
            golden_outcome=self.golden_outcome or "unknown",
            golden_status=self.golden_status or "warn",
            response_shape_hash=self.response_shape_hash,
            golden_contract=self.golden_contract,
            http_status=self.http_status,
            probe_stability="stateful",
            semantic_profile=self.semantic_profile,
        )

    def has_golden(self) -> bool:
        return self.golden_response is not None


def document_hash(document: str) -> str:
    normalized = re.sub(r"\s+", " ", document.strip())
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"sha256:{digest[:16]}"


def load_bundle_manifest(source: str, version: str) -> dict[str, Any] | None:
    path = bundle_dir_for_version(source, version) / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_fixtures(source: str, version: str) -> dict[str, Any]:
    path = bundle_dir_for_version(source, version) / "fixtures.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_fixtures(source: str, version: str, fixtures: dict[str, Any]) -> Path:
    directory = bundle_dir_for_version(source, version)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "fixtures.json"
    path.write_text(json.dumps(fixtures, indent=2), encoding="utf-8")
    return path


def load_bundle_from_disk(source: str, version: str, bundle_id: str) -> ClientBundle | None:
    path = bundle_dir_for_version(source, version) / "bundles" / bundle_filename(bundle_id)
    if not path.is_file():
        return None
    return ClientBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_all_bundles_from_disk(
    source: str,
    version: str,
    *,
    priority: str | None = None,
    recorded_only: bool = False,
) -> list[ClientBundle]:
    bundles_dir = bundle_dir_for_version(source, version) / "bundles"
    if not bundles_dir.is_dir():
        return []
    bundles: list[ClientBundle] = []
    for path in sorted(bundles_dir.glob("*.graphql.json")):
        bundle = ClientBundle.from_dict(json.loads(path.read_text(encoding="utf-8")))
        if priority and bundle.priority != priority:
            continue
        if recorded_only and not bundle.has_golden():
            continue
        bundles.append(bundle)
    return bundles


def write_bundle(source: str, version: str, bundle: ClientBundle) -> Path:
    directory = bundle_dir_for_version(source, version)
    bundles_dir = directory / "bundles"
    bundles_dir.mkdir(parents=True, exist_ok=True)
    if not bundle.document_hash:
        bundle.document_hash = document_hash(bundle.document)
    path = bundles_dir / bundle_filename(bundle.bundle_id)
    path.write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
    return path


def bundles_hash(source: str, version: str) -> str:
    bundles_dir = bundle_dir_for_version(source, version) / "bundles"
    if not bundles_dir.is_dir():
        return ""
    parts = [p.read_text(encoding="utf-8") for p in sorted(bundles_dir.glob("*.graphql.json"))]
    if not parts:
        return ""
    digest = hashlib.sha256("".join(parts).encode()).hexdigest()
    return f"sha256:{digest}"


def update_bundle_manifest(source: str, version: str, *, dashboard_git_tag: str | None = None) -> None:
    directory = bundle_dir_for_version(source, version)
    manifest_path = directory / "manifest.json"
    bundles = load_all_bundles_from_disk(source, version)
    bundles_index: dict[str, Any] = {}
    for b in bundles:
        bundles_index[b.bundle_id] = {
            "document_hash": b.document_hash or document_hash(b.document),
            "operation_names": b.operation_names,
            "priority": b.priority,
            "recorded": b.has_golden(),
            "golden_contract": b.golden_contract,
        }
    manifest = load_bundle_manifest(source, version) or {}
    manifest.update({
        "source": source,
        "dashboard_version": version,
        "dashboard_git_tag": dashboard_git_tag or version,
        "bundle_count": len(bundles),
        "recorded_count": sum(1 for b in bundles if b.has_golden()),
        "bundles_hash": bundles_hash(source, version),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "bundles_index": bundles_index,
    })
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_registry() -> dict[str, Any]:
    path = BUNDLES_ROOT / "registry.json"
    if not path.is_file():
        return {"default_dashboard_version": "3.23.6", "supported": []}
    return json.loads(path.read_text(encoding="utf-8"))


def register_bundle_version(source: str, version: str, *, bundle_count: int) -> None:
    registry = load_registry()
    supported = [e for e in registry.get("supported", []) if e.get("version") != version]
    supported.append({
        "source": source,
        "version": version,
        "bundle_count": bundle_count,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    registry["supported"] = supported
    if source == "dashboard":
        registry["default_dashboard_version"] = version
    if source == "storefront":
        registry["default_storefront_version"] = version
    (BUNDLES_ROOT / "registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")


def resolve_storefront_bundle_version(detected: str | None = None) -> str:
    from app.core.config import settings

    if settings.client_bundles_storefront_version:
        return settings.client_bundles_storefront_version
    baseline = settings.reference_baseline_version
    registry = load_registry()
    default = registry.get("default_storefront_version", baseline)
    if load_all_bundles_from_disk("storefront", baseline, recorded_only=True):
        return baseline
    if load_all_bundles_from_disk("storefront", default, recorded_only=True):
        return default
    if load_all_bundles_from_disk("storefront", baseline):
        return baseline
    return detected or default


def resolve_dashboard_bundle_version(detected: str | None = None) -> str:
    from app.core.config import settings

    if settings.client_bundles_dashboard_version:
        return settings.client_bundles_dashboard_version
    baseline = settings.reference_baseline_version
    registry = load_registry()
    default = registry.get("default_dashboard_version", baseline)
    if load_all_bundles_from_disk("dashboard", baseline, recorded_only=True):
        return baseline
    if load_all_bundles_from_disk("dashboard", default, recorded_only=True):
        return default
    if load_all_bundles_from_disk("dashboard", baseline):
        return baseline
    return detected or default


def bundles_compatible_with_schema(
    bundles: list[ClientBundle],
    intro: dict[str, list[str]],
) -> tuple[list[ClientBundle], list[dict[str, str]]]:
    from app.services.client_bundle_schema_gate import compute_client_bundle_schema_gate

    gate = compute_client_bundle_schema_gate(bundles, intro, recorded_only=False)
    incompatible = {m["bundle_id"] for m in gate.get("missing_l3_fields") or []}
    compatible = [b for b in bundles if b.bundle_id not in incompatible]
    excluded = [m for m in gate.get("missing_l3_fields") or [] if m["bundle_id"] in incompatible]
    return compatible, excluded


def build_client_bundle_endpoints(
    version: str | None = None,
    *,
    source: str = "dashboard",
    priority: str | None = None,
    recorded_only: bool = True,
    schema_intro: dict[str, list[str]] | None = None,
) -> list[dict]:
    if source == "storefront":
        ver = version or resolve_storefront_bundle_version()
    else:
        ver = version or resolve_dashboard_bundle_version()
    bundles = load_all_bundles_from_disk(
        source,
        ver,
        priority=priority,
        recorded_only=recorded_only,
    )
    if schema_intro is not None:
        bundles, _ = bundles_compatible_with_schema(bundles, schema_intro)
    fixtures = load_fixtures(source, ver)
    endpoints: list[dict] = []
    for bundle in bundles:
        endpoints.append({
            "name": bundle.bundle_id,
            "kind": CLIENT_BUNDLE_KIND,
            "category": bundle.client_category(),
            "is_public": bundle.auth_context == "anonymous",
            "auth_context": bundle.auth_context,
            "golden_input": bundle.document,
            "bundle_document": bundle.document,
            "bundle_variables": bundle.variables,
            "bundle_fixtures": fixtures,
            "source": bundle.source,
            "client_source": source,
        })
    return endpoints


def build_all_client_bundle_endpoints(
    *,
    recorded_only: bool = True,
    schema_intro: dict[str, list[str]] | None = None,
    sources: tuple[str, ...] = CLIENT_SOURCES,
) -> list[dict]:
    endpoints: list[dict] = []
    for source in sources:
        endpoints.extend(
            build_client_bundle_endpoints(
                source=source,
                recorded_only=recorded_only,
                schema_intro=schema_intro,
            )
        )
    return endpoints


def remove_client_bundles(source: str, version: str, bundle_ids: list[str]) -> int:
    removed = 0
    bundles_dir = bundle_dir_for_version(source, version) / "bundles"
    for bid in bundle_ids:
        path = bundles_dir / bundle_filename(bid)
        if path.is_file():
            path.unlink()
            removed += 1
    if removed:
        update_bundle_manifest(source, version)
    return removed


def is_stub_bundle(bundle: ClientBundle) -> bool:
    dh = bundle.document_hash or ""
    return dh.startswith("sha256:seed") or bundle.source_path.startswith("seed/")


def client_bundle_count(
    version: str | None = None,
    *,
    source: str = "dashboard",
) -> int:
    if source == "storefront":
        ver = version or resolve_storefront_bundle_version()
    else:
        ver = version or resolve_dashboard_bundle_version()
    return len(load_all_bundles_from_disk(source, ver, recorded_only=True))


def total_client_bundle_count(
    *,
    schema_intro: dict[str, list[str]] | None = None,
) -> int:
    return len(
        build_all_client_bundle_endpoints(
            recorded_only=True,
            schema_intro=schema_intro,
        )
    )

