"""Observe and attach a browser to an exact, currently managed tmux session."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
import errno
import fcntl
import json
import os
from pathlib import Path
import pty
import re
import shutil
import struct
import sys
import termios
import time

from starlette.websockets import WebSocket

from houmao.agents.launch_env import owner_launch_baseline
from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    SAFE_MANAGED_AGENT_COMPONENT_PATTERN,
)
from houmao.agents.realm_controller.backends.dispatch_control import _dispatch_origin_birth_token
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.execution.context import require_owner_tmux_socket
from houmao.execution.tmux import TmuxCommandError, TmuxServer

_TARGET_FORMAT = "\t".join(
    f"#{{{field_name}}}"
    for field_name in (
        "session_name",
        "session_id",
        "session_created",
        "window_id",
        "window_index",
        "pane_id",
        "pane_pid",
        "pane_dead",
        "pid",
        "start_time",
        "destroy-unattached",
        "exit-unattached",
        "detach-on-destroy",
        "W:,#{window_width}",
        "W:,#{window_height}",
        "status",
        AGENT_ID_ENV_VAR,
        AGENT_MANIFEST_PATH_ENV_VAR,
    )
)
_SAFE_OPTIONS = {"destroy-unattached": "off", "exit-unattached": "0", "detach-on-destroy": "on"}
_STATUS_ROWS = {"off": 0, "on": 1, "2": 2, "3": 3, "4": 4, "5": 5}
_CHECK_INTERVAL = 0.5
_OBSERVATION_TIMEOUT = 1.0
_START_TIMEOUT = 4.0
_STOP_TIMEOUT = 1.0
_STALL_TIMEOUT = 8.0
_MAX_INPUT_FRAME = 64 * 1024
_MAX_CONTROL_FRAME = 256
_OUTPUT_WINDOW = 256 * 1024
_OUTPUT_CHUNK = 16 * 1024
_MAX_DIMENSION = 1000


class TerminalUnavailable(RuntimeError):
    """The verified terminal could not be safely attached or the stream ended."""


@dataclass(frozen=True)
class TerminalTarget:
    """Pin one managed generation and its server-local native attachment handles."""

    agent_id: str
    generation: str
    runtime_session_id: str
    socket_path: str
    session_id: str
    session_created: str
    window_id: str
    pane_id: str
    pane_pid: str
    server_pid: str
    server_started: str
    server_birth: str
    manifest_path: str
    cols: int = field(compare=False)
    rows: int = field(compare=False)

    @property
    def pane_target(self) -> str:
        """Address the exact recorded pane for the final attach guard."""

        return f"{self.session_id}:{self.window_id}.{self.pane_id}"


def resolve_terminal_target(
    manifest: SessionManifestPayloadV4, *, manifest_path: Path | None = None
) -> TerminalTarget:
    """Observe the owner-published tmux binding in an already verified active manifest."""

    binding = manifest.tmux
    generation = manifest.registry_generation_id
    runtime_id = manifest.runtime.session_id
    if (
        binding is None
        or binding.session_name != manifest.tmux_session_name
        or not generation
        or not runtime_id
        or manifest.runtime.execution_binding is None
        or not binding.primary_window_id
        or not binding.primary_pane_id
        or not re.fullmatch(r"@[0-9]+", binding.primary_window_id)
        or not re.fullmatch(r"%[0-9]+", binding.primary_pane_id)
        or not re.fullmatch(SAFE_MANAGED_AGENT_COMPONENT_PATTERN, manifest.agent_id)
    ):
        raise TerminalUnavailable("The active agent has no verified tmux attachment binding.")
    try:
        socket_path = require_owner_tmux_socket(
            manifest.runtime.execution_binding, binding.socket_path
        )
        server = TmuxServer(socket_path, allow_start=False)
        details = server.display_format(
            f"={binding.session_name}:{binding.primary_window_id}.{binding.primary_pane_id}",
            _TARGET_FORMAT,
            timeout_seconds=_OBSERVATION_TIMEOUT,
        )
    except (OSError, ValueError, TmuxCommandError):
        raise TerminalUnavailable("The recorded tmux session is unavailable.") from None

    values = details.split("\t", maxsplit=17)
    if len(values) != 18:
        raise TerminalUnavailable("The recorded tmux session is unavailable.")
    (
        name,
        session_id,
        session_created,
        window_id,
        window_index,
        pane_id,
        pane_pid,
        pane_dead,
        server_pid,
        server_started,
        destroy,
        exit_,
        detach,
        cols,
        rows,
        status,
        agent_id,
        published_manifest,
    ) = values
    if (
        name != binding.session_name
        or window_id != binding.primary_window_id
        or window_index != binding.primary_window_index
        or pane_id != binding.primary_pane_id
        or agent_id != manifest.agent_id
        or pane_dead != "0"
        or not re.fullmatch(r"\$[0-9]+", session_id)
        or not all(
            re.fullmatch(r"[1-9][0-9]{0,15}", value)
            for value in (session_created, pane_pid, server_pid, server_started, cols, rows)
        )
        or not Path(published_manifest).is_absolute()
        or (manifest_path is not None and published_manifest != str(manifest_path))
        or status not in _STATUS_ROWS
    ):
        raise TerminalUnavailable(
            "The managed tmux identity is stale. Check the live agent and retry."
        )
    for name, actual in zip(_SAFE_OPTIONS, (destroy, exit_, detach), strict=True):
        if actual != _SAFE_OPTIONS[name]:
            required = "off" if name == "exit-unattached" else _SAFE_OPTIONS[name]
            raise TerminalUnavailable(
                f"Browser terminal requires effective tmux {name}={required}. "
                "Review the execution owner's tmux configuration and retry."
            )
    server_birth = _dispatch_origin_birth_token(int(server_pid))
    if server_birth is None:
        raise TerminalUnavailable("The recorded tmux server incarnation is unavailable.")
    return TerminalTarget(
        agent_id=agent_id,
        generation=generation,
        runtime_session_id=runtime_id,
        socket_path=socket_path,
        session_id=session_id,
        session_created=session_created,
        window_id=window_id,
        pane_id=pane_id,
        pane_pid=pane_pid,
        server_pid=server_pid,
        server_started=server_started,
        server_birth=server_birth,
        manifest_path=published_manifest,
        cols=min(int(cols), _MAX_DIMENSION),
        rows=min(int(rows) + _STATUS_ROWS[status], _MAX_DIMENSION),
    )


def _attach_argv(
    target: TerminalTarget, *, interact: bool, sizing_companion: bool = False
) -> list[str]:
    """Run the last identity and policy checks in the attaching client's tmux queue."""

    if _dispatch_origin_birth_token(int(target.server_pid)) != target.server_birth:
        raise TerminalUnavailable("The recorded tmux server has been replaced.")
    expected = {
        "pid": target.server_pid,
        "start_time": target.server_started,
        "session_id": target.session_id,
        "session_created": target.session_created,
        "window_id": target.window_id,
        "pane_id": target.pane_id,
        "pane_pid": target.pane_pid,
        "pane_dead": "0",
        AGENT_ID_ENV_VAR: target.agent_id,
        **_SAFE_OPTIONS,
    }
    condition = "1"
    for variable, value in reversed(expected.items()):
        condition = f"#{{&&:#{{==:#{{{variable}}},{value}}},{condition}}}"
    executable = shutil.which("tmux")
    if executable is None:
        raise TerminalUnavailable("The execution owner needs tmux available to the gateway.")
    tmux = TmuxServer(target.socket_path, executable=executable, allow_start=False)
    return tmux.attach_invocation(
        target.session_id,
        readonly=not interact and not sizing_companion,
        preserve_environment=True,
        control_mode=sizing_companion,
        client_flags="read-only,no-output" if sizing_companion else None,
        guard=(target.pane_target, condition),
    )


def _set_size(fd: int, *, cols: int, rows: int) -> None:
    """Set this client's PTY dimensions through the native winsize ioctl."""

    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


async def _reap_client(process: asyncio.subprocess.Process) -> None:
    """Reap the acquired tmux client with bounded termination, keeping the server alive."""

    if process.stdin is not None:
        process.stdin.close()
    for signal_client in (process.terminate, process.kill):
        if process.returncode is not None:
            return
        try:
            signal_client()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(process.wait(), timeout=_STOP_TIMEOUT)
        except TimeoutError:
            continue
        return
    raise TerminalUnavailable("The browser terminal client did not exit in time.")


async def _launch_client(
    argv: list[str], *, stdin: int, stdout: int, stderr: int
) -> asyncio.subprocess.Process:
    """Launch a child without losing its handle if the gateway is cancelled."""

    environment = owner_launch_baseline(os.environ)
    environment.update(TERM="xterm-256color", COLORTERM="truecolor")
    startup = asyncio.create_task(
        asyncio.create_subprocess_exec(
            *argv,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            env=environment,
            start_new_session=True,
        )
    )
    try:
        return await asyncio.shield(startup)
    except asyncio.CancelledError:
        try:
            process = await asyncio.shield(startup)
        except (OSError, ValueError):
            # The native process was never acquired.
            pass
        else:
            await _reap_client(process)
        raise


async def _wait_for_client(process: asyncio.subprocess.Process, target: TerminalTarget) -> None:
    """Wait until tmux reports the acquired process attached to the pinned session."""

    tmux = TmuxServer(target.socket_path, allow_start=False)
    expected_client = f"{process.pid}\t{target.session_id}"
    try:
        async with asyncio.timeout(_START_TIMEOUT):
            while process.returncode is None:
                try:
                    clients = await asyncio.to_thread(
                        tmux.clients_in_session,
                        target.session_id,
                        timeout_seconds=_OBSERVATION_TIMEOUT,
                    )
                except TmuxCommandError:
                    break
                if expected_client in clients.splitlines():
                    return
                await asyncio.sleep(0.025)
    except TimeoutError:
        raise TerminalUnavailable("The browser terminal attachment timed out.") from None
    raise TerminalUnavailable("The browser client could not attach to the verified tmux session.")


@dataclass(frozen=True)
class _Attachment:
    """Own a PTY and only the native clients acquired for its browser attachment."""

    fd: int
    process: asyncio.subprocess.Process
    companion: asyncio.subprocess.Process | None = None

    @classmethod
    async def start(cls, target: TerminalTarget, *, interact: bool) -> _Attachment:
        """Start a fresh controlling-terminal helper without running code after fork."""

        argv = await asyncio.to_thread(_attach_argv, target, interact=interact)
        companion = None
        try:
            if not interact:
                # A sole ignore-size native client still sizes the session. A control
                # client with no size negotiation excludes both clients from sizing.
                companion_argv = await asyncio.to_thread(
                    _attach_argv, target, interact=False, sizing_companion=True
                )
                companion = await _launch_client(
                    companion_argv,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await _wait_for_client(companion, target)
            master, slave = pty.openpty()
            try:
                _set_size(slave, cols=target.cols, rows=target.rows)
                os.set_blocking(master, False)
                process = await _launch_client(
                    [
                        sys.executable,
                        "-m",
                        "houmao.agents.realm_controller._gateway_terminal_child",
                        *argv,
                    ],
                    stdin=slave,
                    stdout=slave,
                    stderr=slave,
                )
            except BaseException:
                os.close(master)
                raise
            finally:
                os.close(slave)
        except BaseException:
            if companion is not None:
                await _reap_client(companion)
            raise
        return cls(master, process, companion)

    async def close(self) -> None:
        """Close the PTY and reap the browser's clients, keeping the viewer size neutral."""

        os.close(self.fd)
        try:
            await _reap_client(self.process)
        finally:
            if self.companion is not None:
                await _reap_client(self.companion)

    async def wait_until_attached(self, target: TerminalTarget) -> None:
        """Wait until tmux reports the PTY process attached to the pinned session."""

        await _wait_for_client(self.process, target)

    async def watch_companion(self) -> None:
        """Close the viewer if its unsized companion unexpectedly leaves."""

        assert self.companion is not None
        await self.companion.wait()
        raise TerminalUnavailable("The browser viewer's tmux sizing companion exited.")

    async def confirm_viewer_binding(self, target: TerminalTarget) -> None:
        """Refuse output if an owner-side command moves the viewer to another session."""

        assert self.companion is not None
        tmux = TmuxServer(target.socket_path, allow_start=False)
        try:
            observed = await asyncio.to_thread(
                tmux.clients_in_session, target.session_id, timeout_seconds=_OBSERVATION_TIMEOUT
            )
        except TmuxCommandError:
            raise TerminalUnavailable(
                "The browser viewer lost its verified tmux binding."
            ) from None
        expected = {f"{child.pid}\t{target.session_id}" for child in (self.process, self.companion)}
        if not expected.issubset(observed.splitlines()):
            raise TerminalUnavailable("The browser viewer lost its verified tmux binding.")


async def _wait_fd(fd: int, *, writing: bool = False) -> None:
    """Wait for nonblocking PTY readiness while allowing prompt cancellation."""

    loop = asyncio.get_running_loop()
    ready: asyncio.Future[None] = loop.create_future()

    def wake() -> None:
        """Wake the single waiting reader or writer."""

        if not ready.done():
            ready.set_result(None)

    if writing:
        loop.add_writer(fd, wake)
    else:
        loop.add_reader(fd, wake)
    try:
        await ready
    finally:
        if writing:
            loop.remove_writer(fd)
        else:
            loop.remove_reader(fd)


async def _read(fd: int, size: int) -> bytes:
    """Read at most the permitted PTY output, recognizing Linux PTY EOF."""

    while True:
        try:
            return os.read(fd, size)
        except BlockingIOError:
            await _wait_fd(fd)
        except OSError as error:
            if error.errno == errno.EIO:
                return b""
            raise


async def _write(fd: int, data: bytes, *, authorize: Callable[[], Awaitable[None]]) -> None:
    """Flush a browser frame while rechecking authority before each partial write."""

    pending = memoryview(data)
    while pending:
        await authorize()
        try:
            pending = pending[os.write(fd, pending) :]
        except BlockingIOError:
            await _wait_fd(fd, writing=True)


class _OutputCredit:
    """Bound bytes sent to the browser and enforce progress on rendered output."""

    def __init__(self) -> None:
        self.m_pending: int = 0
        self.m_last_progress: float = time.monotonic()
        self.m_space: asyncio.Event = asyncio.Event()
        self.m_space.set()

    async def read_capacity(self) -> int:
        """Wait until xterm.js has processed enough output for a read."""

        await self.m_space.wait()
        return min(_OUTPUT_CHUNK, _OUTPUT_WINDOW - self.m_pending)

    def sent(self, count: int) -> None:
        """Reserve output credit before exposing frames to the browser."""

        if self.m_pending == 0:
            self.m_last_progress = time.monotonic()
        self.m_pending += count
        if self.m_pending >= _OUTPUT_WINDOW:
            self.m_space.clear()

    def acknowledge(self, count: object) -> None:
        """Release only bytes previously sent on this connection."""

        if type(count) is not int or not 0 < count <= self.m_pending:
            raise TerminalUnavailable("The terminal flow acknowledgement is invalid.")
        self.m_pending -= count
        self.m_last_progress = time.monotonic()
        self.m_space.set()

    def check_progress(self) -> None:
        """End a stalled browser attachment regardless of remaining credit."""

        if self.m_pending and time.monotonic() - self.m_last_progress >= _STALL_TIMEOUT:
            raise TerminalUnavailable("The browser stopped processing terminal output.")


def _control(raw: str) -> dict[str, object]:
    """Parse a bounded terminal control without echoing untrusted content."""

    if len(raw) <= _MAX_CONTROL_FRAME:
        try:
            message: object = json.loads(raw)
        except (ValueError, RecursionError):
            pass
        else:
            if isinstance(message, dict):
                return message
    raise TerminalUnavailable("The browser terminal received an invalid control message.")


async def run_terminal_stream(
    websocket: WebSocket,
    target: TerminalTarget,
    *,
    interact: bool,
    check_current: Callable[[], None],
) -> None:
    """Relay a redeemed browser connection until either side or its authority ends."""

    credit = _OutputCredit()
    attachment: _Attachment | None = None
    allocated = asyncio.Event()
    ready = asyncio.Event()

    async def authorize() -> None:
        """Verify the original authority immediately before terminal I/O."""

        await asyncio.to_thread(check_current)
        if not interact and ready.is_set() and attachment is not None:
            await attachment.confirm_viewer_binding(target)

    async def to_browser() -> None:
        """Forward intact PTY bytes under the browser's output credit window."""

        nonlocal attachment
        await authorize()
        try:
            opened = await _Attachment.start(target, interact=interact)
        except OSError:
            raise TerminalUnavailable("Unable to allocate the browser terminal client.") from None
        attachment = opened
        allocated.set()
        await opened.wait_until_attached(target)
        await authorize()
        ready.set()
        await websocket.send_json({"type": "ready", "cols": target.cols, "rows": target.rows})
        while True:
            data = await _read(opened.fd, await credit.read_capacity())
            if not data:
                return
            await authorize()
            credit.sent(len(data))
            await websocket.send_bytes(data)

    async def from_browser() -> None:
        """Apply only the selected access mode's bounded terminal operations."""

        while True:
            received = await websocket.receive()
            if received["type"] == "websocket.disconnect":
                return
            opened = attachment
            if not ready.is_set() or opened is None:
                raise TerminalUnavailable("The browser terminal client is still attaching.")
            data = received.get("bytes")
            if data is not None:
                if not interact or len(data) > _MAX_INPUT_FRAME:
                    raise TerminalUnavailable("This terminal does not accept the browser input.")
                await _write(opened.fd, data, authorize=authorize)
                continue
            raw = received.get("text")
            message = _control(raw) if isinstance(raw, str) else {}
            if message.get("type") == "ack" and message.keys() == {"type", "bytes"}:
                credit.acknowledge(message["bytes"])
                continue
            if interact and message.get("type") == "resize":
                cols, rows = message.get("cols"), message.get("rows")
                if (
                    message.keys() == {"type", "cols", "rows"}
                    and type(cols) is int
                    and type(rows) is int
                    and 1 <= cols <= _MAX_DIMENSION
                    and 1 <= rows <= _MAX_DIMENSION
                ):
                    await authorize()
                    _set_size(opened.fd, cols=cols, rows=rows)
                    continue
            raise TerminalUnavailable("This terminal does not accept the browser control message.")

    async def monitor() -> None:
        """Recheck idle authority and detach if the browser stops processing bytes."""

        while True:
            await asyncio.sleep(_CHECK_INTERVAL)
            credit.check_progress()
            await authorize()

    async def monitor_viewer() -> None:
        """Wait for the read-only native clients and then watch their size neutrality."""

        await allocated.wait()
        assert attachment is not None
        await attachment.watch_companion()

    tasks: set[asyncio.Task[None]] = set()
    try:
        tasks.update(asyncio.create_task(work()) for work in (to_browser, from_browser, monitor))
        if not interact:
            tasks.add(asyncio.create_task(monitor_viewer()))
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except OSError:
        raise TerminalUnavailable("The browser terminal attachment ended.") from None
    finally:
        for task in tasks:
            task.cancel()
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            if attachment is not None:
                await attachment.close()
