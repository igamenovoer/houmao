"""Houmao AG-UI component authoring and event validation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Literal, TypeAlias, cast

from ag_ui.core import BaseEvent, Event, ToolCallArgsEvent, ToolCallEndEvent, ToolCallStartEvent
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator
from pydantic.alias_generators import to_camel

from houmao.ag_ui.encoder import encode_sse_event
from houmao.ag_ui.state import JsonObject

HOUMAO_AG_UI_SCHEMA_VERSION = 1
"""Current Houmao AG-UI application-protocol schema version."""

HOUMAO_AG_UI_EVENT_BATCH_MAX_COUNT = 100
"""Maximum AG-UI events accepted in one authoring or gateway publish batch."""

HOUMAO_AG_UI_EVENT_BATCH_MAX_BYTES = 256 * 1024
"""Maximum encoded JSON byte size accepted for one publish batch."""

HoumaoAgUiComponentName = Literal[
    "houmao.chart.bar",
    "houmao.chart.line",
    "houmao.chart.pie",
    "houmao.table",
    "houmao.metric_grid",
    "houmao.dashboard",
]
"""Supported Houmao-owned AG-UI component names."""

AgUiEventPayload: TypeAlias = dict[str, Any]
"""One JSON-compatible AG-UI event payload."""

_EventAdapter: TypeAdapter[Any] = TypeAdapter(Event)
_SECRET_FIELD_PATTERN = re.compile(
    r"(token|key|secret|password|credential|authorization|cookie)", re.I
)
_UNSAFE_TEXT_PATTERNS = (
    re.compile(r"<\s*script\b", re.IGNORECASE),
    re.compile(r"\son[a-z0-9_-]+\s*=", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"<\s*iframe\b", re.IGNORECASE),
    re.compile(r"<\s*svg\b", re.IGNORECASE),
)


class HoumaoAgUiValidationError(ValueError):
    """Validation failure for Houmao AG-UI authoring helpers."""

    def __init__(
        self,
        message: str,
        *,
        component: str | None = None,
        event_index: int | None = None,
        field_paths: Sequence[str] | None = None,
        repair_hint: str | None = None,
    ) -> None:
        """Initialize one validation error with safe diagnostic fields."""

        super().__init__(message)
        self.component = component
        self.event_index = event_index
        self.field_paths = tuple(field_paths or ())
        self.repair_hint = repair_hint

    def to_payload(self) -> JsonObject:
        """Return a JSON-compatible diagnostic payload."""

        payload: JsonObject = {
            "ok": False,
            "message": str(self),
        }
        if self.component is not None:
            payload["component"] = self.component
        if self.event_index is not None:
            payload["eventIndex"] = self.event_index
        if self.field_paths:
            payload["fieldPaths"] = list(self.field_paths)
        if self.repair_hint is not None:
            payload["repairHint"] = self.repair_hint
        return payload


class _HoumaoAgUiAuthoringModel(BaseModel):
    """Base class for Houmao component payload models."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )


class _VersionedComponentPayload(_HoumaoAgUiAuthoringModel):
    """Base payload carrying the Houmao component schema version."""

    schema_version: Literal[1] = 1

    @field_validator("*", mode="before")
    @classmethod
    def _reject_unsafe_text_fields(cls, value: object) -> object:
        """Reject unsafe strings wherever Pydantic visits field values."""

        _reject_unsafe_payload_tree(value)
        return value


class ChartDatum(_HoumaoAgUiAuthoringModel):
    """One labeled numeric chart datum."""

    label: str
    value: float
    color: str | None = None

    @field_validator("label")
    @classmethod
    def _label_not_blank(cls, value: str) -> str:
        """Require a non-empty datum label."""

        return _non_blank_text(value, field_name="label")


class LineSeries(_HoumaoAgUiAuthoringModel):
    """One named line chart series."""

    name: str
    data: list[ChartDatum] = Field(min_length=1)
    color: str | None = None

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        """Require a non-empty series name."""

        return _non_blank_text(value, field_name="name")


class HoumaoBarChartPayload(_VersionedComponentPayload):
    """Payload for `houmao.chart.bar`."""

    title: str
    subtitle: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    data: list[ChartDatum] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        """Require a non-empty title."""

        return _non_blank_text(value, field_name="title")


class HoumaoPieChartPayload(_VersionedComponentPayload):
    """Payload for `houmao.chart.pie`."""

    title: str
    subtitle: str | None = None
    data: list[ChartDatum] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        """Require a non-empty title."""

        return _non_blank_text(value, field_name="title")


class HoumaoLineChartPayload(_VersionedComponentPayload):
    """Payload for `houmao.chart.line`."""

    title: str
    subtitle: str | None = None
    x_label: str | None = None
    y_label: str | None = None
    series: list[LineSeries] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        """Require a non-empty title."""

        return _non_blank_text(value, field_name="title")


class TableColumn(_HoumaoAgUiAuthoringModel):
    """One table column definition."""

    key: str
    label: str
    kind: Literal["text", "number", "boolean"] = "text"
    align: Literal["left", "right", "center"] | None = None

    @field_validator("key", "label")
    @classmethod
    def _text_not_blank(cls, value: str) -> str:
        """Require non-empty table column text."""

        return _non_blank_text(value, field_name="column")


class HoumaoTablePayload(_VersionedComponentPayload):
    """Payload for `houmao.table`."""

    title: str | None = None
    columns: list[TableColumn] = Field(min_length=1)
    rows: list[dict[str, Any]] = Field(min_length=1)

    @field_validator("rows")
    @classmethod
    def _rows_match_columns(
        cls,
        value: list[dict[str, Any]],
        info: Any,
    ) -> list[dict[str, Any]]:
        """Validate table rows against declared columns when available."""

        columns = info.data.get("columns", [])
        if not columns:
            return value
        column_keys = {column.key for column in columns}
        for index, row in enumerate(value):
            missing = sorted(column_keys.difference(row))
            if missing:
                raise ValueError(f"row {index} is missing columns: {', '.join(missing)}")
        return value


class MetricItem(_HoumaoAgUiAuthoringModel):
    """One metric in a metric grid."""

    label: str
    value: str | int | float
    unit: str | None = None
    delta: str | None = None
    trend: Literal["up", "down", "neutral"] | None = None

    @field_validator("label")
    @classmethod
    def _label_not_blank(cls, value: str) -> str:
        """Require a non-empty metric label."""

        return _non_blank_text(value, field_name="label")


class HoumaoMetricGridPayload(_VersionedComponentPayload):
    """Payload for `houmao.metric_grid`."""

    title: str | None = None
    metrics: list[MetricItem] = Field(min_length=1)


class DashboardChild(_HoumaoAgUiAuthoringModel):
    """One child component in a Houmao dashboard payload."""

    component: HoumaoAgUiComponentName
    props: dict[str, Any]
    width: Literal["full", "half", "third"] = "full"


class HoumaoDashboardPayload(_VersionedComponentPayload):
    """Payload for `houmao.dashboard`."""

    title: str
    children: list[DashboardChild] = Field(min_length=1)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        """Require a non-empty dashboard title."""

        return _non_blank_text(value, field_name="title")


ComponentPayloadModel: TypeAlias = type[_VersionedComponentPayload]
"""Concrete Pydantic model class for one Houmao component payload."""


@dataclass(frozen=True)
class HoumaoAgUiComponentSpec:
    """Registry entry for one Houmao AG-UI component schema."""

    name: HoumaoAgUiComponentName
    description: str
    model: ComponentPayloadModel
    example: JsonObject

    def to_summary(self) -> JsonObject:
        """Return compact component metadata."""

        return {
            "name": self.name,
            "schemaVersion": HOUMAO_AG_UI_SCHEMA_VERSION,
            "description": self.description,
        }

    def to_schema_payload(self) -> JsonObject:
        """Return the JSON Schema-compatible component schema payload."""

        return {
            **self.to_summary(),
            "schema": cast(JsonObject, self.model.model_json_schema(by_alias=True)),
            "example": self.example,
            "protocol": "houmao.application.ag-ui",
        }


_COMPONENT_SPECS: dict[str, HoumaoAgUiComponentSpec] = {
    "houmao.chart.bar": HoumaoAgUiComponentSpec(
        name="houmao.chart.bar",
        description="Display labeled numeric values as a bar chart.",
        model=HoumaoBarChartPayload,
        example={
            "schemaVersion": 1,
            "title": "Quarterly Revenue",
            "xLabel": "Quarter",
            "yLabel": "USD",
            "data": [
                {"label": "Q1", "value": 120000},
                {"label": "Q2", "value": 155000},
            ],
        },
    ),
    "houmao.chart.line": HoumaoAgUiComponentSpec(
        name="houmao.chart.line",
        description="Display one or more labeled numeric series as a line chart.",
        model=HoumaoLineChartPayload,
        example={
            "schemaVersion": 1,
            "title": "Latency Trend",
            "xLabel": "Time",
            "yLabel": "ms",
            "series": [
                {
                    "name": "p95",
                    "data": [
                        {"label": "09:00", "value": 120},
                        {"label": "10:00", "value": 98},
                    ],
                }
            ],
        },
    ),
    "houmao.chart.pie": HoumaoAgUiComponentSpec(
        name="houmao.chart.pie",
        description="Display labeled numeric values as proportional slices.",
        model=HoumaoPieChartPayload,
        example={
            "schemaVersion": 1,
            "title": "Revenue Mix",
            "data": [
                {"label": "Enterprise", "value": 62},
                {"label": "SMB", "value": 38},
            ],
        },
    ),
    "houmao.table": HoumaoAgUiComponentSpec(
        name="houmao.table",
        description="Display rows against a declared set of columns.",
        model=HoumaoTablePayload,
        example={
            "schemaVersion": 1,
            "title": "Top Issues",
            "columns": [
                {"key": "id", "label": "ID", "kind": "text"},
                {"key": "count", "label": "Count", "kind": "number", "align": "right"},
            ],
            "rows": [
                {"id": "A", "count": 4},
                {"id": "B", "count": 2},
            ],
        },
    ),
    "houmao.metric_grid": HoumaoAgUiComponentSpec(
        name="houmao.metric_grid",
        description="Display a compact grid of labeled KPI values.",
        model=HoumaoMetricGridPayload,
        example={
            "schemaVersion": 1,
            "title": "Build Health",
            "metrics": [
                {"label": "Pass rate", "value": "98%", "trend": "up"},
                {"label": "Failures", "value": 2, "trend": "down"},
            ],
        },
    ),
    "houmao.dashboard": HoumaoAgUiComponentSpec(
        name="houmao.dashboard",
        description="Compose Houmao chart, table, and metric components into one layout.",
        model=HoumaoDashboardPayload,
        example={
            "schemaVersion": 1,
            "title": "Release Dashboard",
            "children": [
                {
                    "component": "houmao.metric_grid",
                    "width": "full",
                    "props": {
                        "schemaVersion": 1,
                        "title": "Summary",
                        "metrics": [{"label": "Open blockers", "value": 1}],
                    },
                },
                {
                    "component": "houmao.chart.bar",
                    "width": "half",
                    "props": {
                        "schemaVersion": 1,
                        "title": "Tests",
                        "data": [{"label": "passed", "value": 42}],
                    },
                },
            ],
        },
    ),
}


def list_component_summaries() -> list[JsonObject]:
    """Return all supported component summaries."""

    return [spec.to_summary() for spec in _COMPONENT_SPECS.values()]


def get_component_spec(component: str) -> HoumaoAgUiComponentSpec:
    """Return one component spec or raise a safe validation error."""

    spec = _COMPONENT_SPECS.get(component)
    if spec is None:
        raise HoumaoAgUiValidationError(
            f"Unknown Houmao AG-UI component `{component}`.",
            component=component,
            repair_hint="Run `houmao-mgr internals ag-ui components list`.",
        )
    return spec


def component_schema_payload(component: str) -> JsonObject:
    """Return JSON Schema-compatible metadata for one component."""

    return get_component_spec(component).to_schema_payload()


def validate_component_payload(component: str, payload: object) -> JsonObject:
    """Validate one component payload and return its normalized JSON object."""

    spec = get_component_spec(component)
    try:
        _reject_unsafe_payload_tree(payload)
        validated = spec.model.model_validate(payload)
        normalized = validated.model_dump(mode="json", by_alias=True, exclude_none=True)
    except ValidationError as exc:
        raise HoumaoAgUiValidationError(
            f"Payload does not match `{component}` schema.",
            component=component,
            field_paths=_validation_error_paths(exc),
            repair_hint=f"Inspect the schema with `houmao-mgr internals ag-ui components schema {component}`.",
        ) from exc
    except ValueError as exc:
        raise HoumaoAgUiValidationError(
            str(exc),
            component=component,
            repair_hint="Remove unsafe inline content and use typed component fields.",
        ) from exc
    return cast(JsonObject, normalized)


def render_component_events(
    *,
    component: str,
    payload: object,
    message_id: str | None = None,
    tool_call_id: str | None = None,
) -> list[AgUiEventPayload]:
    """Render one validated component payload as standard AG-UI tool-call events."""

    normalized = validate_component_payload(component, payload)
    digest = _payload_digest(component=component, payload=normalized)
    resolved_tool_call_id = tool_call_id or f"houmao-tool-{digest}"
    resolved_message_id = message_id or f"houmao-message-{digest}"
    args_json = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    events = [
        ToolCallStartEvent(
            tool_call_id=resolved_tool_call_id,
            tool_call_name=component,
            parent_message_id=resolved_message_id,
        ),
        ToolCallArgsEvent(tool_call_id=resolved_tool_call_id, delta=args_json),
        ToolCallEndEvent(tool_call_id=resolved_tool_call_id),
    ]
    return [event.model_dump(mode="json", by_alias=True, exclude_none=True) for event in events]


def validate_ag_ui_event_sequence(
    events: object,
    *,
    max_count: int = HOUMAO_AG_UI_EVENT_BATCH_MAX_COUNT,
    max_bytes: int = HOUMAO_AG_UI_EVENT_BATCH_MAX_BYTES,
) -> list[AgUiEventPayload]:
    """Validate a bounded standard AG-UI event sequence."""

    if not isinstance(events, list):
        raise HoumaoAgUiValidationError(
            "AG-UI events input must be a JSON array of event objects.",
            repair_hint="Render a component first or provide an array of AG-UI events.",
        )
    if len(events) > max_count:
        raise HoumaoAgUiValidationError(
            f"AG-UI event batch has {len(events)} events, above the limit of {max_count}.",
            repair_hint="Split the events into smaller batches.",
        )
    encoded_size = len(json.dumps(events, separators=(",", ":"), default=str).encode("utf-8"))
    if encoded_size > max_bytes:
        raise HoumaoAgUiValidationError(
            f"AG-UI event batch is {encoded_size} bytes, above the limit of {max_bytes}.",
            repair_hint="Reduce payload size or split the events into smaller batches.",
        )

    normalized: list[AgUiEventPayload] = []
    started_tool_ids: set[str] = set()
    active_tool_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, Mapping):
            raise HoumaoAgUiValidationError(
                "AG-UI event must be a JSON object.",
                event_index=index,
                field_paths=["$"],
            )
        try:
            parsed = _EventAdapter.validate_python(dict(event))
        except ValidationError as exc:
            raise HoumaoAgUiValidationError(
                "AG-UI event does not match a standard event shape.",
                event_index=index,
                field_paths=_validation_error_paths(exc),
                repair_hint="Check the event `type` and required AG-UI fields.",
            ) from exc
        payload = cast(
            AgUiEventPayload,
            parsed.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        _validate_tool_call_order(
            payload=payload,
            index=index,
            started_tool_ids=started_tool_ids,
            active_tool_ids=active_tool_ids,
        )
        normalized.append(payload)
    return normalized


def parse_ag_ui_event_payloads(events: Sequence[AgUiEventPayload]) -> list[BaseEvent]:
    """Parse normalized AG-UI event payloads into SDK event models."""

    return [cast(BaseEvent, _EventAdapter.validate_python(event)) for event in events]


def render_events_as_json(events: Sequence[AgUiEventPayload]) -> str:
    """Render events as a stable JSON array."""

    return json.dumps(list(events), indent=2, sort_keys=True)


def render_events_as_jsonl(events: Sequence[AgUiEventPayload]) -> str:
    """Render events as JSON Lines."""

    return "\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n"


def render_events_as_sse(events: Sequence[AgUiEventPayload]) -> str:
    """Render events as AG-UI SSE frames."""

    parsed_events = validate_ag_ui_event_sequence(list(events))
    return "".join(
        encode_sse_event(_EventAdapter.validate_python(event)) for event in parsed_events
    )


def validation_error_payload(exc: HoumaoAgUiValidationError) -> JsonObject:
    """Return one safe validation error payload for CLI and HTTP responses."""

    return exc.to_payload()


def _validate_tool_call_order(
    *,
    payload: AgUiEventPayload,
    index: int,
    started_tool_ids: set[str],
    active_tool_ids: set[str],
) -> None:
    """Validate locally checkable tool-call event ordering."""

    event_type = str(payload.get("type", ""))
    if not event_type.startswith("TOOL_CALL_"):
        return
    tool_call_id = payload.get("toolCallId")
    if not isinstance(tool_call_id, str) or not tool_call_id:
        raise HoumaoAgUiValidationError(
            "AG-UI tool-call event is missing `toolCallId`.",
            event_index=index,
            field_paths=["toolCallId"],
        )
    if event_type == "TOOL_CALL_START":
        if tool_call_id in active_tool_ids:
            raise HoumaoAgUiValidationError(
                "AG-UI tool call starts more than once before ending.",
                event_index=index,
                field_paths=["toolCallId"],
            )
        started_tool_ids.add(tool_call_id)
        active_tool_ids.add(tool_call_id)
        return
    if tool_call_id not in started_tool_ids:
        raise HoumaoAgUiValidationError(
            "AG-UI tool-call args, chunk, result, or end references an unknown tool call.",
            event_index=index,
            field_paths=["toolCallId"],
            repair_hint="Emit TOOL_CALL_START before TOOL_CALL_ARGS, TOOL_CALL_CHUNK, TOOL_CALL_RESULT, or TOOL_CALL_END.",
        )
    if event_type == "TOOL_CALL_END":
        active_tool_ids.discard(tool_call_id)


def _payload_digest(*, component: str, payload: JsonObject) -> str:
    """Return a short deterministic digest for generated ids."""

    payload_json = json.dumps({"component": component, "payload": payload}, sort_keys=True)
    return sha256(payload_json.encode("utf-8")).hexdigest()[:12]


def _validation_error_paths(exc: ValidationError) -> tuple[str, ...]:
    """Return normalized field paths without raw values."""

    paths: list[str] = []
    for error in exc.errors(include_url=False, include_context=False, include_input=False):
        location = error.get("loc", ())
        if isinstance(location, tuple):
            paths.append(".".join(str(part) for part in location))
        else:
            paths.append(str(location))
    return tuple(paths)


def _reject_unsafe_payload_tree(value: object, *, path: tuple[str, ...] = ()) -> None:
    """Reject unsafe raw inline content in a nested payload."""

    if isinstance(value, str):
        for pattern in _UNSAFE_TEXT_PATTERNS:
            if pattern.search(value):
                safe_path = ".".join(_redacted_path(path)) or "$"
                raise ValueError(f"payload contains unsafe inline content at `{safe_path}`")
        return
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            _reject_unsafe_payload_tree(nested_value, path=(*path, str(key)))
        return
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for index, nested_value in enumerate(value):
            _reject_unsafe_payload_tree(nested_value, path=(*path, str(index)))


def _redacted_path(path: tuple[str, ...]) -> tuple[str, ...]:
    """Return a field path with secret-like segments replaced."""

    return tuple("<redacted>" if _SECRET_FIELD_PATTERN.search(part) else part for part in path)


def _non_blank_text(value: str, *, field_name: str) -> str:
    """Return stripped text or raise for a blank value."""

    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


__all__ = [
    "AgUiEventPayload",
    "HOUMAO_AG_UI_EVENT_BATCH_MAX_BYTES",
    "HOUMAO_AG_UI_EVENT_BATCH_MAX_COUNT",
    "HOUMAO_AG_UI_SCHEMA_VERSION",
    "HoumaoAgUiComponentName",
    "HoumaoAgUiValidationError",
    "component_schema_payload",
    "get_component_spec",
    "list_component_summaries",
    "render_component_events",
    "render_events_as_json",
    "render_events_as_jsonl",
    "render_events_as_sse",
    "parse_ag_ui_event_payloads",
    "validate_ag_ui_event_sequence",
    "validate_component_payload",
    "validation_error_payload",
]
