"""Provide synchronized native Messages work and human questions for browser checks."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any


@dataclass
class BrowserModel:
    """Keep synthetic request evidence and explicit streaming gates in one test model."""

    endpoint: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)
    active: threading.Event = field(default_factory=threading.Event)
    release: threading.Event = field(default_factory=threading.Event)


@contextmanager
def controlled_browser_model() -> Iterator[BrowserModel]:
    """Serve actual native requests locally with deterministic question and progress oracles."""

    model = BrowserModel()

    class Handler(BaseHTTPRequestHandler):
        """Return native Messages SSE without a provider account or network dependency."""

        def do_POST(self) -> None:
            """Ask once, hold selected work, and expose real streamed browser progress."""

            assert self.path.endswith("/messages")
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            model.requests.append(body)
            last_user = next(row for row in reversed(body["messages"]) if row["role"] == "user")
            content = json.dumps(last_user["content"])
            answered = any(
                block.get("type") == "tool_result"
                for row in body["messages"]
                if isinstance(row.get("content"), list)
                for block in row["content"]
                if isinstance(block, dict)
            )
            question = "BROWSER_QUESTION" in content and not answered
            approval = "BROWSER_APPROVAL" in content and not answered
            blocked = "BROWSER_BLOCK" in content and not answered
            tool_call: tuple[str, dict[str, Any]] | None = None
            if question:
                tool_call = (
                    "ask_user_question",
                    {
                        "questions": [
                            {
                                "id": "choice",
                                "question": "Controlled browser question",
                                "options": [{"label": "Proceed"}, {"label": "Wait"}],
                            }
                        ]
                    },
                )
            elif approval:
                tool_call = (
                    "bash",
                    {
                        "description": "Run a harmless approval probe",
                        "command": "printf APPROVAL_PROBE",
                        "sandbox_permissions": "danger-full-access",
                        "justification": "Controlled browser approval probe",
                    },
                )
            frames: list[dict[str, Any]] = [
                {
                    "type": "message_start",
                    "message": {
                        "id": f"browser-message-{len(model.requests)}",
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
                    "content_block": {
                        "type": "tool_use",
                        "id": "browser-tool-call",
                        "name": tool_call[0],
                        "input": {},
                    }
                    if tool_call
                    else {"type": "text", "text": ""},
                },
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": json.dumps(tool_call[1]),
                    }
                    if tool_call
                    else {
                        "type": "text_delta",
                        "text": "Controlled active browser progress"
                        if blocked
                        else "Controlled browser completion",
                    },
                },
            ]
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.end_headers()
            try:
                self._frames(frames)
                if blocked:
                    model.active.set()
                    model.release.wait(40)
                self._frames(
                    [
                        {"type": "content_block_stop", "index": 0},
                        {
                            "type": "message_delta",
                            "delta": {"stop_reason": "tool_use" if tool_call else "end_turn"},
                            "usage": {"output_tokens": 5},
                        },
                        {"type": "message_stop"},
                    ]
                )
            except (BrokenPipeError, ConnectionResetError):
                pass

        def _frames(self, frames: list[dict[str, Any]]) -> None:
            """Flush progress before releasing the controlled terminal boundary."""

            for frame in frames:
                self.wfile.write(f"event: {frame['type']}\ndata: {json.dumps(frame)}\n\n".encode())
            self.wfile.flush()

        def log_message(self, format: str, *args: Any) -> None:
            """Keep even synthetic HTTP requests out of public qualification output."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    model.endpoint = f"http://127.0.0.1:{server.server_port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield model
    finally:
        model.release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
