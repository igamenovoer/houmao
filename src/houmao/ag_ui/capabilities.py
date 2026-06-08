"""Capability response construction for Houmao AG-UI attachment."""

from __future__ import annotations

from typing import Protocol, cast

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


def build_ag_ui_capabilities(runtime: AgUiCapabilityRuntime) -> HoumaoAgUiCapabilitiesResponse:
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

    status = runtime.status()
    target_transport_family = ag_ui_target_transport_family_for_backend(str(status.backend))
    task_run_submission = target_transport_family != "unknown"
    generated_graphics = target_transport_family == "headless"
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
        "lifecycle": {
            "agentLifecycleManagedByGui": False,
            "boundary": (
                "GUI attachment observes only; Houmao owns start, stop, restart, abort, "
                "interrupt, and shutdown."
            ),
        },
        "replaySupport": "current_snapshot_only",
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
                )
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
            replay_support="current_snapshot_only",
            connect_stream_keepalive="sse_comment_heartbeat",
            features=features,
            gateway={
                "attachIdentity": status.attach_identity,
                "backend": str(status.backend),
                "targetTransportFamily": target_transport_family,
                "activeExecution": str(status.active_execution),
                "graphicsToolName": HOUMAO_RENDER_GRAPHIC_TOOL_NAME,
            },
        ),
    )
