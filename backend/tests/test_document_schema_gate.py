"""Tests for deep document schema gate."""

from app.services.document_schema_gate import validate_document_against_schema

MINIMAL_INTROSPECTION = {
    "data": {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": {"name": "Mutation"},
            "subscriptionType": None,
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "fields": [
                        {
                            "name": "shop",
                            "args": [],
                            "type": {"kind": "OBJECT", "name": "Shop", "ofType": None},
                        }
                    ],
                },
                {
                    "kind": "OBJECT",
                    "name": "Shop",
                    "fields": [
                        {
                            "name": "name",
                            "args": [],
                            "type": {"kind": "SCALAR", "name": "String", "ofType": None},
                        }
                    ],
                },
                {"kind": "SCALAR", "name": "String"},
            ],
            "directives": [],
        }
    }
}


def test_valid_document_passes_or_schema_incomplete():
    doc = "query { shop { name } }"
    issues = validate_document_against_schema(doc, MINIMAL_INTROSPECTION)
    assert not any("parse_error" in (i.get("reason") or "") for i in issues)


def test_invalid_field_reported():
    doc = "query { shop { missingField } }"
    issues = validate_document_against_schema(doc, MINIMAL_INTROSPECTION)
    assert len(issues) >= 1
