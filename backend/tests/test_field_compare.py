"""Field-level response comparison tests."""

from app.services.field_compare import compare_response_fields


def test_matching_fields():
    golden = {"data": {"products": {"edges": [{"node": {"id": "1"}}]}}}
    actual = {"data": {"products": {"edges": [{"node": {"id": "2"}}]}}}
    items = compare_response_fields(golden, actual)
    assert items
    assert all(i["item_status"] == "match" for i in items)


def test_missing_field():
    golden = {"data": {"shop": {"version": "3.23.7"}}}
    actual = {"data": {}}
    items = compare_response_fields(golden, actual)
    statuses = {i["item_key"]: i["item_status"] for i in items}
    assert statuses.get("data.shop.version") == "missing"
