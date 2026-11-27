"""Exercise the browser gateway attachment on private real tmux servers."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import time

import pytest
from starlette.types import Message
from starlette.websockets import WebSocket

from houmao.agents.realm_controller import gateway_terminal_pty as terminal
from houmao.agents.realm_controller.boundary_models import (
    SessionManifestPayloadV4,
    SessionManifestRuntimeSectionV1,
    SessionManifestTmuxSectionV1,
)
from houmao.execution.context import observed_local_binding

_SESSION = "HOUMAO-terminal-fixture"
_AGENT_ID = "test-terminal-agent"


def _tmux(socket: Path, *args: str, start: bool = False, check: bool = True) -> str:
    """Run a command on the explicit fixture server alone."""

    env = {key: val for key, val in os.environ.items() if key not in {"TMUX", "TMUX_PANE"}}
    result = subprocess.run(
        ["tmux", "-S", str(socket), *([] if start else ["-N"]), *args],
        env=env,
        check=check,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class _Runtime:
    """Carry the fixture's saved authority and private tmux socket."""

    socket: Path
    manifest_path: Path
    manifest: SessionManifestPayloadV4

    def target(self) -> terminal.TerminalTarget:
        """Resolve the exact live target as a gateway would."""

        return terminal.resolve_terminal_target(self.manifest, manifest_path=self.manifest_path)

    def clients(self) -> str:
        """List client IDs on only the fixture session."""

        return _tmux(self.socket, "list-clients", "-t", f"={_SESSION}", "-F", "#{client_pid}")

    def viewer_tty(self) -> str:
        """Identify the sole browser PTY alongside its control-mode companion."""

        clients = _tmux(
            self.socket,
            "list-clients",
            "-t",
            self.target().session_id,
            "-F",
            "#{client_tty} #{client_flags}",
        )
        (tty,) = (line.split()[0] for line in clients.splitlines() if "control-mode" not in line)
        return tty


def _new_session(socket: Path, manifest_path: Path, *, label: str) -> tuple[str, str]:
    """Start a test-owned application that echoes individual lines through a PTY."""

    result = _tmux(
        socket,
        "-f",
        os.devnull,
        "new-session",
        "-d",
        "-E",
        "-s",
        _SESSION,
        "-x",
        "80",
        "-y",
        "25",
        "-e",
        f"HOUMAO_AGENT_ID={_AGENT_ID}",
        "-e",
        f"HOUMAO_MANIFEST_PATH={manifest_path}",
        "-P",
        "-F",
        "#{window_id} #{pane_id}",
        f"stty -echo; printf '{label}\\n'; exec cat",
        start=True,
    )
    window_id, pane_id = result.split()
    return window_id, pane_id


@pytest.fixture
def runtime(tmp_path: Path) -> Iterator[_Runtime]:
    """Start and retire only explicitly isolated test-owned sessions."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is unavailable")
    with TemporaryDirectory(prefix="hmt-") as directory:
        socket = Path(directory) / "tmux.sock"
        manifest_path = tmp_path / "manifest.json"
        window_id, pane_id = _new_session(socket, manifest_path, label="owned-terminal")
        binding = observed_local_binding(
            working_directory=tmp_path,
            runtime_root=tmp_path / "runtime",
            registry_root=tmp_path / "registry",
            tmux_socket=str(socket),
        )
        manifest = SessionManifestPayloadV4.model_construct(
            agent_id=_AGENT_ID,
            registry_generation_id="original-generation",
            runtime=SessionManifestRuntimeSectionV1(
                session_id="runtime", execution_binding=binding
            ),
            tmux_session_name=_SESSION,
            tmux=SessionManifestTmuxSectionV1(
                session_name=_SESSION,
                socket_path=str(socket),
                primary_window_id=window_id,
                primary_pane_id=pane_id,
            ),
        )
        try:
            yield _Runtime(socket, manifest_path, manifest)
        finally:
            _tmux(socket, "kill-session", "-t", f"={_SESSION}", check=False)
            _tmux(socket, "kill-session", "-t", "=sibling-fixture", check=False)


class _Browser:
    """Expose a real Starlette WebSocket through in-memory ASGI channels."""

    def __init__(self) -> None:
        self.incoming: asyncio.Queue[Message] = asyncio.Queue()
        self.outgoing: asyncio.Queue[Message] = asyncio.Queue()
        self.websocket = WebSocket(
            {"type": "websocket", "path": "/stream"}, self.incoming.get, self.outgoing.put
        )

    async def start(self) -> None:
        """Start at the already authorized state expected by the PTY adapter."""

        await self.incoming.put({"type": "websocket.connect"})
        await self.websocket.accept()
        assert (await self.outgoing.get())["type"] == "websocket.accept"

    async def frame(self) -> Message:
        """Wait for one typed message from the native terminal bridge."""

        return await asyncio.wait_for(self.outgoing.get(), timeout=6)

    async def ready(self) -> dict[str, object]:
        """Receive the attached client's initial dimensions."""

        message = json.loads((await self.frame())["text"])
        assert message["type"] == "ready"
        return message

    async def read(self, expected: bytes) -> None:
        """Process and acknowledge output until the expected bytes have arrived."""

        accumulated = b""
        async with asyncio.timeout(6):
            while expected not in accumulated:
                data = (await self.outgoing.get())["bytes"]
                accumulated += data
                await self.control(type="ack", bytes=len(data))

    async def control(self, **fields: object) -> None:
        """Send one browser control after terminal attach."""

        await self.incoming.put({"type": "websocket.receive", "text": json.dumps(fields)})

    async def close(self) -> None:
        """Send the browser-side ASGI close to the bridge."""

        await self.incoming.put({"type": "websocket.disconnect", "code": 1000})


def _current(runtime: _Runtime, expected: terminal.TerminalTarget) -> None:
    """Require the initial identity for each protected I/O handoff."""

    if runtime.target() != expected:
        raise terminal.TerminalUnavailable("The fixture terminal changed.")


def test_recorded_socket_and_live_identity_are_required(
    runtime: _Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignore ambient decoys and refuse missing, stale, or unbound evidence."""

    with TemporaryDirectory(prefix="hmt-decoy-") as directory:
        decoy = Path(directory) / "tmux.sock"
        _new_session(decoy, runtime.manifest_path, label="decoy-terminal")
        try:
            pid = _tmux(decoy, "display-message", "-p", "#{pid}")
            monkeypatch.setenv("TMUX", f"{decoy},{pid},0")
            monkeypatch.setenv("TMUX_PANE", "%0")
            assert runtime.target().socket_path == str(runtime.socket)
            with pytest.raises(terminal.TerminalUnavailable, match="no verified"):
                terminal.resolve_terminal_target(runtime.manifest.model_copy(update={"tmux": None}))
            with pytest.raises(terminal.TerminalUnavailable, match="identity is stale"):
                terminal.resolve_terminal_target(
                    runtime.manifest, manifest_path=runtime.manifest_path.with_name("other.json")
                )
            _tmux(runtime.socket, "set-environment", "-t", f"={_SESSION}", "HOUMAO_AGENT_ID", "old")
            with pytest.raises(terminal.TerminalUnavailable, match="identity is stale"):
                runtime.target()
        finally:
            _tmux(decoy, "kill-session", "-t", f"={_SESSION}", check=False)


def test_final_tmux_fence_rejects_reused_native_ids(
    runtime: _Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replacement between native argv preparation and connect cannot attach."""

    previous = runtime.target()
    argv = terminal._attach_argv(previous, interact=True)
    _tmux(runtime.socket, "kill-session", "-t", f"={_SESSION}")
    deadline = time.monotonic() + 3
    while (
        terminal._dispatch_origin_birth_token(int(previous.server_pid)) == previous.server_birth
        and time.monotonic() < deadline
    ):
        time.sleep(0.02)
    with pytest.raises(terminal.TerminalUnavailable, match="unavailable"):
        runtime.target()
    assert terminal._dispatch_origin_birth_token(int(previous.server_pid)) != previous.server_birth
    runtime.socket.unlink(missing_ok=True)
    _new_session(runtime.socket, runtime.manifest_path, label="replacement-terminal")
    current = runtime.target()
    assert (current.session_id, current.window_id, current.pane_id) == (
        previous.session_id,
        previous.window_id,
        previous.pane_id,
    )
    assert current != previous
    monkeypatch.setattr(terminal, "_attach_argv", lambda *_args, **_kwargs: argv)

    async def exercise() -> None:
        """Run the stale invocation against the replacement and verify it failed."""

        attachment = await terminal._Attachment.start(previous, interact=True)
        try:
            with pytest.raises(terminal.TerminalUnavailable, match="could not attach"):
                await attachment.wait_until_attached(previous)
            assert not runtime.clients()
        finally:
            await attachment.close()

    asyncio.run(exercise())


def test_interactive_browser_resize_unicode_and_disconnect_preserve_native_client(
    runtime: _Runtime,
) -> None:
    """Browser input uses a controlling PTY and native clients retain identity."""

    async def exercise() -> None:
        """Attach a second client, interact through the bridge, and release only it."""

        target = runtime.target()
        native_client = await terminal._Attachment.start(target, interact=True)
        stream: asyncio.Task[None] | None = None
        try:
            await native_client.wait_until_attached(target)
            browser = _Browser()
            await browser.start()
            stream = asyncio.create_task(
                terminal.run_terminal_stream(
                    browser.websocket,
                    target,
                    interact=True,
                    check_current=lambda: _current(runtime, target),
                )
            )
            await browser.ready()
            await browser.read(b"owned-terminal")
            paste = "paste café 日本語".encode()
            await browser.incoming.put({"type": "websocket.receive", "bytes": paste + b"\r"})
            await browser.read(paste)
            await browser.control(type="resize", cols=52, rows=17)
            async with asyncio.timeout(4):
                while "52x17" not in _tmux(
                    runtime.socket,
                    "list-clients",
                    "-t",
                    target.session_id,
                    "-F",
                    "#{client_width}x#{client_height}",
                ):
                    await asyncio.sleep(0.025)
            await browser.close()
            await asyncio.wait_for(stream, timeout=5)
            assert runtime.clients() == str(native_client.process.pid)
            assert runtime.target() == target
        finally:
            if stream is not None and not stream.done():
                stream.cancel()
                await asyncio.gather(stream, return_exceptions=True)
            await native_client.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "message",
    [
        {"bytes": b"\x02ssecret\r"},
        {"text": '{"type":"resize","cols":21,"rows":8}'},
    ],
)
def test_view_does_not_mutate_focus_size_or_input(runtime: _Runtime, message: Message) -> None:
    """Crafted viewer commands never reach the tmux client or change the session."""

    async def exercise() -> None:
        """Open a view while another window is active and reject its fabricated input."""

        target = runtime.target()
        alternate = _tmux(
            runtime.socket,
            "new-window",
            "-t",
            f"{target.session_id}:",
            "-n",
            "fixture-alternate",
            "-P",
            "-F",
            "#{window_id}",
            "stty -echo; printf 'alternate-window\\n'; exec cat",
        )
        alternate_target = f"{target.session_id}:{alternate}"
        _tmux(runtime.socket, "resize-window", "-t", alternate_target, "-x", "64", "-y", "18")
        _tmux(runtime.socket, "set-window-option", "-t", alternate_target, "window-size", "latest")
        dimensions = "#{window_id} #{window_width}x#{window_height}"

        def focus_and_size() -> str:
            """Observe the native session's focused window and dimensions."""

            return _tmux(
                runtime.socket, "display-message", "-p", "-t", target.session_id, dimensions
            )

        before = focus_and_size()
        assert before.startswith(alternate)
        target = runtime.target()
        assert (target.cols, target.rows) == (64, 19)
        list_sizes = ("list-windows", "-t", target.session_id, "-F", dimensions)
        before_all = _tmux(runtime.socket, *list_sizes)
        browser = _Browser()
        await browser.start()
        stream = asyncio.create_task(
            terminal.run_terminal_stream(
                browser.websocket,
                target,
                interact=False,
                check_current=lambda: _current(runtime, target),
            )
        )
        try:
            await browser.ready()
            await browser.read(b"alternate-window")
            assert focus_and_size() == before
            assert _tmux(runtime.socket, *list_sizes) == before_all
            await browser.incoming.put({"type": "websocket.receive", **message})
            with pytest.raises(terminal.TerminalUnavailable, match="does not accept"):
                await asyncio.wait_for(stream, timeout=5)
            assert not runtime.clients()
            assert focus_and_size() == before
            assert _tmux(runtime.socket, *list_sizes) == before_all
            assert "secret" not in _tmux(
                runtime.socket, "capture-pane", "-p", "-t", f"{target.session_id}:{alternate}"
            )
        finally:
            if not stream.done():
                stream.cancel()
                await asyncio.gather(stream, return_exceptions=True)

    asyncio.run(exercise())


def test_view_does_not_resize_after_a_native_client_closes(runtime: _Runtime) -> None:
    """A lone viewer stays size neutral after another client resizes and detaches."""

    async def exercise() -> None:
        """Resize through a separate native client while the browser is reading."""

        target = runtime.target()
        native_client = await terminal._Attachment.start(target, interact=True)
        stream: asyncio.Task[None] | None = None
        native_closed = False
        try:
            await native_client.wait_until_attached(target)
            browser = _Browser()
            await browser.start()
            stream = asyncio.create_task(
                terminal.run_terminal_stream(
                    browser.websocket,
                    target,
                    interact=False,
                    check_current=lambda: _current(runtime, target),
                )
            )
            await browser.ready()
            await browser.read(b"owned-terminal")
            terminal._set_size(native_client.fd, cols=66, rows=21)

            async with asyncio.timeout(3):
                while runtime.target().cols != 66:
                    await asyncio.sleep(0.025)
            received = runtime.target()
            assert (received.cols, received.rows) == (66, 21)
            await native_client.close()
            native_closed = True
            assert len(runtime.clients().splitlines()) == 2
            assert (runtime.target().cols, runtime.target().rows) == (66, 21)
            await browser.close()
            await asyncio.wait_for(stream, timeout=3)
            assert not runtime.clients()
            assert (runtime.target().cols, runtime.target().rows) == (66, 21)
        finally:
            if stream is not None and not stream.done():
                stream.cancel()
                await asyncio.gather(stream, return_exceptions=True)
            if not native_closed:
                await native_client.close()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("session_option", "option", "unsafe", "safe"),
    [
        (True, "destroy-unattached", "on", "off"),
        (True, "detach-on-destroy", "off", "on"),
        (False, "exit-unattached", "on", "off"),
    ],
)
def test_effective_unsafe_options_refuse_admission(
    runtime: _Runtime, option: str, unsafe: str, safe: str, *, session_option: bool
) -> None:
    """Detect inherited or per-session options without changing user configuration."""

    async def exercise() -> None:
        """Keep a native client on the deliberately unsafe test configuration."""

        target = runtime.target()
        setting_args = ["-t", f"{target.session_id}:"] if session_option else ["-s"]
        native_client = await terminal._Attachment.start(target, interact=True)
        try:
            await native_client.wait_until_attached(target)
            _tmux(runtime.socket, "set-option", *setting_args, option, unsafe)
            with pytest.raises(terminal.TerminalUnavailable, match=option):
                runtime.target()
            assert runtime.clients() == str(native_client.process.pid)
            assert _tmux(runtime.socket, "show-options", *setting_args, "-v", option) == unsafe
        finally:
            try:
                _tmux(runtime.socket, "set-option", *setting_args, option, safe)
            finally:
                await native_client.close()

    asyncio.run(exercise())


def test_browser_stall_ends_only_attachment(
    runtime: _Runtime, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A browser missing acknowledgements gets at most its configured byte credit."""

    monkeypatch.setattr(terminal, "_OUTPUT_WINDOW", 128)
    monkeypatch.setattr(terminal, "_STALL_TIMEOUT", 0.2)
    monkeypatch.setattr(terminal, "_CHECK_INTERVAL", 0.05)

    async def exercise() -> None:
        """Watch the tmux startup redraw without processing its frames."""

        target = runtime.target()
        browser = _Browser()
        await browser.start()
        stream = asyncio.create_task(
            terminal.run_terminal_stream(
                browser.websocket,
                target,
                interact=False,
                check_current=lambda: _current(runtime, target),
            )
        )
        await browser.ready()
        with pytest.raises(terminal.TerminalUnavailable, match="stopped processing"):
            await asyncio.wait_for(stream, timeout=4)
        sent = sum(
            len(browser.outgoing.get_nowait()["bytes"]) for _ in range(browser.outgoing.qsize())
        )
        assert 0 < sent <= 128
        assert not runtime.clients()
        assert runtime.target() == target

    asyncio.run(exercise())


@pytest.mark.parametrize("cancel_gateway", [False, True])
def test_disconnect_or_shutdown_during_attachment_reaps_the_owned_client(
    runtime: _Runtime, monkeypatch: pytest.MonkeyPatch, *, cancel_gateway: bool
) -> None:
    """Browser disconnect and gateway cancellation clean up incomplete startups."""

    async def exercise() -> None:
        """Pause native confirmation to force cancellation after attach acquisition."""

        previous_wait = terminal._Attachment.wait_until_attached
        acquired = asyncio.Event()
        block = asyncio.Event()

        async def wait_for_ready(
            attachment: terminal._Attachment, target: terminal.TerminalTarget
        ) -> None:
            """Hold startup after the tmux child is up and before the browser receives data."""

            await previous_wait(attachment, target)
            acquired.set()
            await block.wait()

        monkeypatch.setattr(terminal._Attachment, "wait_until_attached", wait_for_ready)
        target = runtime.target()
        browser = _Browser()
        await browser.start()
        stream = asyncio.create_task(
            terminal.run_terminal_stream(
                browser.websocket,
                target,
                interact=False,
                check_current=lambda: _current(runtime, target),
            )
        )
        await asyncio.wait_for(acquired.wait(), timeout=4)
        assert runtime.clients()
        if cancel_gateway:
            stream.cancel()
            with pytest.raises(asyncio.CancelledError):
                await stream
        else:
            await browser.close()
            await asyncio.wait_for(stream, timeout=3)
        assert not runtime.clients()
        assert runtime.target() == target
        assert browser.outgoing.empty()

    asyncio.run(exercise())


def test_tmux_client_eof_reaps_the_browser_attachment(runtime: _Runtime) -> None:
    """Native detach closes the browser PTY and its companion without affecting the agent."""

    async def exercise() -> None:
        """Detach the single browser PTY from within the private native server."""

        target = runtime.target()
        browser = _Browser()
        await browser.start()
        stream = asyncio.create_task(
            terminal.run_terminal_stream(
                browser.websocket,
                target,
                interact=False,
                check_current=lambda: _current(runtime, target),
            )
        )
        await browser.ready()
        await browser.read(b"owned-terminal")
        _tmux(runtime.socket, "detach-client", "-t", runtime.viewer_tty())
        try:
            await asyncio.wait_for(stream, timeout=3)
        except terminal.TerminalUnavailable as error:
            assert "lost its verified tmux binding" in str(error)
        assert not runtime.clients()
        assert runtime.target() == target

    asyncio.run(exercise())


def test_out_of_band_viewer_switch_never_exposes_a_sibling_session(runtime: _Runtime) -> None:
    """Hold read-only output to the admitted session, even after native retargeting."""

    async def exercise() -> None:
        """Use the fixture owner's ordinary tmux authority to move the client."""

        _tmux(
            runtime.socket,
            "new-session",
            "-d",
            "-s",
            "sibling-fixture",
            "stty -echo; printf 'private-sibling-output\\n'; exec cat",
        )
        target = runtime.target()
        browser = _Browser()
        await browser.start()
        stream = asyncio.create_task(
            terminal.run_terminal_stream(
                browser.websocket,
                target,
                interact=False,
                check_current=lambda: _current(runtime, target),
            )
        )
        await browser.ready()
        await browser.read(b"owned-terminal")
        _tmux(runtime.socket, "switch-client", "-c", runtime.viewer_tty(), "-t", "=sibling-fixture")
        with pytest.raises(terminal.TerminalUnavailable, match="lost its verified tmux binding"):
            await asyncio.wait_for(stream, timeout=3)
        remaining = b"".join(
            browser.outgoing.get_nowait().get("bytes", b"") for _ in range(browser.outgoing.qsize())
        )
        assert b"private-sibling-output" not in remaining
        assert not _tmux(runtime.socket, "list-clients", "-t", "=sibling-fixture")
        assert not runtime.clients()
        assert runtime.target() == target

    asyncio.run(exercise())
