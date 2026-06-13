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
from houmao.ag_ui.plotly_trace_catalog import (
    PLOTLY_2D_TRACE_CATALOG,
    PLOTLY_2D_TRACE_TYPES,
    PLOTLY_EXCLUDED_TRACE_TYPES,
    PLOTLY_TRACE_CATALOG_POLICY,
    PLOTLY_TRACE_CATALOG_VERSION,
)
from houmao.ag_ui.state import JsonObject

HOUMAO_AG_UI_SCHEMA_VERSION = 1
"""Current schema version for existing non-graphic Houmao component payloads."""

HOUMAO_AG_UI_EVENT_BATCH_MAX_COUNT = 100
"""Maximum AG-UI events accepted in one authoring or gateway publish batch."""

HOUMAO_AG_UI_EVENT_BATCH_MAX_BYTES = 256 * 1024
"""Maximum encoded JSON byte size accepted for one publish batch."""

HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME: Literal["houmao.graphic.template"] = "houmao.graphic.template"
"""Houmao Layer 1 template-graphics AG-UI tool-call name."""

HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION = 3
"""Current Houmao Layer 1 template-graphics payload schema version."""

HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE: Literal["plotly2d"] = "plotly2d"
"""Figure type for Houmao Layer 1 Plotly 2D template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_RENDERERS = ("plotly",)
"""Renderer ids for Houmao Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER = "plotly"
"""Default renderer id for Houmao Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_BUNDLE_ID = "plotly.js-dist-min"
"""Plotly browser bundle identifier advertised for Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES = PLOTLY_2D_TRACE_TYPES
"""Plotly trace families supported by Houmao Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_EXCLUDED_TRACE_TYPES = PLOTLY_EXCLUDED_TRACE_TYPES
"""Plotly trace families explicitly excluded from Layer 1 template graphics."""

HOUMAO_TEMPLATE_GRAPHIC_CHART_TYPES = HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES
"""Deprecated compatibility alias; use HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES."""

HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME: Literal["houmao.graphic.vegalite"] = "houmao.graphic.vegalite"
"""Houmao Layer 2 Vega-Lite DSL graphics AG-UI tool-call name."""

HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION = 1
"""Current Houmao Layer 2 Vega-Lite graphics payload schema version."""

HOUMAO_VEGALITE_GRAPHIC_LIBRARY: Literal["vega-lite"] = "vega-lite"
"""Library identifier accepted by the Layer 2 Vega-Lite payload envelope."""

HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS: tuple[Literal["6"], ...] = ("6",)
"""Supported Vega-Lite major versions for Layer 2 graphics."""

HOUMAO_VEGALITE_GRAPHIC_DEFAULT_SPEC_VERSION: Literal["6"] = "6"
"""Default Vega-Lite major version for Layer 2 graphics."""

HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES = 128 * 1024
"""Maximum encoded JSON byte size accepted for one Vega-Lite component payload."""

HOUMAO_VEGALITE_GRAPHIC_MAX_INLINE_ROWS = 5_000
"""Maximum inline row objects accepted across one Vega-Lite component payload."""

HOUMAO_RETIRED_FIXED_CHART_COMPONENTS = frozenset(
    {"houmao.chart.bar", "houmao.chart.line", "houmao.chart.pie"}
)
"""Retired fixed chart component names that must be rewritten as template graphics."""

HoumaoAgUiComponentName = Literal[
    "houmao.graphic.template",
    "houmao.graphic.vegalite",
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
    re.compile(r"image/svg\+xml", re.IGNORECASE),
)
_REMOTE_URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
_VEGALITE_SCHEMA_URL_PATTERN = re.compile(
    r"^https://vega\.github\.io/schema/vega-lite/v6(?:\.\d+)*\.json$",
    re.IGNORECASE,
)
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

    schema_version: Literal[3] = 3

    @field_validator("*", mode="before")
    @classmethod
    def _reject_unsafe_text_fields(cls, value: object) -> object:
        """Reject unsafe strings wherever Pydantic visits field values."""

        _reject_unsafe_payload_tree(value)
        return value


TemplateGraphicJsonObject: TypeAlias = dict[str, Any]
"""JSON object accepted inside curated Plotly template fields."""

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


class VegaLiteGraphicDisplay(_HoumaoAgUiAuthoringModel):
    """Display metadata that is not part of the Vega-Lite spec."""

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


class HoumaoVegaLiteGraphicPayload(_VersionedComponentPayload):
    """Payload for `houmao.graphic.vegalite`."""

    schema_version: Literal[1] = 1
    library: Literal["vega-lite"] = HOUMAO_VEGALITE_GRAPHIC_LIBRARY
    spec_version: Literal["6"] = Field(
        default=HOUMAO_VEGALITE_GRAPHIC_DEFAULT_SPEC_VERSION,
        alias="specVersion",
    )
    title: str
    description: str | None = None
    spec: dict[str, Any]
    display: VegaLiteGraphicDisplay | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        """Require a non-empty Vega-Lite title."""

        return _non_blank_text(value, field_name="title")

    @field_validator("description")
    @classmethod
    def _description_stripped(cls, value: str | None) -> str | None:
        """Normalize optional descriptions."""

        return _optional_non_blank_text(value, field_name="description")

    @model_validator(mode="before")
    @classmethod
    def _prevalidate_vegalite_shape(cls, value: object) -> object:
        """Apply Vega-Lite-specific payload checks before normal validation."""

        _prevalidate_vegalite_graphic_payload(value)
        return value


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


class TemplateGraphicTraceSource(_HoumaoAgUiAuthoringModel):
    """Reserved datasource bindings for one trace."""

    data_ref: str = Field(alias="dataRef")
    bindings: dict[str, TemplateGraphicColumnBinding] = Field(default_factory=dict, min_length=1)

    @field_validator("data_ref")
    @classmethod
    def _data_ref_not_blank(cls, value: str) -> str:
        """Require a non-empty datasource id."""

        return _non_blank_text(value, field_name="source.dataRef")


    @field_validator("bindings")
    @classmethod
    def _binding_paths_not_blank(
        cls,
        value: dict[str, TemplateGraphicColumnBinding],
    ) -> dict[str, TemplateGraphicColumnBinding]:
        """Require non-empty binding field paths."""

        normalized: dict[str, TemplateGraphicColumnBinding] = {}
        for path, binding in value.items():
            stripped = _non_blank_text(path, field_name="source.bindings")
            normalized[stripped] = binding
        return normalized


class TemplateGraphicTrace(_HoumaoAgUiAuthoringModel):
    """One catalog-backed Plotly 2D trace."""

    type: str
    name: str | None = None
    data: TemplateGraphicJsonObject = Field(default_factory=dict)
    style: TemplateGraphicJsonObject = Field(default_factory=dict)
    source: TemplateGraphicTraceSource | None = None

    @field_validator("type")
    @classmethod
    def _type_not_blank(cls, value: str) -> str:
        """Normalize the required trace type."""

        return _non_blank_text(value, field_name="trace.type")

    @field_validator("name")
    @classmethod
    def _optional_text_stripped(cls, value: str | None) -> str | None:
        """Normalize optional trace text."""

        return _optional_non_blank_text(value, field_name="trace")


class TemplateGraphicPlotlyExtra(_HoumaoAgUiAuthoringModel):
    """Allowlisted non-essential Plotly presentation refinements."""

    layout: TemplateGraphicJsonObject | None = None
    config: TemplateGraphicJsonObject | None = None
    style: TemplateGraphicJsonObject | None = None
    display: TemplateGraphicDisplay | None = None


class TemplateGraphicExtra(_HoumaoAgUiAuthoringModel):
    """Renderer-scoped extra fields for Layer 1 template graphics."""

    plotly: TemplateGraphicPlotlyExtra | None = None


class HoumaoTemplateGraphicPayload(_TemplateGraphicVersionedPayload):
    """Payload for `houmao.graphic.template`."""

    figure_type: Literal["plotly2d"] = Field(
        default=HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE,
        alias="figureType",
    )
    renderer: TemplateGraphicRendererSelection = Field(
        default_factory=TemplateGraphicRendererSelection
    )
    title: str
    subtitle: str | None = None
    traces: list[TemplateGraphicTrace] = Field(min_length=1)
    data_refs: list[TemplateGraphicDataRef] | None = Field(default=None, alias="dataRefs")
    layout: TemplateGraphicJsonObject | None = None
    config: TemplateGraphicJsonObject = Field(default_factory=lambda: {"responsive": True})
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
                    "schema version 3 template graphics use `traces`; "
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
    metadata: JsonObject | None = None

    def to_summary(self) -> JsonObject:
        """Return compact component metadata."""

        return {
            "name": self.name,
            "schemaVersion": self.schema_version,
            "description": self.description,
        }

    def to_schema_payload(self) -> JsonObject:
        """Return the JSON Schema-compatible component schema payload."""

        payload: JsonObject = {
            **self.to_summary(),
            "schema": cast(JsonObject, self.model.model_json_schema(by_alias=True)),
            "example": self.example,
            "protocol": "houmao.application.ag-ui",
        }
        if self.metadata:
            payload.update(self.metadata)
        return payload


_COMPONENT_SPECS: dict[str, HoumaoAgUiComponentSpec] = {
    HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME: HoumaoAgUiComponentSpec(
        name=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
        schema_version=HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION,
        description=("Display standardized Layer 1 Plotly 2D template graphics."),
        model=HoumaoTemplateGraphicPayload,
        example={
            "schemaVersion": 3,
            "figureType": "plotly2d",
            "renderer": {"preferred": "plotly"},
            "title": "Build Results",
            "subtitle": "Latest CI run",
            "traces": [
                {
                    "type": "bar",
                    "name": "Jobs",
                    "data": {"x": ["passed", "failed"], "y": [42, 2]},
                    "style": {
                        "marker": {"color": ["#1f7a4d", "#c2410c"]},
                        "hovertemplate": "%{x}: %{y}<extra></extra>",
                    },
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
        metadata={
            "traceCatalog": {
                "version": PLOTLY_TRACE_CATALOG_VERSION,
                "figureType": HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE,
                "supportedTraceTypes": list(PLOTLY_2D_TRACE_TYPES),
                "excludedTraceTypes": dict(PLOTLY_EXCLUDED_TRACE_TYPES),
                "policy": cast(JsonObject, PLOTLY_TRACE_CATALOG_POLICY),
            }
        },
    ),
    HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME: HoumaoAgUiComponentSpec(
        name=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
        schema_version=HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION,
        description="Display a Layer 2 declarative Vega-Lite v6 graphic.",
        model=HoumaoVegaLiteGraphicPayload,
        example={
            "schemaVersion": 1,
            "library": "vega-lite",
            "specVersion": "6",
            "title": "Queue Status",
            "description": "Inline Vega-Lite data rendered in the workbench.",
            "spec": {
                "$schema": "https://vega.github.io/schema/vega-lite/v6.4.1.json",
                "data": {
                    "values": [
                        {"status": "ready", "count": 58},
                        {"status": "queued", "count": 23},
                    ]
                },
                "mark": "bar",
                "encoding": {
                    "x": {"field": "status", "type": "nominal"},
                    "y": {"field": "count", "type": "quantitative"},
                },
            },
            "display": {"height": 360, "caption": "Current queue status."},
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
        description=("Compose Houmao graphic, table, and metric components into one layout."),
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
                        "schemaVersion": 3,
                        "figureType": "plotly2d",
                        "renderer": {"preferred": "plotly"},
                        "title": "Tests",
                        "traces": [{"type": "bar", "data": {"x": ["passed"], "y": [42]}}],
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
                "Rewrite fixed chart payloads as schema version 3 "
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


def template_graphic_trace_catalog_payload() -> JsonObject:
    """Return discoverable Plotly 2D trace catalog metadata."""

    return {
        "component": HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
        "schemaVersion": HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION,
        "figureType": HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE,
        "catalogVersion": PLOTLY_TRACE_CATALOG_VERSION,
        "supportedTraceTypes": list(PLOTLY_2D_TRACE_TYPES),
        "excludedTraceTypes": dict(PLOTLY_EXCLUDED_TRACE_TYPES),
        "policy": cast(JsonObject, PLOTLY_TRACE_CATALOG_POLICY),
    }


def validate_component_payload(component: str, payload: object) -> JsonObject:
    """Validate one component payload and return its normalized JSON object."""

    spec = get_component_spec(component)
    try:
        _reject_unsafe_payload_tree(payload)
        if component == HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME:
            _prevalidate_template_graphic_payload(payload)
        elif component == HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME:
            _prevalidate_vegalite_graphic_payload(payload)
        elif component == "houmao.dashboard":
            _prevalidate_dashboard_payload(payload)
        validated = spec.model.model_validate(payload)
        normalized = validated.model_dump(mode="json", by_alias=True, exclude_none=True)
        if component == "houmao.dashboard":
            _normalize_dashboard_child_payloads(normalized)
    except HoumaoAgUiValidationError:
        raise
    except ValidationError as exc:
        if component == HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME:
            template_error = _template_validation_error_payload(exc)
            if template_error is not None:
                raise template_error from exc
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


def _template_validation_error_payload(exc: ValidationError) -> HoumaoAgUiValidationError | None:
    """Return a detailed template validation error when one is available."""

    errors = exc.errors(include_url=False)
    if not errors:
        return None
    first = errors[0]
    context = first.get("ctx")
    if not isinstance(context, Mapping):
        return None
    raw_error = context.get("error")
    if not isinstance(raw_error, ValueError):
        return None
    message = str(raw_error)
    field_path = message.split(" ", 1)[0]
    if not field_path.startswith(("traces.", "layout", "config", "extra")):
        field_path = "$"
    return HoumaoAgUiValidationError(
        message,
        component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
        field_paths=(field_path,),
        repair_hint=(
            "Inspect the Plotly 2D trace catalog with "
            "`houmao-mgr internals ag-ui components schema houmao.graphic.template`."
        ),
    )


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


def _prevalidate_vegalite_graphic_payload(payload: object) -> None:
    """Raise direct diagnostics for Layer 2 Vega-Lite payload policy."""

    if not isinstance(payload, Mapping):
        return

    encoded_size = _encoded_json_size(payload)
    if encoded_size > HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES:
        raise HoumaoAgUiValidationError(
            (
                f"`{HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME}` payload is {encoded_size} bytes, "
                f"above the limit of {HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES}."
            ),
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=("$",),
            repair_hint="Reduce inline data or split large charts into smaller components.",
        )

    schema_version = payload.get("schemaVersion", HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION)
    if schema_version != HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION:
        raise HoumaoAgUiValidationError(
            "Layer 2 Vega-Lite graphics require schemaVersion 1.",
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=("schemaVersion",),
            repair_hint="Use the `houmao.graphic.vegalite` envelope with schemaVersion 1.",
        )

    library = payload.get("library", HOUMAO_VEGALITE_GRAPHIC_LIBRARY)
    if library != HOUMAO_VEGALITE_GRAPHIC_LIBRARY:
        raise HoumaoAgUiValidationError(
            "Layer 2 Vega-Lite graphics require library `vega-lite`.",
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=("library",),
            repair_hint='Use `library: "vega-lite"`; direct raw Vega is not supported yet.',
        )

    spec_version = payload.get("specVersion", HOUMAO_VEGALITE_GRAPHIC_DEFAULT_SPEC_VERSION)
    if spec_version not in HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS:
        supported = ", ".join(HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS)
        raise HoumaoAgUiValidationError(
            f"Unsupported Vega-Lite specVersion `{spec_version}`.",
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=("specVersion",),
            repair_hint=f"Use one of the supported Vega-Lite major versions: {supported}.",
        )

    spec = payload.get("spec")
    if "spec" in payload and not isinstance(spec, Mapping):
        raise HoumaoAgUiValidationError(
            "`houmao.graphic.vegalite.spec` must be a Vega-Lite JSON object.",
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=("spec",),
            repair_hint=(
                "Send `chart.to_dict()` or equivalent Vega-Lite JSON, not Python source, "
                "Altair objects, or notebook state."
            ),
        )
    if isinstance(spec, Mapping):
        inline_rows = _InlineRowCounter()
        _reject_vegalite_remote_loading(
            spec,
            path=("spec",),
            inline_rows=inline_rows,
        )


@dataclass
class _InlineRowCounter:
    """Mutable counter for inline Vega-Lite row objects."""

    count: int = 0


def _reject_vegalite_remote_loading(
    value: object,
    *,
    path: tuple[str, ...],
    inline_rows: _InlineRowCounter,
) -> None:
    """Reject remote-loading shapes while allowing known Vega-Lite schema URLs."""

    if isinstance(value, str):
        stripped = value.strip()
        if _REMOTE_URL_PATTERN.search(stripped) and not _is_allowed_vegalite_schema_url(
            stripped,
            path=path,
        ):
            safe_path = ".".join(_redacted_path(path)) or "$"
            raise HoumaoAgUiValidationError(
                f"`{HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME}` contains remote URL content.",
                component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
                field_paths=(safe_path,),
                repair_hint="Use inline `data.values`; remote Vega-Lite loading is disabled.",
            )
        return
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            next_path = (*path, key_text)
            if key_text == "url" and nested_value is not None:
                safe_path = ".".join(_redacted_path(next_path)) or "$"
                raise HoumaoAgUiValidationError(
                    f"`{HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME}` contains a disabled URL field.",
                    component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
                    field_paths=(safe_path,),
                    repair_hint=(
                        "Use inline `data.values`; remote files, local files, and asset URLs "
                        "are not supported."
                    ),
                )
            if key_text == "values" and isinstance(nested_value, list):
                _count_vegalite_inline_rows(nested_value, path=next_path, inline_rows=inline_rows)
            _reject_vegalite_remote_loading(
                nested_value,
                path=next_path,
                inline_rows=inline_rows,
            )
        return
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for index, nested_value in enumerate(value):
            _reject_vegalite_remote_loading(
                nested_value,
                path=(*path, str(index)),
                inline_rows=inline_rows,
            )


def _is_allowed_vegalite_schema_url(value: str, *, path: tuple[str, ...]) -> bool:
    """Return whether a URL string is the supported Vega-Lite v6 schema marker."""

    return path[-1:] == ("$schema",) and _VEGALITE_SCHEMA_URL_PATTERN.fullmatch(value) is not None


def _count_vegalite_inline_rows(
    values: list[object],
    *,
    path: tuple[str, ...],
    inline_rows: _InlineRowCounter,
) -> None:
    """Count inline row objects in Vega-Lite `values` arrays."""

    row_count = sum(1 for item in values if isinstance(item, Mapping))
    if row_count == 0:
        return
    inline_rows.count += row_count
    if inline_rows.count > HOUMAO_VEGALITE_GRAPHIC_MAX_INLINE_ROWS:
        safe_path = ".".join(_redacted_path(path)) or "$"
        raise HoumaoAgUiValidationError(
            (
                f"`{HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME}` contains "
                f"{inline_rows.count} inline rows, above the limit of "
                f"{HOUMAO_VEGALITE_GRAPHIC_MAX_INLINE_ROWS}."
            ),
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=(safe_path,),
            repair_hint="Reduce inline data rows before sending the Vega-Lite payload.",
        )


def _encoded_json_size(value: object) -> int:
    """Return compact encoded JSON byte size or raise a safe validation error."""

    try:
        rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise HoumaoAgUiValidationError(
            "`houmao.graphic.vegalite` payload must be JSON serializable.",
            component=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
            field_paths=("$",),
            repair_hint="Send plain JSON values, not Python objects.",
        ) from exc
    return len(rendered.encode("utf-8"))


def _prevalidate_dashboard_payload(payload: object) -> None:
    """Validate dashboard child component props before normal dashboard parsing."""

    if not isinstance(payload, Mapping):
        return
    children = payload.get("children")
    if not isinstance(children, list):
        return
    for index, child in enumerate(children):
        if not isinstance(child, Mapping):
            continue
        component = child.get("component")
        props = child.get("props")
        if not isinstance(component, str) or not isinstance(props, Mapping):
            continue
        try:
            validate_component_payload(component, props)
        except HoumaoAgUiValidationError as exc:
            child_paths = _prefix_field_paths(
                prefix=f"children.{index}.props",
                paths=exc.field_paths,
            )
            raise HoumaoAgUiValidationError(
                f"Dashboard child `{component}` payload is invalid.",
                component="houmao.dashboard",
                field_paths=child_paths or (f"children.{index}.props",),
                repair_hint=exc.repair_hint,
            ) from exc


def _normalize_dashboard_child_payloads(payload: JsonObject) -> None:
    """Normalize dashboard child props in the already-validated payload."""

    children = payload.get("children")
    if not isinstance(children, list):
        return
    for child in children:
        if not isinstance(child, dict):
            continue
        component = child.get("component")
        props = child.get("props")
        if isinstance(component, str) and isinstance(props, Mapping):
            child["props"] = validate_component_payload(component, props)


def _prefix_field_paths(*, prefix: str, paths: Sequence[str]) -> tuple[str, ...]:
    """Return field paths nested under a dashboard child props prefix."""

    prefixed: list[str] = []
    for path in paths:
        if path == "$":
            prefixed.append(prefix)
        else:
            prefixed.append(f"{prefix}.{path}")
    return tuple(prefixed)


def _prevalidate_template_graphic_payload(payload: object) -> None:
    """Raise direct diagnostics for template-graphics breaking changes."""

    if not isinstance(payload, Mapping):
        return

    schema_version = payload.get("schemaVersion", HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION)
    if schema_version != HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION:
        raise HoumaoAgUiValidationError(
            "Template graphics require schemaVersion 3.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=("schemaVersion",),
            repair_hint=(
                "Rewrite template payloads to schema version 3 with "
                '`figureType: "plotly2d"` and `traces[].type`.'
            ),
        )

    if "chartType" in payload:
        raise HoumaoAgUiValidationError(
            "Schema version 3 template graphics do not use `chartType`.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=("chartType",),
            repair_hint=(
                "Use `figureType: \"plotly2d\"` and choose Plotly families with "
                "`traces[].type`."
            ),
        )

    legacy_keys = sorted(_TEMPLATE_GRAPHIC_LEGACY_KEYS.intersection(payload))
    if legacy_keys:
        raise HoumaoAgUiValidationError(
            "Legacy `data.values` plus `encoding` template payloads are retired.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=tuple(legacy_keys),
            repair_hint="Use schema version 3 `traces[].data` or `traces[].source.bindings`.",
        )

    figure_type = payload.get("figureType", HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE)
    if figure_type != HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE:
        raise HoumaoAgUiValidationError(
            "Template graphics require `figureType` to equal `plotly2d`.",
            component=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
            field_paths=("figureType",),
            repair_hint='Use `figureType: "plotly2d"` for Layer 1 template graphics.',
        )

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
    trace: TemplateGraphicTrace,
    trace_index: int,
    data_ref_ids: frozenset[str],
) -> None:
    """Validate one trace against the Plotly 2D trace catalog."""

    actual_type = trace.type.strip()
    if actual_type in PLOTLY_EXCLUDED_TRACE_TYPES:
        reason = PLOTLY_EXCLUDED_TRACE_TYPES[actual_type]
        raise ValueError(f"traces.{trace_index}.type `{actual_type}` is excluded: {reason}")
    catalog_entry = PLOTLY_2D_TRACE_CATALOG.get(actual_type)
    if catalog_entry is None:
        raise ValueError(f"traces.{trace_index}.type `{actual_type}` is not supported")

    if not trace.data and trace.source is None:
        raise ValueError(f"traces.{trace_index} requires `data` or `source.bindings`")

    _validate_template_object_paths(
        value=trace.data,
        allowed_paths=frozenset(catalog_entry["data_paths"]),
        root=f"traces.{trace_index}.data",
    )
    _validate_template_object_paths(
        value=trace.style,
        allowed_paths=frozenset(catalog_entry["style_paths"]),
        root=f"traces.{trace_index}.style",
    )

    _validate_trace_source_bindings(
        trace=trace,
        trace_index=trace_index,
        data_ref_ids=data_ref_ids,
        binding_paths=frozenset(catalog_entry["binding_paths"]),
    )


def _validate_trace_source_bindings(
    *,
    trace: TemplateGraphicTrace,
    trace_index: int,
    data_ref_ids: frozenset[str],
    binding_paths: frozenset[str],
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

    inline_paths = _template_object_leaf_paths(trace.data)
    for raw_path in source.bindings:
        binding_path = _normalize_binding_path(raw_path)
        if binding_path not in binding_paths:
            raise ValueError(f"traces.{trace_index}.source.bindings.{raw_path} is not supported")
        if binding_path in inline_paths:
            raise ValueError(
                f"traces.{trace_index}.data.{binding_path} cannot be combined with "
                f"traces.{trace_index}.source.bindings.{raw_path}"
            )


def _validate_template_object_paths(
    *,
    value: Mapping[str, Any],
    allowed_paths: frozenset[str],
    root: str,
) -> None:
    """Validate object leaf paths against one catalog allowlist."""

    _reject_plotly_policy_keys(value, path=tuple(root.split(".")))
    for path in _template_object_leaf_paths(value):
        if path not in allowed_paths:
            raise ValueError(f"{root}.{path} is not supported")


def _template_object_leaf_paths(value: Mapping[str, Any]) -> frozenset[str]:
    """Return leaf paths from a template object."""

    paths: set[str] = set()
    _collect_template_object_leaf_paths(value, prefix=(), paths=paths)
    return frozenset(paths)


def _collect_template_object_leaf_paths(
    value: object,
    *,
    prefix: tuple[str, ...],
    paths: set[str],
) -> None:
    """Collect leaf paths, treating arrays as leaf values."""

    if isinstance(value, Mapping):
        if not value and prefix:
            paths.add(".".join(prefix))
            return
        for key, nested in value.items():
            _collect_template_object_leaf_paths(nested, prefix=(*prefix, str(key)), paths=paths)
        return
    if prefix:
        paths.add(".".join(prefix))


def _normalize_binding_path(path: str) -> str:
    """Return a catalog path from a public source binding path."""

    return path.removeprefix("data.")


def _reject_plotly_policy_keys(value: object, *, path: tuple[str, ...]) -> None:
    """Reject globally unsafe Plotly keys inside catalog-controlled objects."""

    rejected = {
        str(key).lower()
        for key in PLOTLY_TRACE_CATALOG_POLICY.get("globalRejectedFields", ())
        if key != "*src"
    }
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            next_path = (*path, key_text)
            if lowered.endswith("src") or lowered in rejected:
                field_path = ".".join(next_path)
                raise ValueError(f"{field_path} is not allowed in Layer 1 Plotly template fields")
            _reject_plotly_policy_keys(nested_value, path=next_path)
        return
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested_value in enumerate(value):
            _reject_plotly_policy_keys(nested_value, path=(*path, str(index)))


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
    "HOUMAO_TEMPLATE_GRAPHIC_BUNDLE_ID",
    "HOUMAO_TEMPLATE_GRAPHIC_CHART_TYPES",
    "HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER",
    "HOUMAO_TEMPLATE_GRAPHIC_EXCLUDED_TRACE_TYPES",
    "HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE",
    "HOUMAO_TEMPLATE_GRAPHIC_RENDERERS",
    "HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION",
    "HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME",
    "HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES",
    "HOUMAO_VEGALITE_GRAPHIC_DEFAULT_SPEC_VERSION",
    "HOUMAO_VEGALITE_GRAPHIC_LIBRARY",
    "HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES",
    "HOUMAO_VEGALITE_GRAPHIC_MAX_INLINE_ROWS",
    "HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION",
    "HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS",
    "HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME",
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
    "template_graphic_trace_catalog_payload",
    "validate_ag_ui_event_sequence",
    "validate_component_payload",
    "validation_error_payload",
]
