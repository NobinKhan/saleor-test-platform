"""
Import GraphQL operation bundles from saleor-storefront vendor source tree.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from graphql import parse, print_ast
from graphql.language.ast import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    OperationDefinitionNode,
)

from app.services.client_bundles import (
    ClientBundle,
    document_hash,
    register_bundle_version,
    update_bundle_manifest,
    write_bundle,
)
from app.services.dashboard_bundle_import import (
    _collect_fragments,
    _default_variables,
    _expand_operation,
    _should_skip_source,
    _slugify,
    extract_gql_blocks_from_ts,
    parse_graphql_file,
    root_fields_in_document,
)

STOREFRONT_P0_ROOT_FIELDS = frozenset({
    "shop",
    "products",
    "product",
    "productVariants",
    "categories",
    "category",
    "collections",
    "collection",
    "checkout",
    "checkouts",
    "attributes",
    "menu",
    "page",
    "pages",
    "me",
})

STOREFRONT_P0_OPERATION_NAMES = frozenset({
    "ProductDetails",
    "VariantList",
    "FeaturedProductsQuery",
    "ShopAttributesQuery",
    "ShopMenusQuery",
})

CUSTOMER_AUTH_OPS = frozenset({
    "me",
    "accountUpdate",
    "accountRegister",
    "passwordChange",
    "requestPasswordReset",
    "confirmAccount",
    "accountAddressCreate",
    "accountAddressUpdate",
    "accountAddressDelete",
})

_GQL_BLOCK = re.compile(r"gql`\s*(.*?)\s*`", re.DOTALL)


def storefront_vendor_path(version: str) -> Path:
    from app.services.client_bundles import VENDOR_ROOT

    safe = re.sub(r"[^\w.\-]", "-", version.strip())
    return VENDOR_ROOT / f"saleor-storefront-{safe}"


def _infer_auth_context(operation_names: list[str], document: str) -> str:
    roots = {name for name, _ in root_fields_in_document(document)}
    if roots & CUSTOMER_AUTH_OPS or any(
        n.lower().startswith("account") for n in operation_names
    ):
        return "customer"
    return "anonymous"


def _operation_priority(operation_names: list[str], document: str) -> str:
    if any(n in STOREFRONT_P0_OPERATION_NAMES for n in operation_names):
        return "P0"
    roots = {name for name, _ in root_fields_in_document(document)}
    if roots & STOREFRONT_P0_ROOT_FIELDS:
        return "P0"
    return "P1"


def _bundle_from_operation(
    definition: OperationDefinitionNode,
    document: str,
    rel_path: str,
) -> ClientBundle:
    op_name = definition.name.value if definition.name else "anonymous"
    op_names = [op_name] if op_name != "anonymous" else []
    if not op_names:
        roots = root_fields_in_document(document)
        op_names = [roots[0][0] if roots else "anonymous"]
    bundle_id = _slugify(op_name if op_name != "anonymous" else op_names[0], rel_path)
    auth_context = _infer_auth_context(op_names, document)
    return ClientBundle(
        bundle_id=bundle_id,
        source="saleor-storefront",
        source_path=rel_path,
        operation_names=op_names,
        document=document,
        variables=_default_variables(document),
        auth_context=auth_context,
        priority=_operation_priority(op_names, document),
        document_hash=document_hash(document),
    )


def build_fragment_registry(storefront_path: Path) -> dict[str, FragmentDefinitionNode]:
    registry: dict[str, FragmentDefinitionNode] = {}
    for path in sorted(storefront_path.rglob("*")):
        if path.suffix == ".ts" and not _should_skip_source(path):
            for block in extract_gql_blocks_from_ts(path.read_text(encoding="utf-8")):
                try:
                    doc = parse(block)
                except Exception:
                    continue
                registry.update(_collect_fragments(doc))
        elif path.suffix in (".graphql", ".gql"):
            try:
                registry.update(_collect_fragments(parse(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
    return registry


def scan_storefront_bundles(
    storefront_path: Path,
    *,
    priority_filter: str | None = None,
) -> list[ClientBundle]:
    registry = build_fragment_registry(storefront_path)
    all_bundles: list[ClientBundle] = []
    seen_ids: set[str] = set()

    def add_bundle(bundle: ClientBundle) -> None:
        if priority_filter and bundle.priority != priority_filter:
            return
        data = bundle.to_dict()
        if not data["bundle_id"].startswith("sf-"):
            data["bundle_id"] = f"sf-{data['bundle_id']}"
        bundle = ClientBundle.from_dict(data)
        if bundle.bundle_id in seen_ids:
            suffix = hashlib.sha256(bundle.source_path.encode()).hexdigest()[:6]
            data = bundle.to_dict()
            data["bundle_id"] = f"{bundle.bundle_id}-{suffix}"
            bundle = ClientBundle.from_dict(data)
        seen_ids.add(bundle.bundle_id)
        all_bundles.append(bundle)

    for path in sorted(storefront_path.rglob("*")):
        if path.suffix in (".graphql", ".gql"):
            rel = str(path.relative_to(storefront_path))
            for bundle in parse_graphql_file(path, rel):
                bundle = ClientBundle.from_dict({
                    **bundle.to_dict(),
                    "source": "saleor-storefront",
                    "auth_context": _infer_auth_context(bundle.operation_names, bundle.document),
                    "priority": _operation_priority(bundle.operation_names, bundle.document),
                })
                add_bundle(bundle)
        elif path.suffix in (".ts", ".tsx") and not _should_skip_source(path):
            rel = str(path.relative_to(storefront_path))
            for block in extract_gql_blocks_from_ts(path.read_text(encoding="utf-8")):
                try:
                    doc = parse(block)
                except Exception:
                    continue
                local_frags = _collect_fragments(doc)
                merged = {**registry, **local_frags}
                for definition in doc.definitions:
                    if not isinstance(definition, OperationDefinitionNode):
                        continue
                    document = _expand_operation(definition, merged)
                    add_bundle(_bundle_from_operation(definition, document, rel))

    return all_bundles


def import_storefront_bundles(
    *,
    storefront_path: Path,
    version: str,
    priority_filter: str | None = None,
) -> dict[str, Any]:
    from app.services.client_bundles import bundle_dir_for_version

    bundles_dir = bundle_dir_for_version("storefront", version) / "bundles"
    if bundles_dir.is_dir():
        for path in bundles_dir.glob("*.graphql.json"):
            path.unlink()

    all_bundles = scan_storefront_bundles(storefront_path, priority_filter=priority_filter)
    seen_hashes: set[str] = set()
    written: list[ClientBundle] = []

    for bundle in all_bundles:
        dh = bundle.document_hash or document_hash(bundle.document)
        if dh in seen_hashes:
            continue
        seen_hashes.add(dh)
        write_bundle("storefront", version, bundle)
        written.append(bundle)

    update_bundle_manifest("storefront", version, dashboard_git_tag=version)
    register_bundle_version("storefront", version, bundle_count=len(written))

    return {
        "version": version,
        "imported": len(written),
        "p0_count": sum(1 for b in written if b.priority == "P0"),
        "path": str(storefront_path),
    }


def sync_storefront_bundles_from_vendor(
    version: str | None = None,
    *,
    priority_filter: str | None = None,
) -> dict[str, Any]:
    from app.core.config import settings

    ver = version or settings.reference_baseline_version
    vendor = storefront_vendor_path(ver)
    src = vendor / "src" if (vendor / "src").is_dir() else vendor
    if not src.is_dir():
        raise FileNotFoundError(f"Storefront vendor source not found: {src}")
    return import_storefront_bundles(
        storefront_path=src,
        version=ver,
        priority_filter=priority_filter,
    )


@dataclass
class ClientBundleDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "added": self.added,
            "removed": self.removed,
            "changed": self.changed,
            "unchanged": self.unchanged,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ClientBundleDiff:
        if not data:
            return cls()
        return cls(
            added=list(data.get("added") or []),
            removed=list(data.get("removed") or []),
            changed=list(data.get("changed") or []),
            unchanged=list(data.get("unchanged") or []),
        )


def compute_storefront_bundle_diff(
    *,
    version: str,
    imported: list[ClientBundle] | None = None,
) -> ClientBundleDiff:
    from app.services.client_bundles import load_all_bundles_from_disk

    if imported is None:
        vendor = storefront_vendor_path(version)
        src = vendor / "src" if (vendor / "src").is_dir() else vendor
        imported = scan_storefront_bundles(src) if src.is_dir() else []

    on_disk = {b.bundle_id: b for b in load_all_bundles_from_disk("storefront", version)}
    incoming = {b.bundle_id: b for b in imported}
    diff = ClientBundleDiff()
    for bid in sorted(incoming):
        if bid not in on_disk:
            diff.added.append(bid)
        elif (on_disk[bid].document_hash or document_hash(on_disk[bid].document)) != (
            incoming[bid].document_hash or document_hash(incoming[bid].document)
        ):
            diff.changed.append(bid)
        else:
            diff.unchanged.append(bid)
    for bid in sorted(on_disk):
        if bid not in incoming:
            diff.removed.append(bid)
    return diff
