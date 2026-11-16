"""Interrupt one real DSH attempt from an independently reconstructed controller."""

from __future__ import annotations

from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from typing import Any
from unittest.mock import Mock

import pytest

from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.usage_support import UsageService
from tests.integration.agents.dsh.test_gateway_passive import _gateway_runtime


@pytest.mark.parametrize("operation", ["interrupt", "stop"])
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
        tmp_path, dsh_executable, f"http://127.0.0.1:{server.server_port}/v1", monkeypatch
    )
    controller = runtime.m_adapter._resume_controller()
    errors: list[BaseException] = []

    def work() -> None:
        """Keep the original control invocation waiting for its real native outcome."""

        try:
            controller.send_prompt(
                "Hold controlled work until explicitly interrupted",
                turn_artifact_dir_name="held-attempt",
                refresh_registry=False,
            )
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=work)
    worker.start()
    try:
        assert started.wait(15)
        binding = json.loads((backend._plan.home_path / "houmao-native-session.json").read_text())
        restored = DshAcpSession(
            launch_plan=backend._plan,
            role_name="controlled",
            session_manifest_path=controller.manifest_path,
            agent_def_dir=tmp_path / "agent-defs",
            state=replace(backend.state),
        )
        independent = replace(controller, backend_session=restored)
        monkeypatch.setattr(independent, "refresh_shared_registry_record", Mock())
        monkeypatch.setattr(independent, "publish_stopped_shared_registry_record", Mock())

        result = independent.interrupt() if operation == "interrupt" else independent.stop()

        assert result.status == "ok"
        worker.join(20)
        assert not worker.is_alive()
        assert len(requests) == 1
        assert errors and isinstance(errors[0], BackendExecutionError)
        assert restored.state.session_id == binding["native_session_id"]
        turn = controller.manifest_path.parent / "manifest.turn-artifacts/held-attempt"
        assert restored._runner.m_active_turn_dir == turn
        assert (turn / "exitcode").read_text().strip() == (
            "130" if operation == "interrupt" else "-9"
        )
        raw = [
            json.loads(line) for line in (turn / "provider-stdout.jsonl").read_text().splitlines()
        ]
        if operation == "interrupt":
            assert any(frame.get("result", {}).get("stopReason") == "cancelled" for frame in raw)
        usage = UsageService.from_manifest(controller.manifest_path)
        usage.reconcile()
        assert [record.outcome for record in usage.get_usage().records] == ["interrupted"]
    finally:
        release.set()
        worker.join(10)
        backend.configure_stop_force_cleanup(force_cleanup=True)
        backend.terminate()
        server.shutdown()
        server.server_close()
        serving.join(3)
