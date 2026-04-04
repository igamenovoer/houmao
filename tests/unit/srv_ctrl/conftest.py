"""Shared fixtures for ``houmao-mgr`` unit tests.

Sets ``HOUMAO_CLI_PRINT_STYLE=json`` so tests that assert on ``json.loads()``
continue to work after the default output style changed from JSON to plain.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force JSON output for all CLI invocations in this test directory."""
    monkeypatch.setenv("HOUMAO_CLI_PRINT_STYLE", "json")
