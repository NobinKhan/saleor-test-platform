"""
Capture golden reference probes from a live Saleor instance (introspection-only).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import ReferenceProbe
from app.services.auth_visibility import infer_is_public, requires_staff_auth
from app.services.introspection import introspect_saleor
from app.services.outcome import classify_graphql_response
from app.services.query_builder import build_query_with_schema, introspect_field_args
from app.services.reference_compare import probe_from_capture
from app.services.reference_corpus import (
    corpus_hash,
    load_all_probes_from_disk,
    load_manifest,
    remove_probes_from_disk,
    update_manifest_after_patch,
    write_corpus,
)
from app.services.response_contract import CONTRACT_AUTH_ERROR, classify_response_contract
from app.services.saleor_auth import ensure_valid_token, refresh_saleor_token, validate_saleor_token
from app.services.test_runner import detect_saleor_version

ME_CHECK_INTERVAL = 50
CAPTURE_BATCH_SIZE = 180
CAPTURE_BATCH_COOLDOWN_SEC = 90

# Mutations that require a customer JWT; auth_error under staff token is expected.
CUSTOMER_CONTEXT_OPS = frozenset({
    "accountAddressCreate",
    "accountAddressDelete",
    "accountAddressUpdate",
    "accountDelete",
    "accountSetDefaultAddress",
    "addressCreate",
    "addressDelete",
    "addressSetDefault",
    "addressUpdate",
    "confirmEmailChange",
    "customerBulkDelete",
    "customerCreate",
    "customerDelete",
    "customerUpdate",
    "orderCreateFromCheckout",
    "passwordChange",
    "requestEmailChange",
    "sendConfirmationEmail",
    "userAvatarDelete",
    "userAvatarUpdate",
})


async def build_capture_endpoints(
    saleor_url: str,
    saleor_token: str | None,
    timeout: int,
) -> tuple[list[dict], dict[str, list[dict]] | None, dict[str, list[str]] | None]:
    """Build endpoint list from Saleor introspection (full schema capture)."""
    intro = await introspect_saleor(saleor_url, saleor_token, timeout)
    try:
        schema_fields = await introspect_field_args(saleor_url, saleor_token, timeout)
    except Exception:
        schema_fields = None

    endpoints: list[dict] = []
    for name in intro.get("queries", []):
        endpoints.append({
            "name": name,
            "kind": "QUERY",
            "category": "unknown",
            "is_public": infer_is_public(name, "QUERY"),
        })
    for name in intro.get("mutations", []):
        endpoints.append({
            "name": name,
            "kind": "MUTATION",
            "category": "unknown",
            "is_public": infer_is_public(name, "MUTATION"),
        })
    return endpoints, schema_fields, intro


def _requires_staff_auth(endpoint: dict) -> bool:
    if endpoint["name"] in CUSTOMER_CONTEXT_OPS:
        return False
    return requires_staff_auth(endpoint)


def _capture_order(endpoints: list[dict]) -> list[dict]:
    """Staff/dashboard probes first; customer-context ops last (they can invalidate staff JWT)."""

    def sort_key(ep: dict) -> tuple[int, str]:
        if ep["name"] in CUSTOMER_CONTEXT_OPS:
            return (2, ep["name"])
        if _requires_staff_auth(ep):
            return (0, ep["name"])
        return (1, ep["name"])

    return sorted(endpoints, key=sort_key)


async def capture_reference_probes(
    *,
    saleor_url: str,
    saleor_token: str | None,
    saleor_version: str | None = None,
    timeout: int = 30,
    db: AsyncSession | None = None,
    saleor_email: str | None = None,
    saleor_password: str | None = None,
) -> dict[str, Any]:
    version = saleor_version or await detect_saleor_version(saleor_url, saleor_token, timeout)
    if not version:
        version = settings.reference_baseline_version

    endpoints, schema_fields, intro = await build_capture_endpoints(
        saleor_url, saleor_token, timeout
    )
    endpoints = _capture_order(endpoints)
    if not saleor_token:
        raise ValueError("Golden capture requires staff authentication token")

    token = saleor_token
    if saleor_email and saleor_password:
        fresh, _err = await refresh_saleor_token(
            saleor_url, saleor_email, saleor_password, timeout
        )
        if fresh:
            token = fresh
    probes = []
    capture_errors: list[str] = []
    batches = [
        endpoints[i : i + CAPTURE_BATCH_SIZE]
        for i in range(0, len(endpoints), CAPTURE_BATCH_SIZE)
    ]

    async with httpx.AsyncClient(timeout=timeout) as client:
        global_idx = 0
        for batch_num, batch in enumerate(batches):
            if batch_num > 0:
                await asyncio.sleep(CAPTURE_BATCH_COOLDOWN_SEC)
                if saleor_email and saleor_password:
                    fresh, _err = await refresh_saleor_token(
                        saleor_url, saleor_email, saleor_password, timeout
                    )
                    if fresh:
                        token = fresh

            token = await ensure_valid_token(
                saleor_url=saleor_url,
                token=token,
                email=saleor_email,
                password=saleor_password,
                timeout=timeout,
                client=client,
            )
            if not token:
                raise ValueError("Staff token invalid during capture — could not obtain token")

            for endpoint in batch:
                idx = global_idx
                global_idx += 1
                if (
                    idx > 0
                    and idx % ME_CHECK_INTERVAL == 0
                    and saleor_email
                    and saleor_password
                    and not await validate_saleor_token(saleor_url, token, timeout, client)
                ):
                    token = await ensure_valid_token(
                        saleor_url=saleor_url,
                        token=token,
                        email=saleor_email,
                        password=saleor_password,
                        timeout=timeout,
                        client=client,
                    ) or token

                query = build_query_with_schema(
                    endpoint["name"], endpoint["kind"], schema_fields
                )
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}",
                }
                resp = await client.post(
                    saleor_url,
                    json={"query": query},
                    headers=headers,
                )
                resp_json = resp.json()
                contract = classify_response_contract(resp_json, http_status=resp.status_code)

                if contract == CONTRACT_AUTH_ERROR and _requires_staff_auth(endpoint):
                    token = await ensure_valid_token(
                        saleor_url=saleor_url,
                        token=token,
                        email=saleor_email,
                        password=saleor_password,
                        timeout=timeout,
                        client=client,
                    ) or token
                    headers["Authorization"] = f"Bearer {token}"
                    resp = await client.post(
                        saleor_url,
                        json={"query": query},
                        headers=headers,
                    )
                    resp_json = resp.json()
                    contract = classify_response_contract(resp_json, http_status=resp.status_code)
                    if contract == CONTRACT_AUTH_ERROR:
                        msg = (
                            f"{endpoint['name']} ({endpoint['kind']}): auth_error after refresh"
                        )
                        capture_errors.append(msg)
                        continue

                classified = classify_graphql_response(
                    resp_json,
                    http_status=resp.status_code,
                    endpoint_kind=endpoint["kind"],
                )
                probes.append(
                    probe_from_capture(
                        endpoint, query, resp_json, classified, http_status=resp.status_code
                    )
                )

    captured_keys = {(p.endpoint_name, p.endpoint_kind) for p in probes}
    for existing in load_all_probes_from_disk(version):
        key = (existing.endpoint_name, existing.endpoint_kind)
        if key not in captured_keys:
            probes.append(existing)
            captured_keys.add(key)

    directory = write_corpus(version, saleor_url, probes, merge=False)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["auth_mode"] = "staff" if saleor_token else "anonymous"
    manifest["reference_queries"] = intro.get("queries", [])
    manifest["reference_mutations"] = intro.get("mutations", [])
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
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
        "probe_count": len(probes),
        "corpus_path": str(directory),
        "corpus_hash": chash,
        "capture_warnings": capture_errors,
        "capture_skipped": len(capture_errors),
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


async def _capture_single_probe(
    client: httpx.AsyncClient,
    *,
    saleor_url: str,
    token: str,
    endpoint: dict,
    schema_fields: dict[str, list[dict]] | None,
    saleor_email: str | None,
    saleor_password: str | None,
    timeout: int,
) -> tuple[Any | None, str | None]:
    query = build_query_with_schema(endpoint["name"], endpoint["kind"], schema_fields)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    resp = await client.post(saleor_url, json={"query": query}, headers=headers)
    resp_json = resp.json()
    contract = classify_response_contract(resp_json, http_status=resp.status_code)

    if contract == CONTRACT_AUTH_ERROR and _requires_staff_auth(endpoint):
        token = await ensure_valid_token(
            saleor_url=saleor_url,
            token=token,
            email=saleor_email,
            password=saleor_password,
            timeout=timeout,
            client=client,
        ) or token
        headers["Authorization"] = f"Bearer {token}"
        resp = await client.post(saleor_url, json={"query": query}, headers=headers)
        resp_json = resp.json()
        contract = classify_response_contract(resp_json, http_status=resp.status_code)
        if contract == CONTRACT_AUTH_ERROR:
            return None, f"{endpoint['name']} ({endpoint['kind']}): auth_error after refresh"

    classified = classify_graphql_response(
        resp_json,
        http_status=resp.status_code,
        endpoint_kind=endpoint["kind"],
    )
    return (
        probe_from_capture(
            endpoint, query, resp_json, classified, http_status=resp.status_code
        ),
        None,
    )


async def capture_subset_probes(
    *,
    saleor_url: str,
    saleor_token: str | None,
    saleor_version: str | None = None,
    ops: list[tuple[str, str]],
    replace: bool = True,
    timeout: int = 30,
    db: AsyncSession | None = None,
    saleor_email: str | None = None,
    saleor_password: str | None = None,
) -> dict[str, Any]:
    version = saleor_version or await detect_saleor_version(saleor_url, saleor_token, timeout)
    if not version:
        version = settings.reference_baseline_version
    if not saleor_token:
        raise ValueError("Capture requires staff authentication token")

    endpoints, schema_fields, intro = await build_capture_endpoints(
        saleor_url, saleor_token, timeout
    )
    by_key = {(e["name"], e["kind"]): e for e in endpoints}
    new_probes = []
    errors: list[str] = []

    token = saleor_token
    if saleor_email and saleor_password:
        fresh, _err = await refresh_saleor_token(
            saleor_url, saleor_email, saleor_password, timeout
        )
        if fresh:
            token = fresh

    async with httpx.AsyncClient(timeout=timeout) as client:
        for name, kind in ops:
            endpoint = by_key.get((name, kind))
            if not endpoint:
                errors.append(f"Unknown op {name} ({kind})")
                continue
            probe, err = await _capture_single_probe(
                client,
                saleor_url=saleor_url,
                token=token,
                endpoint=endpoint,
                schema_fields=schema_fields,
                saleor_email=saleor_email,
                saleor_password=saleor_password,
                timeout=timeout,
            )
            if err:
                errors.append(err)
            elif probe:
                new_probes.append(probe)

    if replace:
        existing = {
            (p.endpoint_name, p.endpoint_kind): p
            for p in load_all_probes_from_disk(version)
        }
        for probe in new_probes:
            existing[(probe.endpoint_name, probe.endpoint_kind)] = probe
        all_probes = list(existing.values())
    else:
        all_probes = load_all_probes_from_disk(version)
        keys = {(p.endpoint_name, p.endpoint_kind) for p in new_probes}
        all_probes = [p for p in all_probes if (p.endpoint_name, p.endpoint_kind) not in keys]
        all_probes.extend(new_probes)

    directory = write_corpus(version, saleor_url, all_probes, merge=True)
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if intro:
        manifest["reference_queries"] = intro.get("queries", [])
        manifest["reference_mutations"] = intro.get("mutations", [])
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    update_manifest_after_patch(version)
    chash = corpus_hash(version)

    if db is not None:
        await _sync_probes_to_db(db, version, all_probes, chash)

    from app.services.reference_registry import register_corpus_version

    register_corpus_version(
        version,
        probe_count=len(all_probes),
        saleor_url=saleor_url,
        set_default=False,
    )

    return {
        "saleor_version": version,
        "recorded": len(new_probes),
        "corpus_path": str(directory),
        "corpus_hash": chash,
        "errors": errors,
    }


async def remove_corpus_ops(version: str, ops: list[tuple[str, str]]) -> int:
    removed = remove_probes_from_disk(version, ops)
    update_manifest_after_patch(version)
    return removed
