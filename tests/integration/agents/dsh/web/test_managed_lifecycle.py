"""Qualify owned Web supervision, exact reconnection, and explicit lifecycle boundaries."""

from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import signal
import time
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import pytest

from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession, DshWebSessionState
from houmao.agents.realm_controller.backends.tmux_runtime import (
    create_tmux_session,
    has_tmux_session,
    run_tmux,
)
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    _relaunch_backend_session,
)
from tests.integration.agents.dsh.test_gateway_passive import bind_fixture_gateway_owner
from tests.integration.agents.dsh.test_managed_acp import _launch_plan
from tests.integration.agents.dsh.web.conftest import (
    call_native_request,
    read_native_history,
    read_native_session_ids,
    read_native_workspaces,
)


def _web_plan(
    root: Path, executable: Path, endpoint: str, *, tmux_socket: Path | None = None
) -> tuple[LaunchPlan, Path]:
    """Prepare an explicit synthetic model and stable managed Web owner."""

    root.mkdir(exist_ok=True)
    plan, manifest = _launch_plan(root, executable, endpoint)
    if tmux_socket is not None:
        plan = bind_fixture_gateway_owner(
            plan,
            root=root,
            tmux_socket=tmux_socket,
            agent_id="web-lifecycle-owner",
            generation="web-lifecycle-generation",
        )
    plan = replace(
        plan,
        backend="dsh_web",
        native_surface_kind="web",
        metadata={
            **plan.metadata,
            "managed_web_identity": {
                "agent_id": "web-lifecycle-owner",
                "runtime_session_id": "runtime",
                "generation": "web-lifecycle-generation",
            },
        },
    )
    manifest.unlink()
    return plan, manifest


def _controller(
    plan: LaunchPlan, manifest: Path, session: DshWebSession
) -> RuntimeSessionController:
    """Publish the same native binding through the real runtime manifest writer."""

    controller = RuntimeSessionController(
        launch_plan=plan,
        role_name="controlled",
        brain_manifest_path=manifest.parent.parent / "brain.yaml",
        manifest_path=manifest,
        backend_session=session,
        agent_identity=session.state.tmux_session_name,
        agent_id="web-lifecycle-owner",
        tmux_session_name=session.state.tmux_session_name,
        registry_generation_id="web-lifecycle-generation",
    )
    controller.persist_manifest(refresh_registry=False)
    return controller


def _stop(session: DshWebSession) -> None:
    """Stop only the exact private host and its explicitly isolated supervisor session."""

    session.configure_stop_force_cleanup(force_cleanup=True)
    assert session.terminate().status == "ok"


def test_managed_workspace_membership_survives_exact_and_replacement_lifecycles(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """Bind before the first turn and keep native Workspace history across lifecycle operations."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint, tmux_socket=isolated_tmux)
    session = DshWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=manifest,
        role_name="controlled",
        provider_start=True,
    )
    try:
        controller = _controller(plan, manifest, session)
        workdir = str(plan.working_directory.resolve())
        original = session.state.web_identity["native_session_id"]
        rows = read_native_workspaces(session._client())
        assert set(rows) == {workdir}
        assert rows[workdir]["sessionIds"] == [original]
        assert json.loads(manifest.read_text())["backend_state"]["web_identity"] == (
            session.state.web_identity
        )
        assert read_native_session_ids(session._client()) == {original}
        assert not requests
        workspace_id = rows[workdir]["workspaceId"]
        controller.send_prompt("managed Workspace history", turn_artifact_dir_name="before")

        other_dir = tmp_path / "another-workspace"
        other_dir.mkdir()
        other_workspace = call_native_request(
            session._client(), "workspace/create", {"request": {"path": str(other_dir)}}
        )["workspace"]
        other = call_native_request(
            session._client(),
            "session/create",
            {"request": {"workspaceId": other_workspace["workspaceId"]}},
        )["sessionId"]
        assert call_native_request(
            session._client(),
            "session/prompt",
            {
                "request": {
                    "requestId": str(uuid4()),
                    "sessionId": other,
                    "mode": "queue",
                    "content": [{"type": "text", "text": "unrelated Workspace history"}],
                }
            },
        )["accepted"]
        deadline = time.monotonic() + 10
        while "Controlled native result" not in read_native_history(session._client(), other):
            assert time.monotonic() < deadline, "Unrelated native turn did not settle"
            time.sleep(0.02)

        expected = read_native_workspaces(session._client())
        assert expected[str(other_dir)]["sessionIds"] == [other]
        for _ in range(2):
            result = _relaunch_backend_session(
                controller,
                chat_session=RelaunchChatSessionSelection(mode="exact", session_id=original),
            )
            assert result.status == "ok", result.detail
            controller.persist_manifest()
            assert session.state.web_identity["native_session_id"] == original
            assert read_native_workspaces(session._client()) == expected
            assert read_native_session_ids(session._client()) == {original, other}
            assert "managed Workspace history" in read_native_history(session._client(), original)
        assert len(requests) == 2

        result = _relaunch_backend_session(
            controller, chat_session=RelaunchChatSessionSelection(mode="new")
        )
        assert result.status == "ok", result.detail
        controller.persist_manifest()
        replacement = session.state.web_identity["native_session_id"]
        assert replacement not in {original, other}
        assert read_native_session_ids(session._client()) == {original, other, replacement}
        after_relaunch = read_native_workspaces(session._client())
        assert set(after_relaunch) == set(expected)
        assert after_relaunch[workdir]["workspaceId"] == workspace_id
        assert after_relaunch[workdir]["sessionIds"] == [replacement, original]
        assert after_relaunch[str(other_dir)] == expected[str(other_dir)]

        controller.send_web_prompt(
            "managed Workspace reset history",
            session_selection=HeadlessTurnSessionSelection(mode="new"),
            turn_artifact_dir_name="reset",
        )
        reset = session.state.web_identity["native_session_id"]
        assert reset not in {original, other, replacement}
        assert read_native_session_ids(session._client()) == {original, other, replacement, reset}
        assert json.loads(manifest.read_text())["backend_state"]["web_identity"] == (
            session.state.web_identity
        )
        after_reset = read_native_workspaces(session._client())
        assert set(after_reset) == set(expected)
        assert after_reset[workdir]["workspaceId"] == workspace_id
        assert after_reset[workdir]["sessionIds"] == [reset, replacement, original]
        assert after_reset[str(other_dir)] == expected[str(other_dir)]
        assert "unrelated Workspace history" in read_native_history(session._client(), other)
        assert "managed Workspace history" in read_native_history(session._client(), original)
        assert "managed Workspace reset history" in read_native_history(session._client(), reset)
        assert len(requests) == 3
    finally:
        _stop(session)


def test_two_owned_hosts_reconnect_without_retargeting_or_disclosing_native_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """An occupied listener and a second host leave each execution and API identity independent."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    endpoint, requests = controlled_messages_server
    sessions: list[DshWebSession] = []
    try:
        for index in range(2):
            plan, manifest = _web_plan(tmp_path / str(index), dsh_executable, endpoint)
            session = DshWebSession.from_launch_plan(
                launch_plan=plan,
                session_manifest_path=manifest,
                role_name="controlled",
                provider_start=True,
                tmux_session_name=f"HOUMAO-web-lifecycle-{index}",
            )
            sessions.append(session)
            _controller(plan, manifest, session)
        first, second = sessions
        assert first.state.origin != second.state.origin
        assert first.state.origin not in endpoint and second.state.origin not in endpoint
        assert (
            first.state.web_identity["native_session_id"]
            != second.state.web_identity["native_session_id"]
        )
        events = first.send_prompt("first exact lifecycle input", turn_artifact_dir_name="first")
        assert any(event.kind == "assistant" for event in events)
        original = dict(first.state.web_identity)
        native_pid = first.state.native_pid
        first.close_control_connection()
        restored = DshWebSession.from_launch_plan(
            launch_plan=first.plan,
            session_manifest_path=first.m_manifest_path,
            role_name="controlled",
            state=DshWebSessionState.from_payload(first.state.to_payload()),
        )
        sessions[0] = restored
        assert restored.observe_web_state()["identity"] == original
        restored.send_prompt("second exact lifecycle input", turn_artifact_dir_name="second")
        assert restored.state.native_pid == native_pid
        assert len(requests) == 2
        assert "first exact lifecycle input" in json.dumps(requests[-1]["messages"])
        bootstrap = json.loads(Path(restored.state.bootstrap_path).read_text())
        console = run_tmux(["capture-pane", "-p", "-t", restored.state.tmux_pane_id]).stdout
        assert bootstrap["launch_token"] not in console
        assert "synthetic-local-only" not in console
        assert Path(restored.state.bootstrap_path).stat().st_mode & 0o077 == 0
        assert (
            Path(restored.state.bootstrap_path).with_name("native-private.log").stat().st_mode
            & 0o077
            == 0
        )
        assert second.observe_web_state()["last_turn"] is None
    finally:
        for session in sessions:
            _stop(session)


def test_explicit_relaunch_restores_exact_history_under_fresh_execution_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """Native IDs survive exact relaunch while old execution leases fail and cold reads stay cold."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint, tmux_socket=isolated_tmux)
    session = DshWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=manifest,
        role_name="controlled",
        provider_start=True,
    )
    try:
        controller = _controller(plan, manifest, session)
        controller.send_prompt("before exact host replacement", turn_artifact_dir_name="before")
        previous = dict(session.state.web_identity)
        result = _relaunch_backend_session(
            controller,
            chat_session=RelaunchChatSessionSelection(
                mode="exact", session_id=previous["native_session_id"]
            ),
        )
        assert result.status == "ok", result.detail
        controller.persist_manifest(refresh_registry=False)
        assert session.state.web_identity["native_session_id"] == previous["native_session_id"]
        for key in ("generation", "host_incarnation", "agent_incarnation"):
            assert session.state.web_identity[key] != previous[key]
        assert session.interrupt_web_turn(previous, turn_start_seq=1).status == "error"
        controller.send_prompt("after exact host replacement", turn_artifact_dir_name="after")
        assert len(requests) == 2
        assert "before exact host replacement" in json.dumps(requests[-1]["messages"])
        old_pid, old_birth = session.state.native_pid, session.state.native_birth_token
        assert session.terminate().status == "ok"
        with pytest.raises(BackendExecutionError, match="unavailable"):
            session.observe_web_state()
        with pytest.raises(BackendExecutionError, match="unavailable"):
            session.send_prompt("must remain cold", turn_artifact_dir_name="refused")
        assert _dispatch_origin_birth_token(old_pid) != old_birth
        assert len(requests) == 2
    finally:
        _stop(session)


def test_external_supervisor_session_is_refused_without_changing_its_pane(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """A matching user-selected session name conveys no native launch ownership."""

    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint)
    name = "external-owned-by-test"
    create_tmux_session(session_name=name, working_directory=tmp_path)
    before = run_tmux(["list-panes", "-t", name, "-F", "#{pane_id}:#{pane_pid}"]).stdout
    with pytest.raises(BackendExecutionError, match="refuses to adopt"):
        DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=manifest,
            role_name="controlled",
            provider_start=True,
            tmux_session_name=name,
        )
    assert has_tmux_session(session_name=name).returncode == 0
    assert run_tmux(["list-panes", "-t", name, "-F", "#{pane_id}:#{pane_pid}"]).stdout == before
    assert not manifest.exists() and not requests


def test_late_completed_controller_cannot_overwrite_an_explicit_native_reset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """A newer binding remains intact when an older completed caller finally publishes."""

    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint, tmux_socket=isolated_tmux)
    session = DshWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=manifest,
        role_name="controlled",
        provider_start=True,
    )
    latest: DshWebSession | None = None
    try:
        stale = _controller(plan, manifest, session)
        original = dict(session.state.web_identity)
        # Stop immediately before this controller would persist its completed result.
        events = session.send_prompt("old caller completed", turn_artifact_dir_name="old")
        assert events[-1].payload["outcome"] == "completed"
        latest = DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=manifest,
            role_name="controlled",
            state=DshWebSessionState.from_payload(session.state.to_payload()),
        )
        current = _controller(plan, manifest, latest)
        current.send_web_prompt(
            "new explicit conversation",
            session_selection=HeadlessTurnSessionSelection(mode="new"),
            turn_artifact_dir_name="new",
        )
        assert latest.state.web_identity["native_session_id"] != original["native_session_id"]
        before = manifest.read_bytes()
        with pytest.raises(SessionManifestError, match="execution binding changed"):
            stale.persist_manifest(refresh_registry=False)
        assert manifest.read_bytes() == before
        assert len(requests) == 2
    finally:
        session.close_control_connection()
        _stop(latest or session)


def test_missing_companion_rolls_back_only_the_created_supervisor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """Failed required companion loading publishes no authority and reaps the created host."""

    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint)
    name = "HOUMAO-web-missing-companion"
    monkeypatch.setattr("houmao.agents.realm_controller.backends.dsh_web.files", lambda _: tmp_path)
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.dsh_web._STARTUP_TIMEOUT_SECONDS", 3
    )
    with pytest.raises(BackendExecutionError, match="startup failed"):
        DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=manifest,
            role_name="controlled",
            provider_start=True,
            tmux_session_name=name,
        )
    assert not manifest.exists() and not requests
    assert has_tmux_session(session_name=name).returncode != 0
    process_files = list((plan.home_path / "houmao-web").glob("*/supervisor.json"))
    assert len(process_files) == 1
    process = json.loads(process_files[0].read_text())
    for prefix in ("supervisor", "native"):
        assert (
            _dispatch_origin_birth_token(process[f"{prefix}_pid"])
            != process[f"{prefix}_birth_token"]
        )


def test_native_listener_conflict_rolls_back_without_adopting_the_existing_listener(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """A native bind failure leaves the occupied listener intact and publishes no Web authority."""

    import houmao.agents.realm_controller.backends.dsh_web as web_module

    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint)
    write_private = web_module._write_private_json
    occupied_port = urlsplit(endpoint).port
    assert occupied_port is not None

    def inject_bind_failure(path: Path, payload: dict[str, Any]) -> None:
        """Force only the private fixture's native launch to bind the already occupied port."""

        if path.name == "supervisor-input.json":
            command = list(payload["command"])
            command[command.index("--port") + 1] = str(occupied_port)
            payload = {**payload, "command": command}
        write_private(path, payload)

    monkeypatch.setattr(web_module, "_write_private_json", inject_bind_failure)
    monkeypatch.setattr(web_module, "_STARTUP_TIMEOUT_SECONDS", 3)
    name = "HOUMAO-web-conflicting-listener"
    with pytest.raises(BackendExecutionError, match="startup failed.*EADDRINUSE"):
        DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=manifest,
            role_name="controlled",
            provider_start=True,
            tmux_session_name=name,
        )
    assert not manifest.exists() and not requests
    assert has_tmux_session(session_name=name).returncode != 0
    logs = list((plan.home_path / "houmao-web").glob("*/native-private.log"))
    assert len(logs) == 1 and "EADDRINUSE" in logs[0].read_text()


def test_hard_supervisor_death_cannot_create_a_second_host_and_owned_stop_reaps_native(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """A surviving exactly captured native process blocks replacement until owned cleanup."""

    endpoint, requests = controlled_messages_server
    plan, manifest = _web_plan(tmp_path, dsh_executable, endpoint)
    session = DshWebSession.from_launch_plan(
        launch_plan=plan,
        session_manifest_path=manifest,
        role_name="controlled",
        provider_start=True,
    )
    try:
        previous = session.state
        assert (
            _dispatch_origin_birth_token(previous.supervisor_pid) == previous.supervisor_birth_token
        )
        os.kill(previous.supervisor_pid, signal.SIGKILL)
        deadline = time.monotonic() + 5
        while (
            _dispatch_origin_birth_token(previous.supervisor_pid) == previous.supervisor_birth_token
        ):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert _dispatch_origin_birth_token(previous.native_pid) == previous.native_birth_token
        with pytest.raises(BackendExecutionError, match="stopping its owned host first"):
            DshWebSession.from_launch_plan(
                launch_plan=plan,
                session_manifest_path=manifest,
                role_name="controlled",
                state=DshWebSessionState.from_payload(previous.to_payload()),
                provider_start=True,
            )
        assert not requests
        assert session.terminate().status == "ok"
        assert _dispatch_origin_birth_token(previous.native_pid) != previous.native_birth_token
    finally:
        _stop(session)
