"""Observe common native resources and refresh without launch-material projection."""

from __future__ import annotations

from pathlib import Path
import os
import re
import subprocess
import time
from typing import TYPE_CHECKING, Any, cast

from houmao.execution.context import execution_binding_scope, validate_execution_owner
from houmao.execution.tmux import tmux_server_scope
from houmao.agents.launch_policy import is_supported_dsh_version
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4

from houmao.agents.realm_controller.errors import GatewayError, SessionManifestError
from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.managed_terminal import observe_primary_tmux
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    CommonPluginResourceV1,
    Freshness,
    NativeHomeV1,
    NativeRefreshRequestV1,
    NativeRefreshResultV1,
    RefreshOutcome,
)
from houmao.agents.realm_controller.owner_admission import (
    OwnerAdmissionError,
    observe_owner_prompt,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    read_tmux_session_environment_value,
)

if TYPE_CHECKING:
    from houmao.agents.realm_controller.runtime import RuntimeSessionController


def inspect_native_home_from_manifest(path: Path) -> NativeHomeV1:
    """Resolve existing active home authority without constructing a controller."""

    handle = load_session_manifest(path)
    payload = parse_session_manifest_payload(handle.payload, source=str(path))
    binding = payload.runtime.execution_binding
    socket_path = payload.tmux.socket_path if payload.tmux is not None else None
    try:
        validate_execution_owner(binding)
    except ValueError as exc:
        raise GatewayError(str(exc)) from exc
    if binding is not None and binding.tmux_socket is not None:
        if socket_path != binding.tmux_socket:
            raise GatewayError("Native tmux socket differs from execution binding")
    if socket_path is None:
        raise GatewayError("Primary native runtime authority is unavailable")
    with execution_binding_scope(binding), tmux_server_scope(socket_path):
        return _inspect_native_home_payload(path, payload)


def _inspect_native_home_payload(path: Path, payload: SessionManifestPayloadV4) -> NativeHomeV1:
    """Inspect a validated manifest while its exact owner socket is selected."""

    if (
        payload.registry_launch_authority != "runtime"
        or not payload.registry_generation_id
        or not payload.runtime.session_id
    ):
        raise GatewayError("Active native runtime authority is unavailable")
    tmux = payload.tmux
    if tmux is None or payload.agent_launch_authority is None:
        raise GatewayError("Primary native runtime authority is unavailable")
    name = tmux.session_name
    try:
        observed = observe_primary_tmux(tmux)
        if observed.state == "missing_session":
            raise GatewayError("Active native runtime authority is unavailable")
        if observed.state == "dead_pane":
            raise GatewayError("Active native runtime identity is unavailable")
        if observed.state != "valid":
            raise GatewayError("Primary native runtime authority is unavailable")
        manifest_binding = read_tmux_session_environment_value(
            session_name=name, variable_name=AGENT_MANIFEST_PATH_ENV_VAR
        )
        agent_binding = read_tmux_session_environment_value(
            session_name=name, variable_name=AGENT_ID_ENV_VAR
        )
    except (SessionManifestError, TmuxCommandError):
        raise GatewayError("Primary native runtime authority is unavailable") from None
    if (
        not manifest_binding
        or not Path(manifest_binding).is_absolute()
        or Path(manifest_binding).resolve() != path.resolve()
        or agent_binding != payload.agent_id
    ):
        raise GatewayError("Active native runtime identity is unavailable")
    selector = payload.launch_plan.home_selector
    home = Path(selector.home_path)
    if not home.is_absolute() or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", selector.env_var):
        raise GatewayError("Authoritative native home is unavailable")
    identity = {
        "agent_id": payload.agent_id,
        "runtime_session_id": payload.runtime.session_id,
        "generation": payload.registry_generation_id,
        "tmux_session_name": name,
    }
    if payload.backend == "dsh_web":
        native_identity = payload.backend_state.get("web_identity")
        keys = (
            "agent_id",
            "runtime_session_id",
            "generation",
            "host_incarnation",
            "native_session_id",
            "agent_incarnation",
        )
        if (
            not isinstance(native_identity, dict)
            or any(
                not isinstance(native_identity.get(key), str) or not native_identity[key]
                for key in keys
            )
            or any(native_identity[key] != identity[key] for key in identity if key in keys)
        ):
            raise GatewayError("Native execution identity is unavailable")
        identity.update({key: cast(str, native_identity[key]) for key in keys})
    if payload.mode == "service":
        state = payload.backend_state
        incarnation, native_session = (
            state.get("service_incarnation"),
            state.get("native_session_id"),
        )
        if (
            state.get("generation_id") != payload.registry_generation_id
            or state.get("runtime_session_id") != payload.runtime.session_id
            or not isinstance(incarnation, str)
            or not incarnation
            or not isinstance(native_session, str)
            or not native_session
        ):
            raise GatewayError("Native service identity is unavailable")
        identity.update(service_incarnation=incarnation, native_session_id=native_session)
    return NativeHomeV1(
        agent_id=payload.agent_id,
        backend=payload.backend,
        tool=payload.tool,
        home_dir=str(home),
        home_env_var=selector.env_var,
        identity=identity,
    )


def inspect_native_home(controller: RuntimeSessionController) -> NativeHomeV1:
    """Inspect only active persisted authority, leaving all home files unread."""

    home = inspect_native_home_from_manifest(controller.manifest_path)
    if (
        home.backend != controller.launch_plan.backend
        or home.home_dir != str(controller.launch_plan.home_path)
        or (controller.agent_id is not None and home.agent_id != controller.agent_id)
        or (
            getattr(controller, "tmux_session_name", None) is not None
            and home.identity.get("tmux_session_name") != controller.tmux_session_name
        )
        or (
            controller.registry_generation_id is not None
            and home.identity.get("generation") != controller.registry_generation_id
        )
    ):
        raise GatewayError("Native execution authority changed")
    state = getattr(controller.backend_session, "state", None)
    native_identity = getattr(state, "web_identity", None)
    if home.backend == "dsh_web":
        keys = (
            "agent_id",
            "runtime_session_id",
            "generation",
            "host_incarnation",
            "native_session_id",
            "agent_incarnation",
        )
        if not isinstance(native_identity, dict) or any(
            native_identity.get(key) != home.identity.get(key) for key in keys
        ):
            raise GatewayError("Native execution incarnation changed")
        state = controller.backend_session.observe_web_state()  # type: ignore[attr-defined]
        if not state.get("available") or state.get("identity") != native_identity:
            raise GatewayError("Bound native agent is unavailable")
    return home


def _safe_code(value: object, default: str) -> str:
    """Retain controlled diagnostic codes, excluding arbitrary native exceptions."""

    if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:/ -]{1,120}", value):
        return value
    return default


def _resource(raw: dict[str, Any]) -> CommonPluginResourceV1:
    """Project public resource evidence without native configuration or bodies."""

    names = []
    for item in raw.get("inventory", []):
        name = item.get("name") if isinstance(item, dict) else item
        if isinstance(name, str):
            names.append(name)
    return CommonPluginResourceV1.model_validate(
        {
            "kind": raw["kind"],
            "component": raw["component"],
            "freshness": raw.get("freshness", "unknown"),
            "boundary": raw.get("boundary", "unknown"),
            "inventory": names,
            "complete": raw.get("complete", False),
            "supported": raw.get("supported", False),
            "required": raw.get("required", True),
            "health": _safe_code(raw.get("health"), "unknown"),
            "reason": _safe_code(raw.get("reason"), "native_evidence_unavailable"),
            "evidence": [_safe_code(item, "native_evidence") for item in raw.get("evidence", [])],
        }
    )


def _observation(home: NativeHomeV1, raw: dict[str, Any]) -> CommonPluginObservationV1:
    """Normalize native evidence and derive aggregate freshness conservatively."""

    native_identity = raw.get("identity")
    if not isinstance(native_identity, dict) or any(
        native_identity.get(key) != value
        for key, value in home.identity.items()
        if key != "tmux_session_name"
    ):
        raise GatewayError("Native observation identity does not match authority")
    flags = {}
    for name in (
        "coverage_complete",
        "native_reload",
        "automatic",
        "native_settled",
        "native_ready",
    ):
        value = raw.get(name, False)
        if type(value) is not bool:
            raise ValueError("Native observation flags must be booleans")
        flags[name] = value
    resources = [_resource(item) for item in raw.get("resources", [])]
    required = [item for item in resources if item.required]
    complete = (
        flags["coverage_complete"]
        and {item.kind for item in required} == {"skills", "mcp"}
        and all(item.complete and item.supported for item in required)
    )
    freshness: Freshness = (
        "pending"
        if any(item.freshness == "pending" for item in required)
        else "current"
        if complete and all(item.freshness == "current" for item in required)
        else "unknown"
    )
    return CommonPluginObservationV1(
        home=home,
        **({"observed_at_utc": raw["observed_at_utc"]} if "observed_at_utc" in raw else {}),
        native_version=raw.get("native_version"),
        profile=raw.get("profile"),
        resources=resources,
        coverage_complete=complete,
        freshness=freshness,
        native_reload=flags["native_reload"],
        automatic=flags["automatic"],
        native_settled=flags["native_settled"],
        native_ready=flags["native_ready"],
    )


def unknown_common_observation(home: NativeHomeV1) -> CommonPluginObservationV1:
    """Expose unqualified native evidence without hiding either common kind."""

    return CommonPluginObservationV1(
        home=home,
        resources=[
            CommonPluginResourceV1(kind="skills", component="inventory"),
            CommonPluginResourceV1(kind="mcp", component="inventory"),
        ],
    )


def observe_common_plugins(controller: RuntimeSessionController) -> CommonPluginObservationV1:
    """Read native common state without starting a worker or forcing discovery."""

    home = inspect_native_home(controller)
    observe = getattr(controller.backend_session, "observe_common_plugins", None)
    if callable(observe):
        raw = observe()
        observation = _observation(home, raw)
        if inspect_native_home(controller) != home:
            raise GatewayError("Native authority changed during observation")
        return observation
    observation = unknown_common_observation(home)
    if home.backend == "dsh_acp":
        control = controller.observe_managed_service()
        if control.connection_ready is True and (
            control.native_session_id != home.identity.get("native_session_id")
            or control.service_incarnation != home.identity.get("service_incarnation")
        ):
            raise GatewayError("Native service changed during observation")
        observation.profile = "acp"
        dsh = controller.launch_plan.metadata.get("dsh", {})
        version = dsh.get("detected_tool_version") if isinstance(dsh, dict) else None
        observation.native_version = version if isinstance(version, str) else None
        observation.native_ready = control.can_accept_prompt_now is True
        observation.native_settled = (
            control.connection_ready is True
            and control.active_request_id is None
            and control.last_outcome != "uncertain"
        )
        observation.resources = [
            CommonPluginResourceV1(
                kind="skills",
                component="provider_start",
                boundary="next_load",
                supported=True,
                reason="dsh_service_skill_loader_relaunch",
            ),
            CommonPluginResourceV1(
                kind="mcp",
                component="session_binding",
                boundary="next_load",
                supported=True,
                reason="dsh_service_mcp_session_binding",
            ),
        ]
    elif home.backend == "dsh_headless":
        # The loader reads the currently materialized setup and native patch on
        # every ordinary attempt. No worker is created for this qualification.
        from houmao.agents.dsh_configuration import (
            MATERIALIZED_DSH_TOOL_PARAMS,
            DshEffectiveToolParams,
            load_dsh_home,
            read_dsh_mcp_environment,
        )

        observation.profile = "headless"
        generation = home.identity.get("generation")
        try:
            idle = (
                generation is not None
                and observe_owner_prompt(controller.manifest_path, generation) is None
            )
        except OwnerAdmissionError:
            idle = False
        observation.native_settled = idle
        observation.native_ready = idle

        metadata = controller.launch_plan.metadata.get("dsh", {})
        setup_path = metadata.get("setup_path") if isinstance(metadata, dict) else None
        setup = DshEffectiveToolParams.from_file(
            Path(setup_path)
            if isinstance(setup_path, str)
            else controller.launch_plan.home_path / MATERIALIZED_DSH_TOOL_PARAMS
        )
        load_dsh_home(
            controller.launch_plan.home_path,
            setup,
            controller.launch_plan.env,
            credential_environment=read_dsh_mcp_environment(
                setup, controller.launch_plan.metadata.get("env_source_file")
            ),
            native_profile="headless",
        )
        try:
            selected = subprocess.run(
                [controller.launch_plan.executable, "--version"],
                env={
                    "PATH": controller.launch_plan.env.get(
                        "PATH", os.environ.get("PATH", os.defpath)
                    )
                },
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            selected = None
        observation.native_version = selected
        if is_supported_dsh_version(selected):
            observation.resources = [
                CommonPluginResourceV1(
                    kind="skills",
                    component="next_invocation",
                    supported=True,
                    boundary="next_turn",
                    reason="qualified_current_home_loading",
                ),
                CommonPluginResourceV1(
                    kind="mcp", component="inventory", reason="dsh_cli_mcp_unqualified"
                ),
            ]
    if inspect_native_home(controller) != home:
        raise GatewayError("Native authority changed during observation")
    return observation


def plan_native_refresh(observation: CommonPluginObservationV1) -> NativeRefreshResultV1 | None:
    """Select a mutation-free decision, or request a qualified native handoff."""

    if not observation.native_settled or not observation.native_ready:
        return NativeRefreshResultV1(
            method="none",
            outcome="unavailable",
            observation=observation,
            native_settled=observation.native_settled,
            native_ready=observation.native_ready,
        )
    if observation.freshness == "current":
        return NativeRefreshResultV1(
            method="noop", outcome="already_current", observation=observation
        )
    if observation.automatic_qualified:
        return NativeRefreshResultV1(
            method="automatic", outcome="automatic", observation=observation
        )
    if observation.native_reload:
        return None
    if observation.home.backend == "dsh_acp" and observation.profile == "acp":
        return NativeRefreshResultV1(
            method="none", outcome="restart_required", observation=observation
        )
    return NativeRefreshResultV1(method="none", outcome="unsupported", observation=observation)


def perform_native_refresh(
    controller: RuntimeSessionController,
    request: NativeRefreshRequestV1,
    *,
    deadline_monotonic: float | None = None,
    observation: CommonPluginObservationV1 | None = None,
) -> NativeRefreshResultV1:
    """Run a native operation within one deadline, retaining partial or uncertain effects."""

    entered = time.monotonic()
    deadline = entered + request.timeout_seconds
    if deadline_monotonic is not None:
        deadline = min(deadline, deadline_monotonic)

    def expired(before: CommonPluginObservationV1) -> NativeRefreshResultV1:
        """Confirm that no native handoff was attempted after budget exhaustion."""

        return NativeRefreshResultV1(
            method="none",
            outcome="unavailable",
            observation=before,
            before=before,
            native_settled=before.native_settled,
            native_ready=before.native_ready,
            diagnostics=["native_refresh_deadline_expired_before_handoff"],
        )

    if entered >= deadline:
        if observation is None:
            raise GatewayError("Native refresh deadline expired before observation")
        return expired(observation)
    before = observe_common_plugins(controller)
    if observation is not None and before.home != observation.home:
        return NativeRefreshResultV1(
            method="none",
            outcome="unavailable",
            observation=observation,
            before=observation,
            native_settled=observation.native_settled,
            native_ready=observation.native_ready,
            diagnostics=["native_authority_changed_before_handoff"],
        )
    planned = plan_native_refresh(before)
    if planned is not None:
        return planned
    refresh = getattr(controller.backend_session, "refresh_common_plugins", None)
    if not callable(refresh):
        return NativeRefreshResultV1(method="none", outcome="unsupported", observation=before)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return expired(before)
    try:
        raw = refresh(
            timeout_seconds=remaining,
            deadline_monotonic=deadline,
            expected_identity=before.home.identity,
        )
        after = _observation(before.home, raw.get("observation", {}))
        outcome = raw.get("outcome", "partial")
        if outcome in {"refreshed", "already_current"} and after.freshness != "current":
            outcome = "partial"
        if inspect_native_home(controller) != before.home:
            raise GatewayError("Native execution changed during refresh")
        return NativeRefreshResultV1(
            method=raw.get("method", "noop" if outcome == "already_current" else "native_reload"),
            outcome=cast(RefreshOutcome, outcome),
            before=before,
            observation=after,
            effects=raw.get("effects", "unknown"),
            native_settled=raw.get("native_settled", False),
            native_ready=raw.get("native_ready", False),
            diagnostics=[
                _safe_code(
                    item.get("reason") if isinstance(item, dict) else item,
                    "native_refresh_diagnostic",
                )
                for item in raw.get("diagnostics", [])
            ],
        )
    except Exception:
        # A lost response is not evidence that no native work happened. The
        # gateway reconciles settlement through later passive observation.
        return NativeRefreshResultV1(
            method="native_reload",
            outcome="outcome_unknown",
            before=before,
            observation=before,
            effects="unknown",
            native_settled=False,
            native_ready=False,
            diagnostics=["native_confirmation_unavailable"],
        )
