"""Interrupt one real DSH attempt from an independently reconstructed controller."""

from __future__ import annotations

from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import time
from typing import Any
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.backends.dsh_headless import DshHeadlessSession
from houmao.agents.realm_controller.gateway_models import GatewayRequestCreateV1
from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.usage_support import UsageService
from tests.integration.agents.dsh.test_gateway_passive import _gateway_runtime


@pytest.mark.parametrize("operation", ["interrupt", "stop", "gateway_interrupt"])
def test_independent_controller_interrupts_the_bound_native_attempt(
    tmp_path: Path,
    dsh_executable: Path,
    isolated_tmux: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """Control reconstruction cancels the original worker without another provider request."""

    assert isolated_tmux.is_absolute()
    started = threading.Event()
    release = threading.Event()
    requests: list[dict[str, Any]] = []

    class Handler(BaseHTTPRequestHandler):
        """Hold one synthetic Messages response until native cancellation is observable."""

        def do_POST(self) -> None:
            """Send partial text while the exact native request remains active."""

            requests.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.end_headers()
            frames = [
                {
                    "type": "message_start",
                    "message": {
                        "id": "held-message",
                        "type": "message",
                        "role": "assistant",
                        "model": "controlled",
                        "content": [],
                        "usage": {"input_tokens": 11, "output_tokens": 0},
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
                    "delta": {"type": "text_delta", "text": "Controlled work is active"},
                },
            ]
            try:
                for frame in frames:
                    self.wfile.write(
                        f"event: {frame['type']}\ndata: {json.dumps(frame)}\n\n".encode()
                    )
                self.wfile.flush()
                started.set()
                release.wait(30)
            except OSError:
                return

        def log_message(self, format: str, *args: Any) -> None:
            """Keep local synthetic transport output out of native diagnostics."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    serving = threading.Thread(target=server.serve_forever, daemon=True)
    serving.start()
    runtime, backend = _gateway_runtime(
        tmp_path,
        dsh_executable,
        f"http://127.0.0.1:{server.server_port}/v1",
        monkeypatch,
        isolated_tmux,
    )
    controller = runtime.m_adapter._resume_controller()
    errors: list[BaseException] = []
    events: list[SessionEvent] = []

    def work() -> None:
        """Keep the original control invocation waiting for its real native outcome."""

        try:
            events.extend(
                controller.send_prompt(
                    "Hold controlled work until explicitly interrupted",
                    turn_artifact_dir_name="held-attempt",
                    refresh_registry=False,
                )
            )
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=work)
    accepted = None
    if operation == "gateway_interrupt":
        runtime.start()
        accepted = runtime.create_request(
            GatewayRequestCreateV1(
                kind="submit_prompt",
                payload={"prompt": "Hold controlled gateway work", "turn_id": "held-attempt"},
            )
        )
    else:
        worker.start()
    try:
        assert started.wait(15)
        binding = json.loads((backend._plan.home_path / "houmao-native-session.json").read_text())
        restored = DshHeadlessSession(
            launch_plan=backend._plan,
            role_name="controlled",
            session_manifest_path=controller.manifest_path,
            agent_def_dir=tmp_path / "agent-defs",
            state=replace(backend.state),
        )
        independent = replace(controller, backend_session=restored)
        monkeypatch.setattr(independent, "refresh_shared_registry_record", Mock())
        monkeypatch.setattr(independent, "publish_stopped_shared_registry_record", Mock())

        result = independent.stop() if operation == "stop" else independent.interrupt()

        assert result.status == "ok"
        if accepted is None:
            worker.join(20)
            assert not worker.is_alive() and not errors
            assert any(
                event.kind == "done" and (event.payload or {}).get("outcome") == "interrupted"
                for event in events
            )
        else:
            deadline = time.monotonic() + 20
            state = runtime.ag_ui_request_state(accepted.request_id)
            while state is not None and not state.terminal and time.monotonic() < deadline:
                time.sleep(0.02)
                state = runtime.ag_ui_request_state(accepted.request_id)
            assert state is not None and state.state == "failed"
            assert isinstance(state.result, dict) and state.result["outcome"] == "interrupted"
            assert state.result["source"] == "owner_process"
        assert len(requests) == 1
        assert restored.state.session_id == binding["native_session_id"]
        turn = controller.manifest_path.parent / "manifest.turn-artifacts/held-attempt"
        assert (turn / "exitcode").read_text().strip() == "130"
        closure = json.loads((turn / "dsh-native-closure.json").read_text())
        process = json.loads((turn / "process.json").read_text())
        assert closure["source"] == "owner_process" and closure["attempt_id"] == "held-attempt"
        assert closure["process_id"] == binding["process_id"] == process["child_pid"]
        assert closure["process_birth_token"] == process["child_birth_token"]
        raw = [json.loads(line) for line in (turn / "stdout.jsonl").read_text().splitlines()]
        assert raw[0]["type"] == "session" and raw[0]["sessionId"] == binding["native_session_id"]
        assert not any(frame.get("reason", {}) == {"kind": "completed"} for frame in raw)
        usage = UsageService.from_manifest(controller.manifest_path)
        usage.reconcile()
        assert [record.outcome for record in usage.get_usage().records] == ["interrupted"]
    finally:
        release.set()
        if operation == "gateway_interrupt":
            runtime.shutdown()
        else:
            worker.join(10)
        backend.configure_stop_force_cleanup(force_cleanup=True)
        backend.terminate()
        server.shutdown()
        server.server_close()
        serving.join(3)
