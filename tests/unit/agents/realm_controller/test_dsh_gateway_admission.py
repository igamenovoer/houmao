"""Inspect DSH native invocation ownership without activating an ACP worker."""

from __future__ import annotations

import fcntl
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.gateway_models import GatewayAttachBackendMetadataHeadlessV1
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_session_root,
    load_attach_contract,
)
from tests.unit.agents.realm_controller.test_gateway_support import _seed_headless_gateway_root


def test_native_lock_inspection_is_read_only_and_observes_independent_ownership(
    tmp_path: Path,
) -> None:
    """A separately opened lock prevents ordinary admission until its actual owner exits."""

    session = object.__new__(DshAcpSession)
    session._plan = SimpleNamespace(home_path=tmp_path)
    path = tmp_path / "houmao-invocation.lock"
    assert session.native_invocation_active is False
    assert not path.exists()
    with path.open("a+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert session.native_invocation_active is True
    assert session.native_invocation_active is False


def test_unknown_native_lock_ownership_fails_closed(tmp_path: Path) -> None:
    """An unreadable lock shape cannot be interpreted as an idle native execution."""

    session = object.__new__(DshAcpSession)
    session._plan = SimpleNamespace(home_path=tmp_path)
    (tmp_path / "houmao-invocation.lock").mkdir()
    with pytest.raises(BackendExecutionError, match="ownership is unavailable"):
        _ = session.native_invocation_active


@pytest.mark.parametrize("tool", ["claude", "dsh"])
def test_only_dsh_publication_describes_the_native_cli_capability_contract(
    tmp_path: Path, tool: str
) -> None:
    """Published capabilities identify native control and explicit limits without activating a body."""

    root = _seed_headless_gateway_root(tmp_path, tool=tool)
    paths = gateway_paths_from_session_root(session_root=root.parent)
    contract = load_attach_contract(paths.attach_path)
    assert isinstance(contract.backend_metadata, GatewayAttachBackendMetadataHeadlessV1)
    capabilities = contract.backend_metadata.native_capabilities
    if tool == "claude":
        assert capabilities is None
        return
    assert contract.backend == "dsh_headless"
    assert capabilities is not None
    assert {
        "create",
        "exact_resume",
        "prompt",
        "cancel",
        "close",
        "native_system_prompt",
        "skills",
        "journal_accounting",
        "native_home",
        "common_plugin_observation",
        "native_home_refresh",
    }.issubset(capabilities.supported_operations)
    assert {
        "fork",
        "load",
        "transcript_replay",
        "delete",
        "additional_workspaces",
        "raw_keys",
        "mcp",
        "acp_wire_reload",
    }.issubset(capabilities.unsupported_operations)
    assert not set(capabilities.supported_operations).intersection(
        capabilities.unsupported_operations
    )
    assert capabilities.resource_activation == "next-invocation"
    assert capabilities.accounting_source == "dsh-journal-v4"
