"""Shared fixtures for ``houmao-mgr`` unit tests.

Sets ``HOUMAO_CLI_PRINT_STYLE=json`` so tests that assert on ``json.loads()``
continue to work after the default output style changed from JSON to plain.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _cli_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force JSON output for all CLI invocations in this test directory."""
    monkeypatch.setenv("HOUMAO_CLI_PRINT_STYLE", "json")


@pytest.fixture(autouse=True)
def _isolated_registry_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep registry/store associations out of the developer's real configuration."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
