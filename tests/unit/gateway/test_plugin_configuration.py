"""Strict public configuration and SDK boundary tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from pydantic import ValidationError
import pytest

from houmao.gateway.plugins import (
    GatewayPluginConfiguration,
    PluginConfigurationError,
    PluginCredentialReference,
    PluginDispatchError,
    PluginEvent,
    PluginInstanceConfiguration,
)


@pytest.mark.parametrize("suffix", ["yaml", "json"])
def test_configuration_reads_explicit_complete_selection(tmp_path: Path, suffix: str) -> None:
    """YAML and JSON expose the same full replacement model without reading secrets."""

    path = tmp_path / f"selection.{suffix}"
    document = {
        "schema_version": 1,
        "gateway": {
            "plugins": {
                "events": {
                    "implementation": "external-example",
                    "credential_ref": {"file": str(tmp_path / "missing-private.json")},
                    "config": {"account": "example-account"},
                },
                "no-auth": {"implementation": "local-events"},
            },
            "dispatch_timeout_seconds": 3.0,
        },
    }
    # JSON is a valid YAML subset, so both loader paths receive identical values.
    path.write_text(json.dumps(document), encoding="utf-8")
    selection = GatewayPluginConfiguration.from_file(path)
    assert selection.plugins["events"].credential_ref.file == tmp_path / "missing-private.json"
    assert selection.plugins["no-auth"].credential_ref is None
    assert selection.dispatch_timeout_seconds == 3.0


@pytest.mark.parametrize(
    ("suffix", "document"),
    [
        (
            "yaml",
            "schema_version: 1\ngateway:\n  plugins:\n    events: {implementation: a}\n    events: {implementation: b}\n",
        ),
        ("yaml", "schema_version: 1\ngateway:\n  plugins: {}\n  plugins: {}\n"),
        ("json", '{"schema_version":1,"gateway":{"plugins":{},"plugins":{}}}'),
        ("json", '{"schema_version":1,"schema_version":1,"gateway":{"plugins":{}}}'),
    ],
)
def test_configuration_rejects_duplicate_keys(tmp_path: Path, suffix: str, document: str) -> None:
    """No configuration layer can silently overwrite a duplicate selection."""

    path = tmp_path / f"selection.{suffix}"
    path.write_text(document, encoding="utf-8")
    with pytest.raises(PluginConfigurationError, match="Duplicate"):
        GatewayPluginConfiguration.from_file(path)


@pytest.mark.parametrize(
    "gateway",
    [
        {},
        {"plugins": None},
        {"plugins": {}, "schema_version": 1},
        {"plugins": {}, "unknown": "private-sentinel"},
        {"plugins": {"Bad_ID": {"implementation": "example"}}},
        {"plugins": {"ok": {"implementation": "example", "unknown": "private-sentinel"}}},
        {"plugins": {"ok": {"implementation": "example", "config": {"value": float("nan")}}}},
        {"plugins": {}, "max_event_bytes": True},
        {"plugins": {}, "max_event_bytes": 0},
        {"plugins": {}, "dispatch_timeout_seconds": float("inf")},
        {"plugins": {}, "startup_timeout_seconds": -1},
        {"plugins": {}, "shutdown_timeout_seconds": "5"},
    ],
)
def test_configuration_schema_errors_are_safe(tmp_path: Path, gateway: object) -> None:
    """Invalid settings fail before persistence without echoing private values."""

    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({"schema_version": 1, "gateway": gateway}), encoding="utf-8")
    with pytest.raises(PluginConfigurationError) as error:
        GatewayPluginConfiguration.from_file(path)
    assert "private-sentinel" not in str(error.value)


@pytest.mark.parametrize("version", [True, "1", 1.0, 2, None])
def test_configuration_requires_exact_integer_version(tmp_path: Path, version: object) -> None:
    """Boolean and coercible schema versions are unsupported."""

    path = tmp_path / "invalid.json"
    path.write_text(
        json.dumps({"schema_version": version, "gateway": {"plugins": {}}}), encoding="utf-8"
    )
    with pytest.raises(PluginConfigurationError):
        GatewayPluginConfiguration.from_file(path)


@pytest.mark.parametrize("path", ["relative.json", "~/private.json", "/tmp/a/../private.json"])
def test_credential_reference_requires_explicit_absolute_path(path: str) -> None:
    """Credential references do not expand ambient homes or parent traversal."""

    with pytest.raises(ValidationError):
        PluginCredentialReference(file=path)


def test_complete_selection_identity_is_canonical() -> None:
    """Equivalent dictionaries share identity; clearing is a distinct selection."""

    first = GatewayPluginConfiguration(
        plugins={
            "beta": PluginInstanceConfiguration(implementation="example", config={"b": 2, "a": 1}),
            "alpha": PluginInstanceConfiguration(implementation="example"),
        }
    )
    second = GatewayPluginConfiguration(
        plugins={
            "alpha": PluginInstanceConfiguration(implementation="example"),
            "beta": PluginInstanceConfiguration(implementation="example", config={"a": 1, "b": 2}),
        }
    )
    assert first.configuration_digest == second.configuration_digest
    assert first.configuration_digest != GatewayPluginConfiguration(plugins={}).configuration_digest


def test_event_and_dispatch_failure_keep_safe_correlation() -> None:
    """Public event errors preserve sender correlation and uncertainty explicitly."""

    event = PluginEvent(source_event_id="source-1", text="/ordinary text", metadata={"n": 1})
    assert event.text == "/ordinary text"
    error = PluginDispatchError(
        error_code="body_lost",
        status_code=503,
        retryable=True,
        dispatch_outcome="unknown",
        source_event_id=event.source_event_id,
    )
    assert error.to_detail()["source_event_id"] == "source-1"
    assert error.to_detail()["dispatch_outcome"] == "unknown"
    assert error.retryable is True


def test_public_sdk_import_does_not_import_gateway_implementation() -> None:
    """Plugin distributions can use the supported SDK without internal service types."""

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import houmao.gateway.plugins as sdk; "
            "assert all(hasattr(sdk, name) for name in sdk.__all__); "
            "assert 'houmao.agents.realm_controller.gateway_service' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
