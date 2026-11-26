"""Exercise project birth and revival on explicitly isolated tmux servers."""

from __future__ import annotations

from collections.abc import Iterator
from io import BytesIO
import json
import os
from pathlib import Path
import pwd
import shutil
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from typing import Any

from click.testing import CliRunner, Result
import pytest

from houmao.agents.realm_controller.runtime import RuntimeSessionController
from houmao.execution import tmux_selection
from houmao.execution.models import (
    ControllerScopeV1,
    ExecutionProfileV1,
    ExecutionRequestV1,
    ExecutionResponseV1,
)
from houmao.execution.owner import OwnerPolicyV1, serve_stdio
from houmao.execution.protocol import decode_response, encode_request
from houmao.execution.tmux import TmuxServer, tmux_server_scope
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.service import PassiveServerService
from houmao.srv_ctrl.commands.main import cli


def _invoke(*args: str) -> dict[str, Any]:
    """Run a manager command and decode its JSON object."""

    result = CliRunner().invoke(cli, ["--print-json", *args])
    assert result.exit_code == 0, (result.output, result.exception)
    payload, _ = json.JSONDecoder().raw_decode(result.output.lstrip())
    assert isinstance(payload, dict)
    return payload


def _launch(*args: str) -> Result:
    """Invoke the selected profile for error-path assertions."""

    return CliRunner().invoke(cli, ["project", "agents", "launch", "--profile", "review", *args])


def _wait_for_server_exit(socket: Path) -> None:
    """Allow the explicitly addressed tmux process to exit after its final session."""

    server = TmuxServer(socket, allow_start=False)
    deadline = monotonic() + 4
    while monotonic() < deadline:
        result = server.command(["list-sessions"])
        if result.returncode and (
            "no server running" in result.stderr or "No such file or directory" in result.stderr
        ):
            return
        sleep(0.05)
    raise AssertionError(f"Expected the isolated server at {socket} to exit: {result}")


@pytest.fixture
def socket_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Initialize a synthetic Codex project and a short, private tmux namespace."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required")
    for name in ("TMUX", "TMUX_PANE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOUMAO_GLOBAL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("HOUMAO_GLOBAL_RUNTIME_DIR", str(tmp_path / "runtime"))
    monkeypatch.chdir(tmp_path)
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\nprintf '%s\\n' 'codex-cli 0.167.2'\n", encoding="utf-8")
    executable.chmod(0o700)
    auth = tmp_path / "auth.json"
    auth.write_text('{"logged_in": true}\n', encoding="utf-8")
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ['PATH']}")
    _invoke("project", "init")
    _invoke(
        "project",
        "specialist",
        "create",
        "--name",
        "researcher",
        "--tool",
        "codex",
        "--api-key",
        "synthetic-key",
        "--codex-auth-json",
        str(auth),
        "--system-prompt",
        "Review the supplied inputs.",
    )
    _invoke(
        "project",
        "profile",
        "create",
        "--name",
        "review",
        "--specialist",
        "researcher",
        "--agent-name",
        "reviewer",
        "--mode",
        "headless",
        "--prompt-mode",
        "unattended",
        "--no-gateway",
        "--tmux-server",
        "new",
    )
    with TemporaryDirectory(prefix="hm-prof-") as directory:
        base = Path(directory)
        monkeypatch.setattr(tmux_selection, "_managed_socket_directory", lambda _uid: base)
        monkeypatch.setenv("TMUX_TMPDIR", str(base))
        try:
            yield base
        finally:
            for socket in base.rglob("*"):
                if socket.is_socket():
                    TmuxServer(socket).command(["kill-server"], no_start=True)


def _start_sibling(socket: Path, name: str) -> TmuxServer:
    """Create a test-owned session on an explicitly addressed socket."""

    server = TmuxServer(socket)
    server.start(
        ["-f", "/dev/null", "new-session", "-d", "-s", name], environment=os.environ
    ).require_success()
    return server


@pytest.mark.parametrize("mode", ("tui", "headless"))
def test_native_birth_is_discoverable_until_stop(socket_root: Path, mode: str) -> None:
    """Discover a real isolated tmux launch and drop it after manager stop."""

    project = Path.cwd()
    (project / "codex").write_text(
        "#!/bin/bash\n"
        'case "$1" in\n'
        "  --version|-V) printf '%s\\n' 'codex-cli 0.167.2';;\n"
        "  *) exec -a codex sleep 30;;\n"
        "esac\n",
        encoding="utf-8",
    )
    service = PassiveServerService(
        PassiveServerConfig(runtime_root=project / "runtime", registry_root=project / "registry")
    )

    start = _invoke("project", "agents", "launch", "--profile", "review", "--mode", mode)
    binding = json.loads(Path(start["manifest_path"]).read_text())["tmux"]
    assert Path(binding["socket_path"]).is_relative_to(socket_root)
    assert binding["session_name"] in TmuxServer(binding["socket_path"]).list_sessions()
    agent_id = start["agent_id"]
    assert [agent["agent_id"] for agent in _invoke("agents", "global", "list")["agents"]] == [
        agent_id
    ]
    service.m_discovery.scan_once()
    assert [(agent.agent_id, agent.mode) for agent in service.list_agents().agents] == [
        (agent_id, mode)
    ]

    assert _invoke("agents", "single", "--agent-id", agent_id, "stop")["success"]
    assert _invoke("agents", "global", "list")["agents"] == []
    service.m_discovery.scan_once()
    assert service.list_agents().agents == []


def test_manager_reports_required_startup_failure_and_can_retry(
    socket_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass a required startup error through the CLI after undoing the exact birth."""

    socket = socket_root / "manager-required.sock"
    server = _start_sibling(socket, "keeper")
    args = (
        "--session-name",
        "manager-failure",
        "--tmux-server",
        "socket",
        "--tmux-socket-path",
        str(socket),
    )

    def fail_publication(self: RuntimeSessionController, **kwargs: object) -> None:
        """Fail after the new runtime began using the shared test socket."""

        assert "manager-failure" in server.list_sessions()
        raise OSError("required gateway publication failed")

    with monkeypatch.context() as patch:
        patch.setattr(RuntimeSessionController, "ensure_gateway_capability", fail_publication)
        result = _launch(*args)
    assert result.exit_code == 1
    assert "required gateway publication failed" in result.output
    assert server.list_sessions() == {"keeper"}
    assert _invoke("agents", "global", "list")["agents"] == []

    start = _invoke("project", "agents", "launch", "--profile", "review", *args)
    assert _invoke("agents", "single", "--agent-id", start["agent_id"], "stop")["success"]
    assert server.list_sessions() == {"keeper"}


def test_manager_optional_gateway_failure_keeps_native_runtime_usable(
    socket_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Report the partial result while allowing normal lifecycle follow-up."""

    def fail_attach(self: RuntimeSessionController, **kwargs: object) -> None:
        """Fail only the optional attach after required startup has committed."""

        raise OSError("optional gateway listener unavailable")

    monkeypatch.setattr(RuntimeSessionController, "attach_gateway", fail_attach)
    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "project",
            "agents",
            "launch",
            "--profile",
            "review",
            "--gateway-port",
            "41923",
        ],
    )
    assert result.exit_code == 2, (result.output, result.exception)
    report = json.loads(result.output)
    assert report["gateway_auto_attach_error"] == "optional gateway listener unavailable"
    assert Path(report["manifest_path"]).is_file()
    assert [agent["agent_id"] for agent in _invoke("agents", "global", "list")["agents"]] == [
        report["agent_id"]
    ]
    assert _invoke("agents", "single", "--agent-id", report["agent_id"], "stop")["success"]


def test_stdio_owner_launches_and_controls_on_its_recorded_socket(socket_root: Path) -> None:
    """Run one real managed lifecycle through the private owner v1 entrypoint."""

    socket = socket_root / "stdio.sock"
    server = _start_sibling(socket, "keeper")
    project = Path.cwd()
    policy_path = project / "owner-policy.json"
    profile = ExecutionProfileV1(
        name="fixture",
        transport="local",
        account=pwd.getpwuid(os.geteuid()).pw_name,
        entrypoint="/usr/bin/houmao-mgr",
        policy_path=str(policy_path),
        project_root=str(project),
        environment={"PATH": os.environ["PATH"]},
    )
    policy = OwnerPolicyV1(
        profile=profile,
        controller=ControllerScopeV1(
            controller_id="isolated-operator",
            authority="local_uid",
            operations=("launch", "describe", "state", "stop"),
            project_roots=(str(project),),
        ),
        uid=os.geteuid(),
        gid=os.getegid(),
        registry_root=str(project / "delegated-registry"),
        runtime_root=str(project / "delegated-runtime"),
        tmux_socket=str(socket),
    )
    policy_path.write_text(policy.model_dump_json(), encoding="utf-8")
    policy_path.chmod(0o600)

    def request_owner(request: ExecutionRequestV1) -> ExecutionResponseV1:
        """Send and verify one bounded, correlated v1 message."""

        output = BytesIO()
        status = serve_stdio(
            policy_path, input_stream=BytesIO(encode_request(request)), output_stream=output
        )
        response = decode_response(output.getvalue())
        assert status == 0 and response.outcome == "completed", response.model_dump()
        assert response.request_id == request.request_id and response.admitted
        return response

    born = request_owner(
        ExecutionRequestV1(
            operation="launch",
            arguments={
                "profile": "review",
                "tmux_server": "socket",
                "tmux_socket_path": str(socket),
                "session_name": "owner-birth",
            },
        )
    )
    assert born.binding is not None and born.binding.tmux_socket == str(socket)
    assert born.result["mode"] == "headless"
    assert born.result["backend"] == "codex_headless"
    assert server.list_sessions() == {"keeper", "owner-birth"}
    agent_id = born.result["agent_id"]
    assert isinstance(agent_id, str)
    selected = request_owner(
        ExecutionRequestV1(
            operation="describe",
            agent_id=agent_id,
            expected_binding=born.binding,
        )
    )
    generation = selected.result["generation_id"]
    assert isinstance(generation, str)
    state = request_owner(
        ExecutionRequestV1(
            operation="state",
            agent_id=agent_id,
            expected_binding=born.binding,
            generation_id=generation,
        )
    )
    assert state.result["identity"]["agent_id"] == agent_id
    assert state.result["identity"]["transport"] == "headless"
    assert [diagnostic["kind"] for diagnostic in state.result["diagnostics"]] == [
        "headless_admission_unverified"
    ]
    stopped = request_owner(
        ExecutionRequestV1(
            operation="stop",
            agent_id=agent_id,
            expected_binding=born.binding,
            generation_id=generation,
        )
    )
    assert stopped.result["success"] is True
    assert server.list_sessions() == {"keeper"}


def test_stopped_relaunch_reuses_new_socket_after_profile_edit(socket_root: Path) -> None:
    """Saved socket routing survives a change in profile and the enclosing scope."""

    session_name = "overlapping-session"
    sibling = _start_sibling(socket_root / "sibling.sock", session_name)
    with tmux_server_scope(sibling.socket_path):
        launch = _invoke(
            "project", "agents", "launch", "--profile", "review", "--session-name", session_name
        )
        manifest = Path(launch["manifest_path"])
        binding = json.loads(manifest.read_text())["tmux"]
        socket_path = Path(binding["socket_path"])
        assert socket_path.is_relative_to(socket_root)
        assert str(socket_path) != sibling.socket_path
        assert binding["server_allow_start"] is True
        selector = ("agents", "single", "--agent-id", launch["agent_id"])
        result = _launch(
            "--agent-id",
            launch["agent_id"],
            "--force",
            "clean",
            "--tmux-server",
            "socket",
            "--tmux-socket-path",
            str(socket_root / "missing.sock"),
        )
        assert result.exit_code != 0
        assert "missing.sock" in result.output
        assert TmuxServer(socket_path).list_sessions() == {session_name}
        TmuxServer(socket_path).checked_command(["set-option", "-s", "exit-empty", "on"])
        assert _invoke(*selector, "stop")["success"]
        _wait_for_server_exit(socket_path)
        assert sibling.list_sessions() == {session_name}
        _invoke(
            "project",
            "profile",
            "set",
            "--name",
            "review",
            "--tmux-server",
            "socket",
            "--tmux-socket-path",
            sibling.socket_path,
        )
        assert _invoke(*selector, "relaunch")["success"]
        relaunched_binding = json.loads(manifest.read_text())["tmux"]
        assert relaunched_binding["socket_path"] == str(socket_path)
        assert TmuxServer(socket_path).list_sessions() == {relaunched_binding["session_name"]}
        assert sibling.list_sessions() == {session_name}


def test_existing_only_wins_one_birth_and_cannot_restart_server(socket_root: Path) -> None:
    """Precedence and force safety hold on an existing-only server."""

    socket = socket_root / "existing.sock"
    server = _start_sibling(socket, "keeper")
    launch = _invoke(
        "project",
        "agents",
        "launch",
        "--profile",
        "review",
        "--session-name",
        "owned",
        "--tmux-server",
        "socket",
        "--tmux-socket-path",
        str(socket),
    )
    manifest = Path(launch["manifest_path"])
    binding = json.loads(manifest.read_text())["tmux"]
    assert binding["socket_path"] == str(socket)
    assert binding["server_allow_start"] is False
    profile = _invoke("project", "profile", "get", "--name", "review")
    assert profile["defaults"]["posture"]["tmux"]["server"] == "new"
    server.checked_command(["kill-session", "-t", "=keeper"])
    result = _launch(
        "--agent-id",
        launch["agent_id"],
        "--force",
        "clean",
        "--tmux-server",
        "socket",
        "--tmux-socket-path",
        str(socket),
    )
    assert result.exit_code != 0
    assert "would stop the existing-only tmux server" in result.output
    assert server.list_sessions() == {"owned"}

    selector = ("agents", "single", "--agent-id", launch["agent_id"])
    assert _invoke(*selector, "stop")["success"]
    _wait_for_server_exit(socket)
    revived = CliRunner().invoke(cli, ["--print-json", *selector, "relaunch"])
    assert "startup" in revived.output or "unavailable" in revived.output
    _wait_for_server_exit(socket)
    persisted = json.loads(manifest.read_text())["tmux"]
    assert persisted["socket_path"] == str(socket)
    assert persisted["server_allow_start"] is False
