"""Per-bundle L3 setup registry tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.bundle_setup import apply_bundle_setup, get_bundle_setup


def test_productvariantsetdefault_has_secondary_variant_and_copy():
    steps = get_bundle_setup("productvariantsetdefault")
    assert len(steps) == 2
    assert steps[0]["fixture_key"] == "secondary_variant_id"
    assert steps[1]["fixture_key"] == "default_variant_id"
    assert steps[1].get("_from_key") == "secondary_variant_id"


def test_productvariantreorder_has_secondary_variant_setup():
    steps = get_bundle_setup("productvariantreorder")
    assert len(steps) == 1
    assert steps[0]["fixture_key"] == "secondary_variant_id"


def test_variant_bulk_mutations_share_secondary_variant_setup():
    bulk = get_bundle_setup("productvariantbulkdelete")
    assert bulk == get_bundle_setup("productvariantbulkupdate")
    assert bulk[0]["fixture_key"] == "secondary_variant_id"


@pytest.mark.asyncio
async def test_apply_bundle_setup_merges_fixture_overlay():
    run_setup = AsyncMock(return_value="VmFyaWFudDoy")
    overlay = await apply_bundle_setup(
        bundle_id="productvariantsetdefault",
        fixtures={
            "default_product_id": "UHJvZHVjdDox",
            "default_channel_id": "Q2hhbm5lbDox",
        },
        run_setup_mutation=run_setup,
    )
    assert overlay["secondary_variant_id"] == "VmFyaWFudDoy"
    assert overlay["default_variant_id"] == "VmFyaWFudDoy"
    run_setup.assert_awaited_once()


@pytest.mark.asyncio
async def test_sf_accountupdate_setup_uses_customer_auth_for_profile_step():
    auth_contexts: list[str] = []

    async def run_setup(setup, auth):
        auth_contexts.append(auth)
        if auth == "anonymous":
            return "VXNlcjox"
        if auth == "customer":
            return "VXNlcjox"
        return None

    await apply_bundle_setup(
        bundle_id="sf-accountupdate",
        fixtures={"default_channel": "harness-channel"},
        run_setup_mutation=run_setup,
    )
    assert auth_contexts == ["anonymous", "customer"]


def test_categorydetails_aftercreate_setup_creates_category():
    steps = get_bundle_setup("categorydetails-aftercreate")
    assert len(steps) == 1
    assert steps[0]["fixture_key"] == "_smoke_category_id"
    assert steps[0]["auth"] == "staff"
    assert "categoryCreate" in steps[0]["mutation"]


def test_externalrefresh_success_setup_runs_token_create():
    steps = get_bundle_setup("externalrefresh-success")
    assert len(steps) == 1
    assert steps[0]["fixture_key"] == "refresh_token"
    assert steps[0]["auth"] == "staff"
    assert "tokenCreate" in steps[0]["mutation"]


@pytest.mark.asyncio
async def test_categorydetails_aftercreate_extracts_category_id():
    run_setup = AsyncMock(return_value="Q2F0ZWdvcnk6NDI=")
    overlay = await apply_bundle_setup(
        bundle_id="categorydetails-aftercreate",
        fixtures={},
        run_setup_mutation=run_setup,
    )
    assert overlay["_smoke_category_id"] == "Q2F0ZWdvcnk6NDI="
    run_setup.assert_awaited_once()


@pytest.mark.asyncio
async def test_externalrefresh_success_extracts_refresh_token():
    run_setup = AsyncMock(return_value="refresh-token-value")
    overlay = await apply_bundle_setup(
        bundle_id="externalrefresh-success",
        fixtures={"staff_email": "admin@example.com", "staff_password": "admin"},
        run_setup_mutation=run_setup,
    )
    assert overlay["refresh_token"] == "refresh-token-value"
    run_setup.assert_awaited_once()
