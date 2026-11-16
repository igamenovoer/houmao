"""Fence native insertion against caller cancellation during asynchronous preparation."""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession, DshWebSessionState
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebError
from houmao.agents.realm_controller.errors import BackendExecutionError
from tests.integration.agents.dsh.web.conftest import NativeWebGates, NativeWebHost
from tests.integration.agents.dsh.web.test_native_control import wait_terminal


@pytest.mark.parametrize(
    "damage", [None, "cancel", "generation", "binding", "birth", "origin", "expiry", "missing"]
)
def test_native_permission_is_rechecked_after_async_preparation_without_insertion_or_replay(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    damage: str | None,
) -> None:
    """A private logical lifetime fence remains effective while the HTTP call holds its lock."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    manifest = host.root / "permission-manifest.json"
    binding = {
        "registry_generation_id": host.identity["generation"],
        "backend_state": {"web_identity": dict(host.identity)},
    }
    manifest.write_text(json.dumps(binding))
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: None,
        deadline=time.monotonic() + 30,
        manifest_path=manifest,
        generation_id=host.identity["generation"],
    )
    permission: Path = control.prepare_bridge_permission(host.root)
    text = "ordinary lifetime fenced input"
    native_web_gates.hold("prepare", text)
    with ThreadPoolExecutor(max_workers=1) as pool:
        attempt = pool.submit(
            host.client.prompt,
            host.identity,
            text,
            operation_id="lifetime-fence",
            deadline_epoch_ms=int(time.time() * 1000) + 10000,
            dispatch_permission_path=permission,
        )
        try:
            native_web_gates.wait("prepare")
            if damage == "cancel":
                started = time.monotonic()
                control.cancel()
                assert time.monotonic() - started < 1
            elif damage in {"generation", "binding"}:
                if damage == "generation":
                    binding["registry_generation_id"] = "replacement-generation"
                else:
                    binding["backend_state"]["web_identity"]["agent_incarnation"] = "replacement"
                manifest.write_text(json.dumps(binding))
            elif damage in {"birth", "origin", "expiry"}:
                value = json.loads(permission.read_text())
                if damage == "origin":
                    value["origin_pid"] = 2**30
                else:
                    value["origin_birth_token" if damage == "birth" else "expires_at"] = (
                        "proc:replacement" if damage == "birth" else 0
                    )
                permission.write_text(json.dumps(value))
            elif damage == "missing":
                permission.unlink()
            native_web_gates.release("prepare")
            if damage is None:
                assert attempt.result(timeout=10)["message_id"]
            else:
                with pytest.raises(DshWebError) as refused:
                    attempt.result(timeout=10)
                assert refused.value.code == "cancelled"
        finally:
            native_web_gates.release("prepare")
    if damage is None:
        assert wait_terminal(host, "lifetime-fence")["result"] == "completed"
        assert len(controlled_messages_server[1]) == 1
    else:
        assert host.client.receipt(host.identity, "lifetime-fence") is None
        assert host.client.state(host.identity)["pending_inbox"] == []
        assert controlled_messages_server[1] == []
    if permission.exists():
        assert text not in permission.read_text()


def test_semantic_backend_cancellation_during_native_prepare_returns_without_http_lock_wait(
    native_web_factory: Callable[..., NativeWebHost],
    native_web_gates: NativeWebGates,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runtime writes its native fence and revokes it before asynchronous preparation ends."""

    host = native_web_factory(extra_plugins=[native_web_gates.plugin])
    manifest = host.root / "permission-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "registry_generation_id": host.identity["generation"],
                "backend_state": {"web_identity": dict(host.identity)},
            }
        )
    )
    backend = DshWebSession()
    backend.m_manifest_path = manifest
    backend.m_client = host.client
    backend.m_state = DshWebSessionState(
        origin=host.origin,
        web_identity=dict(host.identity),
        bootstrap_path=str(host.root / "bootstrap.json"),
        cookie_path=str(host.root / "api.json"),
        control_path=str(host.root / "control.json"),
        supervisor_pid=host.process.pid,
        supervisor_birth_token=host.birth_token,
        tmux_session_name="unused-native-only-fixture",
        evidence_path=str(host.root / "evidence.jsonl"),
        working_directory=str(host.root),
    )
    monkeypatch.setattr(backend, "_begin_managed_accounting", lambda _operation: None)
    control = HeadlessDispatchControl.from_callbacks(
        allowed=lambda: True,
        confirmed=lambda: None,
        deadline=time.monotonic() + 30,
        manifest_path=manifest,
        generation_id=host.identity["generation"],
    )
    backend.configure_request_dispatch(control)
    text = "cancel actual semantic preparation"
    native_web_gates.hold("prepare", text)
    with ThreadPoolExecutor(max_workers=1) as pool:
        attempt = pool.submit(backend.send_prompt, text, turn_artifact_dir_name="logical-cancel")
        try:
            native_web_gates.wait("prepare")
            started = time.monotonic()
            backend.cancel_request_dispatch(control)
            assert time.monotonic() - started < 1
            native_web_gates.release("prepare")
            with pytest.raises(BackendExecutionError, match="cancelled"):
                attempt.result(timeout=10)
        finally:
            native_web_gates.release("prepare")
    assert not control.m_handoff_confirmed.is_set()
    assert host.client.receipt(host.identity, "logical-cancel") is None
    assert host.client.state(host.identity)["pending_inbox"] == []
    assert controlled_messages_server[1] == []
