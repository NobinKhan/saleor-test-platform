"""Per-bundle L3 setup registry tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.bundle_setup import apply_bundle_setup, get_bundle_setup


def test_productvariantsetdefault_has_secondary_variant_setup():
    steps = get_bundle_setup("productvariantsetdefault")
    assert len(steps) == 1
    assert steps[0]["fixture_key"] == "secondary_variant_id"


def test_productvariantreorder_shares_secondary_variant_setup():
    assert get_bundle_setup("productvariantreorder") == get_bundle_setup("productvariantsetdefault")


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
    run_setup.assert_awaited_once()
