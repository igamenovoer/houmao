"""Managed prompt delivery and lifecycle against isolated tmux servers."""

from pathlib import Path
import shlex
import shutil
import tempfile
import time
from collections.abc import Sequence
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.backends import local_interactive
from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
from houmao.agents.realm_controller.backends.tmux_runtime import (
    create_tmux_session,
    prepare_headless_agent_window,
    probe_tmux_backed_authority,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.gateway_models import (
    GatewayCurrentInstanceV1,
    GatewayTuiTrackingTimingConfigV1,
)
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_session_root
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller import runtime
from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.execution.tmux import TmuxCommandError, TmuxCommandResult, TmuxServer, tmux_server_scope


def _wait_for_prompt(path: Path) -> str:
    """Wait for the fixture to receive a complete prompt line."""

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.is_file() and (data := path.read_text()):
            return data
        time.sleep(0.02)
    pytest.fail("The selected pane did not receive the prompt")


def test_tui_prompt_uses_manifest_socket_and_exact_pane(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise the managed TUI with an auxiliary window and a same-name peer."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for the isolated runtime test")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setattr(local_interactive, "_SUPPORTED_TUI_PROCESSES", {"codex": ("sh",)})

    session_name = "HOUMAO-fixture"
    target_output = tmp_path / "target-prompt"
    peer_output = tmp_path / "peer-prompt"
    target_command = (
        "stty -echo\nprintf 'fixture-ready\\n'\n"
        f"while IFS= read -r line; do printf '%s\\n' \"$line\" >> {shlex.quote(str(target_output))}; done"
    )
    peer_command = target_command.replace(str(target_output), str(peer_output))
    plan = LaunchPlan(
        backend="local_interactive",
        tool="codex",
        executable="/bin/sh",
        args=["-c", target_command],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(method="cao_profile", role_name="fixture", prompt=""),
    )
    with tempfile.TemporaryDirectory(prefix="houmao-tui-") as socket_dir:
        owner = TmuxServer(Path(socket_dir) / "owner.sock")
        peer = TmuxServer(Path(socket_dir) / "peer.sock")
        try:
            peer.start(
                [
                    "new-session",
                    "-d",
                    "-s",
                    session_name,
                    "exec /bin/sh -c " + shlex.quote(peer_command),
                ],
                environment=peer.native_environment(),
            ).require_success()
            with tmux_server_scope(owner.socket_path):
                backend = LocalInteractiveSession(
                    launch_plan=plan,
                    role_name="fixture",
                    session_manifest_path=tmp_path / "manifest.json",
                    tmux_session_name=session_name,
                )
                controller = RuntimeSessionController(
                    launch_plan=plan,
                    role_name="fixture",
                    brain_manifest_path=tmp_path / "brain.json",
                    manifest_path=tmp_path / "manifest.json",
                    backend_session=backend,
                    tmux_session_name=session_name,
                )
                target = backend.state.tmux_pane_id
                assert target is not None
                assert "fixture-ready" in backend._capture_live_pane_output()

            peer_panes = peer.observe_session(session_name)
            assert peer_panes is not None and peer_panes[0].pane_id == target
            owner.checked_command(["new-window", "-t", f"={session_name}:", "-n", "other"])
            focused = owner.checked_command(
                ["display-message", "-p", "-t", f"={session_name}:", "#{pane_id}"]
            )
            assert focused.stdout.strip() != target
            enclosing = (
                peer.checked_command(
                    ["display-message", "-p", "-t", f"={session_name}:", "#{pid},#{session_id}"]
                )
                .stdout.strip()
                .replace("$", "")
            )
            monkeypatch.setenv("TMUX", f"{peer.socket_path},{enclosing}")
            monkeypatch.setenv("TMUX_PANE", target)
            monkeypatch.setattr(controller, "persist_manifest", lambda **_: None)

            events = controller.send_prompt("literal <[Enter]>;")

            assert events[0].kind == "submitted"
            assert _wait_for_prompt(target_output) == "literal <[Enter]>;\n"
            assert not peer_output.exists()

            command = TmuxServer.command
            sent_keys: list[tuple[str, ...]] = []

            def refuse_paste(
                self: TmuxServer, args: Sequence[str], **kwargs: bool
            ) -> TmuxCommandResult:
                """Refuse the paste after loading a real buffer on the owner socket."""

                if args[0] == "paste-buffer":
                    assert self.socket_path == owner.socket_path
                    return TmuxCommandResult(tuple(args), 2, "", "")
                if args[0] == "send-keys":
                    sent_keys.append(tuple(args))
                return command(self, args, **kwargs)

            monkeypatch.setattr(TmuxServer, "command", refuse_paste)
            with pytest.raises(BackendExecutionError, match="paste-buffer.*status 2"):
                controller.send_prompt("never sent")
            assert sent_keys == []
            assert owner.checked_command(["list-buffers", "-F", "#{buffer_name}"]).stdout == ""
            assert target_output.read_text() == "literal <[Enter]>;\n"
            assert not peer_output.exists()
        finally:
            owner.command(["kill-server"])
            peer.command(["kill-server"])


def test_owned_launch_and_gateway_use_distinct_window_handles(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Keep window zero on one-based defaults and stop only the recorded auxiliary window."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for the isolated runtime test")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.delenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", raising=False)
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(runtime, "_same_session_gateway_shell_command", lambda **_: "exec sleep 30")
    with tempfile.TemporaryDirectory(prefix="houmao-gateway-tmux-") as socket_dir:
        server = TmuxServer(Path(socket_dir) / "owned.sock")
        try:
            server.start(
                ["new-session", "-d", "-s", "seed"], environment=server.native_environment()
            ).require_success()
            server.checked_command(["set-option", "-g", "base-index", "1"])
            server.checked_command(["set-option", "-g", "mouse", "off"])
            server.checked_command(["set-option", "-gw", "pane-base-index", "1"])
            with tmux_server_scope(server.socket_path):
                create_tmux_session(session_name="managed", working_directory=tmp_path)
                primary = prepare_headless_agent_window(session_name="managed", fresh_session=True)
                assert primary.window_index == "0"
                assert (
                    probe_tmux_backed_authority(
                        session_name="managed",
                        primary_window_id=primary.window_id,
                        primary_pane_id=primary.pane_id,
                    ).state
                    == "healthy"
                )
                assert (
                    server.checked_command(
                        ["show-options", "-v", "-t", "=managed:", "mouse"]
                    ).stdout.strip()
                    == "on"
                )
                assert (
                    server.checked_command(
                        ["show-environment", "-t", "=managed", "NO_COLOR"]
                    ).stdout.strip()
                    == "-NO_COLOR"
                )
                controller = SimpleNamespace(
                    launch_plan=SimpleNamespace(
                        backend="local_interactive",
                        working_directory=tmp_path,
                    ),
                )
                handle = runtime._launch_same_session_gateway_window(
                    controller=controller,
                    session_name="managed",
                    paths=gateway_paths_from_session_root(session_root=tmp_path),
                    host="127.0.0.1",
                    port=12345,
                    tui_tracking_timings=GatewayTuiTrackingTimingConfigV1(),
                )
                assert handle.window_index != "0"
                assert handle.window_id != primary.window_id
                current = GatewayCurrentInstanceV1(
                    pid=1,
                    host="127.0.0.1",
                    port=12345,
                    execution_mode="tmux_auxiliary_window",
                    tmux_window_id=handle.window_id,
                    tmux_window_index=handle.window_index,
                    tmux_pane_id=handle.pane_id,
                    managed_agent_instance_epoch=1,
                )
                assert runtime._same_session_gateway_is_alive(
                    session_name="managed", current_instance=current
                )
                server.checked_command(["select-window", "-t", primary.window_id])
                assert runtime._stop_same_session_gateway_surface(
                    session_name="managed", current_instance=current, strict=True
                )
                expected = server.observe_session("managed")
                assert expected is not None and len(expected) == 1
                assert expected[0].pane_id == primary.pane_id

                monkeypatch.setenv("HOUMAO_ENABLE_TMUX_CONFIG_INJECTION", "0")
                create_tmux_session(session_name="opt-out", working_directory=tmp_path)
                assert (
                    server.checked_command(
                        ["show-options", "-Av", "-t", "=opt-out:", "mouse"]
                    ).stdout.strip()
                    == "off"
                )

                with pytest.raises(TmuxCommandError, match="Timed out"):
                    server.wait_for("unpublished-signal", timeout_seconds=0.05)
                notification = shlex.join(server.signal_invocation("worker-complete"))
                server.checked_command(
                    ["new-window", "-d", "-t", "=managed:", f"sleep 0.1; {notification}"]
                )
                server.wait_for("worker-complete", timeout_seconds=3).require_success()
        finally:
            server.command(["kill-server"])
