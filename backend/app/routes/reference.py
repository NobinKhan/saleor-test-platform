"""
Reference corpus capture and status endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User
from app.services.reference_capture import capture_reference_probes, sync_corpus_from_disk
from app.services.reference_corpus import corpus_hash, load_manifest
from app.services.run_helpers import authenticate_saleor

router = APIRouter(prefix="/api/reference", tags=["reference"])


class ReferenceCaptureRequest(BaseModel):
    saleor_url: str
    saleor_email: str = Field(min_length=3, max_length=255)
    saleor_password: str = Field(min_length=1)
    saleor_version: str | None = None

    @field_validator("saleor_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip()
        if email.count("@") != 1:
            raise ValueError("Invalid email format")
        return email


@router.post("/capture")
async def capture_reference(
    data: ReferenceCaptureRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    token, auth_error = await authenticate_saleor(
        data.saleor_url,
        data.saleor_email,
        data.saleor_password,
    )
    if not token:
        raise HTTPException(400, auth_error or "Could not authenticate with Saleor")

    result = await capture_reference_probes(
        saleor_url=data.saleor_url,
        saleor_token=token,
        saleor_version=data.saleor_version,
        db=db,
        saleor_email=data.saleor_email,
        saleor_password=data.saleor_password,
    )
    return {"ok": True, "user_id": str(user.id), **result}


@router.post("/sync")
async def sync_reference(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    count = await sync_corpus_from_disk(db)
    return {
        "ok": True,
        "user_id": str(user.id),
        "synced_probes": count,
        "corpus_version": settings.reference_baseline_version,
        "corpus_hash": corpus_hash(settings.reference_baseline_version),
    }


@router.get("/status")
async def reference_status(
    user: User = Depends(get_current_user),
):
    version = settings.reference_baseline_version
    manifest = load_manifest(version)
    return {
        "baseline_version": version,
        "baseline_source": settings.reference_baseline_source,
        "corpus_hash": corpus_hash(version),
        "manifest": manifest,
    }
