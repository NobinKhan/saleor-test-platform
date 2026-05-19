"""Schema comparison helpers."""

from app.services.introspection import compare_schema, compare_two_introspections


def test_compare_schema_missing_and_extra():
    intro = {"queries": ["products", "shop"], "mutations": ["productCreate"]}
    diff = compare_schema(intro, ["products", "orders"], ["productCreate", "orderCreate"])
    assert "orders" in diff["missing_queries"]
    assert "products" in intro["queries"]
    assert "orderCreate" in diff["missing_mutations"]


def test_compare_two_introspections():
    target = {"queries": ["a", "b"], "mutations": ["m1"]}
    reference = {"queries": ["b", "c"], "mutations": ["m1", "m2"]}
    drift = compare_two_introspections(target, reference)
    assert "a" in drift["target_only_queries"]
    assert "c" in drift["reference_only_queries"]
    assert "b" in drift["shared_queries"]
