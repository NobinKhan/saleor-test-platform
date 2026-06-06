"""Client bundle fixture substitution tests."""

import pytest

from app.services.client_bundle_fixtures import substitute_fixtures


def test_substitute_fixture_placeholder():
    variables = {"channel": "{{fixtures.default_channel}}", "first": 10}
    fixtures = {"default_channel": "default-channel"}
    result = substitute_fixtures(variables, fixtures)
    assert result["channel"] == "default-channel"
    assert result["first"] == 10


def test_substitute_missing_fixture_raises():
    with pytest.raises(KeyError, match="default_channel"):
        substitute_fixtures({"id": "{{fixtures.default_channel}}"}, {})
