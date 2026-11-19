"""Exercise the Codex service against a deterministic native-protocol subprocess."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading

import pytest

from houmao.agents.realm_controller.backends.codex_app_server import (
    CodexAppServerProvider,
    create_codex_service_provider,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
    ServiceOwnerConfig,
)
from houmao.agents.realm_controller.errors import BackendExecutionError


_THREAD = "00000000-0000-4000-8000-000000000001"
_PEER = """
import json
import os
from pathlib import Path
import sys
import time

os.umask(0o077)
home = Path(os.environ["CODEX_HOME"])
root = Path(os.environ["HOUMAO_PEER_ROOT"])
thread = "00000000-0000-4000-8000-000000000001"
foreign = "00000000-0000-4000-8000-000000000099"
rollout = home / "sessions" / ("rollout-2026-11-19T00-00-00-" + thread + ".jsonl")
initialized = False
bound = False
turn_index = 0

def send(frame):
    print(json.dumps(frame), flush=True)

def reply(frame, result):
    send({"id": frame["id"], "result": result})

def receive():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def emit(method, **params):
    send({"method": method, "params": {"threadId": thread, **params}})

def check_request(method, turn, expected):
    send({"method": method, "id": "reverse", "params": {
        "threadId": thread, "turnId": turn, "itemId": "tool",
    }})
    assert receive() == {"id": "reverse", **expected}

def thread_state(status):
    return {"id": thread, "status": {"type": status}, "path": str(rollout),
            "cwd": os.getcwd(), "ephemeral": False}

while (frame := receive()) is not None:
    assert "jsonrpc" not in frame
    method = frame["method"]
    with (root / "methods.jsonl").open("a") as log:
        log.write(json.dumps(method) + "\\n")
    params = frame.get("params", {})
    if method == "initialize":
        assert sys.argv[1:] == ["app-server", "--listen", "stdio://"]
        assert params["clientInfo"]["name"] == "houmao"
        assert params["capabilities"]["experimentalApi"] is False
        assert os.environ["HTTP_PROXY"] == "http://proxy.internal:8080"
        if os.environ.get("HOUMAO_PRESERVE_NO_PROXY_ENV"):
            assert os.environ["NO_PROXY"] == "corp.internal"
        else:
            assert "localhost" in os.environ["NO_PROXY"].split(",")
            assert os.environ["NO_PROXY"] == os.environ["no_proxy"]
        reply(frame, {"userAgent": "houmao/" + os.environ.get("HOUMAO_PEER_VERSION", "0.169.0"),
                      "codexHome": str(home), "platformFamily": "unix", "platformOs": "linux"})
    elif method == "initialized":
        initialized = True
    elif method in ("thread/start", "thread/resume"):
        assert initialized
        assert params["approvalPolicy"] == "never" and params["sandbox"] == "danger-full-access"
        assert params["developerInstructions"] == "Private managed role"
        assert params["config"] == {"model": "local-qwen"}
        if method == "thread/start":
            assert params["cwd"] == os.getcwd() and params["ephemeral"] is False
        else:
            assert params["threadId"] == thread and params["excludeTurns"] is True
            assert all(key not in params for key in ("cwd", "history", "path"))
        bound = True
        reply(frame, {"thread": thread_state("idle"), "cwd": os.getcwd(), "model": "local-qwen",
                      "approvalPolicy": "never", "sandbox": {"type": "dangerFullAccess"}})
    elif method == "thread/read":
        assert initialized and params == {"threadId": thread, "includeTurns": False}
        status = "idle" if bound else "notLoaded"
        if os.environ.get("HOUMAO_PEER_BUSY"):
            status = "active"
        reply(frame, {"thread": thread_state(status)})
    elif method == "turn/start":
        [item] = params["input"]
        text, client = item["text"], params["clientUserMessageId"]
        assert params["threadId"] == thread and item["type"] == "text" and item["textElements"] == []
        if text == "disconnect-before-handle":
            sys.exit(0)
        if text == "overflow-before-handle":
            for _ in range(300):
                emit("item/agentMessage/delta", turnId=foreign, itemId="foreign", delta="overflow")
            continue
        rollout.parent.mkdir(exist_ok=True)
        if not rollout.exists():
            rollout.write_text(json.dumps({"type": "session_meta", "payload": {
                "id": thread, "cwd": os.getcwd(), "cli_version": "0.169.0",
            }}) + "\\n")
        turn_index += 1
        turn = "00000000-0000-4000-8001-" + f"{turn_index:012}"
        admitted = {"turn": {"id": turn, "status": "inProgress"}}
        if text != "early":
            reply(frame, admitted)
        emit("turn/started", turn=admitted["turn"])
        emit("item/completed", turnId=turn, item={"type": "userMessage", "id": "user", "clientId": client})
        emit("item/agentMessage/delta", turnId=foreign, itemId="foreign", delta="FOREIGN")
        emit("turn/completed", turn={"id": foreign, "status": "completed"})
        emit("item/agentMessage/delta", turnId=turn, itemId="assistant", delta="partial")
        if text == "early":
            tool = {"type": "commandExecution", "id": "tool", "command": "PRIVATE ARGUMENT"}
            emit("item/started", turnId=turn, item=tool)
            check_request("item/commandExecution/requestApproval", turn, {"result": {"decision": "decline"}})
            check_request("item/fileChange/requestApproval", turn, {"result": {"decision": "decline"}})
            check_request("item/permissions/requestApproval", turn, {"result": {"permissions": {}, "scope": "turn"}})
            check_request("item/tool/requestUserInput", turn, {"result": {"answers": {}}})
            check_request("account/chatgptAuthTokens/refresh", turn,
                          {"error": {"code": -32601, "message": "Unsupported ACP client request"}})
            emit("item/completed", turnId=turn, item=tool)
        if text == "disconnect-after-handle":
            sys.exit(0)
        status = "completed"
        items = []
        if text == "hold":
            interrupt = receive()
            assert interrupt["method"] == "turn/interrupt"
            assert interrupt["params"] == {"threadId": thread, "turnId": turn}
            reply(interrupt, {})
            time.sleep(0.05)
            status = "interrupted"
        elif text == "failed":
            status = "failed"
        else:
            assistant = {"type": "agentMessage", "id": "assistant", "text": "exact answer"}
            emit("item/completed", turnId=turn, item=assistant)
            emit("item/completed", turnId=turn, item=assistant)
            items = [assistant]
        emit("turn/completed", turn={"id": turn, "status": status, "items": items})
        if text == "early":
            reply(frame, admitted)
    else:
        raise AssertionError(method)
"""


@pytest.fixture
def peer_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ServiceOwnerConfig:
    """Create private local inputs and a credential-free native wire peer."""

    executable = tmp_path / "codex"
    executable.write_text(f"#!{sys.executable}\n{_PEER}")
    executable.chmod(0o700)
    home, workspace, owner = (tmp_path / name for name in ("home", "workspace", "owner"))
    for directory in (home, workspace, owner):
        directory.mkdir(mode=0o700)
    monkeypatch.setattr(CodexAppServerProvider, "_begin_usage", lambda *_: None)
    return ServiceOwnerConfig(
        backend="codex_app_server",
        executable=str(executable),
        arguments=["app-server", "--listen", "stdio://"],
        working_directory=workspace,
        home_path=home,
        environment={
            "CODEX_HOME": str(home),
            "HOUMAO_PEER_ROOT": str(owner),
            "HTTP_PROXY": "http://proxy.internal:8080",
            "NO_PROXY": "corp.internal",
        },
        metadata={
            "codex_app_server": {
                "operator_prompt_mode": "unattended",
                "thread_config": {"model": "local-qwen"},
            }
        },
        role_prompt="Private managed role",
        root=owner,
        manifest_path=tmp_path / "manifest.json",
        agent_id="managed-agent",
        runtime_session_id="runtime-session",
        generation_id="generation",
        service_incarnation="incarnation",
    )


def _operation(
    config: ServiceOwnerConfig, name: str
) -> tuple[ServiceOperationContext, list[str | None], threading.Event]:
    """Record prewrite and handle evidence before any eventual settlement."""

    directory = config.root / name
    directory.mkdir()
    callbacks: list[str | None] = []
    handed_off = threading.Event()

    def handoff(turn: str | None) -> None:
        callbacks.append(turn)
        handed_off.set()

    return (
        ServiceOperationContext(
            name, directory, lambda: callbacks.append("authorized"), handoff, lambda _: None
        ),
        callbacks,
        handed_off,
    )


def test_app_server_correlates_early_and_late_notifications_on_one_process(
    peer_config: ServiceOwnerConfig,
) -> None:
    provider = create_codex_service_provider(peer_config)
    try:
        process, birth = provider.process_id, provider.process_birth_token
        for name in ("early", "late"):
            operation, callbacks, _ = _operation(peer_config, name)
            result = provider.prompt(name, execution_model=None, operation=operation)
            assert result.outcome == "completed" and result.native_turn_id
            assert callbacks == ["authorized", result.native_turn_id]
            assert [item.message for item in result.events if item.kind == "assistant"] == [
                "exact answer"
            ]
            if name == "early":
                assert [
                    event.payload["native_item_phase"]
                    for event in result.events
                    if event.kind == "status"
                ] == ["started", "completed"]
                assert "PRIVATE ARGUMENT" not in repr(result.events)
            receipt = json.loads((operation.turn_dir / "codex-native-turn.json").read_text())
            assert receipt["native_turn_id"] == result.native_turn_id
            assert receipt["native_session_id"] == _THREAD
            assert receipt["native_client_message_id"] == operation.request_id
            assert receipt["process_id"] == process and receipt["process_birth_token"] == birth
            rollout = Path(receipt["rollout_path"])
            assert rollout.is_file()
            assert receipt["rollout_baseline_offset"] == (
                0 if name == "early" else rollout.stat().st_size
            )
        assert provider.connection_ready
    finally:
        provider.close()
    assert not Path(f"/proc/{process}").exists()


def test_app_server_interrupts_only_the_bound_turn(peer_config: ServiceOwnerConfig) -> None:
    provider = create_codex_service_provider(peer_config)
    first, _, _ = _operation(peer_config, "first")
    second, _, handed_off = _operation(peer_config, "second")
    try:
        assert provider.prompt("late", execution_model=None, operation=first).outcome == "completed"
        with ThreadPoolExecutor() as pool:
            future = pool.submit(provider.prompt, "hold", execution_model=None, operation=second)
            assert handed_off.wait(3)
            assert not provider.cancel(first.request_id)
            assert provider.cancel(second.request_id)
            assert not provider.cancel(second.request_id)
            result = future.result(timeout=3)
        assert result.outcome == "interrupted"
        assert [event.message for event in result.events if event.kind == "assistant"] == [
            "partial"
        ]
        assert provider.connection_ready
    finally:
        provider.close()


@pytest.mark.parametrize(
    ("prompt", "outcome", "partial"),
    [
        ("failed", "failed", True),
        ("disconnect-before-handle", "uncertain", False),
        ("disconnect-after-handle", "uncertain", True),
    ],
)
def test_app_server_preserves_failure_and_transport_loss(
    peer_config: ServiceOwnerConfig, prompt: str, outcome: str, partial: bool
) -> None:
    provider = create_codex_service_provider(peer_config)
    operation, callbacks, _ = _operation(peer_config, "attempt")
    try:
        result = provider.prompt(prompt, execution_model=None, operation=operation)
        assert result.outcome == outcome
        assert bool([event for event in result.events if event.kind == "assistant"]) == partial
        assert provider.connection_ready == (outcome == "failed")
        assert callbacks[0] == "authorized"
        assert (len(callbacks) == 2) == (prompt != "disconnect-before-handle")
        assert (operation.turn_dir / "codex-native-turn.json").exists() == (outcome == "failed")
    finally:
        provider.close()
    assert (peer_config.root / "methods.jsonl").read_text().count("turn/start") == 1


@pytest.mark.parametrize("busy", [True, False])
def test_app_server_guards_native_idle_and_prewrite(
    peer_config: ServiceOwnerConfig, busy: bool
) -> None:
    config = peer_config
    if busy:
        config = config.model_copy(
            update={"environment": {**config.environment, "HOUMAO_PEER_BUSY": "1"}}
        )
    provider = create_codex_service_provider(config)
    operation, callbacks, _ = _operation(config, "attempt")

    def revoked() -> None:
        """Veto input at the transport write boundary."""

        raise BackendExecutionError("revoked")

    fenced = ServiceOperationContext(
        operation.request_id,
        operation.turn_dir,
        revoked,
        operation.record_handoff,
        operation.publish_event,
    )
    try:
        with pytest.raises(BackendExecutionError, match="cannot accept" if busy else "revoked"):
            provider.prompt("never transmitted", execution_model=None, operation=fenced)
        assert not callbacks and "turn/start" not in (config.root / "methods.jsonl").read_text()
    finally:
        provider.close()


@pytest.mark.parametrize("foreign_metadata", [False, True])
def test_app_server_fresh_incarnation_resumes_only_exact_owned_rollout(
    peer_config: ServiceOwnerConfig,
    foreign_metadata: bool,
) -> None:
    provider = create_codex_service_provider(peer_config)
    operation, _, _ = _operation(peer_config, "initial")
    try:
        assert (
            provider.prompt("late", execution_model=None, operation=operation).outcome
            == "completed"
        )
    finally:
        provider.close()
    other_root = peer_config.root / "replacement"
    other_root.mkdir()
    exact = peer_config.model_copy(
        update={
            "session_id": _THREAD,
            "root": other_root,
            "service_incarnation": "replacement",
            "environment": {
                **peer_config.environment,
                "HOUMAO_PEER_ROOT": str(other_root),
                "HOUMAO_PRESERVE_NO_PROXY_ENV": "1",
            },
        }
    )
    if foreign_metadata:
        rollout = next((peer_config.home_path / "sessions").glob("rollout-*.jsonl"))
        state = json.loads(rollout.read_text())
        state["payload"]["cwd"] = str(peer_config.home_path)
        rollout.write_text(json.dumps(state) + "\n")
        with pytest.raises(BackendExecutionError, match="exact persisted workspace evidence"):
            create_codex_service_provider(exact)
        assert "thread/resume" not in (other_root / "methods.jsonl").read_text()
        return
    replacement = create_codex_service_provider(exact)
    try:
        assert replacement.native_session_id == _THREAD and replacement.connection_ready
    finally:
        replacement.close()
    methods = (other_root / "methods.jsonl").read_text()
    assert "thread/resume" in methods and "thread/start" not in methods


def test_app_server_pre_response_event_capacity_fails_closed(
    peer_config: ServiceOwnerConfig,
) -> None:
    provider = create_codex_service_provider(peer_config)
    operation, callbacks, _ = _operation(peer_config, "overflow")
    try:
        result = provider.prompt(
            "overflow-before-handle", execution_model=None, operation=operation
        )
        assert result.outcome == "uncertain" and result.native_turn_id is None
        assert callbacks == ["authorized"] and not provider.connection_ready
        assert not (operation.turn_dir / "codex-native-turn.json").exists()
    finally:
        provider.close()


def test_app_server_incompatible_build_refuses_thread_traffic(
    peer_config: ServiceOwnerConfig,
) -> None:
    wrong = peer_config.model_copy(
        update={"environment": {**peer_config.environment, "HOUMAO_PEER_VERSION": "0.168.0"}}
    )
    with pytest.raises(BackendExecutionError, match="headless and tui"):
        create_codex_service_provider(wrong)
    assert (wrong.root / "methods.jsonl").read_text().splitlines() == ['"initialize"']
