"""
Capture golden reference probes from a live Saleor instance.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ReferenceProbe
from app.services.introspection import introspect_saleor
from app.services.outcome import classify_graphql_response
from app.services.query_builder import build_query_with_schema, introspect_field_args
from app.services.reference_compare import probe_from_capture
from app.services.reference_corpus import (
    corpus_hash,
    load_manifest,
    write_corpus,
)
from app.services.test_runner import (
    SALEOR_MUTATIONS,
    SALEOR_QUERIES,
    build_endpoints_list,
    detect_saleor_version,
)


async def build_capture_endpoints(
    saleor_url: str,
    saleor_token: str | None,
    test_scope: str,
    timeout: int,
) -> tuple[list[dict], dict[str, list[dict]] | None]:
    endpoints = build_endpoints_list(test_scope, public_only=False)
    schema_fields: dict[str, list[dict]] | None = None

    if test_scope == "full":
        intro = await introspect_saleor(saleor_url, saleor_token, timeout)
        try:
            schema_fields = await introspect_field_args(saleor_url, saleor_token, timeout)
        except Exception:
            schema_fields = None
        known = {e["name"] for e in endpoints}
        for name in intro.get("queries", []):
            if name not in known:
                endpoints.append(
                    {
                        "name": name,
                        "kind": "QUERY",
                        "category": "unknown",
                        "is_public": True,
                    }
                )
                known.add(name)
        for name in intro.get("mutations", []):
            if name not in known:
                endpoints.append(
                    {
                        "name": name,
                        "kind": "MUTATION",
                        "category": "unknown",
                        "is_public": False,
                    }
                )
                known.add(name)

    return endpoints, schema_fields


async def capture_reference_probes(
    *,
    saleor_url: str,
    saleor_token: str | None,
    saleor_version: str | None = None,
    test_scope: str = "full",
    timeout: int = 30,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    version = saleor_version or await detect_saleor_version(saleor_url, saleor_token, timeout)
    if not version:
        version = settings.reference_baseline_version

    endpoints, schema_fields = await build_capture_endpoints(
        saleor_url, saleor_token, test_scope, timeout
    )
    headers = {"Content-Type": "application/json"}
    if saleor_token:
        headers["Authorization"] = f"Bearer {saleor_token}"

    probes = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        for endpoint in endpoints:
            query = build_query_with_schema(
                endpoint["name"], endpoint["kind"], schema_fields
            )
            resp = await client.post(
                saleor_url,
                data=json.dumps({"query": query}),
                headers=headers,
            )
            resp_json = resp.json()
            classified = classify_graphql_response(
                resp_json,
                http_status=resp.status_code,
                endpoint_kind=endpoint["kind"],
            )
            probes.append(probe_from_capture(endpoint, query, resp_json, classified))

    directory = write_corpus(version, saleor_url, probes)
    chash = corpus_hash(version)

    if db is not None:
        await _sync_probes_to_db(db, version, probes, chash)

    from app.services.reference_registry import register_corpus_version

    register_corpus_version(
        version,
        probe_count=len(probes),
        saleor_url=saleor_url,
        set_default=True,
    )

    return {
        "saleor_version": version,
        "saleor_url": saleor_url,
        "test_scope": test_scope,
        "probe_count": len(probes),
        "corpus_path": str(directory),
        "corpus_hash": chash,
    }


async def _sync_probes_to_db(
    db: AsyncSession,
    version: str,
    probes: list,
    corpus_hash_value: str,
) -> None:
    for probe in probes:
        result = await db.execute(
            select(ReferenceProbe).where(
                ReferenceProbe.saleor_version == version,
                ReferenceProbe.endpoint_name == probe.endpoint_name,
                ReferenceProbe.endpoint_kind == probe.endpoint_kind,
            )
        )
        row = result.scalar_one_or_none()
        payload = json.dumps(probe.golden_response)
        if row:
            row.category = probe.category
            row.input_sent = probe.input_sent
            row.golden_response = payload
            row.golden_outcome = probe.golden_outcome
            row.golden_status = probe.golden_status
            row.error_pattern = probe.error_pattern
            row.response_shape_hash = probe.response_shape_hash
            row.corpus_hash = corpus_hash_value
        else:
            db.add(
                ReferenceProbe(
                    saleor_version=version,
                    endpoint_name=probe.endpoint_name,
                    endpoint_kind=probe.endpoint_kind,
                    category=probe.category,
                    input_sent=probe.input_sent,
                    golden_response=payload,
                    golden_outcome=probe.golden_outcome,
                    golden_status=probe.golden_status,
                    error_pattern=probe.error_pattern,
                    response_shape_hash=probe.response_shape_hash,
                    corpus_hash=corpus_hash_value,
                )
            )
    await db.commit()


async def sync_corpus_from_disk(db: AsyncSession, version: str | None = None) -> int:
    """Import JSON corpus into DB cache if present."""
    from app.services.reference_corpus import load_all_probes_from_disk

    ver = version or settings.reference_baseline_version
    probes = load_all_probes_from_disk(ver)
    if not probes:
        return 0
    chash = corpus_hash(ver)
    manifest = load_manifest(ver)
    if manifest and manifest.get("corpus_hash") == chash:
        existing = await db.execute(
            select(ReferenceProbe).where(ReferenceProbe.saleor_version == ver).limit(1)
        )
        row = existing.scalar_one_or_none()
        if row and row.corpus_hash == chash:
            return len(probes)

    await _sync_probes_to_db(db, ver, probes, chash)
    return len(probes)


def catalog_endpoint_count() -> tuple[int, int]:
    return len(SALEOR_QUERIES), len(SALEOR_MUTATIONS)
