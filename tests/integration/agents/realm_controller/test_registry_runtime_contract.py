from __future__ import annotations

import json
import os
import shutil
from threading import Event, Thread, get_ident
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller import cli, manifest, registry_storage, runtime
from houmao.agents.realm_controller.backends.tmux_runtime import create_tmux_session
from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.errors import RuntimeStartupRollbackError, SessionManifestError
from houmao.agents.realm_controller.gateway_access_runtime import gateway_access_for_manifest
from houmao.agents.realm_controller.hook_observation_launch import start_collector
from houmao.agents.realm_controller.models import LaunchPlan, SessionControlResult
from houmao.agents.realm_controller.owner_admission import OwnerAdmissionError
from houmao.agents.realm_controller.registry_storage import (
    load_managed_agent_record_by_agent_id,
    publish_live_agent_record,
    remove_live_agent_record,
    resolve_live_agent_record,
)
from houmao.execution.tmux import TmuxServer, tmux_server_scope
from houmao.execution.tmux_selection import ResolvedTmuxServer
from houmao.passive_server import headless as passive_headless
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import PassiveHeadlessLaunchRequest


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_role(agent_def_dir: Path) -> None:
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _seed_brain_manifest(tmp_path: Path) -> Path:
    env_file = tmp_path / "vars.env"
    env_file.write_text("ANTHROPIC_API_KEY=secret\n", encoding="utf-8")
    manifest_path = tmp_path / "brain.yaml"
    manifest_path.write_text(
        "\n".join(
            [
                "schema_version: 3",
                "inputs:",
                "  tool: claude",
                "  skills: []",
                "  setup: default",
                "  auth: default",
                "  adapter_path: /tmp/tool-adapter.yaml",
                "  preset_path: null",
                "launch_policy:",
                "  operator_prompt_mode: as_is",
                "runtime:",
                f"  runtime_root: {tmp_path}",
                "  home_id: test-home",
                f"  home_path: {tmp_path / 'home'}",
                f"  launch_helper: {tmp_path / 'home' / 'launch.sh'}",
                "  launch_executable: claude",
                "  launch_home_selector:",
                "    env_var: CLAUDE_CONFIG_DIR",
                f"    value: {tmp_path / 'home'}",
                "  launch_contract:",
                "    adapter_defaults:",
                "      args: []",
                "      tool_params: {}",
                "    requested_overrides:",
                "      preset: null",
                "      direct: null",
                "    tool_metadata:",
                "      tool_params: {}",
                "    construction_provenance:",
                "      adapter_path: /tmp/tool-adapter.yaml",
                "      preset_path: null",
                "      preset_overrides_present: false",
                "      direct_overrides_present: false",
                "credentials:",
                f"  auth_path: {tmp_path / 'auth'}",
                "  projected_files: []",
                "  env_contract:",
                f"    source_file: {env_file}",
                "    allowlisted_env_vars:",
                "      - ANTHROPIC_API_KEY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest_path


class _FakeHeadlessSession:
    def __init__(self, *, tmux_session_name: str, launch_plan: LaunchPlan) -> None:
        self.backend = "claude_headless"
        self.m_launch_plan = launch_plan
        self.m_state = HeadlessSessionState(
            session_id="sess-1",
            turn_index=0,
            role_bootstrap_applied=True,
            working_directory=str(launch_plan.working_directory),
            tmux_session_name=tmux_session_name,
        )

    @property
    def state(self) -> HeadlessSessionState:
        return self.m_state

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        self.m_launch_plan = launch_plan

    def set_tmux_binding(self, binding: SessionManifestTmuxSectionV1, repair: object) -> None:
        """Keep the controller's verified terminal coordinates in the fake state."""

        self.m_state = replace(
            self.m_state,
            tmux_session_name=binding.session_name,
            tmux_window_name=binding.primary_window_name,
            tmux_window_id=binding.primary_window_id,
            tmux_pane_id=binding.primary_pane_id,
        )

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        del force_cleanup

    def send_prompt(self, prompt: str, **_kwargs: object) -> list[object]:
        del prompt
        self.m_state = replace(self.m_state, turn_index=self.m_state.turn_index + 1)
        return []

    def interrupt(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="interrupt", detail="interrupted")

    def terminate(self) -> SessionControlResult:
        return SessionControlResult(status="ok", action="terminate", detail="stopped")

    def close(self) -> None:
        return


@pytest.fixture
def isolated_startup(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[tuple[TmuxServer, dict[str, Any]]]:
    """Start only an isolated tmux server and use a fake native CLI."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is unavailable")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "owner-config"))
    native_cli = tmp_path / "bin" / "claude"
    _write(native_cli, "#!/bin/sh\nprintf '2.1.3 (Claude Code)\\n'\n")
    native_cli.chmod(0o700)
    monkeypatch.setenv("PATH", f"{native_cli.parent}:{os.environ['PATH']}")
    workdir = tmp_path / "work"
    _write(workdir / "operator-data", "keep workspace\n")
    _write(tmp_path / "home" / "operator-data", "keep home\n")
    definitions = tmp_path / "repo"
    _seed_role(definitions)
    socket_path = str(tmp_path / "t.sock")
    request = {
        "agent_def_dir": definitions,
        "brain_manifest_path": _seed_brain_manifest(tmp_path),
        "role_name": "r",
        "backend": "claude_headless",
        "runtime_root": tmp_path / "runtime",
        "working_directory": workdir,
        "agent_name": "gpu",
        "agent_id": "startup-agent",
        "tmux_session_name": "launch-attempt",
        "resolved_tmux_server": ResolvedTmuxServer(socket_path, True),
    }
    with tmux_server_scope(socket_path):
        server = TmuxServer()
        create_tmux_session(session_name="sentinel", working_directory=workdir)
        try:
            yield server, request
        finally:
            server.command(["kill-server"], no_start=True)


@pytest.mark.parametrize("fault", ["controller", "manifest"])
def test_required_startup_rolls_back_real_container_and_observer(
    fault: str,
    isolated_startup: tuple[TmuxServer, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Clean up both acquired processes when a birth fails before publication."""

    server, request = isolated_startup
    observer_pids: list[int] = []

    def activate_observation(plan: LaunchPlan, *, session_root: Path) -> LaunchPlan:
        observer = start_collector(session_root=session_root, generation=1, token="x" * 32)
        observer_pids.append(observer.pid)
        return plan

    def fail(*args: object, **kwargs: object) -> None:
        assert server.list_sessions() == {"sentinel", "launch-attempt"}
        assert len(observer_pids) == 1
        os.kill(observer_pids[0], 0)
        raise OSError(f"injected {fault} failure")

    with monkeypatch.context() as injected:
        injected.setattr(
            runtime, "activate_hook_observation_for_provider_start", activate_observation
        )
        if fault == "controller":
            injected.setattr(runtime.RuntimeSessionController, "__post_init__", fail)
        else:
            injected.setattr(runtime, "write_session_manifest", fail)
        with pytest.raises(OSError, match=f"injected {fault} failure"):
            runtime.start_runtime_session(**request)

    assert server.list_sessions() == {"sentinel"}
    with pytest.raises(ProcessLookupError):
        os.kill(observer_pids[0], 0)
    assert load_managed_agent_record_by_agent_id("startup-agent") is None
    assert not list((request["runtime_root"] / "sessions/claude_headless").iterdir())
    retried = runtime.start_runtime_session(**request)
    assert retried.manifest_path.is_file()
    assert server.list_sessions() == {"sentinel", "launch-attempt"}
    assert retried.stop(force_cleanup=True).status == "ok"


@pytest.mark.parametrize("other_generation", ["absent", "previous", "competing"])
def test_required_publication_withdraws_only_failed_generation(
    other_generation: str,
    isolated_startup: tuple[TmuxServer, dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remove partial discovery without touching operator or other launch resources."""

    server, request = isolated_startup
    existing = runtime.start_runtime_session(
        **{
            **request,
            "tmux_session_name": "existing",
            "registry_launch_authority": "external",
        }
    )
    existing_access = gateway_access_for_manifest(existing.manifest_path)
    existing_snapshot = existing_access.store.snapshot()
    existing_key = existing_access.store.load_self(existing_access.target.incarnation)
    other_record = existing.build_shared_registry_record()
    previous_record = (
        existing.publish_stopped_shared_registry_record(last_tmux_session_name="existing")
        if other_generation == "previous"
        else None
    )
    failed_paths: list[Path] = []
    publish = runtime.RuntimeSessionController.refresh_shared_registry_record

    def publish_then_fail(controller: runtime.RuntimeSessionController):
        published = publish(controller)
        assert published is not None
        assert controller.gateway_attach_path is not None
        assert controller.gateway_attach_path.is_file()
        failed_paths.append(controller.manifest_path)
        if other_generation == "competing":
            assert other_record is not None
            assert remove_live_agent_record(
                published.agent_id, generation_id=published.generation_id
            )
            publish_live_agent_record(other_record)
        raise SessionManifestError("injected discovery failure")

    monkeypatch.setattr(
        runtime.RuntimeSessionController, "refresh_shared_registry_record", publish_then_fail
    )
    with pytest.raises(SessionManifestError, match="injected discovery failure"):
        runtime.start_runtime_session(**request)

    assert len(failed_paths) == 1 and not failed_paths[0].parent.exists()
    assert server.list_sessions() == {"sentinel", "existing"}
    record = load_managed_agent_record_by_agent_id("startup-agent")
    if other_generation == "competing":
        assert record == other_record
    else:
        assert record == previous_record
    assert existing.manifest_path.is_file()
    assert existing_access.store.snapshot() == existing_snapshot
    assert existing_access.store.load_self(existing_access.target.incarnation) == existing_key
    assert (request["working_directory"] / "operator-data").read_text() == "keep workspace\n"
    assert (request["working_directory"].parent / "home/operator-data").read_text() == "keep home\n"


def test_optional_attach_failure_keeps_committed_runtime(
    isolated_startup: tuple[TmuxServer, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Return a live runtime when an optional gateway operation raises."""

    server, request = isolated_startup

    def fail_attach(*args: object, **kwargs: object) -> None:
        raise OSError("injected optional attach failure")

    monkeypatch.setattr(runtime.RuntimeSessionController, "attach_gateway", fail_attach)
    controller = runtime.start_runtime_session(**request, gateway_auto_attach=True)

    assert controller.gateway_auto_attach_error == "injected optional attach failure"
    found = resolve_live_agent_record("startup-agent")
    assert found is not None
    assert found.runtime.manifest_path == str(controller.manifest_path)
    assert server.list_sessions() == {"sentinel", "launch-attempt"}
    assert controller.interrupt().status == "ok"
    assert controller.stop(force_cleanup=True).status == "ok"


def test_incomplete_rollback_reports_failure_and_retains_manifest(
    isolated_startup: tuple[TmuxServer, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the manifest available to fence a publication that cleanup could not withdraw."""

    server, request = isolated_startup
    publish = runtime.RuntimeSessionController.refresh_shared_registry_record

    def publish_then_fail(controller: runtime.RuntimeSessionController):
        assert publish(controller) is not None
        raise OSError("injected startup failure")

    def fail_removal(*args: object, **kwargs: object) -> None:
        raise OSError("injected rollback failure")

    monkeypatch.setattr(
        runtime.RuntimeSessionController, "refresh_shared_registry_record", publish_then_fail
    )
    monkeypatch.setattr(registry_storage, "_rollback_startup_registry_publication", fail_removal)
    with pytest.raises(
        RuntimeStartupRollbackError,
        match="injected startup failure.*Incomplete launch cleanup: shared registry publication",
    ):
        runtime.start_runtime_session(**request)

    assert server.list_sessions() == {"sentinel"}
    record = load_managed_agent_record_by_agent_id("startup-agent")
    assert record is not None
    assert Path(record.runtime.manifest_path).is_file()


def test_rollback_preserves_an_in_place_handoff_that_already_won(
    isolated_startup: tuple[TmuxServer, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generation transferred on the same durable path owns that terminal and its files."""

    server, request = isolated_startup
    publish = runtime.RuntimeSessionController.refresh_shared_registry_record

    def publish_then_transfer(controller: runtime.RuntimeSessionController):
        published = publish(controller)
        assert published is not None
        transferred = published.model_copy(update={"generation_id": "in-place-generation"})
        payload = manifest.load_session_manifest(controller.manifest_path).payload
        payload["registry_generation_id"] = transferred.generation_id
        payload["runtime"]["registry_generation_id"] = transferred.generation_id
        manifest.write_session_manifest(
            controller.manifest_path,
            payload,
            expected_registry_generation_id=published.generation_id,
        )
        publish_live_agent_record(transferred, expected_generation_id=published.generation_id)
        raise OSError("injected failure after generation transfer")

    monkeypatch.setattr(
        runtime.RuntimeSessionController, "refresh_shared_registry_record", publish_then_transfer
    )
    with pytest.raises(
        RuntimeStartupRollbackError, match="runtime generation changed before cleanup"
    ):
        runtime.start_runtime_session(**request)

    current = load_managed_agent_record_by_agent_id("startup-agent")
    assert current is not None and current.generation_id == "in-place-generation"
    assert Path(current.runtime.manifest_path).is_file()
    assert server.list_sessions() == {"sentinel", "launch-attempt"}


def test_rollback_excludes_in_place_relaunch_and_manifest_handoff(
    isolated_startup: tuple[TmuxServer, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep a competing writer from replacing a generation while rollback tears it down."""

    server, request = isolated_startup
    publish = runtime.RuntimeSessionController.refresh_shared_registry_record
    withdraw = registry_storage._rollback_startup_registry_publication
    flock = manifest.fcntl.flock
    writer_waiting = Event()
    finished = Event()
    errors: list[Exception] = []
    controllers: list[runtime.RuntimeSessionController] = []

    def publish_then_fail(controller: runtime.RuntimeSessionController):
        assert publish(controller) is not None
        controllers.append(controller)
        raise OSError("injected publication failure")

    def observe_writer_lock(descriptor: int, operation: int) -> None:
        if competitor.ident == get_ident() and operation == manifest.fcntl.LOCK_EX:
            writer_waiting.set()
        flock(descriptor, operation)

    def try_handoff():
        controller = controllers[0]
        try:
            controller.relaunch()
        except OwnerAdmissionError as exc:
            errors.append(exc)
        payload = manifest.load_session_manifest(controller.manifest_path).payload
        generation = payload["registry_generation_id"]
        payload["registry_generation_id"] = "concurrent-same-path-generation"
        payload["runtime"]["registry_generation_id"] = "concurrent-same-path-generation"
        try:
            manifest.write_session_manifest(
                controller.manifest_path, payload, expected_registry_generation_id=generation
            )
        except SessionManifestError as exc:
            errors.append(exc)
        finally:
            finished.set()

    competitor = Thread(target=try_handoff, daemon=True)

    def withdraw_while_competing(*args, **kwargs):
        competitor.start()
        assert writer_waiting.wait(2)
        assert not finished.is_set()
        withdraw(*args, **kwargs)

    monkeypatch.setattr(
        runtime.RuntimeSessionController, "refresh_shared_registry_record", publish_then_fail
    )
    monkeypatch.setattr(
        registry_storage, "_rollback_startup_registry_publication", withdraw_while_competing
    )
    monkeypatch.setattr(manifest.fcntl, "flock", observe_writer_lock)
    with pytest.raises(OSError, match="injected publication failure"):
        runtime.start_runtime_session(**request)

    competitor.join(3)
    assert finished.is_set()
    assert len(errors) == 2
    assert isinstance(errors[0], OwnerAdmissionError)
    assert "handoff requires the existing session manifest" in str(errors[1])
    assert not controllers[0].manifest_path.parent.exists()
    assert load_managed_agent_record_by_agent_id("startup-agent") is None
    assert server.list_sessions() == {"sentinel"}


def test_passive_publication_failure_rolls_back_the_external_birth(
    isolated_startup: tuple[TmuxServer, dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Roll back a published passive-owned registry record without an ordinary stop."""

    server, request = isolated_startup
    passive = passive_headless.HeadlessAgentService(
        PassiveServerConfig(
            api_base_url="http://127.0.0.1:19891",
            runtime_root=request["runtime_root"],
            registry_root=request["runtime_root"].parent / "registry",
        )
    )
    failed_paths: list[Path] = []

    def publish_then_fail(record, *, env=None):
        assert server.list_sessions() != {"sentinel"}
        published = publish_live_agent_record(record, env=env)
        failed_paths.append(Path(published.runtime.manifest_path))
        assert json.loads(failed_paths[-1].read_text())["registry_launch_authority"] == "external"
        raise OSError("injected external publication failure")

    monkeypatch.setattr(passive_headless, "publish_live_agent_record", publish_then_fail)
    response = passive.launch(
        PassiveHeadlessLaunchRequest(
            tool="claude",
            working_directory=str(request["working_directory"]),
            agent_def_dir=str(request["agent_def_dir"]),
            brain_manifest_path=str(request["brain_manifest_path"]),
            role_name="r",
            agent_name="gpu",
            agent_id="startup-agent",
        )
    )

    assert response == (
        503,
        {"detail": "Managed headless launch could not establish current owner authority"},
    )
    assert len(failed_paths) == 1 and not failed_paths[0].parent.exists()
    assert passive.m_store.list_authority_records() == []
    assert load_managed_agent_record_by_agent_id("startup-agent") is None
    assert server.list_sessions() == {"sentinel"}


def test_cli_runtime_registry_contract_start_send_and_stop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(
                kwargs.get("agent_identity")
                or kwargs["resume_state"].backend_state["tmux_session_name"]
            ),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(runtime, "tmux_session_exists_shared", lambda **_: False)

    start_exit = cli.main(
        [
            "start-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--runtime-root",
            str(runtime_root),
            "--brain-manifest",
            str(brain_manifest_path),
            "--role",
            "r",
            "--backend",
            "claude_headless",
            "--workdir",
            str(tmp_path),
            "--agent-identity",
            "gpu",
        ]
    )
    start_payload = json.loads(capsys.readouterr().out)
    manifest_path = Path(start_payload["session_manifest"])

    assert start_exit == 0
    started_record = resolve_live_agent_record("HOUMAO-gpu")
    assert started_record is not None
    generation_id = started_record.generation_id

    prompt_exit = cli.main(
        [
            "send-prompt",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
            "--prompt",
            "hello",
        ]
    )
    capsys.readouterr()

    assert prompt_exit == 0
    refreshed_record = resolve_live_agent_record("HOUMAO-gpu")
    assert refreshed_record is not None
    assert refreshed_record.generation_id == generation_id

    stop_exit = cli.main(
        [
            "stop-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
        ]
    )
    capsys.readouterr()

    assert stop_exit == 0
    assert resolve_live_agent_record("HOUMAO-gpu") is None


def test_cli_runtime_registry_contract_surfaces_nonfatal_registry_warnings(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    registry_root = tmp_path / "registry"
    brain_manifest_path = _seed_brain_manifest(tmp_path)
    _seed_role(agent_def_dir)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(registry_root))
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.HeadlessInteractiveSession",
        _FakeHeadlessSession,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeHeadlessSession(
            tmux_session_name=str(
                kwargs.get("agent_identity")
                or kwargs["resume_state"].backend_state["tmux_session_name"]
            ),
            launch_plan=kwargs["launch_plan"],
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.set_tmux_session_environment_shared",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(runtime, "tmux_session_exists_shared", lambda **_: False)

    start_exit = cli.main(
        [
            "start-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--runtime-root",
            str(runtime_root),
            "--brain-manifest",
            str(brain_manifest_path),
            "--role",
            "r",
            "--backend",
            "claude_headless",
            "--workdir",
            str(tmp_path),
            "--agent-identity",
            "gpu",
        ]
    )
    manifest_path = Path(json.loads(capsys.readouterr().out)["session_manifest"])
    assert start_exit == 0

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.RuntimeSessionController.ensure_gateway_capability",
        lambda self, blueprint_gateway_defaults=None: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.publish_live_agent_record",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            SessionManifestError("registry publish down")
        ),
    )

    prompt_exit = cli.main(
        [
            "send-prompt",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
            "--prompt",
            "hello",
        ]
    )
    prompt_capture = capsys.readouterr()

    assert prompt_exit == 0
    assert (
        "warning: Shared-registry refresh failed after manifest persistence" in prompt_capture.err
    )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime.remove_live_agent_record",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("permission denied")),
    )

    stop_exit = cli.main(
        [
            "stop-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            str(manifest_path),
        ]
    )
    stop_capture = capsys.readouterr()

    assert stop_exit == 0
    assert (
        "warning: Shared-registry stop transition failed after successful stop-session teardown"
        in stop_capture.err
    )
