"""Schema comparison tests — connection cardinality forgiveness."""

from app.services.schema_compare import compare_schemas


def test_connection_forgives_empty_edges_when_pageinfo_present():
    golden = {
        "data": {
            "search": {
                "edges": [
                    {"node": {"id": "UHJvZHVjdDox", "name": "A"}},
                    {"node": {"id": "UHJvZHVjdDoy", "name": "B"}},
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }
    actual = {
        "data": {
            "search": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }
    }
    result = compare_schemas(golden, actual)
    assert result.compatible is True
    assert result.match_status == "match"


def test_connection_single_edge_matches_multi_edge_golden_element_schema():
    golden = {
        "data": {
            "collections": {
                "edges": [
                    {"node": {"id": "Q29sbGVjdGlvbjox", "name": "One"}},
                    {"node": {"id": "Q29sbGVjdGlvbjoy", "name": "Two"}},
                ],
                "pageInfo": {"hasNextPage": False},
            }
        }
    }
    actual = {
        "data": {
            "collections": {
                "edges": [{"node": {"id": "Q29sbGVjdGlvbjoz", "name": "Only"}}],
                "pageInfo": {"hasNextPage": False},
            }
        }
    }
    result = compare_schemas(golden, actual)
    assert result.compatible is True


def test_structural_mismatch_still_fails():
    golden = {"data": {"product": {"isAvailable": True}}}
    actual = {"data": {"product": {"isAvailable": "yes"}}}
    result = compare_schemas(golden, actual)
    assert result.compatible is False
    assert result.match_status == "schema_mismatch"
