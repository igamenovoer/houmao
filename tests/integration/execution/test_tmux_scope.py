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

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    create_tmux_session,
    has_tmux_session,
    kill_tmux_session,
    list_tmux_sessions,
    publish_tmux_launch_environment,
    read_tmux_session_environment_value,
    run_tmux,
    set_tmux_session_environment,
)
from houmao.agents.realm_controller.backends.local_interactive import LocalInteractiveSession
from houmao.agents.realm_controller.backends import tmux_runtime
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.agents.launch_env import owner_launch_baseline
from houmao.execution.tmux import tmux_server_scope


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
                run_tmux(["kill-server"])


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
    assert run_tmux(["show-environment", "-g", "FIXTURE_PROVIDER_TOKEN"]).returncode != 0
    assert (
        run_tmux(["set-environment", "-g", "FIXTURE_PROVIDER_TOKEN", "prior-server"]).returncode
        == 0
    )
    assert run_tmux(["set-environment", "-g", "EXPIRED", "prior-server"]).returncode == 0
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
    launched = run_tmux(["new-window", "-d", "-t", "owned:", command])
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
    pane_command = run_tmux(["display-message", "-p", "-t", "owned:0.0", "#{pane_start_command}"])
    assert pane_command.returncode == 0
    assert "synthetic-launch-secret" not in pane_command.stdout
    assert (
        read_tmux_session_environment_value(
            session_name="owned", variable_name="FIXTURE_PROVIDER_TOKEN"
        )
        is None
    )


def test_managed_tui_aborts_on_tmux_publication_error(
    isolated_launch_tmux: None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Suppress tmux diagnostics that echo values and clean the failed owned session."""

    def fail_publication(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        """Return a value-bearing diagnostic from the failed publication command."""

        if args[:1] == ["set-environment"] and args[-2:-1] == ["http_proxy"]:
            return subprocess.CompletedProcess(args, 1, "", "tmux rejected value fixture-token")
        return run_tmux(args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(tmux_runtime, "run_tmux", fail_publication)
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
            for index, socket in enumerate(sockets):
                with tmux_server_scope(socket):
                    started = run_tmux(["-f", "/dev/null", "new-session", "-d", "-s", "same-name"])
                    assert started.returncode == 0, started.stderr
                    assert run_tmux(["new-session", "-d", "-s", "sibling"]).returncode == 0
                    assert run_tmux(["new-session", "-d", "-s", "same-name-other"]).returncode == 0
                    set_tmux_session_environment(
                        session_name="same-name", env_vars={"HOUMAO_TEST_OWNER": str(index)}
                    )
            # Simulate an operator enclosed in the other server. Explicit scope
            # must still select owner 0 and remove inherited native selectors.
            monkeypatch.setenv("TMUX", f"{sockets[1]},123,0")
            monkeypatch.setenv("TMUX_PANE", "%0")
            with tmux_server_scope(sockets[0]):
                assert (
                    read_tmux_session_environment_value(
                        session_name="same-name", variable_name="HOUMAO_TEST_OWNER"
                    )
                    == "0"
                )
                assert list_tmux_sessions() == {"same-name", "same-name-other", "sibling"}
                kill_tmux_session(session_name="same-name")
                assert has_tmux_session(session_name="same-name").returncode == 1
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
