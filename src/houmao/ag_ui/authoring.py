"""Houmao AG-UI component authoring and event validation helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Any, Literal, TypeAlias, cast

from ag_ui.core import BaseEvent, Event, ToolCallArgsEvent, ToolCallEndEvent, ToolCallStartEvent
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

from houmao.ag_ui.encoder import encode_sse_event
from houmao.ag_ui.state import JsonObject

HOUMAO_AG_UI_SCHEMA_VERSION = 1
"""Current schema version for existing non-graphic Houmao component payloads."""

HOUMAO_AG_UI_EVENT_BATCH_MAX_COUNT = 100
"""Maximum AG-UI events accepted in one authoring or gateway publish batch."""

HOUMAO_AG_UI_EVENT_BATCH_MAX_BYTES = 256 * 1024
"""Maximum encoded JSON byte size accepted for one publish batch."""

HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME: Literal["houmao.graphic.template"] = "houmao.graphic.template"
"""Houmao Layer 1 template-graphics AG-UI tool-call name."""

HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION = 2
"""Current Houmao Layer 1 template-graphics payload schema version."""

HOUMAO_TEMPLATE_GRAPHIC_RENDERERS = ("plotly",)
"""Renderer ids for Houmao Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER = "plotly"
"""Default renderer id for Houmao Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_CHART_TYPES = ("bar", "line", "scatter", "pie", "histogram")
"""Initial chart types supported by Houmao Layer 1 template graphics."""

HOUMAO_RETIRED_FIXED_CHART_COMPONENTS = frozenset(
    {"houmao.chart.bar", "houmao.chart.line", "houmao.chart.pie"}
)
"""Retired fixed chart component names that must be rewritten as template graphics."""

HoumaoAgUiComponentName = Literal[
    "houmao.graphic.template",
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
_REMOTE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_RENDERER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_TEMPLATE_GRAPHIC_LEGACY_KEYS = frozenset({"data", "encoding", "interactions", "style"})
_PLOTLY_EXTRA_DISALLOWED_KEYS = frozenset(
    {
        "$schema",
        "autosize",
        "concat",
        "data",
        "datasets",
        "encoding",
        "facet",
        "figure",
        "frames",
        "hconcat",
        "html",
        "iframe",
        "javascript",
        "layer",
        "params",
        "projection",
        "repeat",
        "resolve",
        "script",
        "signals",
        "spec",
        "svg",
        "template",
        "templates",
        "transform",
        "transforms",
        "traces",
        "usermeta",
        "vega",
        "vegaLite",
        "vega-lite",
        "vconcat",
    }
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


class _TemplateGraphicVersionedPayload(_HoumaoAgUiAuthoringModel):
    """Base payload carrying the template-graphics schema version."""

    schema_version: Literal[2] = 2

    @field_validator("*", mode="before")
    @classmethod
    def _reject_unsafe_text_fields(cls, value: object) -> object:
        """Reject unsafe strings wherever Pydantic visits field values."""

        _reject_unsafe_payload_tree(value)
        return value


TemplateGraphicChartType = Literal["bar", "line", "scatter", "pie", "histogram"]
"""Supported standardized Layer 1 Plotly-backed chart intents."""

TemplateGraphicTraceType = Literal["bar", "scatter", "pie", "histogram"]
"""Supported Plotly trace families used by the template compiler."""

TemplateGraphicArrayValue: TypeAlias = str | int | float | bool | None
"""Scalar JSON values accepted in inline trace arrays."""

TemplateGraphicColumnType = Literal["string", "number", "boolean", "datetime"]
"""Reserved datasource column type labels."""


class TemplateGraphicRendererSelection(_HoumaoAgUiAuthoringModel):
    """Renderer metadata for one template graphic payload."""

    preferred: Literal["plotly"] = "plotly"

    @field_validator("preferred")
    @classmethod
    def _preferred_is_plotly(cls, value: str) -> Literal["plotly"]:
        """Require the only supported Layer 1 renderer id."""

        if value != HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER:
            raise ValueError("renderer.preferred must be `plotly`")
        return "plotly"


class TemplateGraphicMargin(_HoumaoAgUiAuthoringModel):
    """Safe Plotly-compatible margin refinements."""

    left: int | None = Field(default=None, alias="l", ge=0, le=500)
    right: int | None = Field(default=None, alias="r", ge=0, le=500)
    top: int | None = Field(default=None, alias="t", ge=0, le=500)
    bottom: int | None = Field(default=None, alias="b", ge=0, le=500)
    pad: int | None = Field(default=None, ge=0, le=100)


class TemplateGraphicAxis(_HoumaoAgUiAuthoringModel):
    """Safe Plotly-compatible axis display refinements."""

    title: str | None = None
    tickformat: str | None = None
    type: Literal["linear", "log", "date", "category", "multicategory"] | None = None
    range: list[float] | None = Field(default=None, min_length=2, max_length=2)

    @field_validator("title", "tickformat")
    @classmethod
    def _optional_text_stripped(cls, value: str | None) -> str | None:
        """Normalize optional axis text."""

        return _optional_non_blank_text(value, field_name="axis")


class TemplateGraphicLegend(_HoumaoAgUiAuthoringModel):
    """Safe Plotly-compatible legend display refinements."""

    orientation: Literal["v", "h"] | None = None
    x: float | None = None
    y: float | None = None


class TemplateGraphicLayout(_HoumaoAgUiAuthoringModel):
    """Curated layout fields accepted by Layer 1 template graphics."""

    xaxis: TemplateGraphicAxis | None = None
    yaxis: TemplateGraphicAxis | None = None
    legend: TemplateGraphicLegend | None = None
    margin: TemplateGraphicMargin | None = None
    show_legend: bool | None = None
    hovermode: Literal["x", "y", "closest", "x unified", "y unified"] | None = None
    bargap: float | None = Field(default=None, ge=0, le=1)
    barmode: Literal["group", "stack", "relative", "overlay"] | None = None


class TemplateGraphicConfig(_HoumaoAgUiAuthoringModel):
    """Curated Plotly config fields accepted by Layer 1 template graphics."""

    responsive: bool = True
    display_mode_bar: bool | Literal["hover"] | None = Field(
        default=None,
        alias="displayModeBar",
    )
    scroll_zoom: bool | None = Field(default=None, alias="scrollZoom")
    static_plot: bool | None = Field(default=None, alias="staticPlot")


class TemplateGraphicDisplay(_HoumaoAgUiAuthoringModel):
    """Display metadata that is not part of the Plotly figure."""

    width: int | None = Field(default=None, ge=120, le=2400)
    height: int | None = Field(default=None, ge=120, le=1800)
    aspect_ratio: float | None = Field(default=None, alias="aspectRatio", gt=0, le=4)
    caption: str | None = None
    description: str | None = None

    @field_validator("caption", "description")
    @classmethod
    def _optional_text_stripped(cls, value: str | None) -> str | None:
        """Normalize optional display text."""

        return _optional_non_blank_text(value, field_name="display")


class TemplateGraphicDataRefColumn(_HoumaoAgUiAuthoringModel):
    """One reserved datasource column declaration."""

    name: str
    type: TemplateGraphicColumnType | None = None
    label: str | None = None

    @field_validator("name", "label")
    @classmethod
    def _optional_or_required_text(cls, value: str | None, info: Any) -> str | None:
        """Normalize datasource column text."""

        if info.field_name == "name":
            return _non_blank_text(str(value), field_name="dataRefs.columns.name")
        return _optional_non_blank_text(value, field_name="dataRefs.columns.label")


class TemplateGraphicDataRef(_HoumaoAgUiAuthoringModel):
    """One reserved datasource dependency declaration."""

    id: str
    label: str | None = None
    description: str | None = None
    columns: list[TemplateGraphicDataRefColumn] | None = None

    @field_validator("id")
    @classmethod
    def _id_not_blank(cls, value: str) -> str:
        """Require a non-empty datasource id."""

        return _non_blank_text(value, field_name="dataRefs.id")

    @field_validator("label", "description")
    @classmethod
    def _optional_text_stripped(cls, value: str | None) -> str | None:
        """Normalize optional datasource text."""

        return _optional_non_blank_text(value, field_name="dataRefs")


class TemplateGraphicColumnBinding(_HoumaoAgUiAuthoringModel):
    """One reserved datasource column binding."""

    column: str

    @field_validator("column")
    @classmethod
    def _column_not_blank(cls, value: str) -> str:
        """Require a non-empty datasource column name."""

        return _non_blank_text(value, field_name="source.column")


class TemplateGraphicMarkerSource(_HoumaoAgUiAuthoringModel):
    """Reserved datasource bindings for marker channels."""

    color: TemplateGraphicColumnBinding | None = None
    size: TemplateGraphicColumnBinding | None = None


class TemplateGraphicTraceSource(_HoumaoAgUiAuthoringModel):
    """Reserved datasource bindings for one trace."""

    data_ref: str = Field(alias="dataRef")
    x: TemplateGraphicColumnBinding | None = None
    y: TemplateGraphicColumnBinding | None = None
    z: TemplateGraphicColumnBinding | None = None
    labels: TemplateGraphicColumnBinding | None = None
    values: TemplateGraphicColumnBinding | None = None
    text: TemplateGraphicColumnBinding | None = None
    marker: TemplateGraphicMarkerSource | None = None

    @field_validator("data_ref")
    @classmethod
    def _data_ref_not_blank(cls, value: str) -> str:
        """Require a non-empty datasource id."""

        return _non_blank_text(value, field_name="source.dataRef")


class TemplateGraphicMarkerLine(_HoumaoAgUiAuthoringModel):
    """Safe marker border styling."""

    color: str | None = None
    width: float | None = Field(default=None, ge=0, le=20)

    @field_validator("color")
    @classmethod
    def _color_stripped(cls, value: str | None) -> str | None:
        """Normalize optional marker border color."""

        return _optional_non_blank_text(value, field_name="marker.line.color")


class TemplateGraphicMarker(_HoumaoAgUiAuthoringModel):
    """Safe marker styling."""

    color: str | list[TemplateGraphicArrayValue] | None = None
    colors: list[str] | None = None
    size: float | list[float] | None = None
    opacity: float | None = Field(default=None, ge=0, le=1)
    line: TemplateGraphicMarkerLine | None = None

    @field_validator("color")
    @classmethod
    def _color_safe(cls, value: str | list[TemplateGraphicArrayValue] | None) -> object:
        """Normalize optional marker color."""

        if isinstance(value, str):
            return _optional_non_blank_text(value, field_name="marker.color")
        return value

    @field_validator("colors")
    @classmethod
    def _colors_not_blank(cls, value: list[str] | None) -> list[str] | None:
        """Require non-empty pie marker colors."""

        if value is None:
            return None
        return [_non_blank_text(item, field_name="marker.colors") for item in value]

    @field_validator("size")
    @classmethod
    def _size_non_negative(cls, value: float | list[float] | None) -> float | list[float] | None:
        """Require non-negative marker sizes."""

        if isinstance(value, list):
            if any(item < 0 for item in value):
                raise ValueError("marker.size values must be non-negative")
            return value
        if value is not None and value < 0:
            raise ValueError("marker.size must be non-negative")
        return value


class TemplateGraphicLine(_HoumaoAgUiAuthoringModel):
    """Safe line styling."""

    color: str | None = None
    width: float | None = Field(default=None, ge=0, le=20)
    dash: Literal["solid", "dot", "dash", "longdash", "dashdot", "longdashdot"] | None = None
    shape: Literal["linear", "spline", "hv", "vh", "hvh", "vhv"] | None = None

    @field_validator("color")
    @classmethod
    def _color_stripped(cls, value: str | None) -> str | None:
        """Normalize optional line color."""

        return _optional_non_blank_text(value, field_name="line.color")


class TemplateGraphicTrace(_HoumaoAgUiAuthoringModel):
    """One curated Plotly-aligned trace."""

    type: TemplateGraphicTraceType | None = None
    name: str | None = None
    x: list[TemplateGraphicArrayValue] | None = Field(default=None, min_length=1)
    y: list[TemplateGraphicArrayValue] | None = Field(default=None, min_length=1)
    z: list[TemplateGraphicArrayValue] | None = Field(default=None, min_length=1)
    labels: list[TemplateGraphicArrayValue] | None = Field(default=None, min_length=1)
    values: list[float] | None = Field(default=None, min_length=1)
    text: str | list[TemplateGraphicArrayValue] | None = None
    hovertemplate: str | None = None
    mode: Literal[
        "lines",
        "markers",
        "text",
        "lines+markers",
        "lines+text",
        "markers+text",
        "lines+markers+text",
    ] | None = None
    orientation: Literal["v", "h"] | None = None
    marker: TemplateGraphicMarker | None = None
    line: TemplateGraphicLine | None = None
    source: TemplateGraphicTraceSource | None = None
    opacity: float | None = Field(default=None, ge=0, le=1)
    show_legend: bool | None = Field(default=None, alias="showLegend")

    @field_validator("name", "hovertemplate")
    @classmethod
    def _optional_text_stripped(cls, value: str | None) -> str | None:
        """Normalize optional trace text."""

        return _optional_non_blank_text(value, field_name="trace")

    @field_validator("text")
    @classmethod
    def _text_safe(cls, value: str | list[TemplateGraphicArrayValue] | None) -> object:
        """Normalize optional trace text."""

        if isinstance(value, str):
            return _optional_non_blank_text(value, field_name="text")
        return value


class TemplateGraphicPlotlyExtra(_HoumaoAgUiAuthoringModel):
    """Allowlisted non-essential Plotly presentation refinements."""

    layout: TemplateGraphicLayout | None = None
    config: TemplateGraphicConfig | None = None
    marker: TemplateGraphicMarker | None = None
    line: TemplateGraphicLine | None = None
    display: TemplateGraphicDisplay | None = None


class TemplateGraphicExtra(_HoumaoAgUiAuthoringModel):
    """Renderer-scoped extra fields for Layer 1 template graphics."""

    plotly: TemplateGraphicPlotlyExtra | None = None


class HoumaoTemplateGraphicPayload(_TemplateGraphicVersionedPayload):
    """Payload for `houmao.graphic.template`."""

    chart_type: TemplateGraphicChartType
    renderer: TemplateGraphicRendererSelection = Field(
        default_factory=TemplateGraphicRendererSelection
    )
    title: str
    subtitle: str | None = None
    traces: list[TemplateGraphicTrace] = Field(min_length=1)
    data_refs: list[TemplateGraphicDataRef] | None = Field(default=None, alias="dataRefs")
    layout: TemplateGraphicLayout | None = None
    config: TemplateGraphicConfig = Field(default_factory=TemplateGraphicConfig)
    display: TemplateGraphicDisplay | None = None
    extra: TemplateGraphicExtra | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_shape(cls, value: object) -> object:
        """Reject old row-and-encoding payloads before normal validation."""

        if isinstance(value, Mapping):
            legacy_keys = sorted(_TEMPLATE_GRAPHIC_LEGACY_KEYS.intersection(value))
            if legacy_keys:
                raise ValueError(
                    "schema version 2 template graphics use `traces`; "
                    f"legacy field `{legacy_keys[0]}` is not supported"
                )
            _reject_remote_urls_in_payload_tree(value, path=())
            extra = value.get("extra")
            if isinstance(extra, Mapping):
                _reject_disallowed_plotly_extra_keys(extra, path=("extra",))
        return value

    @field_validator("title")
    @classmethod
    def _template_title_not_blank(cls, value: str) -> str:
        """Require a non-empty template graphic title."""

        return _non_blank_text(value, field_name="title")

    @field_validator("subtitle")
    @classmethod
    def _subtitle_stripped(cls, value: str | None) -> str | None:
        """Normalize optional subtitles."""

        return _optional_non_blank_text(value, field_name="subtitle")

    @model_validator(mode="after")
    def _validate_plotly_trace_contract(self) -> "HoumaoTemplateGraphicPayload":
        """Validate chart-family and datasource-binding semantics."""

        data_ref_ids = _template_graphic_data_ref_ids(self.data_refs)
        for index, trace in enumerate(self.traces):
            _validate_template_trace(
                chart_type=self.chart_type,
                trace=trace,
                trace_index=index,
                data_ref_ids=data_ref_ids,
            )
        return self


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


ComponentPayloadModel: TypeAlias = type[_HoumaoAgUiAuthoringModel]
"""Concrete Pydantic model class for one Houmao component payload."""


@dataclass(frozen=True)
class HoumaoAgUiComponentSpec:
    """Registry entry for one Houmao AG-UI component schema."""

    name: HoumaoAgUiComponentName
    schema_version: int
    description: str
    model: ComponentPayloadModel
    example: JsonObject

    def to_summary(self) -> JsonObject:
        """Return compact component metadata."""

        return {
            "name": self.name,
            "schemaVersion": self.schema_version,
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
    HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME: HoumaoAgUiComponentSpec(
        name=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
        schema_version=HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION,
        description=(
            "Display standardized Layer 1 chart intent through Plotly.js."
        ),
        model=HoumaoTemplateGraphicPayload,
        example={
            "schemaVersion": 2,
            "chartType": "bar",
            "renderer": {"preferred": "plotly"},
            "title": "Build Results",
            "subtitle": "Latest CI run",
            "traces": [
                {
                    "name": "Jobs",
                    "x": ["passed", "failed"],
                    "y": [42, 2],
                    "marker": {"color": ["#1f7a4d", "#c2410c"]},
                    "hovertemplate": "%{x}: %{y}<extra></extra>",
                }
            ],
            "layout": {
                "xaxis": {"title": "Status"},
                "yaxis": {"title": "Count"},
                "bargap": 0.28,
            },
            "extra": {
                "plotly": {
                    "layout": {"margin": {"l": 48, "r": 16, "t": 48, "b": 44}},
                }
            },
        },
    ),
    "houmao.table": HoumaoAgUiComponentSpec(
        name="houmao.table",
        schema_version=HOUMAO_AG_UI_SCHEMA_VERSION,
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
        schema_version=HOUMAO_AG_UI_SCHEMA_VERSION,
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
        schema_version=HOUMAO_AG_UI_SCHEMA_VERSION,
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
                    "component": "houmao.graphic.template",
                    "width": "half",
                    "props": {
                        "schemaVersion": 2,
                        "chartType": "bar",
                        "renderer": {"preferred": "plotly"},
                        "title": "Tests",
                        "traces": [{"x": ["passed"], "y": [42]}],
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

    if component in HOUMAO_RETIRED_FIXED_CHART_COMPONENTS:
        raise HoumaoAgUiValidationError(
            f"Retired Houmao AG-UI component `{component}` is no longer supported.",
            component=component,
            repair_hint=(
                "Rewrite fixed chart payloads as schema version 2 "
                "`houmao.graphic.template` payloads."
            ),
        )
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
        if component == HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME:
            _prevalidate_template_graphic_payload(payload)
        validated = spec.model.model_validate(payload)
        normalized = validated.model_dump(mode="json", by_alias=True, exclude_none=True)
    except HoumaoAgUiValidationError:
        raise
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


def _renderer_id(value: str, *, field_name: str) -> str:
    """Return a normalized renderer id or raise for an invalid id."""

    stripped = _non_blank_text(value, field_name=field_name)
    if _RENDERER_ID_PATTERN.fullmatch(stripped) is None:
        raise ValueError(f"{field_name} must be a lower-case renderer id")
    return stripped


def _prevalidate_template_graphic_payload(payload: object) -> None:
    """Raise direct diagnostics for template-graphics breaking changes."""

    if not isinstance(payload, Mapping):
        return

    schema_version = payload.get("schemaVersion", HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION)
    if schema_version != HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION:
        raise HoumaoAgUiValidationError(
            "Template graphics require schemaVersion 2.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=("schemaVersion",),
            repair_hint=(
                "Rewrite experimental schema version 1 payloads to the Plotly-backed "
                "`traces` shape."
            ),
        )

    legacy_keys = sorted(_TEMPLATE_GRAPHIC_LEGACY_KEYS.intersection(payload))
    if legacy_keys:
        raise HoumaoAgUiValidationError(
            "Legacy `data.values` plus `encoding` template payloads are retired.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=tuple(legacy_keys),
            repair_hint="Use schema version 2 `traces` with inline arrays or source bindings.",
        )

    chart_type = payload.get("chartType")
    if isinstance(chart_type, str) and chart_type not in HOUMAO_TEMPLATE_GRAPHIC_CHART_TYPES:
        raise HoumaoAgUiValidationError(
            f"Chart type `{chart_type}` is outside this Layer 1 Plotly template scope.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=("chartType",),
            repair_hint="Use one of: bar, line, scatter, pie, histogram.",
        )
    if isinstance(chart_type, str) and chart_type in HOUMAO_TEMPLATE_GRAPHIC_CHART_TYPES:
        _prevalidate_template_trace_types(payload, chart_type=chart_type)

    renderer = payload.get("renderer")
    if isinstance(renderer, Mapping):
        if "fallback" in renderer:
            raise HoumaoAgUiValidationError(
                "Layer 1 template graphics no longer support renderer fallback lists.",
                component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
                field_paths=("renderer.fallback",),
                repair_hint="Omit `renderer.fallback`; Plotly is the only Layer 1 renderer.",
            )
        preferred = renderer.get("preferred", HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER)
        if preferred != HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER:
            raise HoumaoAgUiValidationError(
                "Layer 1 template graphics require `renderer.preferred` to equal `plotly`.",
                component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
                field_paths=("renderer.preferred",),
                repair_hint="Omit `renderer` or set `renderer.preferred` to `plotly`.",
            )

    extra = payload.get("extra")
    if isinstance(extra, Mapping):
        extra_keys = set(str(key) for key in extra)
        unsupported = sorted(extra_keys.difference({"plotly"}))
        if unsupported:
            raise HoumaoAgUiValidationError(
                f"`extra.{unsupported[0]}` is not supported for Layer 1 template graphics.",
                component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
                field_paths=(f"extra.{unsupported[0]}",),
                repair_hint="Only `extra.plotly` is allowed, and it must stay non-essential.",
            )
        _reject_disallowed_plotly_extra_keys(extra, path=("extra",))

    _reject_remote_urls_in_payload_tree(payload, path=())


def _prevalidate_template_trace_types(
    payload: Mapping[object, object],
    *,
    chart_type: str,
) -> None:
    """Raise direct diagnostics for obvious trace family mismatches."""

    traces = payload.get("traces")
    if not isinstance(traces, list):
        return
    expected_types: dict[str, set[str]] = {
        "bar": {"bar"},
        "line": {"scatter"},
        "scatter": {"scatter"},
        "pie": {"pie"},
        "histogram": {"histogram"},
    }
    expected = expected_types[chart_type]
    for index, trace in enumerate(traces):
        if not isinstance(trace, Mapping):
            continue
        trace_type = trace.get("type")
        if isinstance(trace_type, str) and trace_type not in expected:
            raise HoumaoAgUiValidationError(
                f"Trace type `{trace_type}` is invalid for chartType `{chart_type}`.",
                component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
                field_paths=(f"traces.{index}.type",),
                repair_hint=f"Use Plotly trace type `{sorted(expected)[0]}` for this chart type.",
            )


def _template_graphic_data_ref_ids(
    data_refs: Sequence[TemplateGraphicDataRef] | None,
) -> frozenset[str]:
    """Return declared datasource ids and reject duplicates."""

    ids: set[str] = set()
    for index, data_ref in enumerate(data_refs or ()):
        if data_ref.id in ids:
            raise ValueError(f"dataRefs.{index}.id duplicates `{data_ref.id}`")
        ids.add(data_ref.id)
    return frozenset(ids)


def _validate_template_trace(
    *,
    chart_type: TemplateGraphicChartType,
    trace: TemplateGraphicTrace,
    trace_index: int,
    data_ref_ids: frozenset[str],
) -> None:
    """Validate one trace against its declared chart family."""

    expected_types: dict[str, set[str]] = {
        "bar": {"bar"},
        "line": {"scatter"},
        "scatter": {"scatter"},
        "pie": {"pie"},
        "histogram": {"histogram"},
    }
    actual_type = trace.type
    if actual_type is not None and actual_type not in expected_types[str(chart_type)]:
        expected = ", ".join(sorted(expected_types[str(chart_type)]))
        raise ValueError(
            f"traces.{trace_index}.type `{actual_type}` is invalid for chartType "
            f"`{chart_type}`; expected {expected}"
        )
    if chart_type == "line" and trace.mode is not None and "lines" not in trace.mode:
        raise ValueError(f"traces.{trace_index}.mode for line charts must include `lines`")

    _validate_trace_source_bindings(
        trace=trace,
        trace_index=trace_index,
        data_ref_ids=data_ref_ids,
    )

    if chart_type in {"bar", "line", "scatter"}:
        _require_trace_channel(trace, trace_index=trace_index, channel="x")
        _require_trace_channel(trace, trace_index=trace_index, channel="y")
        _validate_equal_inline_lengths(trace, trace_index=trace_index, channels=("x", "y"))
        return
    if chart_type == "pie":
        _require_trace_channel(trace, trace_index=trace_index, channel="labels")
        _require_trace_channel(trace, trace_index=trace_index, channel="values")
        _validate_equal_inline_lengths(
            trace,
            trace_index=trace_index,
            channels=("labels", "values"),
        )
        return
    if chart_type == "histogram" and not (
        _trace_has_channel(trace, "x") or _trace_has_channel(trace, "y")
    ):
        raise ValueError(f"traces.{trace_index} for histogram charts requires `x` or `y`")


def _validate_trace_source_bindings(
    *,
    trace: TemplateGraphicTrace,
    trace_index: int,
    data_ref_ids: frozenset[str],
) -> None:
    """Validate datasource binding references and channel exclusivity."""

    source = trace.source
    if source is None:
        return
    if not data_ref_ids:
        raise ValueError(f"traces.{trace_index}.source requires matching dataRefs")
    if source.data_ref not in data_ref_ids:
        raise ValueError(
            f"traces.{trace_index}.source.dataRef `{source.data_ref}` is not declared in dataRefs"
        )

    for channel in ("x", "y", "z", "labels", "values", "text"):
        if _source_has_channel(source, channel) and _trace_has_inline_channel(trace, channel):
            raise ValueError(
                f"traces.{trace_index}.{channel} cannot be combined with "
                f"traces.{trace_index}.source.{channel}"
            )
    if source.marker is not None and trace.marker is not None:
        if source.marker.color is not None and trace.marker.color is not None:
            raise ValueError(
                f"traces.{trace_index}.marker.color cannot be combined with "
                f"traces.{trace_index}.source.marker.color"
            )
        if source.marker.size is not None and trace.marker.size is not None:
            raise ValueError(
                f"traces.{trace_index}.marker.size cannot be combined with "
                f"traces.{trace_index}.source.marker.size"
            )


def _require_trace_channel(
    trace: TemplateGraphicTrace,
    *,
    trace_index: int,
    channel: Literal["x", "y", "labels", "values"],
) -> None:
    """Require one inline or datasource-bound trace channel."""

    if not _trace_has_channel(trace, channel):
        raise ValueError(f"traces.{trace_index} requires `{channel}`")


def _trace_has_channel(trace: TemplateGraphicTrace, channel: str) -> bool:
    """Return whether a trace has either inline data or a source binding."""

    return _trace_has_inline_channel(trace, channel) or (
        trace.source is not None and _source_has_channel(trace.source, channel)
    )


def _trace_has_inline_channel(trace: TemplateGraphicTrace, channel: str) -> bool:
    """Return whether a trace has an inline value for a channel."""

    return getattr(trace, channel) is not None


def _source_has_channel(source: TemplateGraphicTraceSource, channel: str) -> bool:
    """Return whether a source object binds one channel."""

    return getattr(source, channel) is not None


def _validate_equal_inline_lengths(
    trace: TemplateGraphicTrace,
    *,
    trace_index: int,
    channels: tuple[str, str],
) -> None:
    """Require matching inline array lengths when both compared channels are inline."""

    first = getattr(trace, channels[0])
    second = getattr(trace, channels[1])
    if isinstance(first, list) and isinstance(second, list) and len(first) != len(second):
        raise ValueError(
            f"traces.{trace_index}.{channels[0]} and traces.{trace_index}.{channels[1]} "
            "must have the same length"
        )


def _reject_disallowed_plotly_extra_keys(value: object, *, path: tuple[str, ...]) -> None:
    """Reject raw backend replacement fields inside Plotly extra data."""

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            next_path = (*path, key_text)
            if key_text in _PLOTLY_EXTRA_DISALLOWED_KEYS:
                field_path = ".".join(next_path)
                raise ValueError(f"{field_path} is not allowed in Layer 1 Plotly extra")
            _reject_disallowed_plotly_extra_keys(nested_value, path=next_path)
        return
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested_value in enumerate(value):
            _reject_disallowed_plotly_extra_keys(nested_value, path=(*path, str(index)))


def _reject_remote_urls_in_payload_tree(value: object, *, path: tuple[str, ...]) -> None:
    """Reject remote URL strings in backend-specific Layer 1 extra blocks."""

    if isinstance(value, str):
        if _REMOTE_URL_PATTERN.search(value.strip()):
            safe_path = ".".join(_redacted_path(path)) or "$"
            raise ValueError(f"payload contains remote URL content at `{safe_path}`")
        return
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            _reject_remote_urls_in_payload_tree(nested_value, path=(*path, str(key)))
        return
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for index, nested_value in enumerate(value):
            _reject_remote_urls_in_payload_tree(nested_value, path=(*path, str(index)))


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


def _optional_non_blank_text(value: str | None, *, field_name: str) -> str | None:
    """Return stripped optional text, treating blank strings as omitted."""

    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


__all__ = [
    "AgUiEventPayload",
    "HOUMAO_AG_UI_EVENT_BATCH_MAX_BYTES",
    "HOUMAO_AG_UI_EVENT_BATCH_MAX_COUNT",
    "HOUMAO_AG_UI_SCHEMA_VERSION",
    "HOUMAO_RETIRED_FIXED_CHART_COMPONENTS",
    "HOUMAO_TEMPLATE_GRAPHIC_CHART_TYPES",
    "HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER",
    "HOUMAO_TEMPLATE_GRAPHIC_RENDERERS",
    "HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION",
    "HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME",
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
