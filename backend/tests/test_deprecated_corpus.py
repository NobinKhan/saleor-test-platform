"""Corpus must not contain legacy Sale API references."""

from types import SimpleNamespace

from app.services.deprecated_scanner import (
    check_corpus_deprecated,
    find_deprecated_mutations_in_list,
    is_deprecated_mutation,
)


def test_find_deprecated_mutations_in_list():
    found = find_deprecated_mutations_in_list(
        ["productCreate", "saleBulkDelete", "orderCreate"]
    )
    assert found == ["saleBulkDelete"]


def test_check_corpus_deprecated_manifest():
    errors = check_corpus_deprecated(
        manifest_mutations=["productCreate", "saleCreate"],
        probes=[],
    )
    assert len(errors) == 1
    assert "saleCreate" in errors[0]


def test_check_corpus_deprecated_probe_input():
    probe = SimpleNamespace(
        endpoint_name="saleBulkDelete",
        endpoint_kind="MUTATION",
        input_sent='mutation { saleBulkDelete(ids: ["U2FsZTox"]) { count } }',
    )
    errors = check_corpus_deprecated(manifest_mutations=[], probes=[probe])
    assert len(errors) == 1
    assert "saleBulkDelete" in errors[0]


def test_check_corpus_clean():
    errors = check_corpus_deprecated(
        manifest_mutations=["productCreate"],
        probes=[
            SimpleNamespace(
                endpoint_name="productCreate",
                endpoint_kind="MUTATION",
                input_sent="mutation { productCreate(input: {}) { errors { message } } }",
            )
        ],
    )
    assert errors == []


def test_is_deprecated_mutation_sale_ops():
    assert is_deprecated_mutation("saleBulkDelete")
    assert not is_deprecated_mutation("promotionBulkDelete")
