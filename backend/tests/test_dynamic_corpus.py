"""Dynamic corpus tests."""

from app.services.dynamic_corpus import (
    DynamicProbe,
    load_dynamic_probes,
    build_dynamic_probe_endpoints,
    compare_dynamic_response,
    BUILT_IN_PROBES,
)


def test_built_in_probe_count():
    assert len(BUILT_IN_PROBES) >= 5


def test_load_dynamic_probes_contains_builtin():
    probes = load_dynamic_probes()
    builtin_ids = {p.probe_id for p in BUILT_IN_PROBES}
    loaded_ids = {p.probe_id for p in probes}
    assert builtin_ids.issubset(loaded_ids)


def test_load_dynamic_probes_deduplicates_by_probe_id():
    probes = load_dynamic_probes()
    probe_ids = [p.probe_id for p in probes]
    assert len(probe_ids) == len(set(probe_ids))
    assert len(probes) == 5


def test_dynamic_probe_generate_input():
    probe = BUILT_IN_PROBES[0]
    doc, variables, generated = probe.generate_input("test-run", product_type_id="PT123")
    assert "test-run" in doc or generated["run_slug"] in doc
    assert "run_slug" in generated
    assert "uuid" in generated
    assert len(generated["uuid"]) > 8
    if probe.requires_product_type:
        assert "PT123" in doc


def test_generate_input_creates_unique_values():
    probe = BUILT_IN_PROBES[0]
    _, _, gen1 = probe.generate_input("run-1")
    _, _, gen2 = probe.generate_input("run-1")
    assert gen1["uuid"] != gen2["uuid"]
    assert gen1["nonce"] != gen2["nonce"]


def test_echo_validation_passes():
    probe = DynamicProbe(
        probe_id="test",
        operation_name="testCreate",
        operation_kind="MUTATION",
        category="test",
        document_template="mutation { testCreate(input: { name: \"{{run_slug}}\" }) }",
        comparison_mode="echo",
    )
    resp = {"data": {"testCreate": {"result": "harness-run1-abc"}}}
    passes, msg = probe.validate_response(resp, {"run_slug": "harness-run1-abc"})
    assert passes


def test_echo_validation_fails_when_missing():
    probe = BUILT_IN_PROBES[0]
    resp = {"data": {"productCreate": {"product": {"name": "Canned Response"}}}}
    passes, msg = probe.validate_response(resp, {"run_slug": "harness-run1-UNIQUE"})
    assert not passes
    assert "not found" in msg


def test_echo_validation_empty_response():
    probe = BUILT_IN_PROBES[0]
    passes, msg = probe.validate_response({}, {"run_slug": "test"})
    assert not passes
    assert "missing both" in msg


def test_structural_validation():
    probe = DynamicProbe(
        probe_id="test",
        operation_name="testQuery",
        operation_kind="QUERY",
        category="test",
        document_template="query { test }",
        comparison_mode="structural",
    )
    passes, msg = probe.validate_response({"data": {"test": "ok"}}, {})
    assert passes


def test_semantic_error_validation_passes():
    probe = DynamicProbe(
        probe_id="test_error",
        operation_name="product",
        operation_kind="QUERY",
        category="products",
        document_template="query { product(id: \"{{uuid}}\") { id } }",
        comparison_mode="semantic_error",
    )
    uuid_val = "abc-123-uuid"
    resp = {"errors": [{"message": f"Product not found: {uuid_val}", "path": ["product"]}]}
    passes, msg = probe.validate_response(resp, {"uuid": uuid_val})
    assert passes


def test_semantic_error_validation_fails():
    probe = DynamicProbe(
        probe_id="test_error",
        operation_name="product",
        operation_kind="QUERY",
        category="products",
        document_template="query { product(id: \"{{uuid}}\") { id } }",
        comparison_mode="semantic_error",
    )
    resp = {"errors": [{"message": "Generic error", "path": ["product"]}]}
    passes, msg = probe.validate_response(resp, {"uuid": "not-in-response"})
    assert not passes


def test_not_found_null_validation_passes():
    probe = DynamicProbe(
        probe_id="test_not_found",
        operation_name="product",
        operation_kind="QUERY",
        category="products",
        document_template="query { product(id: \"{{uuid}}\") { id } }",
        comparison_mode="not_found_null",
    )
    resp = {"data": {"product": None}}
    passes, msg = probe.validate_response(resp, {})
    assert passes


def test_not_found_null_validation_passes_with_errors():
    probe = DynamicProbe(
        probe_id="test_not_found",
        operation_name="product",
        operation_kind="QUERY",
        category="products",
        document_template="query { product(id: \"{{uuid}}\") { id } }",
        comparison_mode="not_found_null",
    )
    resp = {"errors": [{"message": "Channel issue"}], "data": {"product": None}}
    passes, msg = probe.validate_response(resp, {})
    assert passes


def test_not_found_null_validation_fails_when_entity_present():
    probe = DynamicProbe(
        probe_id="test_not_found",
        operation_name="product",
        operation_kind="QUERY",
        category="products",
        document_template="query { product(id: \"{{uuid}}\") { id } }",
        comparison_mode="not_found_null",
    )
    resp = {"data": {"product": {"id": "abc"}}}
    passes, msg = probe.validate_response(resp, {})
    assert not passes


def test_build_dynamic_probe_endpoints():
    endpoints = build_dynamic_probe_endpoints("test-run", product_type_id="PT123")
    assert len(endpoints) >= 5
    for ep in endpoints:
        assert ep["kind"] == "DYNAMIC_PROBE"
        assert ep["name"].startswith("dynamic__")
        assert "bundle_document" in ep
        assert "bundle_variables" in ep
        assert "generated_values" in ep
        assert "dynamic_probe" in ep


def test_build_endpoints_product_type_resolved():
    endpoints = build_dynamic_probe_endpoints("test-run", product_type_id="PT-RESOLVED")
    product_create = [ep for ep in endpoints if "product_create" in ep["name"]]
    if product_create:
        doc = product_create[0]["bundle_document"]
        assert "PT-RESOLVED" in doc


def test_compare_dynamic_response_delegation():
    probe = BUILT_IN_PROBES[0]
    resp = {"data": {"productCreate": {"product": {"name": "test", "slug": "test"}}}}
    passes, msg = compare_dynamic_response(probe, resp, {"run_slug": "test"})
    assert passes
