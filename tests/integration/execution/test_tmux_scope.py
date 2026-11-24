"""Real isolated-server routing for same-named execution-context sessions."""

from pathlib import Path
from dataclasses import replace
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    create_tmux_session,
    has_tmux_session,
    kill_tmux_session,
    list_tmux_sessions,
    publish_tmux_launch_environment,
    read_tmux_session_environment_value,
    set_tmux_session_environment,
)
from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.realm_controller.runtime import _resolve_managed_launch_environment
from houmao.agents.launch_env import owner_launch_baseline, owner_tmux_launch_environment
from houmao.execution import tmux_selection
from houmao.execution.tmux import (
    TmuxCommandResult,
    TmuxObservationUnavailable,
    TmuxServer,
    tmux_command,
    tmux_server_scope,
)
from houmao.execution.tmux_selection import TmuxServerSelector, resolve_tmux_server


@pytest.fixture
def isolated_launch_tmux(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Test managed launch on a socket owned exclusively by this test."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for managed launch integration")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    with tempfile.TemporaryDirectory(prefix="houmao-launch-tmux-") as directory:
        with tmux_server_scope(Path(directory) / "owned.sock"):
            try:
                yield
            finally:
                tmux_command(["kill-server"])


def _managed_tui_plan(tmp_path: Path, *, args: list[str]) -> LaunchPlan:
    """Return a resolved fixture provider with one private env binding."""

    public = {**owner_launch_baseline(os.environ), "http_proxy": "http://127.0.0.1:7990"}
    return LaunchPlan(
        backend="local_interactive",
        tool="codex",
        executable="/bin/sh",
        args=args,
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={**public, "FIXTURE_PROVIDER_TOKEN": "synthetic-launch-secret"},
        env_var_names=list(public),
        role_injection=RoleInjectionPlan(method="cao_profile", role_name="fixture", prompt=""),
        public_env=public,
        private_env_var_names=frozenset({"FIXTURE_PROVIDER_TOKEN"}),
    )


def test_managed_tmux_launch_masks_private_and_expired_keys(
    isolated_launch_tmux: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Inspect both fresh server startup and a pane started after reconciliation."""

    monkeypatch.setenv("FIXTURE_PROVIDER_TOKEN", "ambient-secret")
    plan = _managed_tui_plan(tmp_path, args=[])
    create_tmux_session(session_name="owned", working_directory=tmp_path, launch_plan=plan)
    assert tmux_command(["show-environment", "-g", "FIXTURE_PROVIDER_TOKEN"]).returncode != 0
    assert (
        tmux_command(["set-environment", "-g", "FIXTURE_PROVIDER_TOKEN", "prior-server"]).returncode
        == 0
    )
    assert tmux_command(["set-environment", "-g", "EXPIRED", "prior-server"]).returncode == 0
    set_tmux_session_environment(session_name="owned", env_vars={"USER_SETTING": "preserved"})
    assert plan.public_env is not None
    publish_tmux_launch_environment(
        session_name="owned",
        launch_plan=replace(
            plan,
            public_env={**plan.public_env, "TERMINAL_SEMICOLON": "literal;"},
            previous_public_env_var_names=frozenset({"EXPIRED"}),
        ),
    )
    result_path = tmp_path / "pane-env"
    command = 'printf "%s\\n" "${FIXTURE_PROVIDER_TOKEN-unset}" "${EXPIRED-unset}" '
    command += f'"$USER_SETTING" "$TERMINAL_SEMICOLON" >{shlex.quote(str(result_path))}'
    launched = tmux_command(["new-window", "-d", "-t", "owned:", command])
    assert launched.returncode == 0, launched.stderr
    _wait_for_launch_result(result_path)
    assert result_path.read_text().splitlines() == ["unset", "unset", "preserved", "literal;"]


def test_managed_tui_starts_with_published_and_private_values(
    isolated_launch_tmux: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observe the primary pane's actual spawn environment and pane command."""

    result_path = tmp_path / "tui-env"
    monkeypatch.setenv("UNDECLARED_LAUNCH_SETTING", "controller-only")
    command = 'printf "%s\\n" "$http_proxy" "$FIXTURE_PROVIDER_TOKEN" '
    command += f'"${{UNDECLARED_LAUNCH_SETTING-unset}}" >{shlex.quote(str(result_path))}'

    def wait_for_fixture(self: LocalInteractiveSession, **_kwargs: float) -> None:
        """Treat the fixture result as native provider readiness."""

        _wait_for_launch_result(result_path)

    monkeypatch.setattr(LocalInteractiveSession, "_wait_for_provider_tui", wait_for_fixture)
    LocalInteractiveSession(
        launch_plan=_managed_tui_plan(tmp_path, args=["-c", command]),
        role_name="fixture",
        session_manifest_path=tmp_path / "session.json",
        tmux_session_name="owned",
    )
    assert read_tmux_session_environment_value(
        session_name="owned", variable_name="http_proxy"
    ) == ("http://127.0.0.1:7990")
    assert result_path.read_text().splitlines() == [
        "http://127.0.0.1:7990",
        "synthetic-launch-secret",
        "unset",
    ]
    pane_command = tmux_command(
        ["display-message", "-p", "-t", "owned:0.0", "#{pane_start_command}"]
    )
    assert pane_command.returncode == 0
    assert "synthetic-launch-secret" not in pane_command.stdout
    assert (
        read_tmux_session_environment_value(
            session_name="owned", variable_name="FIXTURE_PROVIDER_TOKEN"
        )
        is None
    )


def test_managed_kimi_start_and_relaunch_mask_environment_per_tmux_session(
    isolated_launch_tmux: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observe config-owned names and private credentials around both provider starts."""

    config_names = ("KIMI_MODEL_NAME", "KIMI_MODEL_THINKING_EFFORT", "KIMI_DISABLE_TELEMETRY")
    private_names = ("KIMI_MODEL_API_KEY", "KIMI_MODEL_TEMPERATURE")
    for name in (*config_names, *private_names):
        monkeypatch.setenv(name, "ambient")
    TmuxServer().start(
        ["new-session", "-d", "-s", "peer"], environment=os.environ
    ).require_success()
    for name in (*config_names, *private_names):
        assert tmux_command(["set-environment", "-g", name, "server-global"]).returncode == 0
        set_tmux_session_environment(session_name="peer", env_vars={name: "peer-value"})

    provider_path = tmp_path / "kimi-provider"
    env_fields = " ".join(f'"${{{name}-unset}}"' for name in (*config_names, *private_names))

    def command(path: Path) -> str:
        """Capture the fixture process's real environment inside the selected pane."""

        return f'printf "%s\\n" {env_fields} >{shlex.quote(str(path))}'

    def wait_for_fixture(self: LocalInteractiveSession, **_kwargs: float) -> None:
        """Wait until the provider wrapper has handed over the environment."""

        _wait_for_launch_result(provider_path)

    monkeypatch.setattr(LocalInteractiveSession, "_wait_for_provider_tui", wait_for_fixture)
    source_plan = replace(
        _managed_tui_plan(tmp_path, args=["-c", command(provider_path)]),
        tool="kimi",
        home_env_var="KIMI_CODE_HOME",
        env={"KIMI_MODEL_API_KEY": "selected-test-key", "KIMI_MODEL_TEMPERATURE": "0.25"},
        env_var_names=list(private_names),
        public_env=None,
        private_env_var_names=frozenset(),
    )

    def resolve(previous_keys: frozenset[str] = frozenset()) -> LaunchPlan:
        """Apply ordinary managed provider environment preparation."""

        return _resolve_managed_launch_environment(
            source_plan,
            root_context={},
            agent_id=None,
            manifest_path=tmp_path / "session.json",
            agent_def_dir=None,
            previous_keys=previous_keys,
        )

    initial_plan = resolve()
    session = LocalInteractiveSession(
        launch_plan=initial_plan,
        role_name="fixture",
        session_manifest_path=tmp_path / "session.json",
        tmux_session_name="owned",
    )
    for generation in ("fresh", "relaunched"):
        if generation == "relaunched":
            provider_path.unlink()
            set_tmux_session_environment(
                session_name="owned", env_vars={name: "stale-pane-value" for name in config_names}
            )
            session.update_launch_plan(resolve(initial_plan.previous_public_env_var_names))
            assert session.relaunch().status == "ok"
        assert provider_path.read_text().splitlines() == [
            *("unset" for _ in config_names),
            "selected-test-key",
            "0.25",
        ]
        pane_path = tmp_path / generation
        result = tmux_command(["new-window", "-d", "-t", "owned:", command(pane_path)])
        assert result.returncode == 0, result.stderr
        _wait_for_launch_result(pane_path)
        assert pane_path.read_text().splitlines() == ["unset"] * (
            len(config_names) + len(private_names)
        )
        for name in (*config_names, *private_names):
            global_binding = tmux_command(["show-environment", "-g", name])
            assert global_binding.stdout.strip() == f"{name}=server-global"
            assert (
                read_tmux_session_environment_value(session_name="peer", variable_name=name)
                == "peer-value"
            )
        pane = tmux_command(["display-message", "-p", "-t", "owned:0.0", "#{pane_start_command}"])
        assert pane.returncode == 0
        assert "selected-test-key" not in pane.stdout


def test_managed_tui_aborts_on_tmux_publication_error(
    isolated_launch_tmux: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Suppress tmux diagnostics that echo values and clean the failed owned session."""

    command = TmuxServer.command

    def fail_publication(
        self: TmuxServer, args: list[str], *, sensitive: bool = False, no_start: bool = False
    ) -> TmuxCommandResult:
        """Return a value-bearing diagnostic from the failed publication command."""

        if args[:1] == ["set-environment"] and args[-2:-1] == ["http_proxy"]:
            return TmuxCommandResult(tuple(args), 1, "", "tmux rejected value fixture-token")
        return command(self, args, sensitive=sensitive, no_start=no_start)

    monkeypatch.setattr(TmuxServer, "command", fail_publication)
    marker = tmp_path / "started"
    plan = _managed_tui_plan(tmp_path, args=["-c", f"touch {shlex.quote(str(marker))}"])
    with pytest.raises(
        BackendExecutionError, match="Failed to publish tmux.*http_proxy"
    ) as failure:
        LocalInteractiveSession(
            launch_plan=plan,
            role_name="fixture",
            session_manifest_path=tmp_path / "session.json",
            tmux_session_name="owned",
        )
    assert "fixture-token" not in str(failure.value)
    assert not marker.exists()
    assert has_tmux_session(session_name="owned").returncode != 0


def _wait_for_launch_result(path: Path) -> None:
    """Wait for a pane fixture to complete its single output write."""

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.is_file() and path.stat().st_size:
            return
        time.sleep(0.02)
    pytest.fail(f"Fixture provider did not write {path.name}")


def test_same_session_names_route_to_recorded_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    """A selected agent can stop while sibling and other-server sessions survive."""

    executable = shutil.which("tmux")
    if executable is None:
        pytest.skip("tmux is required for execution-context routing integration")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    clean_env = {
        key: value for key, value in os.environ.items() if key not in {"TMUX", "TMUX_PANE"}
    }
    with tempfile.TemporaryDirectory(prefix="houmao-execution-tmux-") as directory:
        sockets = [Path(directory) / f"owner-{index}.sock" for index in range(2)]
        try:
            primary_ids: list[tuple[str | None, str, str]] = []
            for index, socket in enumerate(sockets):
                with tmux_server_scope(socket):
                    server = TmuxServer()
                    started = server.start(
                        [
                            "-f",
                            "/dev/null",
                            "new-session",
                            "-d",
                            "-s",
                            "same-name",
                            "-n",
                            "primary",
                        ],
                        environment=clean_env,
                    )
                    assert started.returncode == 0, started.stderr
                    server.start(
                        ["new-session", "-d", "-s", "sibling"], environment=clean_env
                    ).require_success()
                    server.start(
                        ["new-session", "-d", "-s", "same-name-other"], environment=clean_env
                    ).require_success()
                    server.checked_command(
                        ["new-window", "-d", "-t", "=same-name:", "-n", f"auxiliary-{index}"]
                    )
                    panes = server.observe_session("same-name")
                    assert panes is not None
                    assert {pane.window_name for pane in panes} == {"primary", f"auxiliary-{index}"}
                    primary = next(pane for pane in panes if pane.window_name == "primary")
                    primary_ids.append((primary.session_id, primary.window_id, primary.pane_id))
                    set_tmux_session_environment(
                        session_name="same-name", env_vars={"HOUMAO_TEST_OWNER": str(index)}
                    )
            assert primary_ids[0] == primary_ids[1]
            # Simulate an operator enclosed in the other server. Explicit scope
            # must still select owner 0 and remove inherited native selectors.
            monkeypatch.setenv("TMUX", f"{sockets[1]},123,0")
            monkeypatch.setenv("TMUX_PANE", "%0")
            with tmux_server_scope(sockets[0]):
                server = TmuxServer()
                panes = server.observe_session("same-name")
                assert panes is not None
                assert {pane.window_name for pane in panes} == {"primary", "auxiliary-0"}
                assert server.observe_session("same") is None
                assert (
                    read_tmux_session_environment_value(
                        session_name="same-name", variable_name="HOUMAO_TEST_OWNER"
                    )
                    == "0"
                )
                assert list_tmux_sessions() == {"same-name", "same-name-other", "sibling"}
                kill_tmux_session(session_name="same-name")
                assert has_tmux_session(session_name="same-name").returncode == 1
                assert server.observe_session("same-name") is None
                assert has_tmux_session(session_name="sibling").returncode == 0
                with pytest.raises(TmuxCommandError):
                    kill_tmux_session(session_name="same-name")
                assert has_tmux_session(session_name="same-name-other").returncode == 0
            with tmux_server_scope(sockets[1]):
                assert (
                    read_tmux_session_environment_value(
                        session_name="same-name", variable_name="HOUMAO_TEST_OWNER"
                    )
                    == "1"
                )
                assert list_tmux_sessions() == {"same-name", "same-name-other", "sibling"}
            assert os.environ["TMUX"] == f"{sockets[1]},123,0"
            assert os.environ["TMUX_PANE"] == "%0"
            inaccessible = TmuxServer(Path(directory) / "inaccessible.sock")
            assert inaccessible.list_sessions(allow_missing_server=True) == set()
            with pytest.raises(TmuxObservationUnavailable):
                inaccessible.observe_session("same-name")
        finally:
            # These two sockets were created exclusively by this fixture. Never
            # clean up an inherited/default server or a non-fixture session.
            for socket in sockets:
                subprocess.run(
                    [executable, "-S", str(socket), "kill-server"],
                    env=clean_env,
                    capture_output=True,
                    check=False,
                    timeout=10,
                )


def test_checked_pane_input_preserves_bytes_and_explicit_enter(
    isolated_launch_tmux: None, tmp_path: Path
) -> None:
    """Deliver literal input and bracketed paste to a real isolated raw-mode pane."""

    ready, received = tmp_path / "ready", tmp_path / "received"
    shell = (
        "stty -echo -icanon -icrnl min 1 time 0 && "
        "printf '\\033[?2004h' && "
        f"touch {shlex.quote(str(ready))} && "
        f"exec cat > {shlex.quote(str(received))}"
    )
    server = TmuxServer()
    server.start(
        ["-f", "/dev/null", "new-session", "-d", "-s", "input", shell],
        environment=owner_launch_baseline(os.environ),
    ).require_success()
    deadline = time.monotonic() + 5
    while (not ready.exists() or not received.exists()) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert ready.exists() and received.exists()

    panes = server.observe_session("input")
    assert panes is not None and len(panes) == 1
    pane_id = panes[0].pane_id
    literal = "-literal;"
    prompt = "pasted; -- token"
    server.send_keys(pane_id, literal, literal=True)
    server.load_buffer("prompt", prompt)
    server.paste_buffer("prompt", pane_id)
    server.delete_buffer("prompt")
    assert server.command(["show-buffer", "-b", "prompt"]).returncode != 0

    expected = literal.encode() + b"\x1b[200~" + prompt.encode() + b"\x1b[201~"
    deadline = time.monotonic() + 5
    while received.stat().st_size < len(expected) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert received.read_bytes() == expected

    server.send_keys(pane_id, "Enter")
    deadline = time.monotonic() + 5
    while received.stat().st_size == len(expected) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert received.read_bytes() == expected + b"\r"
    assert server.capture_pane(pane_id, history=True, escape_sequences=True) == ""
    exact = server.capture_exact(["capture-pane", "-p", "-t", pane_id])
    exact.require_success()
    assert panes[0].pane_height is not None
    assert exact.stdout == "\n" * panes[0].pane_height


@pytest.mark.parametrize("changed_environment", [False, True])
def test_cold_default_server_creates_owned_native_socket_directory(
    monkeypatch: pytest.MonkeyPatch, changed_environment: bool
) -> None:
    """Initialize the captured native default even after the caller's root changes."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for execution-context routing integration")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    with tempfile.TemporaryDirectory(prefix="houmao-default-tmux-") as directory:
        root = Path(directory).resolve()
        monkeypatch.setenv("TMUX_TMPDIR", directory)
        resolved = resolve_tmux_server(TmuxServerSelector(server="user-default"))
        server = TmuxServer(resolved.socket_path, allow_start=resolved.allow_start)
        socket = Path(server.socket_path)
        assert socket == root / f"tmux-{os.getuid()}" / "default"
        other_root = root / "other"
        other_root.mkdir()
        if changed_environment:
            monkeypatch.setenv("TMUX_TMPDIR", str(other_root))
        assert not socket.parent.exists()
        try:
            server.start(
                ["-f", "/dev/null", "new-session", "-d", "-s", "owned"],
                environment=os.environ,
            ).require_success()
            assert socket.is_socket()
            assert server.list_sessions() == {"owned"}
            assert list(other_root.iterdir()) == []
        finally:
            server.command(["kill-server"], no_start=True)


def test_houmao_default_starts_once_and_keeps_sibling_sessions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two cold launches start their sessions at the same published private socket."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for execution-context routing integration")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    with tempfile.TemporaryDirectory(prefix="houmao-shared-tmx-") as directory:
        namespace = Path(directory) / "sockets"
        monkeypatch.setattr(tmux_selection, "_managed_socket_directory", lambda uid: namespace)
        selector = TmuxServerSelector(server="houmao-default")
        first = resolve_tmux_server(selector, registry_root=tmp_path / "registry-1")
        second = resolve_tmux_server(selector, registry_root=tmp_path / "registry-2")
        assert first == second
        socket = Path(first.socket_path)
        assert not socket.exists()

        barrier = Barrier(2, timeout=10)

        def start(session: str) -> None:
            """Launch concurrently on the one bound server using a clean configuration."""

            with tmux_server_scope(socket, allow_start=first.allow_start):
                server = TmuxServer()
                barrier.wait()
                server.start(
                    ["-f", "/dev/null", "new-session", "-d", "-s", session],
                    environment=owner_tmux_launch_environment(os.environ),
                ).require_success()

        server = TmuxServer(socket)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(start, ("first", "second")))
            assert server.list_sessions() == {"first", "second"}
            with tmux_server_scope(socket):
                kill_tmux_session(session_name="first")
            assert server.list_sessions() == {"second"}
            assert resolve_tmux_server(selector, registry_root=tmp_path / "registry-1") == first
        finally:
            server.command(["kill-server"], no_start=True)


def test_existing_only_session_start_does_not_revive_lost_server(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The common session creator enforces existing-only startup after preflight."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for execution-context routing integration")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    with tempfile.TemporaryDirectory(prefix="houmao-existing-tmx-") as directory:
        socket = Path(directory) / "connect-only.sock"
        server = TmuxServer(socket)
        selector = TmuxServerSelector(server="socket", socket_path=str(socket))
        try:
            server.start(
                ["-f", "/dev/null", "new-session", "-d", "-s", "first"],
                environment=owner_tmux_launch_environment(os.environ),
            ).require_success()
            selected = resolve_tmux_server(selector)
            assert not selected.allow_start
            with tmux_server_scope(selected.socket_path, allow_start=selected.allow_start):
                create_tmux_session(session_name="connected", working_directory=tmp_path)
                assert server.list_sessions() == {"first", "connected"}
                kill_tmux_session(session_name="connected")
                kill_tmux_session(session_name="first")

                with pytest.raises(TmuxObservationUnavailable):
                    server.list_sessions()
                with pytest.raises(TmuxCommandError, match="connect-only.sock"):
                    create_tmux_session(session_name="late", working_directory=tmp_path)
                with pytest.raises(TmuxObservationUnavailable):
                    server.list_sessions()
        finally:
            server.command(["kill-server"], no_start=True)
