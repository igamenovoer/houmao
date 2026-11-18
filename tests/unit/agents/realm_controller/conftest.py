"""Owner access fixture for gateway runtime unit tests with synthetic native bodies."""

from pathlib import Path

import pytest

from tests.fixtures.gateway_access import FixtureGatewayAccess, configure_fixture_gateway_access


@pytest.fixture
def gateway_fixture_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureGatewayAccess:
    """Resolve bound gateway authority from isolated private test state."""

    return configure_fixture_gateway_access(tmp_path, monkeypatch)
