"""
Golden reference corpus — JSON files on disk (source of truth) with helpers.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any


def _default_corpus_root() -> Path:
    here = Path(__file__).resolve()
    # Repo layout: project/reference/corpora (backend/app/services -> parents[3])
    repo_root = here.parents[3] / "reference" / "corpora"
    if repo_root.parent.is_dir():
        return repo_root
    # Docker layout: /app/reference/corpora
    docker_root = here.parents[2] / "reference" / "corpora"
    return docker_root


CORPUS_ROOT = Path(os.environ.get("REFERENCE_CORPUS_ROOT", str(_default_corpus_root())))


def corpus_dir_for_version(version: str) -> Path:
    safe = re.sub(r"[^\w.\-]", "-", version.strip())
    return CORPUS_ROOT / f"saleor-{safe}"


def probe_filename(endpoint_name: str, endpoint_kind: str) -> str:
    return f"{endpoint_name}__{endpoint_kind}.json"


@dataclass
class GoldenProbe:
    endpoint_name: str
    endpoint_kind: str
    category: str
    input_sent: str
    golden_response: dict[str, Any]
    golden_outcome: str
    golden_status: str
    error_pattern: str | None = None
    response_shape_hash: str | None = None
    golden_contract: str | None = None
    http_status: int | None = None
    probe_stability: str | None = None
    semantic_profile: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "endpoint_name": self.endpoint_name,
            "endpoint_kind": self.endpoint_kind,
            "category": self.category,
            "input_sent": self.input_sent,
            "golden_response": self.golden_response,
            "golden_outcome": self.golden_outcome,
            "golden_status": self.golden_status,
            "error_pattern": self.error_pattern,
            "response_shape_hash": self.response_shape_hash,
        }
        if self.golden_contract:
            d["golden_contract"] = self.golden_contract
        if self.http_status is not None:
            d["http_status"] = self.http_status
        if self.probe_stability:
            d["probe_stability"] = self.probe_stability
        if self.semantic_profile:
            d["semantic_profile"] = self.semantic_profile
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldenProbe:
        return cls(
            endpoint_name=data["endpoint_name"],
            endpoint_kind=data["endpoint_kind"],
            category=data.get("category", "unknown"),
            input_sent=data["input_sent"],
            golden_response=data["golden_response"],
            golden_outcome=data["golden_outcome"],
            golden_status=data["golden_status"],
            error_pattern=data.get("error_pattern"),
            response_shape_hash=data.get("response_shape_hash"),
            golden_contract=data.get("golden_contract"),
            http_status=data.get("http_status"),
            probe_stability=data.get("probe_stability"),
            semantic_profile=data.get("semantic_profile"),
        )


def response_shape_hash(resp: dict[str, Any]) -> str:
    shape = _shape_of(resp)
    raw = json.dumps(shape, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return f"sha256:{digest[:16]}"


def _shape_of(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _shape_of(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        if not obj:
            return []
        return [_shape_of(obj[0])]
    return type(obj).__name__


def corpus_hash(version: str) -> str:
    """Hash probe files only (manifest excluded to avoid self-referential drift)."""
    directory = corpus_dir_for_version(version)
    if not directory.is_dir():
        return ""
    parts: list[str] = []
    probes_dir = directory / "probes"
    if probes_dir.is_dir():
        for path in sorted(probes_dir.glob("*.json")):
            parts.append(path.read_text(encoding="utf-8"))
    if not parts:
        return ""
    digest = hashlib.sha256("".join(parts).encode()).hexdigest()
    return f"sha256:{digest}"


def load_manifest(version: str) -> dict[str, Any] | None:
    path = corpus_dir_for_version(version) / "manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_probe_from_disk(version: str, endpoint_name: str, endpoint_kind: str) -> GoldenProbe | None:
    path = corpus_dir_for_version(version) / "probes" / probe_filename(endpoint_name, endpoint_kind)
    if not path.is_file():
        return None
    return GoldenProbe.from_dict(json.loads(path.read_text(encoding="utf-8")))


def load_all_probes_from_disk(version: str) -> list[GoldenProbe]:
    probes_dir = corpus_dir_for_version(version) / "probes"
    if not probes_dir.is_dir():
        return []
    probes: list[GoldenProbe] = []
    for path in sorted(probes_dir.glob("*.json")):
        probes.append(GoldenProbe.from_dict(json.loads(path.read_text(encoding="utf-8"))))
    return probes


def write_corpus(
    version: str,
    saleor_url: str,
    probes: list[GoldenProbe],
    *,
    merge: bool = False,
) -> Path:
    directory = corpus_dir_for_version(version)
    probes_dir = directory / "probes"
    probes_dir.mkdir(parents=True, exist_ok=True)

    if not merge:
        for old in probes_dir.glob("*.json"):
            old.unlink()

    for probe in probes:
        path = probes_dir / probe_filename(probe.endpoint_name, probe.endpoint_kind)
        path.write_text(json.dumps(probe.to_dict(), indent=2), encoding="utf-8")

    manifest_path = directory / "manifest.json"
    existing_manifest = load_manifest(version) or {}
    operations_index = existing_manifest.get("operations_index") or {}
    for probe in probes:
        key = f"{probe.endpoint_name}__{probe.endpoint_kind}"
        operations_index[key] = {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "input_hash": hashlib.sha256(probe.input_sent.encode()).hexdigest()[:16],
            "golden_contract": probe.golden_contract,
            "semantic_profile": probe.semantic_profile,
        }

    manifest = {
        "saleor_version": version,
        "saleor_url": saleor_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "probe_count": len(list(probes_dir.glob("*.json"))),
        "corpus_hash": "",
        "operations_index": operations_index,
    }
    if existing_manifest.get("catalog_version"):
        manifest["catalog_version"] = existing_manifest["catalog_version"]
    if existing_manifest.get("reference_queries"):
        manifest["reference_queries"] = existing_manifest["reference_queries"]
    if existing_manifest.get("reference_mutations"):
        manifest["reference_mutations"] = existing_manifest["reference_mutations"]
    manifest["corpus_hash"] = corpus_hash(version)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return directory


def remove_probes_from_disk(
    version: str,
    ops: list[tuple[str, str]],
) -> int:
    """Remove probe files by (name, kind) pairs. Returns count removed."""
    probes_dir = corpus_dir_for_version(version) / "probes"
    removed = 0
    for name, kind in ops:
        path = probes_dir / probe_filename(name, kind)
        if path.is_file():
            path.unlink()
            removed += 1
    return removed


def update_manifest_after_patch(version: str) -> None:
    """Refresh probe_count, corpus_hash, and operations_index after patch."""
    directory = corpus_dir_for_version(version)
    manifest_path = directory / "manifest.json"
    manifest = load_manifest(version) or {"saleor_version": version}
    probes = load_all_probes_from_disk(version)
    operations_index: dict[str, Any] = {}
    for probe in probes:
        key = f"{probe.endpoint_name}__{probe.endpoint_kind}"
        operations_index[key] = {
            "recorded_at": manifest.get("captured_at"),
            "input_hash": hashlib.sha256(probe.input_sent.encode()).hexdigest()[:16],
            "golden_contract": probe.golden_contract,
            "semantic_profile": probe.semantic_profile,
        }
    manifest["operations_index"] = operations_index
    manifest["probe_count"] = len(probes)
    manifest["corpus_hash"] = corpus_hash(version)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _has_probes(version: str) -> bool:
    probes_dir = corpus_dir_for_version(version) / "probes"
    return probes_dir.is_dir() and any(probes_dir.glob("*.json"))


def resolve_corpus_version(detected_version: str | None, baseline: str = "3.23.7") -> str:
    """Pick the best on-disk corpus for a detected Saleor version."""
    if detected_version and _has_probes(detected_version):
        return detected_version
    if _has_probes(baseline):
        det_mm = ".".join((detected_version or "").split(".")[:2])
        base_mm = ".".join(baseline.split(".")[:2])
        if not detected_version or det_mm == base_mm:
            return baseline
    if detected_version:
        det_mm = ".".join(detected_version.split(".")[:2])
        for path in sorted(CORPUS_ROOT.glob("saleor-*"), reverse=True):
            ver = path.name.replace("saleor-", "", 1)
            if ".".join(ver.split(".")[:2]) == det_mm and _has_probes(ver):
                return ver
    if _has_probes(baseline):
        return baseline
    return detected_version or baseline
