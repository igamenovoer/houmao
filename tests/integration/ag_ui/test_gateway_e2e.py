"""End-to-end AG-UI wire coverage for the live per-agent gateway route."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
import json
import sqlite3
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from houmao.ag_ui.graphics import HOUMAO_RENDER_GRAPHIC_TOOL_NAME
from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller import gateway_service
from houmao.agents.realm_controller.backends.headless_output import (
    CanonicalHeadlessEvent,
    canonical_headless_event_artifact_path,
)
from houmao.agents.realm_controller.gateway_models import GatewayAttachContractV1
from houmao.agents.realm_controller.gateway_service import GatewayServiceRuntime, create_app
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    ensure_gateway_capability,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RoleInjectionPlan,
)


ArtifactFactory = Callable[[str, str], Sequence[CanonicalHeadlessEvent]]


@dataclass(frozen=True)
class _SubmittedPrompt:
    """One prompt submitted through the fake gateway execution adapter."""

    prompt: str
    turn_id: str | None
    session_selection: HeadlessTurnSessionSelection | None
    execution_model: ModelConfig | None


class _FakeHeadlessGatewayAdapter(gateway_service._LocalHeadlessGatewayAdapter):
    """Gateway execution adapter that writes deterministic headless artifacts."""

    def __init__(
        self,
        *,
        attach_contract: GatewayAttachContractV1,
        artifact_factory: ArtifactFactory,
    ) -> None:
        """Store the attach contract and deterministic artifact factory."""

        self.m_attach_contract: GatewayAttachContractV1 = attach_contract
        self.m_artifact_factory: ArtifactFactory = artifact_factory
        self.m_submitted_prompts: list[_SubmittedPrompt] = []
        self.m_interrupt_count: int = 0

    @property
    def attach_contract(self) -> GatewayAttachContractV1:
        """Return the strict attach contract."""

        return self.m_attach_contract

    def inspect_target(self) -> gateway_service._GatewayTargetState:
        """Return a ready headless target state."""

        return gateway_service._GatewayTargetState(
            instance_id=self.m_attach_contract.runtime_session_id
            or self.m_attach_contract.attach_identity,
            connectivity="connected",
            terminal_surface_eligibility="ready",
            prompt_admission_open=True,
        )

    def submit_prompt(
        self,
        *,
        prompt: str,
        turn_id: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> None:
        """Record the prompt and write canonical events for its turn id."""

        self.m_submitted_prompts.append(
            _SubmittedPrompt(
                prompt=prompt,
                turn_id=turn_id,
                session_selection=session_selection,
                execution_model=execution_model,
            )
        )
        if turn_id is None:
            raise gateway_service.GatewayError("AG-UI E2E fake requires turn_id.")
        manifest_path_value = self.m_attach_contract.manifest_path
        if manifest_path_value is None:
            raise gateway_service.GatewayError("AG-UI E2E fake requires manifest_path.")
        events = self.m_artifact_factory(prompt, turn_id)
        _write_canonical_events(
            manifest_path=Path(manifest_path_value),
            run_id=turn_id,
            events=events,
        )

    def send_control_input(self, *, sequence: str, escape_special_keys: bool = False) -> str:
        """Reject raw control input for the deterministic E2E fake."""

        del sequence, escape_special_keys
        raise gateway_service.GatewayError("control input is not part of AG-UI E2E.")

    def describe_control_input_support(self) -> gateway_service._GatewayControlInputSupport:
        """Return unsupported raw control-input capability."""

        return gateway_service._GatewayControlInputSupport(
            supported=False,
            detail="control input is not part of AG-UI E2E.",
        )

    def interrupt(self) -> None:
        """Record interrupt attempts for lifecycle-boundary assertions."""

        self.m_interrupt_count += 1


@dataclass
class _GatewayHarness:
    """Live gateway app/runtime harness for deterministic AG-UI E2E tests."""

    client: TestClient
    runtime: GatewayServiceRuntime
    adapter: _FakeHeadlessGatewayAdapter
    manifest_path: Path

    def close(self) -> None:
        """Close HTTP and runtime resources."""

        self.client.close()
        self.runtime.shutdown()


@dataclass
class _CollectedToolCall:
    """CopilotKit-style tool call reconstructed from AG-UI events."""

    id: str
    name: str
    parent_message_id: str | None
    arguments_json: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class _CollectedMessage:
    """CopilotKit-style assistant message reconstructed from AG-UI events."""

    id: str
    role: str = "assistant"
    content: str = ""
    tool_calls: list[_CollectedToolCall] = field(default_factory=list)


def _start_gateway_harness(
    *,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_factory: ArtifactFactory,
) -> _GatewayHarness:
    """Start a real gateway runtime and route surface with a fake headless adapter."""

    adapters: list[_FakeHeadlessGatewayAdapter] = []

    def _build_fake_adapter(
        *,
        attach_contract: GatewayAttachContractV1,
    ) -> _FakeHeadlessGatewayAdapter:
        adapter = _FakeHeadlessGatewayAdapter(
            attach_contract=attach_contract,
            artifact_factory=artifact_factory,
        )
        adapters.append(adapter)
        return adapter

    monkeypatch.setattr(gateway_service, "_build_gateway_execution_adapter", _build_fake_adapter)
    manifest_path = _seed_gateway_manifest(tmp_path)
    gateway_root = (manifest_path.parent / "gateway").resolve()
    runtime = GatewayServiceRuntime.from_gateway_root(
        gateway_root=gateway_root,
        host="127.0.0.1",
        port=43123,
    )
    runtime.start()
    client = TestClient(create_app(runtime=runtime))
    return _GatewayHarness(
        client=client,
        runtime=runtime,
        adapter=adapters[0],
        manifest_path=manifest_path,
    )


def _seed_gateway_manifest(tmp_path: Path) -> Path:
    """Create a runtime-owned headless manifest and gateway capability."""

    runtime_root = tmp_path / "runtime"
    session_id = "ag-ui-e2e-session"
    backend = "codex_headless"
    manifest_path = default_manifest_path(runtime_root, backend, session_id)
    agent_def_dir = tmp_path / "agent-def"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    brain_manifest_path = tmp_path / "brain.yaml"
    brain_manifest_path.write_text("schema_version: 3\n", encoding="utf-8")
    home_path = tmp_path / "codex-home"
    home_path.mkdir(parents=True, exist_ok=True)
    launch_plan = LaunchPlan(
        backend=backend,
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=home_path,
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="ag-ui-e2e",
            prompt="AG-UI E2E role prompt",
        ),
        metadata={"headless_output_format": "jsonl"},
    )
    backend_state: dict[str, Any] = {
        "session_id": "provider-session-1",
        "turn_index": 0,
        "role_bootstrap_applied": True,
        "working_directory": str(tmp_path),
        "resume_selection_kind": "none",
        "tmux_session_name": "HOUMAO-ag-ui-e2e",
    }
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="ag-ui-e2e",
            brain_manifest_path=brain_manifest_path,
            backend_state=backend_state,
            agent_name="ag-ui-e2e-agent",
            tmux_session_name="HOUMAO-ag-ui-e2e",
            session_id=session_id,
            agent_def_dir=agent_def_dir,
        )
    )
    write_session_manifest(manifest_path, payload)
    ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend=backend,
            tool="codex",
            session_id=session_id,
            tmux_session_name="HOUMAO-ag-ui-e2e",
            working_directory=tmp_path,
            backend_state=backend_state,
            agent_def_dir=agent_def_dir,
        )
    )
    return manifest_path


def _write_canonical_events(
    *,
    manifest_path: Path,
    run_id: str,
    events: Sequence[CanonicalHeadlessEvent],
) -> Path:
    """Write canonical headless events under the run-id-derived turn directory."""

    turn_dir = manifest_path.parent / f"{manifest_path.stem}.turn-artifacts" / run_id
    canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.write_text(
        "".join(json.dumps(event.to_artifact_record(), sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )
    return canonical_path


def _run_payload(*, run_id: str, content: str = "please answer") -> dict[str, Any]:
    """Return one AG-UI run input payload."""

    return {
        "threadId": "ag-ui-e2e-thread",
        "runId": run_id,
        "state": {},
        "messages": [
            {
                "id": "message-1",
                "role": "user",
                "content": content,
            }
        ],
        "tools": [],
        "context": [],
        "forwardedProps": {},
    }


def _assistant_event(*, text: str, turn_index: int = 1) -> CanonicalHeadlessEvent:
    """Return one canonical assistant text event."""

    return CanonicalHeadlessEvent(
        kind="assistant",
        message=text,
        turn_index=turn_index,
        provider="codex",
        provider_event_type="assistant.text",
        data={"text": text},
    )


def _graphic_event() -> CanonicalHeadlessEvent:
    """Return one canonical structured graphic action request."""

    return CanonicalHeadlessEvent(
        kind="action_request",
        message="render structured graphic",
        turn_index=2,
        provider="codex",
        provider_event_type="assistant.tool_use",
        data={
            "action_id": "graphic-1",
            "name": HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
            "arguments": {
                "title": "Latency Budget",
                "description": "Request latency by component",
                "format": "svg",
                "content": (
                    '<svg xmlns="http://www.w3.org/2000/svg" '
                    'viewBox="0 0 120 40"><rect width="120" height="40"/></svg>'
                ),
                "altText": "Latency budget bar",
                "metadata": {"series": "latency", "unit": "ms"},
            },
        },
    )


def _sse_payloads(response_text: str) -> list[dict[str, Any]]:
    """Parse AG-UI SSE data frames from one response body."""

    payloads: list[dict[str, Any]] = []
    for frame in response_text.split("\n\n"):
        if not frame.startswith("data: "):
            continue
        parsed = json.loads(frame.removeprefix("data: "))
        payloads.append(cast(dict[str, Any], parsed))
    return payloads


def _reconstruct_messages(payloads: Sequence[dict[str, Any]]) -> list[_CollectedMessage]:
    """Reconstruct assistant messages and tool calls from AG-UI events."""

    messages: dict[str, _CollectedMessage] = {}
    tool_calls: dict[str, _CollectedToolCall] = {}
    for payload in payloads:
        event_type = payload.get("type")
        if event_type == "TEXT_MESSAGE_START":
            message_id = str(payload["messageId"])
            messages.setdefault(message_id, _CollectedMessage(id=message_id))
        elif event_type == "TEXT_MESSAGE_CONTENT":
            message_id = str(payload["messageId"])
            message = messages.setdefault(message_id, _CollectedMessage(id=message_id))
            message.content += str(payload.get("delta", ""))
        elif event_type == "TOOL_CALL_START":
            tool_call_id = str(payload["toolCallId"])
            parent_message_id = _optional_text(payload.get("parentMessageId"))
            tool_call = _CollectedToolCall(
                id=tool_call_id,
                name=str(payload.get("toolCallName", "")),
                parent_message_id=parent_message_id,
            )
            tool_calls[tool_call_id] = tool_call
            if parent_message_id is not None:
                parent = messages.setdefault(
                    parent_message_id,
                    _CollectedMessage(id=parent_message_id),
                )
                parent.tool_calls.append(tool_call)
        elif event_type == "TOOL_CALL_ARGS":
            tool_call = tool_calls[str(payload["toolCallId"])]
            tool_call.arguments_json += str(payload.get("delta", ""))
        elif event_type == "TOOL_CALL_END":
            tool_call = tool_calls[str(payload["toolCallId"])]
            tool_call.args = cast(dict[str, Any], json.loads(tool_call.arguments_json or "{}"))
    return list(messages.values())


def _optional_text(value: object) -> str | None:
    """Return one stripped text value when present."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _request_payload_for_turn(*, gateway_root: Path, turn_id: str) -> dict[str, Any]:
    """Return the durable gateway request payload for one AG-UI turn id."""

    with sqlite3.connect(gateway_root / "queue.sqlite") as connection:
        row = connection.execute(
            """
            SELECT payload_json
            FROM gateway_requests
            WHERE request_kind = 'submit_prompt'
            ORDER BY accepted_at_utc ASC
            """
        ).fetchone()
    assert row is not None
    payload = cast(dict[str, Any], json.loads(str(row[0])))
    assert payload["turn_id"] == turn_id
    return payload


def test_gateway_e2e_run_stream_preserves_run_id_and_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert `/v1/ag-ui/runs` exercises gateway queue, artifacts, and SSE."""

    def _artifact_factory(_prompt: str, turn_id: str) -> Sequence[CanonicalHeadlessEvent]:
        return [_assistant_event(text=f"answer for {turn_id}")]

    harness = _start_gateway_harness(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        artifact_factory=_artifact_factory,
    )
    try:
        other_run_id = "agui-other-run"
        _write_canonical_events(
            manifest_path=harness.manifest_path,
            run_id=other_run_id,
            events=[_assistant_event(text="other run output must not leak")],
        )

        response = harness.client.post(
            "/v1/ag-ui/runs",
            json=_run_payload(run_id="agui-smoke-run-1"),
        )

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        payloads = _sse_payloads(response.text)
        event_types = [payload["type"] for payload in payloads]
        assert event_types == [
            "RUN_STARTED",
            "TEXT_MESSAGE_START",
            "TEXT_MESSAGE_CONTENT",
            "TEXT_MESSAGE_END",
            "RUN_FINISHED",
        ]
        assert payloads[0]["runId"] == "agui-smoke-run-1"
        assert payloads[2]["delta"] == "answer for agui-smoke-run-1"
        assert "other run output must not leak" not in response.text
        assert len([event for event in event_types if event in {"RUN_FINISHED", "RUN_ERROR"}]) == 1
        assert harness.adapter.m_submitted_prompts[0].turn_id == "agui-smoke-run-1"
        assert harness.adapter.m_interrupt_count == 0
        _request_payload_for_turn(
            gateway_root=harness.runtime.m_paths.gateway_root,
            turn_id="agui-smoke-run-1",
        )
        artifact = harness.runtime.ag_ui_headless_artifact("agui-smoke-run-1")
        assert artifact is not None
        assert artifact.canonical_events_path.is_file()
        assert artifact.turn_dir.name == "agui-smoke-run-1"
    finally:
        harness.close()


def test_gateway_e2e_graphics_reconstructs_structured_tool_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert structured graphic artifacts reconstruct as assistant tool calls."""

    def _artifact_factory(_prompt: str, _turn_id: str) -> Sequence[CanonicalHeadlessEvent]:
        return [
            _assistant_event(
                text="Here is a chart: ![not-a-graphic](https://example.invalid/chart.svg)",
            ),
            _graphic_event(),
        ]

    harness = _start_gateway_harness(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        artifact_factory=_artifact_factory,
    )
    try:
        response = harness.client.post(
            "/v1/ag-ui/runs",
            json=_run_payload(run_id="agui-graphic-run-1"),
        )

        assert response.status_code == 200
        payloads = _sse_payloads(response.text)
        event_types = [payload["type"] for payload in payloads]
        assert "TOOL_CALL_START" in event_types
        assert "TOOL_CALL_ARGS" in event_types
        assert "TOOL_CALL_END" in event_types
        messages = _reconstruct_messages(payloads)
        graphic_messages = [
            message
            for message in messages
            if any(tool.name == HOUMAO_RENDER_GRAPHIC_TOOL_NAME for tool in message.tool_calls)
        ]
        assert len(graphic_messages) == 1
        tool_call = graphic_messages[0].tool_calls[0]
        assert tool_call.parent_message_id == graphic_messages[0].id
        assert tool_call.name == HOUMAO_RENDER_GRAPHIC_TOOL_NAME
        assert tool_call.args["title"] == "Latency Budget"
        assert tool_call.args["format"] == "svg"
        assert tool_call.args["altText"] == "Latency budget bar"
        assert tool_call.args["metadata"] == {"series": "latency", "unit": "ms"}
        assert "<svg" in str(tool_call.args["content"])
    finally:
        harness.close()


def test_gateway_e2e_graphics_ignores_markdown_without_structured_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert prose and Markdown alone do not become generated graphics."""

    def _artifact_factory(_prompt: str, _turn_id: str) -> Sequence[CanonicalHeadlessEvent]:
        return [
            _assistant_event(
                text=(
                    "Markdown image only: ![chart](https://example.invalid/chart.svg). "
                    "<svg><rect /></svg>"
                ),
            )
        ]

    harness = _start_gateway_harness(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        artifact_factory=_artifact_factory,
    )
    try:
        response = harness.client.post(
            "/v1/ag-ui/runs",
            json=_run_payload(run_id="agui-markdown-run-1"),
        )

        assert response.status_code == 200
        payloads = _sse_payloads(response.text)
        event_types = [payload["type"] for payload in payloads]
        assert "TOOL_CALL_START" not in event_types
        assert "TOOL_CALL_ARGS" not in event_types
        assert "TOOL_CALL_END" not in event_types
        messages = _reconstruct_messages(payloads)
        assert not any(message.tool_calls for message in messages)
        assert "Markdown image only" in response.text
    finally:
        harness.close()
