"""L3 client bundle schema gate and root-field extraction."""

import json
from pathlib import Path

from app.services.client_bundle_schema_gate import compute_client_bundle_schema_gate
from app.services.client_bundles import ClientBundle
from app.services.dashboard_bundle_import import root_fields_in_document


def test_root_fields_resolves_fragment_spread_at_operation_root():
    doc = """query FeaturedProductsQuery($channel: String!) {
  ...FeaturedProducts
}

fragment FeaturedProducts on Query {
  collection(slug: "featured-products", channel: $channel) {
    id
    backgroundImage { url }
  }
}"""
    roots = root_fields_in_document(doc)
    assert roots == [("collection", "QUERY")]


def test_schema_gate_includes_invalid_root_graphql_error_probe():
    bundle_path = (
        Path(__file__).resolve().parents[1]
        / "reference/client-bundles/storefront-3.23.6/bundles/sf-orderlinecreate.graphql.json"
    )
    if not bundle_path.is_file():
        bundle_path = (
            Path("/app/reference-baked/client-bundles/storefront-3.23.6/bundles")
            / "sf-orderlinecreate.graphql.json"
        )
    bundle = ClientBundle.from_dict(json.loads(bundle_path.read_text(encoding="utf-8")))
    intro = {"queries": ["shop"], "mutations": ["orderLinesCreate"]}
    gate = compute_client_bundle_schema_gate([bundle], intro, recorded_only=True)
    assert gate["client_schema_gate_pass"] is True
    assert gate["missing_l3_fields"] == []
