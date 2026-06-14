"""URL rewrite helpers for harness Docker vs host Saleor access."""

import os
from unittest.mock import patch

from app.core.url_utils import resolve_harness_saleor_url, resolve_saleor_url_for_runner


def test_resolve_saleor_url_unchanged_for_lan():
    url = "http://192.168.1.10:8000/graphql/"
    assert resolve_saleor_url_for_runner(url) == url


def test_resolve_saleor_url_rewrites_localhost_in_docker():
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://u:p@harness-db:5432/db",
            "SALEOR_GRAPHQL_URL": "http://host.docker.internal:8000/graphql/",
        },
        clear=False,
    ):
        from app.core.config import get_settings

        get_settings.cache_clear()
        try:
            resolved = resolve_saleor_url_for_runner("http://localhost:8000/graphql/")
            assert resolved == "http://host.docker.internal:8000/graphql/"
            requested, resolved_pair = resolve_harness_saleor_url(
                "http://localhost:8000/graphql/"
            )
            assert requested == "http://localhost:8000/graphql/"
            assert resolved_pair == "http://host.docker.internal:8000/graphql/"
        finally:
            get_settings.cache_clear()


def test_resolve_saleor_url_localhost_without_docker_context():
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost/test"}, clear=False):
        url = "http://localhost:8000/graphql/"
        assert resolve_saleor_url_for_runner(url) == url
