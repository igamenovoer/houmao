"""Serve deterministic Chat Completions for explicitly selected local fixtures."""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4

from houmao.agents.tool_params.hermes import validate_hermes_reasoning_effort

from fixturelib.auth import external_root, private_write
from fixturelib.config import FixtureError

_MODEL = "houmao-fixture-chat"
_ANSWER = "Houmao fixture response."
_MAX_BODY = 1024 * 1024


class ChatPeerHandler(BaseHTTPRequestHandler):
    """Verify a synthetic binding and serve fixed native-format responses."""

    def __init__(
        self,
        *args: Any,
        token: str,
        observe: Callable[[dict[str, Any]], None],
        **kwargs: Any,
    ) -> None:
        """Retain only the peer's owner-selected evidence sink and synthetic token."""

        self.m_token: str = token
        self.m_observe: Callable[[dict[str, Any]], None] = observe
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Expose the selected fixture model and check the authentication header."""

        if not self._authorized():
            return
        model = {"id": _MODEL, "object": "model", "created": 0, "owned_by": "houmao"}
        if self.path == "/v1/models":
            self._send_json(200, {"object": "list", "data": [model]})
        elif self.path == f"/v1/models/{_MODEL}":
            self._send_json(200, model)
        else:
            self._send_json(404, {"error": {"message": "Unsupported fixture route"}})

    def do_POST(self) -> None:
        """Emit the same deterministic assistant answer in streamed or JSON format."""

        if not self._authorized():
            return
        if self.path != "/v1/chat/completions":
            self._send_json(404, {"error": {"message": "Unsupported fixture route"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= _MAX_BODY:
                raise ValueError("Invalid body size")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict) or body.get("model") != _MODEL:
                raise ValueError("Wrong model")
            messages = body.get("messages")
            if not isinstance(messages, list) or not messages:
                raise ValueError("Missing messages")
        except (UnicodeError, ValueError):
            self._send_json(400, {"error": {"message": "Invalid fixture completion request"}})
            return
        observation = {"model": _MODEL, "messages": messages, "authorization_verified": True}
        if "reasoning_effort" in body:
            try:
                observation["reasoning_effort"] = validate_hermes_reasoning_effort(
                    body["reasoning_effort"]
                )
            except ValueError:
                observation["reasoning_effort"] = "<invalid>"
        self.m_observe(observation)
        usage = {"prompt_tokens": 12, "completion_tokens": 4, "total_tokens": 16}
        base = {"id": "chatcmpl-" + uuid4().hex, "created": 0, "model": _MODEL}
        if body.get("stream") is True:
            base["object"] = "chat.completion.chunk"
            frames = [
                {
                    **base,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": _ANSWER}}],
                },
                {
                    **base,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                    "usage": usage,
                },
            ]
            stream = "".join(f"data: {json.dumps(frame)}\n\n" for frame in frames)
            self._send(200, "text/event-stream", (stream + "data: [DONE]\n\n").encode())
            return
        self._send_json(
            200,
            {
                **base,
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": _ANSWER},
                        "finish_reason": "stop",
                    }
                ],
                "usage": usage,
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        """Keep native peer diagnostics limited to private fixture evidence."""

    def _authorized(self) -> bool:
        """Require the elected synthetic credential on every request."""

        if self.headers.get("Authorization") == f"Bearer {self.m_token}":
            return True
        self._send_json(401, {"error": {"message": "Selected fixture credential required"}})
        return False

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        """Send one bounded JSON response."""

        self._send(status, "application/json", json.dumps(payload).encode())

    def _send(self, status: int, content_type: str, payload: bytes) -> None:
        """Supply a deterministic content type and length."""

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve_chat_peer(state_dir: Path) -> None:
    """Run a foreground loopback peer and publish explicit self-hosted inputs."""

    root = external_root("run", override=state_dir)
    try:
        root.mkdir(parents=True, mode=0o700)
    except FileExistsError:
        raise FixtureError("Select an unused chat-peer state directory") from None
    token = "hf-peer-" + uuid4().hex
    evidence_path = root / "requests.jsonl"
    lock = threading.Lock()

    def observe(request: dict[str, Any]) -> None:
        """Save selected private request evidence without the credential."""

        with lock:
            descriptor = os.open(evidence_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "a", encoding="utf-8") as sink:
                sink.write(json.dumps(request) + "\n")

    handler = partial(ChatPeerHandler, token=token, observe=observe)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        env_file = root / "peer.env"
        private_write(
            env_file,
            (
                f"HOUMAO_TEST_SELF_HOSTED_MODEL={_MODEL}\n"
                f"HOUMAO_TEST_SELF_HOSTED_API_KEY={token}\n"
                f"HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL={base_url}\n"
            ).encode(),
        )
        print(
            json.dumps({"env_file": str(env_file), "model": _MODEL, "base_url": base_url}),
            flush=True,
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
