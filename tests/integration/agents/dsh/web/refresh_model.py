"""Serve deterministic native skill-tool turns without external provider access."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any

from tests.integration.agents.dsh.conftest import ControlledModelGate


@dataclass
class SkillModel:
    """Retain synthetic request evidence for two actual native skill loads."""

    endpoint: str = ""
    requests: list[dict[str, Any]] = field(default_factory=list)


@contextmanager
def controlled_skill_model(
    *, read_asset: bool = False, hold_first: ControlledModelGate | None = None
) -> Iterator[SkillModel]:
    """Alternate one native skill call with a settled assistant completion."""

    model = SkillModel()

    class Handler(BaseHTTPRequestHandler):
        """Return actual native Messages SSE with explicit controlled usage."""

        def do_POST(self) -> None:
            """Request the real skill tool at the beginning of each user turn."""

            assert self.path.endswith("/messages")
            model.requests.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
            number = len(model.requests)
            if hold_first is not None and number == 1:
                hold_first.entered.set()
                if not hold_first.release.wait(timeout=20):
                    self.send_error(504)
                    return
            step = (number - 1 - (hold_first is not None)) % (3 if read_asset else 2)
            tool = step == 0 or (step == 1 and read_asset)
            tool_name, arguments = "skill", {"name": "alpha"}
            if step == 1 and read_asset:
                payload = json.dumps(model.requests[-1])
                base = payload.rsplit("Base directory for this skill: ", 1)[1].split("\\n", 1)[0]
                tool_name, arguments = "read", {"file_path": str(Path(base) / "asset.txt")}
            block = (
                {"type": "tool_use", "id": f"skill-{number}", "name": tool_name, "input": {}}
                if tool
                else {"type": "text", "text": ""}
            )
            delta = (
                {"type": "input_json_delta", "partial_json": json.dumps(arguments)}
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
