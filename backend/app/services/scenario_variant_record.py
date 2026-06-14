"""
Record golden responses for scenario steps and input variants.

Replays each step/variant against the target Saleor and persists the response
into the on-disk step/variant JSON files.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import httpx

from app.services.client_bundle_fixtures import substitute_fixtures
from app.services.scenario_corpus import scenario_dir, substitute_scenario_variables
from app.services.response_contract import classify_response_contract
from app.services.semantic_compare import build_semantic_profile
from app.services.response_normalize import sanitize_for_sgrc

logger = logging.getLogger(__name__)


async def _gql_query(
    saleor_url: str,
    query: str,
    variables: dict[str, Any] | None,
    token: str | None,
    timeout: int = 30,
) -> dict[str, Any]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(saleor_url, json=payload, headers=headers)
        if resp.status_code not in (200, 400):
            resp.raise_for_status()
        return resp.json()


async def _token_for_auth_context(
    *,
    saleor_url: str,
    auth_context: str,
    staff_token: str | None,
    timeout: int = 30,
) -> str | None:
    if auth_context == "anonymous":
        return None
    if auth_context == "customer":
        from app.services.saleor_auth import ensure_customer_token

        return await ensure_customer_token(
            saleor_url=saleor_url,
            token=None,
            email=None,
            password=None,
            timeout=timeout,
            force_refresh=True,
            staff_token=staff_token,
        )
    return staff_token


async def record_scenario_step(
    *,
    saleor_url: str,
    saleor_token: str | None,
    scenario_id: str,
    step,
    context: dict[str, Any] | None = None,
    fixtures: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Replay a scenario step and persist its golden response.

    Returns the updated step dict.
    """
    fixtures = fixtures or {}
    context = context or {}
    substituted = substitute_scenario_variables(
        step.variables, context, fixtures
    )
    auth_context = getattr(step, "auth_context", "staff") or "staff"
    token = await _token_for_auth_context(
        saleor_url=saleor_url,
        auth_context=auth_context,
        staff_token=saleor_token,
        timeout=timeout,
    )
    try:
        resp_json = await _gql_query(
            saleor_url, step.input_sent, substituted, token, timeout
        )
    except Exception as exc:
        logger.error("Scenario step %s/%s failed: %s", scenario_id, step.step_id, exc)
        return {}

    sanitized = sanitize_for_sgrc(resp_json)
    contract = classify_response_contract(sanitized, http_status=200)
    profile = build_semantic_profile(
        golden_response=sanitized,
        golden_contract=contract,
        input_sent=step.input_sent,
        endpoint_name=step.name or step.step_id,
    )

    updated = step.to_dict()
    updated["golden_response"] = sanitized
    updated["golden_contract"] = contract
    updated["golden_status"] = "pass" if contract == "success" else "warn"
    if profile:
        updated["semantic_profile"] = profile
    updated["recorded_at"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()

    step_path = scenario_dir(scenario_id) / "steps" / f"{step.step_id}.json"
    if step_path.is_file():
        step_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
        logger.info("Recorded scenario step %s/%s", scenario_id, step.step_id)
    return updated


async def record_scenario(
    *,
    saleor_url: str,
    saleor_token: str | None,
    scenario_id: str,
    fixtures: dict[str, Any] | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """Record goldens for all steps in a scenario in order, sharing context."""
    import uuid

    from app.services.scenario_corpus import (
        load_scenario_manifest,
        load_scenario_steps,
    )

    manifest = load_scenario_manifest(scenario_id)
    if not manifest:
        return {"error": f"Scenario {scenario_id} not found", "recorded": 0}

    steps = load_scenario_steps(manifest)
    context: dict[str, Any] = {
        "run_slug": f"harness-scenario-{uuid.uuid4().hex[:8]}",
    }
    recorded = 0
    for step in steps:
        result = await record_scenario_step(
            saleor_url=saleor_url,
            saleor_token=saleor_token,
            scenario_id=scenario_id,
            step=step,
            context=context,
            fixtures=fixtures,
            timeout=timeout,
        )
        if result:
            recorded += 1
            for extract_key, json_path in (step.extract or {}).items():
                from app.services.scenario_corpus import _extract_json_path
                value = _extract_json_path(result.get("golden_response") or {}, json_path)
                if value is not None:
                    context[extract_key] = value
    return {"recorded": recorded, "total": len(steps)}


async def record_variant(
    *,
    saleor_url: str,
    saleor_token: str | None,
    operation_name: str,
    variant,
    timeout: int = 30,
) -> dict[str, Any]:
    """Replay an input variant and persist its golden response."""
    try:
        resp_json = await _gql_query(
            saleor_url,
            variant.input_sent,
            variant.variables or None,
            saleor_token,
            timeout,
        )
    except Exception as exc:
        logger.error("Variant %s/%s failed: %s", operation_name, variant.variant_id, exc)
        return {}

    sanitized = sanitize_for_sgrc(resp_json)
    contract = classify_response_contract(sanitized, http_status=200)
    profile = build_semantic_profile(
        golden_response=sanitized,
        golden_contract=contract,
        input_sent=variant.input_sent,
        endpoint_name=f"{operation_name}__{variant.variant_id}",
    )

    updated = variant.to_dict()
    updated["golden_response"] = sanitized
    updated["golden_contract"] = contract
    updated["golden_status"] = "pass" if contract == "success" else "warn"
    if profile:
        updated["semantic_profile"] = profile
    updated["recorded_at"] = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    ).isoformat()

    from app.services.variant_corpus import variant_dir
    vdir = variant_dir(operation_name)
    matrix_path = vdir / "matrix.json"
    if matrix_path.is_file():
        data = json.loads(matrix_path.read_text(encoding="utf-8"))
        for v in data.get("variants") or []:
            if v.get("variant_id") == variant.variant_id:
                v.update({
                    k: val for k, val in updated.items()
                    if k not in ("variant_id", "operation_name", "operation_kind", "category", "input_sent", "tags")
                })
                break
        matrix_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.info("Recorded variant %s/%s", operation_name, variant.variant_id)
    return updated


async def record_operation_variants(
    *,
    saleor_url: str,
    saleor_token: str | None,
    operation_name: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Record goldens for all variants of a given operation."""
    from app.services.variant_corpus import load_variant_matrix

    variants = load_variant_matrix(operation_name)
    recorded = 0
    for variant in variants:
        result = await record_variant(
            saleor_url=saleor_url,
            saleor_token=saleor_token,
            operation_name=operation_name,
            variant=variant,
            timeout=timeout,
        )
        if result:
            recorded += 1
    return {"recorded": recorded, "total": len(variants)}
