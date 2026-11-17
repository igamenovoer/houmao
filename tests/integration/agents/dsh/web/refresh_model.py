"""Serve deterministic native skill-tool turns without external provider access."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from typing import Any


@dataclass
class SkillModel:
    """Retain synthetic request evidence for two actual native skill loads."""

    endpoint: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def controlled_skill_model() -> Iterator[SkillModel]:
    """Alternate one native skill call with a settled assistant completion."""

    model = SkillModel()

    class Handler(BaseHTTPRequestHandler):
        """Return actual native Messages SSE with explicit controlled usage."""

        def do_POST(self) -> None:
            """Request the real skill tool at the beginning of each user turn."""

            assert self.path.endswith("/messages")
            model.requests.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
            number = len(model.requests)
            tool = number % 2 == 1
            block = (
                {"type": "tool_use", "id": f"skill-{number}", "name": "skill", "input": {}}
                if tool
                else {"type": "text", "text": ""}
            )
            delta = (
                {"type": "input_json_delta", "partial_json": '{"name":"alpha"}'}
                if tool
                else {"type": "text_delta", "text": "Controlled skill completion"}
            )
            frames = [
                {
                    "type": "message_start",
                    "message": {
                        "id": f"skill-message-{number}",
                        "type": "message",
                        "role": "assistant",
                        "model": "controlled",
                        "content": [],
                        "usage": {"input_tokens": 11, "output_tokens": 0},
                    },
                },
                {"type": "content_block_start", "index": 0, "content_block": block},
                {"type": "content_block_delta", "index": 0, "delta": delta},
                {"type": "content_block_stop", "index": 0},
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "tool_use" if tool else "end_turn"},
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
            """Keep even synthetic request material out of public logs."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    model.endpoint = f"http://127.0.0.1:{server.server_port}/v1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield model
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)
