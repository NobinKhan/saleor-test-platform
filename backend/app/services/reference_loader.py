"""Load golden probes — DB cache first, JSON corpus fallback."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.reference_corpus import GoldenProbe, load_probe_from_disk, resolve_corpus_version


async def get_golden_probe(
    db: AsyncSession | None,
    saleor_version: str | None,
    endpoint_name: str,
    endpoint_kind: str,
    *,
    baseline_version: str = "3.23.7",
) -> GoldenProbe | None:
    from app.models import ReferenceProbe

    corpus_version = resolve_corpus_version(saleor_version, baseline_version)

    if db is not None:
        result = await db.execute(
            select(ReferenceProbe).where(
                ReferenceProbe.saleor_version == corpus_version,
                ReferenceProbe.endpoint_name == endpoint_name,
                ReferenceProbe.endpoint_kind == endpoint_kind,
            )
        )
        row = result.scalar_one_or_none()
        if row:
            return GoldenProbe(
                endpoint_name=row.endpoint_name,
                endpoint_kind=row.endpoint_kind,
                category=row.category,
                input_sent=row.input_sent,
                golden_response=json.loads(row.golden_response),
                golden_outcome=row.golden_outcome,
                golden_status=row.golden_status,
                error_pattern=row.error_pattern,
                response_shape_hash=row.response_shape_hash,
            )

    return load_probe_from_disk(corpus_version, endpoint_name, endpoint_kind)
