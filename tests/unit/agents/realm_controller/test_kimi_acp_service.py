"""Exercise persistent Kimi ACP against a real subprocess and controlled native journal."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading

import pytest

from houmao.agents.realm_controller.backends.kimi_acp_service import (
    KimiAcpServiceProvider,
    create_kimi_service_provider,
)
from houmao.agents.realm_controller.backends.service_runtime import (
    ServiceOperationContext,
    ServiceOwnerConfig,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    ServiceStartupCheck,
    ServiceStartupCompatibilityError,
)
from houmao.hook_observation.kimi_journal import kimi_native_workspace_path


_PEER = """
import json
import os
from pathlib import Path
import sys

os.umask(0o077)
root = Path(os.environ["HOUMAO_PEER_ROOT"])
session = "session-1"
wire = Path(os.environ["HOUMAO_PEER_WIRE"])
ordinal = 0

def send(frame):
    print(json.dumps({"jsonrpc": "2.0", **frame}), flush=True)

def reply(request, result):
    send({"id": request["id"], "result": result})

def record(row):
    with wire.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({"agentId": "main", **row}) + "\\n")

def updates(text):
    send({"method": "session/update", "params": {"sessionId": session, "update": {
        "sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}}}})

def config(mode="default"):
    def option(name, value):
        return {"id": name, "type": "select", "currentValue": value, "options": [{"value": value}]}
    return {"configOptions": [option("model", "local-qwen"), option("mode", mode)]}

def receive():
    line = sys.stdin.readline()
    return json.loads(line) if line else None

def reverse(method, params, request_id):
    send({"id": request_id, "method": method, "params": params})
    answer = receive()
    assert answer["id"] == request_id
    return answer

while (frame := receive()) is not None:
    method = frame["method"]
    with (root / "request-methods.jsonl").open("a") as log:
        log.write(json.dumps(method) + "\\n")
    params = frame.get("params", {})
    if method == "initialize":
        assert sys.argv[1:] == ["acp"] and params["clientCapabilities"] == {}
        version = os.environ.get("HOUMAO_PEER_VERSION", "2.6.0")
        capabilities = {"close": {}}
        if os.environ.get("HOUMAO_PEER_CONTINUATION", "resume") == "resume":
            capabilities["resume"] = {}
        protocol = json.loads(os.environ.get("HOUMAO_PEER_PROTOCOL", "1"))
        sessions = json.loads(os.environ.get("HOUMAO_PEER_SESSION_CAPABILITIES", json.dumps(capabilities)))
        reply(frame, {"protocolVersion": protocol, "agentInfo": {"version": version},
                      "agentCapabilities": {"sessionCapabilities": sessions,
                          "loadSession": os.environ.get("HOUMAO_PEER_CONTINUATION") == "load"}})
    elif method in ("session/new", "session/resume", "session/load"):
        assert params["cwd"] == os.getcwd() and params["mcpServers"] == []
        if method == "session/new":
            wire.parent.mkdir(parents=True)
            (wire.parents[2] / "state.json").write_text(json.dumps({"id": session, "cwd": os.getcwd()}))
            record({"type": "metadata"})
            reply(frame, {**config(os.environ.get("HOUMAO_PEER_START_MODE", "default")), "sessionId": session})
        else:
            assert params["sessionId"] == session
            if method == "session/load":
                updates("HISTORICAL ACP TEXT")
            reply(frame, config(os.environ.get("HOUMAO_PEER_START_MODE", "default")))
    elif method == "session/set_config_option":
        expected_mode = os.environ.get("HOUMAO_PEER_EXPECT_MODE", "auto")
        assert params == {"sessionId": session, "configId": "mode", "value": expected_mode}
        reply(frame, config(os.environ.get("HOUMAO_PEER_ECHO_MODE", expected_mode)))
    elif method == "session/prompt":
        assert params["sessionId"] == session
        [block] = params["prompt"]
        text = block["text"]
        if text == "disconnect":
            sys.exit(0)
        if text == "no native turn":
            reply(frame, {"stopReason": "end_turn"})
            continue
        prompt_id = f"prompt-{ordinal}"
        input_block = {**block, "text": "wrong request input"} if text == "foreign input" else block
        record({"type": "turn.prompt", "turnId": ordinal, "promptId": prompt_id,
                "origin": {"kind": "user"}, "input": [input_block]})
        updates("UNCORRELATED ACP TEXT")
        if text == "permissions":
            permission = {"sessionId": session, "options": [
                {"optionId": "approve_once", "kind": "allow_once"},
                {"optionId": "reject", "kind": "reject_once"}]}
            assert reverse("session/request_permission", permission, "approval")["result"] == {
                "outcome": {"outcome": "selected", "optionId": "reject"}}
            question = {"sessionId": session, "options": [{"optionId": "q0_a", "kind": "allow_once"}]}
            assert reverse("session/request_permission", question, "question")["result"] == {
                "outcome": {"outcome": "cancelled"}}
            assert reverse("fs/read_text_file", {"sessionId": session}, "unsupported")["error"]["code"] == -32601
        if text == "hold":
            assert receive() == {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session}}
        reason = "cancelled" if text == "hold" else "failed" if text == "fail" else "completed"
        record({"type": "context.append_loop_event", "event": {"type": "content.part",
            "turnId": str(ordinal), "part": {"type": "text", "text": f"journal {ordinal}"}}})
        record({"type": "turn.ended", "turnId": ordinal, "reason": reason})
        record({"type": "prompt.aborted" if reason == "cancelled" else "prompt.completed",
                "promptId": prompt_id, "reason": reason})
        ordinal += 1
        reply(frame, {"stopReason": "cancelled" if reason == "cancelled" else "end_turn"})
        updates("LATE ACP TEXT")
    elif method == "session/close":
        reply(frame, None)
    else:
        raise AssertionError(method)
"""


@pytest.fixture
def peer_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ServiceOwnerConfig:
    """Create one explicitly selected local subprocess with no ambient credentials."""

    executable = tmp_path / "kimi"
    executable.write_text(f"#!{sys.executable}\n{_PEER}")
    executable.chmod(0o700)
    home, workspace, owner = (tmp_path / name for name in ("home", "workspace", "owner"))
    for directory in (home, workspace, owner):
        directory.mkdir(mode=0o700)
    wire = kimi_native_workspace_path(home, workspace) / "session-1" / "agents/main/wire.jsonl"
    monkeypatch.setattr(KimiAcpServiceProvider, "_begin_usage", lambda *_: None)
    return ServiceOwnerConfig(
        backend="kimi_acp",
        executable=str(executable),
        arguments=["acp"],
        working_directory=workspace,
        home_path=home,
        environment={
            "KIMI_CODE_HOME": str(home),
            "HOUMAO_PEER_ROOT": str(owner),
            "HOUMAO_PEER_WIRE": str(wire),
        },
        metadata={"kimi_acp": {"detected_version": "2.6.0", "permission_mode": "auto"}},
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
    """Capture owner callback order without depending on wall-clock events."""

    directory = config.root / name
    directory.mkdir()
    events: list[str | None] = []
    handed_off = threading.Event()

    def record(native: str | None) -> None:
        events.append(native)
        handed_off.set()

    return (
        ServiceOperationContext(
            name, directory, lambda: events.append("authorized"), record, lambda _: None
        ),
        events,
        handed_off,
    )


def test_kimi_service_permits_one_pending_operation_and_only_exact_cancel(
    peer_config: ServiceOwnerConfig,
) -> None:
    provider = create_kimi_service_provider(peer_config)
    try:
        pid, birth = provider.process_id, provider.process_birth_token
        first, callbacks, _ = _operation(peer_config, "first")
        result = provider.prompt("permissions", execution_model=None, operation=first)
        assert result.outcome == "completed" and result.native_turn_id == "0"
        assert [event.message for event in result.events if event.kind == "assistant"] == [
            "journal 0"
        ]
        assert callbacks == ["authorized", None, "0"]
        receipt = json.loads((first.turn_dir / "kimi-native-turn.json").read_text())
        assert receipt["process_id"] == pid and receipt["process_birth_token"] == birth
        assert receipt["terminal"] == "completed" and receipt["native_turn_id"] == "0"
        interval = Path(receipt["journal_path"]).read_bytes()[
            receipt["journal_baseline_offset"] : receipt["journal_settled_offset"]
        ]
        assert interval.endswith(b"\n") and b"prompt.completed" in interval
        assert b"metadata" not in interval
        second, _, handed_off = _operation(peer_config, "second")
        with ThreadPoolExecutor() as executor:
            pending = executor.submit(
                provider.prompt, "hold", execution_model=None, operation=second
            )
            assert handed_off.wait(3)
            assert not provider.cancel(first.request_id)
            assert provider.cancel(second.request_id)
            assert not provider.cancel(second.request_id)
            result = pending.result(timeout=3)
        assert result.outcome == "interrupted" and result.native_turn_id == "1"
        assert provider.connection_ready and provider.process_id == pid
        stopped = json.loads((second.turn_dir / "kimi-native-turn.json").read_text())
        assert stopped["terminal"] == "interrupted"
    finally:
        provider.close()


@pytest.mark.parametrize(
    ("text", "outcome"),
    [
        ("fail", "failed"),
        ("no native turn", "uncertain"),
        ("foreign input", "uncertain"),
        ("disconnect", "uncertain"),
    ],
)
def test_kimi_does_not_accept_bare_end_turn_or_disconnection_as_success(
    peer_config: ServiceOwnerConfig, monkeypatch: pytest.MonkeyPatch, text: str, outcome: str
) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.kimi_acp_service._JOURNAL_TIMEOUT", 0.2
    )
    provider = create_kimi_service_provider(peer_config)
    operation, _, _ = _operation(peer_config, "operation")
    try:
        result = provider.prompt(text, execution_model=None, operation=operation)
        assert result.outcome == outcome
        assert provider.connection_ready == (outcome == "failed")
        assert (operation.turn_dir / "kimi-native-turn.json").exists() == (outcome == "failed")
    finally:
        provider.close()
    assert (peer_config.root / "request-methods.jsonl").read_text().count("session/prompt") == 1


def test_unapproved_or_slash_prompt_cannot_write_a_native_frame(
    peer_config: ServiceOwnerConfig,
) -> None:
    provider = create_kimi_service_provider(peer_config)
    operation, callbacks, _ = _operation(peer_config, "operation")

    def revoked() -> None:
        raise BackendExecutionError("Revoked dispatch")

    try:
        with pytest.raises(BackendExecutionError, match="slash command"):
            provider.prompt("/clear", execution_model=None, operation=operation)
        fenced = ServiceOperationContext(
            operation.request_id,
            operation.turn_dir,
            revoked,
            operation.record_handoff,
            operation.publish_event,
        )
        with pytest.raises(BackendExecutionError, match="Revoked dispatch"):
            provider.prompt("text", execution_model=None, operation=fenced)
        assert provider.connection_ready and not callbacks
        assert "session/prompt" not in (peer_config.root / "request-methods.jsonl").read_text()
    finally:
        provider.close()


def test_exact_load_requires_the_workspace_and_replay_cannot_create_output(
    peer_config: ServiceOwnerConfig,
) -> None:
    exact = peer_config.model_copy(update={"session_id": "session-1"})
    with pytest.raises(BackendExecutionError, match="selected private workspace"):
        create_kimi_service_provider(exact)
    assert not (exact.root / "request-methods.jsonl").exists()
    wire = Path(exact.environment["HOUMAO_PEER_WIRE"])
    wire.parent.mkdir(parents=True)
    state = wire.parents[2] / "state.json"
    state.write_text(json.dumps({"id": "session-1", "cwd": str(exact.home_path)}))
    state.chmod(0o600)
    with pytest.raises(BackendExecutionError, match="selected private workspace"):
        create_kimi_service_provider(exact)
    state.write_text(json.dumps({"id": "session-1", "cwd": str(exact.working_directory)}))
    wire.write_text(json.dumps({"type": "turn.prompt", "agentId": "main", "turnId": 99}) + "\n")
    wire.chmod(0o600)
    exact = exact.model_copy(
        update={"environment": {**exact.environment, "HOUMAO_PEER_CONTINUATION": "load"}}
    )
    provider = create_kimi_service_provider(exact)
    try:
        operation, _, _ = _operation(exact, "post-load")
        result = provider.prompt("plain prompt", execution_model=None, operation=operation)
        assert result.outcome == "completed"
        assert [event.message for event in result.events if event.kind == "assistant"] == [
            "journal 0"
        ]
        assert "session/load" in (exact.root / "request-methods.jsonl").read_text()
    finally:
        provider.close()


@pytest.mark.parametrize(
    ("mode", "expected"), [("auto", "auto"), ("manual", "default"), ("yolo", "yolo")]
)
def test_permission_mode_binds_on_fresh_and_exact_start(
    peer_config: ServiceOwnerConfig, mode: str, expected: str
) -> None:
    """Project the selected mode on the original conversation and its exact continuation."""

    config = peer_config.model_copy(
        update={
            "metadata": {"kimi_acp": {**peer_config.metadata["kimi_acp"], "permission_mode": mode}},
            "environment": {
                **peer_config.environment,
                "HOUMAO_PEER_START_MODE": "plan",
                "HOUMAO_PEER_EXPECT_MODE": expected,
            },
        }
    )
    provider = create_kimi_service_provider(config)
    try:
        session_id = provider.native_session_id
        assert provider.connection_ready
        assert json.loads((config.root / "kimi-acp-binding.json").read_text())["native_mode"] == (
            expected
        )
    finally:
        provider.close()

    resumed_root = config.root / "resume"
    resumed_root.mkdir()
    exact = config.model_copy(
        update={
            "root": resumed_root,
            "session_id": session_id,
            "environment": {**config.environment, "HOUMAO_PEER_ROOT": str(resumed_root)},
        }
    )
    provider = create_kimi_service_provider(exact)
    try:
        assert provider.native_session_id == session_id
        assert provider.connection_ready
        binding = json.loads((resumed_root / "kimi-acp-binding.json").read_text())
        assert binding["binding_method"] == "session/resume"
        assert binding["native_mode"] == expected
    finally:
        provider.close()


def test_permission_mismatch_blocks_readiness(peer_config: ServiceOwnerConfig) -> None:
    """Require the native binding to confirm the requested launch policy."""

    config = peer_config.model_copy(
        update={"environment": {**peer_config.environment, "HOUMAO_PEER_ECHO_MODE": "yolo"}}
    )
    with pytest.raises(ServiceStartupCompatibilityError) as exc_info:
        create_kimi_service_provider(config)
    assert exc_info.value.check is ServiceStartupCheck.KIMI_PERMISSION_MODE
    assert not (config.root / "kimi-acp-binding.json").exists()


@pytest.mark.parametrize(
    ("metadata_version", "peer_version"),
    [("2.6.0", "2.6.0"), ("2.7.2", "2.7.2"), ("2.7.2-rc.1", "2.7.2rc1")],
)
def test_verified_peer_binding_records_the_actual_tool_version(
    peer_config: ServiceOwnerConfig, metadata_version: str, peer_version: str
) -> None:
    """Allow later builds and compare equivalent version spellings by normalized values."""

    config = peer_config.model_copy(
        update={
            "metadata": {"kimi_acp": {"detected_version": metadata_version}},
            "environment": {**peer_config.environment, "HOUMAO_PEER_VERSION": peer_version},
        }
    )
    provider = create_kimi_service_provider(config)
    try:
        assert provider.connection_ready and provider.native_session_id == "session-1"
        binding = json.loads((config.root / "kimi-acp-binding.json").read_text())
        assert binding["tool_version"] == peer_version
        assert binding["agent_capabilities"]["sessionCapabilities"]["resume"] == {}
    finally:
        provider.close()


@pytest.mark.parametrize(
    ("environment", "check"),
    [
        ({"HOUMAO_PEER_VERSION": "2.7.2"}, ServiceStartupCheck.KIMI_VERSION),
        ({"HOUMAO_PEER_VERSION": "invalid"}, ServiceStartupCheck.KIMI_VERSION),
        ({"HOUMAO_PEER_PROTOCOL": "2"}, ServiceStartupCheck.KIMI_PROTOCOL),
        ({"HOUMAO_PEER_PROTOCOL": "true"}, ServiceStartupCheck.KIMI_PROTOCOL),
        ({"HOUMAO_PEER_SESSION_CAPABILITIES": "[]"}, ServiceStartupCheck.KIMI_CAPABILITIES),
    ],
)
def test_incompatible_handshake_fails_before_session_creation(
    peer_config: ServiceOwnerConfig, environment: dict[str, str], check: ServiceStartupCheck
) -> None:
    """Check executable identity independently of protocol and capability verification."""

    config = peer_config.model_copy(
        update={"environment": {**peer_config.environment, **environment}}
    )
    with pytest.raises(ServiceStartupCompatibilityError) as exc_info:
        create_kimi_service_provider(config)
    assert exc_info.value.check is check
    assert (config.root / "request-methods.jsonl").read_text().splitlines() == ['"initialize"']
    assert not (config.root / "kimi-acp-binding.json").exists()


def test_below_floor_executable_is_refused_before_spawning_acp_peer(
    peer_config: ServiceOwnerConfig,
) -> None:
    """Reject a launch plan below the configured minimum before ACP can run."""

    config = peer_config.model_copy(
        update={"metadata": {"kimi_acp": {"detected_version": "2.5.9"}}}
    )
    with pytest.raises(ServiceStartupCompatibilityError) as exc_info:
        create_kimi_service_provider(config)
    assert exc_info.value.check is ServiceStartupCheck.KIMI_EXECUTABLE_VERSION
    assert not (config.root / "request-methods.jsonl").exists()


def test_advertised_model_must_match_explicit_launch_selection(
    peer_config: ServiceOwnerConfig,
) -> None:
    config = peer_config.model_copy(
        update={
            "metadata": {
                "kimi_acp": {
                    **peer_config.metadata["kimi_acp"],
                    "configured_model": "different-model",
                }
            }
        }
    )
    with pytest.raises(BackendExecutionError, match="configured native model"):
        create_kimi_service_provider(config)
    assert not (config.root / "kimi-acp-binding.json").exists()
