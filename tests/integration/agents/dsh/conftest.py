"""Explicit native DSH build and credential-free local model fixtures."""

from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import threading
from typing import Any

import pytest


@pytest.fixture
def isolated_tmux(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Route every runtime tmux command and cleanup to an explicit private socket."""

    executable = shutil.which("tmux")
    if executable is None:
        pytest.skip("tmux is required for managed DSH integration")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "owner-config"))
    with tempfile.TemporaryDirectory(prefix="houmao-dsh-tmux-") as directory:
        socket = Path(directory) / "server.sock"
        commands = tmp_path / "isolated-bin"
        commands.mkdir()
        wrapper = commands / "tmux"
        wrapper.write_text(
            "#!/bin/sh\nunset TMUX TMUX_PANE\n"
            f'exec {shlex.quote(executable)} -S {shlex.quote(str(socket))} "$@"\n',
            encoding="utf-8",
        )
        wrapper.chmod(0o700)
        monkeypatch.setenv("PATH", f"{commands}{os.pathsep}{os.environ['PATH']}")
        try:
            yield socket
        finally:
            subprocess.run(
                [executable, "-S", str(socket), "kill-server"],
                env={
                    key: value
                    for key, value in os.environ.items()
                    if key not in {"TMUX", "TMUX_PANE"}
                },
                capture_output=True,
                check=False,
                timeout=10,
            )


@pytest.fixture
def dsh_executable() -> Path:
    """Require explicit opt-in and the pinned native package version."""

    configured = os.environ.get("HOUMAO_DSH_EXECUTABLE")
    if configured is None:
        pytest.skip("Set HOUMAO_DSH_EXECUTABLE to the qualified DSH rc.3 executable")
    executable = Path(configured).resolve()
    version = subprocess.run(
        [str(executable), "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    assert version == "0.2.2-rc.3", f"unqualified native DSH version: {version}"
    return executable


@pytest.fixture
def controlled_messages_server() -> Iterator[tuple[str, list[dict[str, Any]]]]:
    """Serve deterministic Messages streams without external credentials or network."""

    requests: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        """Capture actual native request bytes and return one settled response."""

        def do_POST(self) -> None:
            """Return one native Messages stream for a synthetic local request."""

            assert self.path.endswith(("/messages", "/chat/completions"))
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            requests.append(body)
            if self.path.endswith("/chat/completions"):
                frames = [
                    {
                        "id": "controlled-chat",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": "controlled",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": None,
                                "delta": {
                                    "role": "assistant",
                                    "content": "Controlled native result",
                                },
                            }
                        ],
                    },
                    {
                        "id": "controlled-chat",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": "controlled",
                        "choices": [{"index": 0, "finish_reason": "stop", "delta": {}}],
                    },
                    {
                        "id": "controlled-chat",
                        "object": "chat.completion.chunk",
                        "created": 0,
                        "model": "controlled",
                        "choices": [],
                        "usage": {"prompt_tokens": 11, "completion_tokens": 5, "total_tokens": 16},
                    },
                ]
                payload = (
                    "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
                    + "data: [DONE]\n\n"
                ).encode()
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("content-length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            frames = [
                {
                    "type": "message_start",
                    "message": {
                        "id": "controlled-message",
                        "type": "message",
                        "role": "assistant",
                        "model": "controlled",
                        "content": [],
                        "usage": {
                            "input_tokens": 11,
                            "output_tokens": 0,
                            "cache_read_input_tokens": 0,
                            "cache_creation_input_tokens": 0,
                        },
                    },
                },
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "Controlled native result"},
                },
                {"type": "content_block_stop", "index": 0},
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 5},
                },
                {"type": "message_stop"},
            ]
            payload = "".join(
                f"event: {frame['type']}\ndata: {json.dumps(frame)}\n\n" for frame in frames
            ).encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            """Keep local HTTP transport noise out of qualification output."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
