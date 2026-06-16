"""
Mutation-first enforcement tests — ensures all L1 success probes create data via mutations
before querying, preventing regression to hardcoded Saleor demo data dependency.
"""

from __future__ import annotations

import pytest

from app.services.probe_setup import SETUP_MUTATIONS, get_setup_for_operation, needs_setup


class TestMutationFirstEnforcement:
    """Verify that mutation-first testing is properly enforced."""

    def test_all_success_operations_have_setup_mutations(self):
        """Every L1 operation that can return data must have a setup mutation."""
        # Operations that require data setup for success probes
        # (excluding read-only shop queries and error probes)
        OPERATIONS_REQUIRING_SETUP = {
            "products", "product", "productTypes", "productType",
            "categories", "category", "collections", "collection",
            "channels", "channel", "attributes", "attribute",
            "pages", "page", "shippingZones", "shippingZone",
            "warehouses", "warehouse", "staffUsers", "customers",
            "customer", "giftCards", "giftCard", "menus", "menu",
            "vouchers", "voucher", "draftOrders", "orders",
            "users", "user", "permissionGroups", "webhooks",
            "taxClasses",
        }
        
        missing = OPERATIONS_REQUIRING_SETUP - set(SETUP_MUTATIONS.keys())
        assert not missing, (
            f"Operations missing setup mutations: {missing}. "
            f"All success probes must create data via mutations first."
        )

    def test_setup_mutations_have_required_fields(self):
        """Each setup mutation must have mutation, variables, extract, category, auth."""
        required_fields = {"mutation", "variables", "extract", "category", "auth"}
        
        for op_name, setup in SETUP_MUTATIONS.items():
            if setup.get("mutation") is None:
                # Shop is read-only, skip
                continue
            
            missing = required_fields - set(setup.keys())
            assert not missing, (
                f"Setup mutation for '{op_name}' missing fields: {missing}"
            )

    def test_needs_setup_returns_true_for_success_probes(self):
        """needs_setup() returns True for success probes with setup mutations."""
        success_ops = ["products", "categories", "collections", "channels"]
        for op in success_ops:
            assert needs_setup(op, "success") is True, (
                f"needs_setup('{op}', 'success') should return True"
            )

    def test_needs_setup_returns_false_for_error_probes(self):
        """needs_setup() returns False for error probes (they don't need data)."""
        error_ops = ["products", "categories", "collections"]
        for op in error_ops:
            assert needs_setup(op, "not_found") is False, (
                f"needs_setup('{op}', 'not_found') should return False"
            )
            assert needs_setup(op, "rejection") is False, (
                f"needs_setup('{op}', 'rejection') should return False"
            )

    def test_needs_setup_returns_false_for_unknown_operations(self):
        """needs_setup() returns False for unknown operations."""
        assert needs_setup("unknownOperation", "success") is False
        assert needs_setup("nonexistent", None) is False

    def test_get_setup_returns_valid_config(self):
        """get_setup_for_operation returns valid config for known operations."""
        for op_name in ["products", "categories", "collections"]:
            setup = get_setup_for_operation(op_name)
            assert setup is not None, f"get_setup_for_operation('{op_name}') should not be None"
            assert setup["mutation"] is not None
            assert callable(setup["variables"])
            assert isinstance(setup["extract"], str)
            assert setup["extract"].startswith("$.data."), (
                f"Extract path should start with $.data., got: {setup['extract']}"
            )

    def test_setup_mutations_create_entities_not_query_existing(self):
        """Setup mutations must create new entities, not query existing ones."""
        for op_name, setup in SETUP_MUTATIONS.items():
            if setup.get("mutation") is None:
                continue
            
            mutation = setup["mutation"]
            # Must use a Create mutation, not a query
            assert "Create" in mutation or "create" in mutation, (
                f"Setup for '{op_name}' must use a Create mutation, "
                f"got: {mutation[:100]}..."
            )

    def test_shop_is_excluded_from_mutation_first(self):
        """Shop query is read-only and should have mutation=None."""
        shop_setup = get_setup_for_operation("shop")
        assert shop_setup is not None
        assert shop_setup["mutation"] is None, (
            "Shop is read-only and should not have a setup mutation"
        )
