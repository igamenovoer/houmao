"""Capability response construction for Houmao AG-UI attachment."""

from __future__ import annotations

from typing import Literal, Protocol, cast

from ag_ui.core import (
    AgentCapabilities,
    ExecutionCapabilities,
    HumanInTheLoopCapabilities,
    IdentityCapabilities,
    MultimodalCapabilities,
    MultimodalInputCapabilities,
    MultimodalOutputCapabilities,
    OutputCapabilities,
    StateCapabilities,
    Tool,
    ToolsCapabilities,
    TransportCapabilities,
)

from houmao.ag_ui.authoring import (
    HOUMAO_TEMPLATE_GRAPHIC_BUNDLE_ID,
    HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER,
    HOUMAO_TEMPLATE_GRAPHIC_EXCLUDED_TRACE_TYPES,
    HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE,
    HOUMAO_TEMPLATE_GRAPHIC_RENDERERS,
    HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION,
    HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
    HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES,
    HOUMAO_VEGALITE_GRAPHIC_DEFAULT_SPEC_VERSION,
    HOUMAO_VEGALITE_GRAPHIC_LIBRARY,
    HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES,
    HOUMAO_VEGALITE_GRAPHIC_MAX_INLINE_ROWS,
    HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION,
    HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS,
    HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
)
from houmao.ag_ui.graphics import HOUMAO_RENDER_GRAPHIC_TOOL_NAME
from houmao.ag_ui.models import (
    HoumaoAgUiCapabilitiesResponse,
    HoumaoAgUiFeatureSupport,
    HoumaoAgUiMetadata,
)
from houmao.ag_ui.runtime import ag_ui_target_transport_family_for_backend
from houmao.ag_ui.state import GatewayStatusSnapshot, JsonObject


class AgUiCapabilityRuntime(Protocol):
    """Runtime subset needed to build AG-UI capability metadata."""

    def status(self) -> GatewayStatusSnapshot:
        """Return the current gateway status snapshot."""


def build_ag_ui_capabilities(
    runtime: AgUiCapabilityRuntime,
    *,
    replay_enabled: bool = False,
) -> HoumaoAgUiCapabilitiesResponse:
    """Return conservative AG-UI capabilities for one live Houmao gateway.

    Parameters
    ----------
    runtime:
        Gateway runtime that owns the observed Houmao agent.

    Returns
    -------
    HoumaoAgUiCapabilitiesResponse
        Standard AG-UI capability categories plus Houmao lifecycle metadata.
    """

    del replay_enabled
    status = runtime.status()
    target_transport_family = ag_ui_target_transport_family_for_backend(str(status.backend))
    task_run_submission = target_transport_family != "unknown"
    generated_graphics = target_transport_family == "headless"
    replay_support: Literal["current_snapshot_only"] = "current_snapshot_only"
    features = HoumaoAgUiFeatureSupport(
        http_sse=True,
        gui_connect=True,
        text_input_parsing=True,
        state_snapshots=True,
        task_run_submission=task_run_submission,
        state_deltas=False,
        frontend_tool_execution=False,
        generated_graphics=generated_graphics,
        open_generative_ui=False,
        multimodal_input=False,
    )
    houmao_custom: JsonObject = {
        "features": cast(JsonObject, features.model_dump(mode="json", by_alias=True)),
        "gateway": {
            "attachIdentity": status.attach_identity,
            "backend": str(status.backend),
            "targetTransportFamily": target_transport_family,
            "activeExecution": str(status.active_execution),
            "requestAdmission": str(status.request_admission),
        },
        "graphics": {
            "toolName": HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
            "generatedGraphics": generated_graphics,
        },
        "presentation": {
            "templateGraphics": {
                "toolName": HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
                "schemaVersion": HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION,
                "figureType": HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE,
                "traceTypes": list(HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES),
                "excludedTraceTypes": dict(HOUMAO_TEMPLATE_GRAPHIC_EXCLUDED_TRACE_TYPES),
                "plotlyBundle": {
                    "id": HOUMAO_TEMPLATE_GRAPHIC_BUNDLE_ID,
                    "registeredTraceTypes": list(HOUMAO_TEMPLATE_GRAPHIC_TRACE_TYPES),
                },
                "renderers": list(HOUMAO_TEMPLATE_GRAPHIC_RENDERERS),
                "defaultRenderer": HOUMAO_TEMPLATE_GRAPHIC_DEFAULT_RENDERER,
                "mapPolicy": "offline_only_no_remote_tiles_styles_or_tokens",
                "extraPolicy": {
                    "rendererScoped": True,
                    "requiredForRendering": False,
                    "unsupportedBehavior": "ignore_or_diagnostic",
                    "supportedRendererKeys": ["plotly"],
                    "forbidden": [
                        "full_backend_spec",
                        "raw_plotly_data",
                        "raw_plotly_traces",
                        "raw_plotly_layout",
                        "raw_plotly_config",
                        "raw_plotly_frames",
                        "raw_plotly_transforms",
                        "plotly_templates",
                        "raw_vega_lite_spec",
                        "remote_data_url",
                        "javascript",
                        "html",
                        "iframe",
                        "scriptable_svg",
                    ],
                },
                "datasourceBindings": {
                    "vocabularySupported": True,
                    "materializationSupported": False,
                    "declaredThrough": ["dataRefs", "traces[].source"],
                    "bindingStyle": "field_path",
                    "exampleBindingPaths": [
                        "data.x",
                        "data.y",
                        "data.z",
                        "data.open",
                        "data.high",
                        "data.low",
                        "data.close",
                        "data.labels",
                        "data.values",
                        "data.node.label",
                        "data.link.source",
                        "data.link.target",
                        "data.link.value",
                        "data.header.values",
                        "data.cells.values",
                    ],
                    "limits": {
                        "materializedRows": None,
                        "rowUpdateModes": [],
                        "refresh": False,
                    },
                },
                "rawPlotlyDsl": False,
                "rawVegaLiteDsl": False,
            },
            "vegaDsl": {
                "supported": True,
                "toolNames": [HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME],
                "schemaVersion": HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION,
                "libraries": [
                    {
                        "name": HOUMAO_VEGALITE_GRAPHIC_LIBRARY,
                        "majorVersions": list(HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS),
                        "pythonAuthoring": ["altair"],
                    },
                    {"name": "vega", "supported": False, "planned": True},
                ],
                "renderer": "vega-embed",
                "remoteData": "disabled",
                "inlineData": True,
                "limits": {
                    "payloadBytes": HOUMAO_VEGALITE_GRAPHIC_MAX_BYTES,
                    "inlineRows": HOUMAO_VEGALITE_GRAPHIC_MAX_INLINE_ROWS,
                },
                "preflight": {
                    "pythonCompile": False,
                    "browserCompile": True,
                },
                "authoring": {
                    "altair": {
                        "supported": True,
                        "send": "chart.to_dict()",
                        "runtimeExecution": False,
                    }
                },
            },
        },
        "lifecycle": {
            "agentLifecycleManagedByGui": False,
            "boundary": (
                "GUI attachment observes only; Houmao owns start, stop, restart, abort, "
                "interrupt, and shutdown."
            ),
        },
        "replaySupport": replay_support,
        "publishedEvents": {
            "delivery": "live_only_fanout",
            "storedCount": 0,
            "cacheOwner": "client",
            "missedEventRecovery": "none",
        },
    }

    capabilities = AgentCapabilities(
        identity=IdentityCapabilities(
            name=status.attach_identity,
            type="houmao-per-agent-gateway",
            provider="houmao",
            metadata={
                "backend": str(status.backend),
                "tmuxSessionName": status.tmux_session_name,
            },
        ),
        transport=TransportCapabilities(
            streaming=True,
            websocket=False,
            http_binary=False,
            push_notifications=False,
            resumable=False,
        ),
        tools=ToolsCapabilities(
            supported=generated_graphics,
            items=[
                Tool(
                    name=HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
                    description="Render a validated Houmao graphics artifact.",
                    parameters={
                        "type": "object",
                        "required": ["title", "format"],
                        "properties": {
                            "title": {"type": "string"},
                            "description": {"type": ["string", "null"]},
                            "format": {
                                "type": "string",
                                "enum": [
                                    "svg",
                                    "html_fragment",
                                    "image_url",
                                    "image_data_uri",
                                    "chart_json",
                                ],
                            },
                            "content": {},
                            "contentUrl": {"type": ["string", "null"]},
                            "altText": {"type": ["string", "null"]},
                            "metadata": {"type": "object"},
                        },
                    },
                ),
                Tool(
                    name=HOUMAO_TEMPLATE_GRAPHIC_TOOL_NAME,
                    description="Render a Plotly-backed Houmao Layer 1 template graphic.",
                    parameters={
                        "type": "object",
                        "required": ["schemaVersion", "figureType", "title", "traces"],
                        "properties": {
                            "schemaVersion": {
                                "type": "integer",
                                "const": HOUMAO_TEMPLATE_GRAPHIC_SCHEMA_VERSION,
                            },
                            "figureType": {
                                "type": "string",
                                "const": HOUMAO_TEMPLATE_GRAPHIC_FIGURE_TYPE,
                            },
                            "renderer": {"type": "object"},
                            "title": {"type": "string"},
                            "subtitle": {"type": ["string", "null"]},
                            "traces": {"type": "array", "minItems": 1},
                            "dataRefs": {"type": "array"},
                            "layout": {"type": "object"},
                            "config": {"type": "object"},
                            "display": {"type": "object"},
                            "extra": {"type": "object"},
                        },
                    },
                ),
                Tool(
                    name=HOUMAO_VEGALITE_GRAPHIC_TOOL_NAME,
                    description="Render a declarative Houmao Layer 2 Vega-Lite graphic.",
                    parameters={
                        "type": "object",
                        "required": [
                            "schemaVersion",
                            "library",
                            "specVersion",
                            "title",
                            "spec",
                        ],
                        "properties": {
                            "schemaVersion": {
                                "type": "integer",
                                "const": HOUMAO_VEGALITE_GRAPHIC_SCHEMA_VERSION,
                            },
                            "library": {
                                "type": "string",
                                "const": HOUMAO_VEGALITE_GRAPHIC_LIBRARY,
                            },
                            "specVersion": {
                                "type": "string",
                                "enum": list(HOUMAO_VEGALITE_GRAPHIC_SPEC_VERSIONS),
                                "default": HOUMAO_VEGALITE_GRAPHIC_DEFAULT_SPEC_VERSION,
                            },
                            "title": {"type": "string"},
                            "description": {"type": ["string", "null"]},
                            "spec": {"type": "object"},
                            "display": {"type": "object"},
                        },
                    },
                ),
            ]
            if generated_graphics
            else [],
            parallel_calls=False,
            client_provided=False,
        ),
        output=OutputCapabilities(
            structured_output=False,
            supported_mime_types=["text/event-stream"],
        ),
        state=StateCapabilities(
            snapshots=True,
            deltas=False,
            memory=False,
            persistent_state=True,
        ),
        multimodal=MultimodalCapabilities(
            input=MultimodalInputCapabilities(
                image=False,
                audio=False,
                video=False,
                pdf=False,
                file=False,
            ),
            output=MultimodalOutputCapabilities(
                image=generated_graphics,
                audio=False,
            ),
        ),
        execution=ExecutionCapabilities(
            code_execution=False,
            sandboxed=False,
        ),
        human_in_the_loop=HumanInTheLoopCapabilities(
            supported=False,
            approvals=False,
            interventions=False,
            feedback=False,
            interrupts=False,
            approve_with_edits=False,
        ),
        custom={"houmao": houmao_custom},
    )
    return HoumaoAgUiCapabilitiesResponse(
        capabilities=capabilities,
        houmao=HoumaoAgUiMetadata(
            agent_lifecycle_managed_by_gui=False,
            lifecycle_boundary=(
                "GUI attachment does not start, stop, restart, abort, interrupt, or shut down "
                "the Houmao agent."
            ),
            replay_support=replay_support,
            connect_stream_keepalive="sse_comment_heartbeat",
            features=features,
            gateway={
                "attachIdentity": status.attach_identity,
                "backend": str(status.backend),
                "targetTransportFamily": target_transport_family,
                "activeExecution": str(status.active_execution),
                "graphicsToolName": HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
            },
            published_events={
                "delivery": "live_only_fanout",
                "storedCount": 0,
                "cacheOwner": "client",
                "missedEventRecovery": "none",
            },
        ),
    )
