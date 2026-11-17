"""Real isolated-server routing for same-named execution-context sessions."""

from pathlib import Path
import os
import shutil
import subprocess
import tempfile

import pytest

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    has_tmux_session,
    kill_tmux_session,
    list_tmux_sessions,
    read_tmux_session_environment_value,
    run_tmux,
    set_tmux_session_environment,
)
from houmao.execution.tmux import tmux_server_scope


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
