"""Own one native DSH Web process while keeping startup credentials off its console."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time
from typing import Any

from houmao.agents.realm_controller.agent_identity import (
    SELF_TMUX_SESSION_ENV_VAR,
    SELF_TMUX_SOCKET_ENV_VAR,
)
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.backends.dsh_acp_connection import _read_process_lineage
from houmao.agents.realm_controller.backends.dsh_acp_driver import _write_private_json
from houmao.execution.tmux import capture_tmux_socket_path


def web_tool_environment(environment: Mapping[str, str], *, session_name: str) -> dict[str, str]:
    """Give detached native tool processes their exact owning tmux locator."""

    detached = {
        key: value for key, value in environment.items() if key not in {"TMUX", "TMUX_PANE"}
    }
    detached[SELF_TMUX_SOCKET_ENV_VAR] = capture_tmux_socket_path()
    detached[SELF_TMUX_SESSION_ENV_VAR] = session_name
    return detached


def _capture_descendants(pid: int, birth: str, owned: dict[int, str]) -> None:
    """Capture only descendants whose ancestry reaches this exact native process."""

    if _dispatch_origin_birth_token(pid) != birth:
        return
    try:
        identities = {
            int(path.name): identity
            for path in Path("/proc").iterdir()
            if path.name.isdigit()
            if (identity := _read_process_lineage(int(path.name))) is not None
        }
    except OSError:
        return
    parents = {pid}
    while True:
        children = {child for child, value in identities.items() if value[0] in parents}
        if children.issubset(parents):
            break
        parents.update(children)
    if _dispatch_origin_birth_token(pid) != birth:
        return
    for child in parents:
        if child in identities:
            owned[child] = identities[child][3]


def _signal_owned(pid: int, birth: str, signum: int, descendants: dict[int, str]) -> None:
    """Signal the verified native group and separately captured escaped descendants."""

    _capture_descendants(pid, birth, descendants)
    if _dispatch_origin_birth_token(pid) == birth:
        try:
            if os.getpgid(pid) == pid:
                os.killpg(pid, signum)
        except ProcessLookupError:
            pass
    for child, expected in tuple(descendants.items()):
        if _dispatch_origin_birth_token(child) != expected:
            continue
        try:
            os.kill(child, signum)
        except ProcessLookupError:
            pass


def main() -> int:
    """Launch a private native Web host and expose only fixed supervisory messages."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    private: dict[str, Any] = json.loads(args.input.read_text(encoding="utf-8"))
    args.input.unlink()
    root = Path(private["root"])
    name = "Kimi Web" if private.get("name") == "Kimi Web" else "DSH Web"
    stopped = threading.Event()

    def request_stop(signum: int, frame: object) -> None:
        """Latch a stop request without cancelling an unrelated process or server."""

        stopped.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGHUP, request_stop)
    try:
        native = subprocess.Popen(
            private["command"],
            cwd=private["working_directory"],
            env=private["environment"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
        )
    except OSError:
        _write_private_json(
            root / "exit.json",
            {"returncode": 127, "ended_at": time.time(), "error": "native_start_failed"},
        )
        print(f"{name} supervisor could not start its native process.", flush=True)
        return 127
    birth = _dispatch_origin_birth_token(native.pid)
    if birth is None:
        native.terminate()
        native.wait(timeout=5)
        raise RuntimeError("Native Web process identity is unavailable")
    _write_private_json(
        root / "supervisor.json",
        {
            "version": 1,
            "supervisor_pid": os.getpid(),
            "supervisor_birth_token": _dispatch_origin_birth_token(os.getpid()),
            "native_pid": native.pid,
            "native_birth_token": birth,
        },
    )
    log_fd = os.open(root / "native-private.log", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)

    def drain() -> None:
        """Drain native output privately; token-bearing bytes never reach tmux output."""

        with os.fdopen(log_fd, "w", encoding="utf-8") as output:
            if native.stdout is not None:
                for line in native.stdout:
                    output.write(line)
                    output.flush()

    reader = threading.Thread(target=drain, name="native-web-private-log", daemon=True)
    reader.start()
    print(f"{name} supervisor started; native diagnostics are private.", flush=True)
    owned: dict[int, str] = {}
    try:
        while native.poll() is None and not stopped.wait(0.1):
            _capture_descendants(native.pid, birth, owned)
        if native.poll() is None:
            _signal_owned(native.pid, birth, signal.SIGTERM, owned)
            try:
                native.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _signal_owned(native.pid, birth, signal.SIGKILL, owned)
                native.wait(timeout=5)
    finally:
        _signal_owned(native.pid, birth, signal.SIGKILL, owned)
        reader.join(timeout=5)
        if reader.is_alive():
            raise RuntimeError("Native Web diagnostic cleanup did not settle")
        if native.stdout is not None:
            native.stdout.close()
        _write_private_json(
            root / "exit.json", {"returncode": native.returncode, "ended_at": time.time()}
        )
        print(f"{name} supervisor stopped.", flush=True)
    return native.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
