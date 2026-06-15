"""Map Houmao gateway observations into AG-UI protocol events."""

from __future__ import annotations

import json
from typing import cast

from ag_ui.core import (
    ActivitySnapshotEvent,
    BaseEvent,
    CustomEvent,
    ReasoningMessageContentEvent,
    ReasoningMessageEndEvent,
    ReasoningMessageStartEvent,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallResultEvent,
    ToolCallStartEvent,
)

from houmao.ag_ui.graphics import (
    HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
    HoumaoGraphicArtifact,
    extract_graphic_artifact_from_headless_event,
    graphic_artifact_to_tool_events,
)
from houmao.ag_ui.runtime import AgUiTuiObservation
from houmao.ag_ui.state import JsonObject, JsonValue
from houmao.agents.realm_controller.backends.headless_output import CanonicalHeadlessEvent


class AgUiEventMapper:
    """Deterministic mapper for one AG-UI run stream."""

    def __init__(
        self,
        *,
        thread_id: str,
        run_id: str,
        parent_run_id: str | None = None,
        expose_reasoning: bool = False,
        emit_graphic_results: bool = False,
    ) -> None:
        """Initialize mapper identity and visibility policy."""

        self.m_thread_id: str = thread_id
        self.m_run_id: str = run_id
        self.m_parent_run_id: str | None = parent_run_id
        self.m_expose_reasoning: bool = expose_reasoning
        self.m_emit_graphic_results: bool = emit_graphic_results

    def run_started_event(self, run_input: RunAgentInput) -> RunStartedEvent:
        """Return the AG-UI run-started lifecycle event."""

        return RunStartedEvent(
            thread_id=self.m_thread_id,
            run_id=self.m_run_id,
            parent_run_id=self.m_parent_run_id,
            input=run_input,
        )

    def run_finished_event(self, result: JsonObject | None = None) -> RunFinishedEvent:
        """Return the AG-UI run-finished lifecycle event."""

        return RunFinishedEvent(
            thread_id=self.m_thread_id,
            run_id=self.m_run_id,
            result=result,
        )

    def run_error_event(self, *, message: str, code: str = "houmao_run_error") -> RunErrorEvent:
        """Return the AG-UI run-error lifecycle event."""

        return RunErrorEvent(message=message, code=code)

    def map_headless_event(
        self,
        event: CanonicalHeadlessEvent,
        *,
        sequence_index: int,
    ) -> list[BaseEvent]:
        """Map one canonical headless event into zero or more AG-UI events."""

        if event.kind == "assistant":
            return self._assistant_text_events(
                message_id=self._message_id("assistant", event, sequence_index),
                text=_assistant_text(event),
            )
        if event.kind == "action_request":
            graphic_events = self._graphic_events(event=event, sequence_index=sequence_index)
            if graphic_events is not None:
                return graphic_events
            return self._action_request_events(event=event, sequence_index=sequence_index)
        if event.kind == "action_result":
            graphic_events = self._graphic_events(event=event, sequence_index=sequence_index)
            if graphic_events is not None:
                return graphic_events
            return [self._action_result_event(event=event, sequence_index=sequence_index)]
        if event.kind == "reasoning":
            return self._reasoning_events(event=event, sequence_index=sequence_index)
        if event.kind == "progress":
            return [
                ActivitySnapshotEvent(
                    message_id=self._message_id("progress", event, sequence_index),
                    activity_type="houmao.gateway.progress",
                    content=json.dumps(_canonical_event_payload(event), sort_keys=True),
                    replace=True,
                )
            ]
        if event.kind == "diagnostic":
            return [
                CustomEvent(
                    name="houmao.gateway.diagnostic",
                    value=_canonical_event_payload(event),
                )
            ]
        if event.kind == "completion":
            return [
                ActivitySnapshotEvent(
                    message_id=self._message_id("completion", event, sequence_index),
                    activity_type="houmao.gateway.completion",
                    content=json.dumps(_canonical_event_payload(event), sort_keys=True),
                    replace=True,
                )
            ]
        return [
            CustomEvent(
                name="houmao.gateway.event",
                value=_canonical_event_payload(event),
            )
        ]

    def map_tui_observation(
        self,
        observation: AgUiTuiObservation,
        *,
        sequence_index: int,
        include_final_text: bool,
    ) -> list[BaseEvent]:
        """Map one lower-fidelity TUI observation to AG-UI activity/text events."""

        activity_payload: JsonObject = {
            "source": "houmao.tui",
            "available": observation.available,
            "status": observation.status,
        }
        if observation.activity is not None:
            activity_payload["activity"] = observation.activity
        if observation.state is not None:
            activity_payload["state"] = observation.state
        events: list[BaseEvent] = [
            ActivitySnapshotEvent(
                message_id=f"{self.m_run_id}:tui:{sequence_index}",
                activity_type="houmao.tui.status",
                content=json.dumps(activity_payload, sort_keys=True),
                replace=True,
            )
        ]
        if include_final_text and observation.final_text is not None:
            events.extend(
                self._assistant_text_events(
                    message_id=f"{self.m_run_id}:tui-final:{sequence_index}",
                    text=observation.final_text,
                )
            )
        return events

    def graphic_artifact_events(
        self,
        *,
        artifact: HoumaoGraphicArtifact,
        sequence_index: int,
        emit_result: bool | None = None,
    ) -> list[BaseEvent]:
        """Build assistant-parented AG-UI events for one validated graphic."""

        parent_message_id = f"{self.m_run_id}:graphic-parent:{sequence_index}"
        tool_call_id = f"{self.m_run_id}:graphic:{sequence_index}"
        return [
            TextMessageStartEvent(message_id=parent_message_id),
            *graphic_artifact_to_tool_events(
                artifact=artifact,
                parent_message_id=parent_message_id,
                tool_call_id=tool_call_id,
                emit_result=self.m_emit_graphic_results if emit_result is None else emit_result,
            ),
            TextMessageEndEvent(message_id=parent_message_id),
        ]

    def _assistant_text_events(self, *, message_id: str, text: str) -> list[BaseEvent]:
        """Build a complete AG-UI assistant text message sequence."""

        if not text:
            return []
        return [
            TextMessageStartEvent(message_id=message_id),
            TextMessageContentEvent(message_id=message_id, delta=text),
            TextMessageEndEvent(message_id=message_id),
        ]

    def _action_request_events(
        self,
        *,
        event: CanonicalHeadlessEvent,
        sequence_index: int,
    ) -> list[BaseEvent]:
        """Map one canonical action request to AG-UI tool-call events."""

        tool_call_id = _tool_call_id(self.m_run_id, event, sequence_index)
        tool_name = _tool_name(event)
        return [
            ToolCallStartEvent(
                tool_call_id=tool_call_id,
                tool_call_name=tool_name,
            ),
            ToolCallArgsEvent(
                tool_call_id=tool_call_id,
                delta=json.dumps(_tool_arguments(event), sort_keys=True),
            ),
            ToolCallEndEvent(tool_call_id=tool_call_id),
        ]

    def _action_result_event(
        self,
        *,
        event: CanonicalHeadlessEvent,
        sequence_index: int,
    ) -> ToolCallResultEvent:
        """Map one canonical action result to an AG-UI tool-result event."""

        tool_call_id = _tool_call_id(self.m_run_id, event, sequence_index)
        return ToolCallResultEvent(
            message_id=f"{tool_call_id}:result",
            tool_call_id=tool_call_id,
            role="tool",
            content=_tool_result_content(event),
        )

    def _reasoning_events(
        self,
        *,
        event: CanonicalHeadlessEvent,
        sequence_index: int,
    ) -> list[BaseEvent]:
        """Map reasoning according to visibility policy."""

        if not self.m_expose_reasoning:
            return [
                CustomEvent(
                    name="houmao.reasoning_redacted",
                    value={
                        "source": "houmao.headless",
                        "kind": "reasoning",
                        "redacted": True,
                        "provider": event.provider,
                        "turnIndex": event.turn_index,
                    },
                )
            ]
        message_id = self._message_id("reasoning", event, sequence_index)
        return [
            ReasoningMessageStartEvent(message_id=message_id, role="reasoning"),
            ReasoningMessageContentEvent(message_id=message_id, delta=_assistant_text(event)),
            ReasoningMessageEndEvent(message_id=message_id),
        ]

    def _graphic_events(
        self,
        *,
        event: CanonicalHeadlessEvent,
        sequence_index: int,
    ) -> list[BaseEvent] | None:
        """Map explicit graphics artifacts to CopilotKit-compatible tool calls."""

        artifact = extract_graphic_artifact_from_headless_event(event)
        if artifact is None:
            return None
        return self.graphic_artifact_events(artifact=artifact, sequence_index=sequence_index)

    def _message_id(
        self,
        category: str,
        event: CanonicalHeadlessEvent,
        sequence_index: int,
    ) -> str:
        """Return a deterministic AG-UI message id."""

        return f"{self.m_run_id}:{category}:{event.turn_index}:{sequence_index}"


def _assistant_text(event: CanonicalHeadlessEvent) -> str:
    """Extract readable assistant text from one canonical event."""

    data = event.data or {}
    text = data.get("text")
    if isinstance(text, str):
        return text
    result_text = data.get("result_text")
    if isinstance(result_text, str):
        return result_text
    return event.message


def _tool_call_id(run_id: str, event: CanonicalHeadlessEvent, sequence_index: int) -> str:
    """Return a stable AG-UI tool-call id."""

    data = event.data or {}
    action_id = data.get("action_id")
    if isinstance(action_id, str) and action_id.strip():
        return f"{run_id}:tool:{action_id}"
    return f"{run_id}:tool:{event.turn_index}:{sequence_index}"


def _tool_name(event: CanonicalHeadlessEvent) -> str:
    """Return a stable AG-UI tool-call name."""

    data = event.data or {}
    name = data.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    action_kind = data.get("action_kind")
    if isinstance(action_kind, str) and action_kind.strip():
        return action_kind.strip()
    return "houmao_action"


def _tool_arguments(event: CanonicalHeadlessEvent) -> JsonObject:
    """Return JSON arguments for one action request."""

    data = event.data or {}
    explicit_arguments = data.get("arguments")
    if isinstance(explicit_arguments, dict):
        return cast(JsonObject, explicit_arguments)
    for key in ("command", "query", "changes"):
        value = data.get(key)
        if value is not None:
            return {key: cast(JsonValue, value)}
    arguments_summary = data.get("arguments_summary")
    if isinstance(arguments_summary, str):
        return {"summary": arguments_summary}
    return {"message": event.message}


def _tool_result_content(event: CanonicalHeadlessEvent) -> str:
    """Return AG-UI tool result content."""

    data = event.data or {}
    result_summary = data.get("result_summary")
    if isinstance(result_summary, str):
        return result_summary
    status = data.get("status")
    if isinstance(status, str):
        return status
    return event.message


def _canonical_event_payload(event: CanonicalHeadlessEvent) -> JsonObject:
    """Return a JSON-safe payload for custom/activity AG-UI events."""

    payload: JsonObject = {
        "source": "houmao.headless",
        "kind": event.kind,
        "message": event.message,
        "provider": event.provider,
        "providerEventType": event.provider_event_type,
        "turnIndex": event.turn_index,
        "timestampUtc": event.timestamp_utc,
    }
    if event.session_id is not None:
        payload["sessionId"] = event.session_id
    if event.data is not None:
        payload["data"] = cast(JsonObject, _jsonable(event.data))
    return payload


def _jsonable(value: object) -> JsonValue:
    """Return a JSON-compatible projection."""

    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


__all__ = [
    "AgUiEventMapper",
    "HOUMAO_RENDER_GRAPHIC_TOOL_NAME",
]
