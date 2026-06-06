"""Dashboard bundle import tests."""

from pathlib import Path

from app.services.dashboard_bundle_import import parse_graphql_file, _operation_priority


def test_parse_simple_query(tmp_path):
    gql = tmp_path / "shop.graphql"
    gql.write_text(
        "query ShopDetails { shop { domain { host } version } }",
        encoding="utf-8",
    )
    bundles = parse_graphql_file(gql, "shop.graphql")
    assert len(bundles) == 1
    assert bundles[0].operation_names == ["ShopDetails"]
    assert bundles[0].priority == "P0"
    assert "shop" in bundles[0].document


def test_priority_p0_for_orders():
    assert _operation_priority(["OrderList"], "query OrderList { orders(first: 1) { edges { node { id } } } }") == "P0"


def test_priority_p1_for_unknown():
    assert _operation_priority(["ObscureOp"], "query ObscureOp { _entities(representations: []) { __typename } }") == "P1"
