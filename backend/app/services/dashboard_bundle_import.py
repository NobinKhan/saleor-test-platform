"""
Import GraphQL operation bundles from saleor-dashboard source tree.
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
    dashboard_vendor_path,
    document_hash,
    register_bundle_version,
    update_bundle_manifest,
    write_bundle,
)

P0_ROOT_FIELDS = frozenset({
    "me",
    "shop",
    "orders",
    "products",
    "channels",
    "checkouts",
    "customers",
    "order",
    "draftOrders",
    "productVariant",
    "productVariants",
    "collections",
    "categories",
    "category",
    "collection",
    "product",
    "checkout",
    "channel",
    "customer",
    "warehouses",
    "warehouse",
    "vouchers",
    "voucher",
    "giftCards",
    "giftCard",
})

P0_OPERATION_NAMES = frozenset({
    "OrderList",
    "OrderDetails",
    "ProductList",
    "ProductDetails",
    "CollectionList",
    "CategoryList",
    "ChannelList",
    "CustomerList",
    "CheckoutList",
    "ShopDetails",
    "Me",
    "MeDetails",
})

_GQL_BLOCK = re.compile(r"gql`\s*(.*?)\s*`", re.DOTALL)

_SKIP_TS_PARTS = frozenset({"testUtils", "node_modules", "__mocks__"})


def _should_skip_source(path: Path) -> bool:
    name = path.name
    if name.endswith(".test.ts") or name.endswith(".stories.ts"):
        return True
    if "generated" in name:
        return True
    return any(part in _SKIP_TS_PARTS for part in path.parts)


def extract_gql_blocks_from_ts(text: str) -> list[str]:
    blocks = []
    for block in _GQL_BLOCK.findall(text):
        cleaned = _strip_gql_interpolation(block.strip())
        if cleaned:
            blocks.append(cleaned)
    return blocks


def _strip_gql_interpolation(block: str) -> str:
    lines = [ln for ln in block.splitlines() if not re.match(r"^\s*\$\{", ln)]
    return "\n".join(lines).strip()


def root_fields_in_document(document: str) -> list[tuple[str, str]]:
    """Return [(root_field, QUERY|MUTATION), ...] for the primary operation."""
    doc = parse(document)
    fragments: dict[str, FragmentDefinitionNode] = {
        d.name.value: d
        for d in doc.definitions
        if isinstance(d, FragmentDefinitionNode)
    }
    results: list[tuple[str, str]] = []
    for definition in doc.definitions:
        if not isinstance(definition, OperationDefinitionNode):
            continue
        kind = definition.operation.value.upper()
        if not definition.selection_set:
            continue
        for sel in definition.selection_set.selections:
            if isinstance(sel, FieldNode):
                results.append((sel.name.value, kind))
            elif isinstance(sel, FragmentSpreadNode):
                frag = fragments.get(sel.name.value)
                if frag and frag.selection_set:
                    for fsel in frag.selection_set.selections:
                        if isinstance(fsel, FieldNode):
                            results.append((fsel.name.value, kind))
            elif isinstance(sel, InlineFragmentNode):
                if sel.selection_set:
                    for fsel in sel.selection_set.selections:
                        if isinstance(fsel, FieldNode):
                            results.append((fsel.name.value, kind))
    if not results:
        return _root_fields_regex(document)
    return results


def _root_fields_regex(document: str) -> list[tuple[str, str]]:
    roots: list[tuple[str, str]] = []
    kind_match = re.search(r"\b(query|mutation|subscription)\b", document, re.I)
    kind = (kind_match.group(1).upper() if kind_match else "QUERY")
    if kind == "SUBSCRIPTION":
        kind = "QUERY"
    for field_name in _root_fields_in_selection(document):
        roots.append((field_name, kind if kind in ("QUERY", "MUTATION") else "QUERY"))
    return roots


def _root_fields_in_selection(document: str) -> set[str]:
    roots: set[str] = set()
    for m in re.finditer(r"(?:query|mutation|subscription)\s+\w*[^{]*\{([^}]+)", document, re.I):
        block = m.group(1)
        for fm in re.finditer(r"\b(\w+)\s*[(\{]", block):
            name = fm.group(1)
            if name not in ("query", "mutation", "subscription", "__typename"):
                roots.add(name)
    return roots


def _operation_priority(operation_names: list[str], document: str) -> str:
    if any(n in P0_OPERATION_NAMES for n in operation_names):
        return "P0"
    roots = _root_fields_in_selection(document)
    if roots & P0_ROOT_FIELDS:
        return "P0"
    return "P1"


def _slugify(name: str, source_path: str) -> str:
    base = name or Path(source_path).stem
    safe = re.sub(r"[^\w.\-]+", "-", base).strip("-").lower()
    return safe or hashlib.sha256(source_path.encode()).hexdigest()[:12]


def _collect_fragments(doc: DocumentNode) -> dict[str, FragmentDefinitionNode]:
    return {
        d.name.value: d
        for d in doc.definitions
        if isinstance(d, FragmentDefinitionNode)
    }


def _expand_operation(
    op: OperationDefinitionNode,
    fragments: dict[str, FragmentDefinitionNode],
) -> str:
    """Print single operation with fragment dependencies inlined."""
    used: dict[str, FragmentDefinitionNode] = {}

    def collect_frags(node: Any) -> None:
        if hasattr(node, "selection_set") and node.selection_set:
            for sel in node.selection_set.selections:
                if isinstance(sel, FragmentSpreadNode):
                    fname = sel.name.value
                    if fname in fragments and fname not in used:
                        used[fname] = fragments[fname]
                        collect_frags(fragments[fname])
                elif hasattr(sel, "selection_set"):
                    collect_frags(sel)

    collect_frags(op)
    mini_doc = DocumentNode(definitions=[op, *used.values()])
    return print_ast(mini_doc).strip()


def _bundle_from_operation(
    definition: OperationDefinitionNode,
    document: str,
    rel_path: str,
) -> ClientBundle:
    op_name = definition.name.value if definition.name else "anonymous"
    op_names = [op_name] if op_name != "anonymous" else []
    if not op_names:
        roots = _root_fields_in_selection(document)
        op_names = [next(iter(roots), "anonymous")]
    bundle_id = _slugify(op_name if op_name != "anonymous" else op_names[0], rel_path)
    return ClientBundle(
        bundle_id=bundle_id,
        source="saleor-dashboard",
        source_path=rel_path,
        operation_names=op_names,
        document=document,
        variables=_default_variables(document),
        auth_context="staff",
        priority=_operation_priority(op_names, document),
        document_hash=document_hash(document),
    )


def parse_graphql_file(path: Path, rel_path: str) -> list[ClientBundle]:
    text = path.read_text(encoding="utf-8")
    bundles: list[ClientBundle] = []
    try:
        doc = parse(text)
    except Exception:
        return _parse_graphql_file_regex(text, rel_path)

    fragments = _collect_fragments(doc)
    for definition in doc.definitions:
        if not isinstance(definition, OperationDefinitionNode):
            continue
        document = _expand_operation(definition, fragments)
        bundles.append(_bundle_from_operation(definition, document, rel_path))
    return bundles


def _parse_graphql_file_regex(text: str, rel_path: str) -> list[ClientBundle]:
    """Fallback when graphql parse fails (e.g. unsupported syntax)."""
    bundles: list[ClientBundle] = []
    pattern = re.compile(
        r"(query|mutation|subscription)\s+(\w+)?[^{]*\{",
        re.I,
    )
    for i, m in enumerate(pattern.finditer(text)):
        op_name = m.group(2) or f"anonymous-{i}"
        start = m.start()
        depth = 0
        end = start
        for j, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j + 1
                    break
        document = text[start:end].strip()
        op_names = [op_name]
        bundle_id = _slugify(op_name, f"{rel_path}-{i}")
        bundles.append(
            ClientBundle(
                bundle_id=bundle_id,
                source="saleor-dashboard",
                source_path=rel_path,
                operation_names=op_names,
                document=document,
                variables=_default_variables(document),
                auth_context="staff",
                priority=_operation_priority(op_names, document),
                document_hash=document_hash(document),
            )
        )
    return bundles


def _default_variables(document: str) -> dict[str, Any]:
    variables: dict[str, Any] = {}
    for m in re.finditer(r"\$(\w+)\s*:\s*(\w+)!?", document):
        name, gtype = m.group(1), m.group(2)
        lname = name.lower()
        if gtype in ("Int", "Float"):
            variables[name] = 10 if lname in ("first", "last") else 0
        elif gtype == "Boolean":
            if "permission" in lname or lname.startswith("has"):
                variables[name] = True
            else:
                variables[name] = False
        elif gtype == "ID":
            if "checkout" in lname and "line" not in lname:
                variables[name] = "{{fixtures.default_checkout_id}}"
            elif "channel" in lname:
                variables[name] = "{{fixtures.default_channel_id}}"
            elif "product" in lname and "variant" not in lname:
                variables[name] = "{{fixtures.default_product_id}}"
            elif "variant" in lname:
                variables[name] = "{{fixtures.default_variant_id}}"
            elif "order" in lname:
                variables[name] = "{{fixtures.default_order_id}}"
            elif "customer" in lname or lname == "userid":
                variables[name] = "{{fixtures.default_customer_id}}"
            elif "warehouse" in lname:
                variables[name] = "{{fixtures.default_warehouse_id}}"
            elif "collection" in lname:
                variables[name] = "{{fixtures.default_collection_id}}"
            elif "category" in lname:
                variables[name] = "{{fixtures.default_category_id}}"
            else:
                variables[name] = "{{fixtures.placeholder_id}}"
        elif gtype == "String":
            if lname == "query":
                variables[name] = "{{fixtures.default_slug}}"
            elif "token" in lname and "checkout" in lname:
                variables[name] = "{{fixtures.default_checkout_token}}"
            elif "channel" in lname:
                variables[name] = "{{fixtures.default_channel}}"
            elif "slug" in lname:
                variables[name] = "{{fixtures.default_slug}}"
            else:
                variables[name] = ""
        elif gtype.startswith("[") or gtype.endswith("]"):
            variables[name] = []
        else:
            variables[name] = None
    return variables


def build_fragment_registry(dashboard_path: Path) -> dict[str, FragmentDefinitionNode]:
    registry: dict[str, FragmentDefinitionNode] = {}
    for path in sorted(dashboard_path.rglob("*")):
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


def scan_dashboard_bundles(
    dashboard_path: Path,
    *,
    priority_filter: str | None = None,
) -> list[ClientBundle]:
    """Parse all operations from vendored dashboard source."""
    registry = build_fragment_registry(dashboard_path)
    all_bundles: list[ClientBundle] = []
    seen_ids: set[str] = set()

    def add_bundle(bundle: ClientBundle) -> None:
        if priority_filter and bundle.priority != priority_filter:
            return
        if bundle.bundle_id in seen_ids:
            suffix = hashlib.sha256(bundle.source_path.encode()).hexdigest()[:6]
            data = bundle.to_dict()
            data["bundle_id"] = f"{bundle.bundle_id}-{suffix}"
            bundle = ClientBundle.from_dict(data)
        seen_ids.add(bundle.bundle_id)
        all_bundles.append(bundle)

    for path in sorted(dashboard_path.rglob("*")):
        if path.suffix in (".graphql", ".gql"):
            rel = str(path.relative_to(dashboard_path))
            for bundle in parse_graphql_file(path, rel):
                add_bundle(bundle)
        elif path.suffix == ".ts" and not _should_skip_source(path):
            rel = str(path.relative_to(dashboard_path))
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


def import_dashboard_bundles(
    *,
    dashboard_path: Path,
    version: str,
    priority_filter: str | None = None,
) -> dict[str, Any]:
    all_bundles = scan_dashboard_bundles(dashboard_path, priority_filter=priority_filter)
    seen_hashes: set[str] = set()
    written: list[ClientBundle] = []

    for bundle in all_bundles:
        dh = bundle.document_hash or document_hash(bundle.document)
        if dh in seen_hashes:
            continue
        seen_hashes.add(dh)
        write_bundle("dashboard", version, bundle)
        written.append(bundle)

    update_bundle_manifest("dashboard", version, dashboard_git_tag=version)
    register_bundle_version("dashboard", version, bundle_count=len(written))

    return {
        "version": version,
        "imported": len(written),
        "p0_count": sum(1 for b in written if b.priority == "P0"),
        "path": str(dashboard_path),
    }


def sync_client_bundles_from_vendor(
    version: str | None = None,
    *,
    priority_filter: str | None = None,
) -> dict[str, Any]:
    from app.core.config import settings

    ver = version or settings.reference_baseline_version
    vendor = dashboard_vendor_path(ver)
    src = vendor / "src" if (vendor / "src").is_dir() else vendor
    if not src.is_dir():
        raise FileNotFoundError(f"Dashboard vendor source not found: {src}")
    return import_dashboard_bundles(
        dashboard_path=src,
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


def compute_client_bundle_diff(
    *,
    version: str,
    imported: list[ClientBundle] | None = None,
) -> ClientBundleDiff:
    from app.services.client_bundles import load_all_bundles_from_disk

    if imported is None:
        vendor = dashboard_vendor_path(version)
        src = vendor / "src" if (vendor / "src").is_dir() else vendor
        imported = scan_dashboard_bundles(src) if src.is_dir() else []

    on_disk = {b.bundle_id: b for b in load_all_bundles_from_disk("dashboard", version)}
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
