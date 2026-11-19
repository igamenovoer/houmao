"""Operator routing storage remains separate from runtime presence and owner state."""

from __future__ import annotations

from importlib import resources
import json
from pathlib import Path

import jsonschema
from pydantic import ValidationError
import pytest

from houmao.execution.locators import (
    ExecutorAgentLocatorV1,
    ExecutorLocatorError,
    forget_executor_locator,
    list_executor_locators,
    load_executor_locator,
    publish_executor_locator,
    resolve_executor_locator,
)
from houmao.execution.models import ControllerScopeV1, ExecutionBindingV1
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import publish_managed_agent_record
from houmao.agents.realm_controller.errors import SessionManifestError


def locator(
    agent_id: str = "agent-1", agent_name: str = "reviewer", context: str = "alice-context"
) -> ExecutorAgentLocatorV1:
    """Create one admitted routing locator without any caller-local runtime authority."""

    binding = ExecutionBindingV1(
        context_id=context,
        host_id="foreign-host",
        account="alice",
        uid=1001,
        gid=1001,
        registry_root="/foreign/registry",
        runtime_root="/foreign/runtime",
        project_root="/foreign/project",
        profile_name="alice",
        transport="sudo",
        controller=ControllerScopeV1(
            controller_id="operator",
            authority="sudo_policy",
            operations=("state", "stop", "relaunch"),
        ),
        route_fingerprint="f" * 64,
        tmux_socket="/foreign/tmux.sock",
    )
    return ExecutorAgentLocatorV1(
        agent_id=agent_id,
        agent_name=agent_name,
        tool="codex",
        mode="headless",
        backend="codex_headless",
        profile_name="alice",
        binding=binding,
    )


def test_locator_schema_resource_matches_strict_model() -> None:
    """Ship the same closed contract validated by the product model."""

    source = resources.files("houmao.execution").joinpath(
        "schemas/executor_agent_locator.v2.schema.json"
    )
    schema = json.loads(source.read_text())
    assert schema == ExecutorAgentLocatorV1.model_json_schema()
    payload = locator().model_dump(mode="json")
    jsonschema.validate(payload, schema)
    for field in ("manifest", "credentials", "gateway", "queue", "session_root"):
        with pytest.raises(ValidationError):
            ExecutorAgentLocatorV1.model_validate_json(json.dumps({**payload, field: "forbidden"}))


def test_publish_load_and_list_do_not_open_foreign_paths(tmp_path: Path) -> None:
    """Owner paths remain qualified data, even when inaccessible from this host."""

    record = locator()
    assert publish_executor_locator(record, root=tmp_path) == record
    assert load_executor_locator("agent-1", root=tmp_path) == record
    assert resolve_executor_locator(agent_id="agent-1", root=tmp_path) == record
    assert resolve_executor_locator(agent_name="reviewer", root=tmp_path) == record
    assert list_executor_locators(root=tmp_path) == (record,)
    assert not (tmp_path / "live_agents").exists()
    assert not (tmp_path / "external_agents").exists()
    stored = json.loads((tmp_path / "executor_agents/agent-1/record.json").read_text())
    assert set(stored) == {
        "schema_version",
        "kind",
        "agent_id",
        "agent_name",
        "tool",
        "mode",
        "backend",
        "profile_name",
        "binding",
    }
    assert stored["binding"]["runtime_root"] == "/foreign/runtime"
    assert (tmp_path / "executor_agents/agent-1/record.json").stat().st_mode & 0o777 == 0o600


def test_rc2_locator_requires_fresh_launch(tmp_path: Path) -> None:
    """A locator without the admitted run-mode binding cannot route a request."""

    publish_executor_locator(locator(), root=tmp_path)
    path = tmp_path / "executor_agents/agent-1/record.json"
    payload = json.loads(path.read_text())
    payload["schema_version"] = 1
    for field in ("mode", "tool", "backend"):
        del payload[field]
    path.write_text(json.dumps(payload))
    with pytest.raises(ExecutorLocatorError, match="start a fresh runtime session"):
        load_executor_locator("agent-1", root=tmp_path)


def test_missing_lookup_and_forget_do_not_create_registry(tmp_path: Path) -> None:
    """Read-only and absent-removal operations leave missing state uninitialized."""

    root = tmp_path / "absent"
    assert load_executor_locator("agent-1", root=root) is None
    assert list_executor_locators(root=root) == ()
    assert forget_executor_locator("agent-1", root=root) is False
    assert not root.exists()


def test_exact_id_never_chooses_a_friendly_name_or_tmux_alias(tmp_path: Path) -> None:
    """Name ambiguity stays explicit across independent owner identities."""

    publish_executor_locator(locator(), root=tmp_path)
    publish_executor_locator(locator("agent-2", context="bob-context"), root=tmp_path)
    with pytest.raises(ExecutorLocatorError, match="agent-1@alice-context.*agent-2@bob-context"):
        resolve_executor_locator(agent_name="reviewer", root=tmp_path)
    assert (
        resolve_executor_locator(agent_id="agent-2", root=tmp_path).binding.context_id
        == "bob-context"
    )
    assert resolve_executor_locator(agent_name="foreign-tmux-session", root=tmp_path) is None
    for arguments in ({}, {"agent_id": "agent-1", "agent_name": "reviewer"}):
        with pytest.raises(ExecutorLocatorError):
            resolve_executor_locator(root=tmp_path, **arguments)


def test_same_id_different_binding_cannot_replace_known_owner(tmp_path: Path) -> None:
    """Republish equivalent ownership but reject implicit agent migration."""

    original = locator()
    publish_executor_locator(original, root=tmp_path)
    assert publish_executor_locator(original, root=tmp_path) == original
    with pytest.raises(ExecutorLocatorError, match="different execution binding"):
        publish_executor_locator(locator(context="replacement"), root=tmp_path)
    assert load_executor_locator("agent-1", root=tmp_path) == original


def test_local_identity_conflict_is_checked_before_locator_publication(tmp_path: Path) -> None:
    """A local lifecycle ID cannot acquire a second foreign owner through routing storage."""

    directory = tmp_path / "live_agents/agent-1"
    directory.mkdir(parents=True)
    path = directory / "record.json"
    path.write_text(
        json.dumps(
            {
                "agent_id": "agent-1",
                "execution_binding": locator(context="other").binding.model_dump(mode="json"),
            }
        )
    )
    with pytest.raises(ExecutorLocatorError, match="different execution binding"):
        publish_executor_locator(locator(), root=tmp_path)
    assert not (tmp_path / "executor_agents").exists()
    path.write_text(
        json.dumps(
            {"agent_id": "agent-1", "execution_binding": locator().binding.model_dump(mode="json")}
        )
    )
    assert publish_executor_locator(locator(), root=tmp_path) == locator()


def test_unbound_local_identity_does_not_gain_execution_authority(tmp_path: Path) -> None:
    """Missing ownership metadata requires deliberate owner-side recovery, never a guess."""

    directory = tmp_path / "live_agents/agent-1"
    directory.mkdir(parents=True)
    (directory / "record.json").write_text('{"agent_id":"agent-1"}')
    with pytest.raises(ExecutorLocatorError, match="without matching execution authority"):
        publish_executor_locator(locator(), root=tmp_path)


def test_malformed_exact_record_fails_closed_but_list_skips_it(tmp_path: Path) -> None:
    """Malformed storage cannot become a live route or trigger local fallback for an exact ID."""

    directory = tmp_path / "executor_agents/agent-1"
    directory.mkdir(parents=True)
    (directory / "record.json").write_text("not-json")
    with pytest.raises(ExecutorLocatorError, match="malformed"):
        load_executor_locator("agent-1", root=tmp_path)
    assert list_executor_locators(root=tmp_path) == ()
    with pytest.raises(ExecutorLocatorError):
        publish_executor_locator(locator(), root=tmp_path)


def test_forget_removes_only_lexical_locator_and_preserves_other_collections(
    tmp_path: Path,
) -> None:
    """Forget is routing maintenance rather than owner stop or artifact cleanup."""

    publish_executor_locator(locator(), root=tmp_path)
    other = tmp_path / "external_agents/communication-only"
    other.mkdir(parents=True)
    marker = other / "record.json"
    marker.write_text("communication marker")
    assert forget_executor_locator("agent-1", root=tmp_path)
    assert load_executor_locator("agent-1", root=tmp_path) is None
    assert marker.read_text() == "communication marker"
    assert not forget_executor_locator("agent-1", root=tmp_path)


def test_forget_symlinked_entry_preserves_external_target(tmp_path: Path) -> None:
    """Never resolve a symlink to choose the recursive removal target."""

    target = tmp_path / "owner-native-home"
    target.mkdir()
    marker = target / "private-key"
    marker.write_text("synthetic-private-material")
    root = tmp_path / "registry"
    collection = root / "executor_agents"
    collection.mkdir(parents=True)
    (collection / "agent-1").symlink_to(target, target_is_directory=True)
    with pytest.raises(ExecutorLocatorError):
        load_executor_locator("agent-1", root=root)
    assert forget_executor_locator("agent-1", root=root)
    assert marker.read_text() == "synthetic-private-material"
    assert not (collection / "agent-1").is_symlink()


def test_symlinked_collection_is_never_followed(tmp_path: Path) -> None:
    """Untrusted registry structure cannot redirect reads, publication, or deletion."""

    root = tmp_path / "registry"
    root.mkdir()
    target = tmp_path / "outside"
    target.mkdir()
    (root / "executor_agents").symlink_to(target, target_is_directory=True)
    for operation in (
        lambda: publish_executor_locator(locator(), root=root),
        lambda: load_executor_locator("agent-1", root=root),
        lambda: forget_executor_locator("agent-1", root=root),
    ):
        with pytest.raises(ExecutorLocatorError):
            operation()
    assert list(target.iterdir()) == []


def test_atomic_replace_failure_leaves_no_orphan_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publication failure preserves the old locator and cleans only its temporary write."""

    original = locator()
    publish_executor_locator(original, root=tmp_path)

    def fail_replace(*args: object, **kwargs: object) -> None:
        """Inject a failed final publication step."""

        raise OSError("simulated filesystem failure")

    monkeypatch.setattr("houmao.execution.locators.os.replace", fail_replace)
    with pytest.raises(OSError):
        publish_executor_locator(original, root=tmp_path)
    assert load_executor_locator("agent-1", root=tmp_path) == original
    assert sorted(path.name for path in (tmp_path / "executor_agents/agent-1").iterdir()) == [
        "record.json"
    ]


def test_locator_lookup_uses_explicit_registry_environment(tmp_path: Path) -> None:
    """Reuse the supported per-user registry-root override without project discovery."""

    env = {"HOUMAO_GLOBAL_REGISTRY_DIR": str(tmp_path)}
    publish_executor_locator(locator(), env=env)
    assert load_executor_locator("agent-1", env=env) == locator()


def test_later_local_publication_cannot_shadow_existing_executor_owner(tmp_path: Path) -> None:
    """The ownership conflict check works in both publication orders."""

    record = ManagedAgentRegistryRecordV3.model_validate_json(
        json.dumps(
            {
                "schema_version": 5,
                "mode": "headless",
                "agent_id": "agent-1",
                "agent_name": "reviewer",
                "generation_id": "local-generation",
                "lifecycle": {
                    "state": "stopped",
                    "relaunchable": True,
                    "state_updated_at": "2026-11-17T00:00:00Z",
                    "stopped_at": "2026-11-17T00:00:00Z",
                    "stop_reason": "operator_stop",
                },
                "identity": {"backend": "codex_headless", "tool": "codex"},
                "runtime": {
                    "manifest_path": "/foreign/runtime/session/manifest.json",
                    "session_root": "/foreign/runtime/session",
                    "agent_def_dir": "/foreign/project/.houmao/agents",
                },
                "terminal": {
                    "current_session_name": None,
                    "last_session_name": "owner-session",
                    "socket_path": "/foreign/tmux.sock",
                },
                "liveness": None,
                "gateway": None,
                "mailboxes": {
                    "offline": {"revision": "offline-empty", "binding": None},
                    "online": {"revision": "online-empty", "binding": None},
                },
                "canonical_mail_identity": None,
            }
        )
    )
    publish_executor_locator(locator(), root=tmp_path)
    env = {"HOUMAO_GLOBAL_REGISTRY_DIR": str(tmp_path)}
    with pytest.raises(SessionManifestError, match="different executor owner"):
        publish_managed_agent_record(record, env=env)
    assert not (tmp_path / "live_agents/agent-1").exists()
    same_owner = record.model_copy(update={"execution_binding": locator().binding})
    assert publish_managed_agent_record(same_owner, env=env).execution_binding == locator().binding
    assert load_executor_locator("agent-1", root=tmp_path) == locator()
