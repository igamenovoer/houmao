"""Managed-agent commands for `houmao-mgr`."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, cast

import click

from houmao.agents.definition_parser import resolve_explicit_or_named_preset_path
from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.launch_policy.models import OperatorPromptMode
from houmao.agents.managed_launch_force import (
    ManagedLaunchForceMode,
    normalize_managed_launch_force_mode,
)
from houmao.agents.managed_prompt_header import (
    ManagedHeaderPolicy,
    ManagedHeaderSectionName,
    ManagedHeaderSectionPolicy,
    compose_managed_launch_prompt_payload,
    managed_prompt_header_metadata,
    normalize_managed_header_policy,
    parse_managed_header_section_policy_assignments,
    resolve_managed_launch_identity,
    resolve_managed_prompt_header_decision,
    resolve_managed_prompt_header_section_decisions,
)
from houmao.agents.mailbox_runtime_models import MailboxDeclarativeConfig
from houmao.agents.mailbox_runtime_support import (
    parse_declarative_mailbox_config,
    replaceable_mailbox_cleanup_paths,
    resolved_mailbox_config_from_payload,
)
from houmao.agents.launch_profile_memo_seeds import (
    LaunchProfileMemoSeedApplication,
    apply_launch_profile_memo_seed,
)
from houmao.agents.agent_workspace import AgentMemoryPaths, resolve_agent_memory
from houmao.agents.model_selection import ModelConfig, normalize_model_config
from houmao.agents.native_launch_resolver import (
    infer_launch_source_directory_from_agent_def_dir,
    resolve_effective_agent_def_dir,
    resolve_native_launch_target,
    resolve_preset_owner_agent_def_dir,
)
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR
from houmao.agents.realm_controller.gateway_models import (
    GatewayCurrentExecutionMode,
    GatewayTuiTrackingTimingOverridesV1,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    attach_tmux_session as attach_tmux_session_shared,
    list_tmux_panes,
)
from houmao.agents.realm_controller.backends.headless_output import (
    HeadlessDisplayDetail,
    HeadlessDisplayStyle,
)
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.loaders import load_brain_manifest
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.agents.realm_controller.runtime import resume_runtime_session, start_runtime_session
from houmao.agents.realm_controller.errors import (
    LaunchPlanError,
    LaunchPolicyResolutionError,
    SessionManifestError,
)
from houmao.agents.realm_controller.models import HeadlessResumeSelection, JoinedLaunchEnvBinding
from houmao.agents.realm_controller.registry_models import LiveAgentRegistryRecordV2
from houmao.agents.realm_controller.registry_storage import resolve_live_agent_record_by_agent_id
from houmao.project.overlay import (
    PROJECT_OVERLAY_DIR_ENV_VAR,
    ProjectAwareLocalRoots,
    ensure_project_aware_local_roots,
    materialize_project_agent_catalog_projection,
    resolve_project_aware_local_roots,
)
from houmao.project.launch_profiles import ResolvedLaunchProfileMemoSeed, resolve_launch_profile
from houmao.server.tui.process import PaneProcessInspector

from .cleanup import cleanup_group
from .gateway import (
    _require_current_tmux_session_name,
    _resolve_current_session_agent_def_dir,
    _resolve_current_session_manifest,
    gateway_group,
)
from .mail import mail_group
from .mailbox import mailbox_group
from .turn import turn_group
from .workspace import memory_group
from ..runtime_artifacts import JoinedSessionArtifacts, materialize_joined_launch
from ..common import (
    managed_agent_selector_options,
    managed_launch_force_option,
    pair_port_option,
    resolve_prompt_text,
    resolve_managed_agent_selector,
)
from ..output import emit
from ..project_aware_wording import (
    describe_mailbox_root_selection,
    describe_overlay_bootstrap,
    describe_overlay_root_selection_source,
    describe_runtime_root_selection,
)
from ..renderers.agents import (
    render_agent_list_fancy,
    render_agent_list_plain,
    render_agent_state_fancy,
    render_agent_state_plain,
    render_launch_completion_fancy,
    render_launch_completion_plain,
)
from ..managed_agents import (
    ManagedAgentTarget,
    interrupt_managed_agent,
    list_managed_agents,
    managed_agent_state_payload,
    prompt_managed_agent,
    relaunch_managed_agent,
    resolve_managed_agent_target,
    stop_managed_agent,
)

_DEFAULT_PROVIDER = "claude_code"
_PROVIDERS = frozenset(
    {
        "claude_code",
        "codex",
        "gemini_cli",
    }
)
_JOIN_SUPPORTED_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "gemini": ("gemini",),
}
_PROVIDER_BY_TOOL: dict[str, str] = {
    "claude": "claude_code",
    "codex": "codex",
    "gemini": "gemini_cli",
}
_PRESET_FILE_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")


@dataclass(frozen=True)
class LocalManagedAgentLaunchResult:
    """Resolved local launch controller plus project-aware root detail fields."""

    controller: Any
    memory: AgentMemoryPaths
    runtime_root: Path
    mailbox_root: Path
    runtime_root_detail: str
    mailbox_root_detail: str
    overlay_root: Path
    overlay_root_detail: str
    project_overlay_bootstrapped: bool
    overlay_bootstrap_detail: str
    memo_seed_application: LaunchProfileMemoSeedApplication | None = None


@dataclass(frozen=True)
class _ManagedForceTakeoverContext:
    """Resolved predecessor state for one forced managed-agent replacement."""

    force_mode: ManagedLaunchForceMode
    agent_name: str
    agent_id: str
    target: ManagedAgentTarget
    record: LiveAgentRegistryRecordV2
    home_id: str
    home_path: Path
    runtime_root: Path
    session_root: Path | None
    mailbox_cleanup_paths: tuple[Path, ...]


def _load_brain_home_identity_from_manifest(
    brain_manifest: Mapping[str, Any],
    *,
    source: str,
) -> tuple[Path, str, Path]:
    """Return runtime-root and home identity fields from one brain manifest."""

    runtime_payload = brain_manifest.get("runtime")
    if not isinstance(runtime_payload, Mapping):
        raise RuntimeError(f"{source} is missing runtime metadata.")

    runtime_root_value = runtime_payload.get("runtime_root")
    home_id_value = runtime_payload.get("home_id")
    home_path_value = runtime_payload.get("home_path")
    if not isinstance(runtime_root_value, str) or not runtime_root_value.strip():
        raise RuntimeError(f"{source} stores invalid runtime.runtime_root.")
    if not isinstance(home_id_value, str) or not home_id_value.strip():
        raise RuntimeError(f"{source} stores invalid runtime.home_id.")
    if not isinstance(home_path_value, str) or not home_path_value.strip():
        raise RuntimeError(f"{source} stores invalid runtime.home_path.")
    return (
        Path(runtime_root_value).expanduser().resolve(),
        home_id_value,
        Path(home_path_value).expanduser().resolve(),
    )


def _prepare_managed_force_takeover_context(
    *,
    managed_launch_identity: Any,
    resolved_runtime_root: Path,
    force_mode: ManagedLaunchForceMode | None,
) -> _ManagedForceTakeoverContext | None:
    """Resolve one predecessor takeover context or fail before build/start."""

    existing_record = resolve_live_agent_record_by_agent_id(managed_launch_identity.agent_id)
    if existing_record is None:
        return None
    if force_mode is None:
        raise RuntimeError(
            "Managed agent "
            f"`{managed_launch_identity.agent_name}` (agent_id `{managed_launch_identity.agent_id}`) "
            "already owns a live registry record. Rerun with `--force` to replace it."
        )
    if existing_record.identity.backend == "houmao_server_rest":
        raise RuntimeError(
            "Managed launch force takeover only supports locally owned agents. "
            f"Managed agent `{managed_launch_identity.agent_name}` is currently owned by "
            "`houmao-server`."
        )

    manifest_path = Path(existing_record.runtime.manifest_path).expanduser().resolve()
    handle = load_session_manifest(manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    session_root = runtime_owned_session_root_from_manifest_path(handle.path)
    resolved_mailbox = resolved_mailbox_config_from_payload(
        payload.launch_plan.mailbox,
        manifest_path=handle.path,
    )
    brain_manifest_path = Path(payload.brain_manifest_path).expanduser().resolve()
    predecessor_brain_manifest = load_brain_manifest(brain_manifest_path)
    predecessor_runtime_root, predecessor_home_id, predecessor_home_path = (
        _load_brain_home_identity_from_manifest(
            predecessor_brain_manifest,
            source=str(brain_manifest_path),
        )
    )
    if predecessor_runtime_root != resolved_runtime_root:
        raise RuntimeError(
            "Managed launch force takeover requires matching runtime roots. Existing owner "
            f"`{managed_launch_identity.agent_name}` uses runtime root "
            f"`{predecessor_runtime_root}`, but this launch resolved `{resolved_runtime_root}`."
        )

    target = resolve_managed_agent_target(
        agent_id=managed_launch_identity.agent_id,
        agent_name=None,
        port=None,
    )
    if target.mode != "local":
        raise RuntimeError(
            "Managed launch force takeover only supports locally owned agents. "
            f"Managed agent `{managed_launch_identity.agent_name}` resolved to `{target.mode}` "
            "control."
        )

    return _ManagedForceTakeoverContext(
        force_mode=force_mode,
        agent_name=managed_launch_identity.agent_name,
        agent_id=managed_launch_identity.agent_id,
        target=target,
        record=existing_record,
        home_id=predecessor_home_id,
        home_path=predecessor_home_path,
        runtime_root=predecessor_runtime_root,
        session_root=session_root,
        mailbox_cleanup_paths=replaceable_mailbox_cleanup_paths(resolved_mailbox),
    )


def _remove_force_takeover_path(path: Path) -> None:
    """Remove one predecessor-owned path during `--force clean` takeover."""

    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
        return
    shutil.rmtree(path)


def _dedupe_force_takeover_paths(paths: tuple[Path | None, ...]) -> tuple[Path, ...]:
    """Drop duplicates and descendant paths from one cleanup candidate list."""

    deduped: list[Path] = []
    for candidate in sorted(
        (item.resolve() for item in paths if item is not None),
        key=lambda item: (len(item.parts), str(item)),
    ):
        if any(candidate == existing or candidate.is_relative_to(existing) for existing in deduped):
            continue
        deduped.append(candidate)
    return tuple(deduped)


def _perform_managed_force_takeover(context: _ManagedForceTakeoverContext) -> None:
    """Stop the predecessor owner and optionally clean predecessor-owned artifacts."""

    stop_result = stop_managed_agent(context.target)
    if not stop_result.success:
        raise RuntimeError(
            "Failed to stop existing managed agent "
            f"`{context.agent_name}` before replacement: {stop_result.detail}"
        )
    if resolve_live_agent_record_by_agent_id(context.agent_id) is not None:
        raise RuntimeError(
            "Existing managed agent "
            f"`{context.agent_name}` still owns the shared registry after stop; aborting "
            "replacement launch."
        )
    if context.force_mode != "clean":
        return

    for cleanup_path in _dedupe_force_takeover_paths(
        (
            context.session_root,
            *context.mailbox_cleanup_paths,
        )
    ):
        _remove_force_takeover_path(cleanup_path)


def _format_launch_policy_resolution_error(
    *,
    runtime_backend: str,
    error: LaunchPolicyResolutionError,
) -> str:
    """Return one operator-facing launch-policy compatibility failure message."""

    return (
        "Managed agent launch selected runtime backend "
        f"`{runtime_backend}`, but provider startup did not begin because launch-policy "
        "compatibility blocked startup "
        f"(requested_operator_prompt_mode={error.requested_operator_prompt_mode!r}, "
        f"tool={error.tool!r}, policy_backend={error.policy_backend!r}, "
        f"detected_version={error.detected_version!r}). "
        f"Detail: {error.detail}"
    )


def _caller_has_interactive_terminal() -> bool:
    """Return whether the CLI currently owns a usable interactive terminal."""

    return all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr))


def _validate_provider(provider: str) -> None:
    """Validate one managed launch provider id."""

    if provider not in _PROVIDERS:
        raise click.ClickException(
            f"Invalid provider `{provider}`. Available providers: {', '.join(sorted(_PROVIDERS))}."
        )


def _is_path_like_launch_selector(selector: str) -> bool:
    """Return whether one launch selector should resolve as an explicit preset path."""

    return (
        "/" in selector
        or "\\" in selector
        or selector.startswith(".")
        or selector.startswith("~")
        or selector.endswith(_PRESET_FILE_SUFFIXES)
    )


def _pinned_launch_source_env() -> dict[str, str]:
    """Return one source-resolution env mapping that ignores invocation overrides."""

    env = dict(os.environ)
    env.pop(AGENT_DEF_DIR_ENV_VAR, None)
    env.pop(PROJECT_OVERLAY_DIR_ENV_VAR, None)
    return env


def _materialize_source_agent_def_dir(*, project_roots: ProjectAwareLocalRoots) -> Path:
    """Resolve the effective agent-definition tree for one source context."""

    if project_roots.project_overlay is not None:
        return materialize_project_agent_catalog_projection(project_roots.project_overlay)
    return project_roots.agent_def_dir.resolve()


def _parse_stored_launch_profile_mailbox_or_click(
    payload: dict[str, Any] | None,
    *,
    profile_name: str,
) -> MailboxDeclarativeConfig | None:
    """Parse one stored launch-profile mailbox payload or raise one CLI-facing error."""

    if payload is None:
        return None
    try:
        return parse_declarative_mailbox_config(
            payload,
            source=f"launch profile `{profile_name}`",
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _normalize_model_name_or_click(value: str | None) -> str | None:
    """Return one optional non-empty model name."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise click.ClickException("`--model` must not be empty.")
    return stripped


def _resolve_operator_prompt_mode_or_click(
    value: str | None,
    *,
    source: str,
) -> OperatorPromptMode | None:
    """Return one validated operator prompt mode from stored launch-profile state."""

    if value is None:
        return None
    if value not in {"as_is", "unattended"}:
        raise click.ClickException(
            f"{source} stores invalid launch.prompt_mode {value!r}; expected `as_is` or "
            "`unattended`."
        )
    return cast(OperatorPromptMode, value)


def _managed_header_section_overrides_from_options(
    values: tuple[str, ...],
) -> dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]:
    """Parse one-shot managed-header section overrides from CLI options."""

    try:
        return parse_managed_header_section_policy_assignments(
            values,
            source="`--managed-header-section`",
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def launch_managed_agent_locally(
    *,
    agents: str,
    agent_name: str | None,
    agent_id: str | None,
    auth: str | None,
    session_name: str | None,
    headless: bool,
    provider: str,
    working_directory: Path,
    source_working_directory: Path | None = None,
    source_agent_def_dir: Path | None = None,
    source_env: Mapping[str, str] | None = None,
    headless_display_style: HeadlessDisplayStyle,
    headless_display_detail: HeadlessDisplayDetail,
    launch_env_overrides: dict[str, str] | None = None,
    gateway_auto_attach: bool = False,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
    gateway_execution_mode: GatewayCurrentExecutionMode | None = None,
    gateway_tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None = None,
    mailbox_transport: str | None = None,
    mailbox_root: Path | None = None,
    mailbox_account_dir: Path | None = None,
    declared_mailbox: MailboxDeclarativeConfig | None = None,
    operator_prompt_mode: OperatorPromptMode | None = None,
    persistent_env_records: dict[str, str] | None = None,
    launch_profile_model_config: ModelConfig | None = None,
    direct_model_config: ModelConfig | None = None,
    prompt_overlay_mode: str | None = None,
    prompt_overlay_text: str | None = None,
    managed_header_override: bool | None = None,
    launch_profile_managed_header_policy: ManagedHeaderPolicy | None = None,
    managed_header_section_overrides: dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy]
    | None = None,
    launch_profile_managed_header_section_policy: dict[
        ManagedHeaderSectionName, ManagedHeaderSectionPolicy
    ]
    | None = None,
    launch_profile_provenance: dict[str, Any] | None = None,
    launch_profile_memo_seed: ResolvedLaunchProfileMemoSeed | None = None,
    force_mode: str | None = None,
) -> LocalManagedAgentLaunchResult:
    """Resolve, build, and start one managed agent locally."""

    _validate_provider(provider)
    normalized_force_mode = normalize_managed_launch_force_mode(
        force_mode,
        source="managed launch force mode",
    )

    resolved_working_directory = working_directory.resolve()
    resolved_source_working_directory = (
        source_working_directory.resolve()
        if source_working_directory is not None
        else resolved_working_directory
    )
    resolved_source_agent_def_dir = (
        source_agent_def_dir.resolve() if source_agent_def_dir is not None else None
    )
    effective_source_env = dict(source_env) if source_env is not None else None

    resolved_backend_name = "unknown"
    takeover_context: _ManagedForceTakeoverContext | None = None
    takeover_completed = False
    memo_seed_application: LaunchProfileMemoSeedApplication | None = None
    try:
        if resolved_source_agent_def_dir is None and _is_path_like_launch_selector(agents):
            invocation_agent_def_dir = resolve_effective_agent_def_dir(
                working_directory=resolved_source_working_directory
            )
            preset_path = resolve_explicit_or_named_preset_path(
                agent_def_dir=invocation_agent_def_dir,
                selector=agents,
            )
            resolved_source_agent_def_dir = resolve_preset_owner_agent_def_dir(
                preset_path=preset_path
            )
            resolved_source_working_directory = infer_launch_source_directory_from_agent_def_dir(
                agent_def_dir=resolved_source_agent_def_dir
            )
            effective_source_env = _pinned_launch_source_env()
        project_roots = ensure_project_aware_local_roots(
            cwd=resolved_source_working_directory,
            env=effective_source_env,
        )
        effective_agent_def_dir = (
            resolved_source_agent_def_dir
            if resolved_source_agent_def_dir is not None
            else _materialize_source_agent_def_dir(project_roots=project_roots)
        )

        resolved_runtime_root = project_roots.runtime_root
        resolved_mailbox_root = (
            mailbox_root.resolve() if mailbox_root is not None else project_roots.mailbox_root
        )
        target = resolve_native_launch_target(
            selector=agents,
            provider=provider,
            working_directory=resolved_working_directory,
            agent_def_dir=effective_agent_def_dir,
        )
        effective_persistent_env_records = dict(target.preset.launch_env_records or {})
        if persistent_env_records is not None:
            effective_persistent_env_records.update(dict(persistent_env_records))
        managed_header_decision = resolve_managed_prompt_header_decision(
            launch_override=managed_header_override,
            stored_policy=launch_profile_managed_header_policy,
        )
        managed_header_section_decisions = resolve_managed_prompt_header_section_decisions(
            launch_overrides=managed_header_section_overrides,
            stored_policy=launch_profile_managed_header_section_policy,
        )
        managed_launch_identity = resolve_managed_launch_identity(
            tool=target.preset.tool,
            role_name=target.role_name,
            requested_agent_name=agent_name,
            requested_agent_id=agent_id,
        )
        memory = resolve_agent_memory(
            overlay_root=project_roots.overlay_root,
            agent_id=managed_launch_identity.agent_id,
        )
        takeover_context = _prepare_managed_force_takeover_context(
            managed_launch_identity=managed_launch_identity,
            resolved_runtime_root=resolved_runtime_root,
            force_mode=normalized_force_mode,
        )
        if takeover_context is not None:
            _perform_managed_force_takeover(takeover_context)
            takeover_completed = True
        if launch_profile_memo_seed is not None:
            memo_seed_application = apply_launch_profile_memo_seed(
                paths=memory,
                memo_seed=launch_profile_memo_seed,
            )
        prompt_payload = compose_managed_launch_prompt_payload(
            base_prompt=target.role_prompt,
            overlay_mode=prompt_overlay_mode,
            overlay_text=prompt_overlay_text,
            managed_header_enabled=managed_header_decision.enabled,
            agent_name=managed_launch_identity.agent_name,
            agent_id=managed_launch_identity.agent_id,
            memo_file=str(memory.memo_file),
            managed_header_section_decisions=managed_header_section_decisions,
        )
        build_result = build_brain_home(
            BuildRequest(
                agent_def_dir=target.agent_def_dir,
                runtime_root=resolved_runtime_root,
                tool=target.preset.tool,
                skills=target.preset.skills,
                setup=target.preset.setup,
                auth=auth or target.preset.auth,
                preset_path=target.preset_path,
                preset_launch_overrides=target.preset.launch_overrides,
                preset_model_config=getattr(target.preset, "launch_model_config", None),
                launch_profile_model_config=launch_profile_model_config,
                direct_model_config=direct_model_config,
                operator_prompt_mode=operator_prompt_mode or target.preset.operator_prompt_mode,
                persistent_env_records=effective_persistent_env_records,
                mailbox=declared_mailbox or target.preset.mailbox,
                extra=target.preset.extra,
                agent_name=managed_launch_identity.agent_name,
                agent_id=managed_launch_identity.agent_id,
                home_id=takeover_context.home_id if takeover_context is not None else None,
                existing_home_mode=(
                    takeover_context.force_mode if takeover_context is not None else None
                ),
                role_prompt_override=prompt_payload.prompt,
                managed_prompt_header=managed_prompt_header_metadata(
                    decision=managed_header_decision,
                    identity=managed_launch_identity,
                    section_decisions=managed_header_section_decisions,
                ),
                houmao_system_prompt_layout=prompt_payload.layout,
                launch_profile_provenance=launch_profile_provenance,
            )
        )
        resolved_backend = backend_for_tool(
            target.tool,
            prefer_local_interactive=not headless,
        )
        resolved_backend_name = resolved_backend
        controller = start_runtime_session(
            agent_def_dir=target.agent_def_dir,
            brain_manifest_path=build_result.manifest_path.resolve(),
            role_name=target.role_name,
            runtime_root=resolved_runtime_root,
            memory_paths=memory,
            backend=resolved_backend,
            working_directory=resolved_working_directory,
            agent_name=agent_name,
            agent_id=agent_id,
            tmux_session_name=session_name,
            launch_env_overrides=launch_env_overrides,
            gateway_auto_attach=gateway_auto_attach,
            gateway_host=gateway_host,
            gateway_port=gateway_port,
            gateway_execution_mode_override=(
                gateway_execution_mode
                if gateway_execution_mode is not None
                else "tmux_auxiliary_window"
                if gateway_auto_attach
                else None
            ),
            gateway_tui_tracking_timing_overrides=gateway_tui_tracking_timing_overrides,
            mailbox_transport=mailbox_transport,
            mailbox_root=resolved_mailbox_root,
            mailbox_account_dir=mailbox_account_dir,
            headless_display_style=headless_display_style if headless else None,
            headless_display_detail=headless_display_detail if headless else None,
            managed_force_mode=takeover_context.force_mode
            if takeover_context is not None
            else None,
        )
    except LaunchPolicyResolutionError as exc:
        raise click.ClickException(
            _format_launch_policy_resolution_error(
                runtime_backend=resolved_backend_name,
                error=exc,
            )
        ) from exc
    except (
        FileNotFoundError,
        LaunchPlanError,
        RuntimeError,
        SessionManifestError,
        ValueError,
    ) as exc:
        detail = str(exc)
        if takeover_completed and takeover_context is not None:
            detail = (
                "Replacement launch failed after predecessor "
                f"`{takeover_context.agent_name}` stood down under "
                f"`--force {takeover_context.force_mode}`: {detail}"
            )
        raise click.ClickException(detail) from exc

    return LocalManagedAgentLaunchResult(
        controller=controller,
        memory=memory,
        runtime_root=resolved_runtime_root,
        mailbox_root=resolved_mailbox_root,
        runtime_root_detail=describe_runtime_root_selection(explicit_root=None),
        mailbox_root_detail=describe_mailbox_root_selection(explicit_root=mailbox_root),
        overlay_root=project_roots.overlay_root,
        overlay_root_detail=describe_overlay_root_selection_source(
            overlay_root_source=project_roots.overlay_root_source,
            overlay_discovery_mode=project_roots.overlay_discovery_mode,
        ),
        project_overlay_bootstrapped=project_roots.created_overlay,
        overlay_bootstrap_detail=describe_overlay_bootstrap(
            created_overlay=project_roots.created_overlay
        ),
        memo_seed_application=memo_seed_application,
    )


def emit_local_launch_completion(
    *,
    launch_result: LocalManagedAgentLaunchResult,
    agent_name: str | None,
    session_name: str | None,
    headless: bool,
) -> None:
    """Print one successful local launch result and hand off to tmux when appropriate."""

    controller = launch_result.controller
    memory = launch_result.memory
    payload = {
        "status": "Managed agent launch complete",
        "agent_name": controller.agent_identity or agent_name,
        "agent_id": controller.agent_id or "unknown",
        "tmux_session_name": controller.tmux_session_name or session_name or "unknown",
        "manifest_path": str(controller.manifest_path),
        "runtime_root": str(launch_result.runtime_root),
        "runtime_root_detail": launch_result.runtime_root_detail,
        "memory_root": str(memory.memory_root),
        "memo_file": str(memory.memo_file),
        "pages_dir": str(memory.pages_dir),
        "mailbox_root": str(launch_result.mailbox_root),
        "mailbox_root_detail": launch_result.mailbox_root_detail,
        "overlay_root": str(launch_result.overlay_root),
        "overlay_root_detail": launch_result.overlay_root_detail,
        "project_overlay_bootstrapped": launch_result.project_overlay_bootstrapped,
        "overlay_bootstrap_detail": launch_result.overlay_bootstrap_detail,
    }
    if launch_result.memo_seed_application is not None:
        payload["memo_seed"] = launch_result.memo_seed_application.to_payload()
    gateway_host = getattr(controller, "gateway_host", None)
    if gateway_host is not None:
        payload["gateway_host"] = gateway_host
    gateway_port = getattr(controller, "gateway_port", None)
    if gateway_port is not None:
        payload["gateway_port"] = gateway_port
    gateway_status = None
    gateway_status_loader = getattr(controller, "gateway_status", None)
    if gateway_host is not None and gateway_port is not None and callable(gateway_status_loader):
        try:
            gateway_status = gateway_status_loader()
        except (click.ClickException, RuntimeError, SessionManifestError):
            gateway_status = None
    if gateway_status is not None:
        payload["gateway_execution_mode"] = gateway_status.execution_mode
        if gateway_status.gateway_tmux_window_index is not None:
            payload["gateway_tmux_window_index"] = gateway_status.gateway_tmux_window_index
    gateway_auto_attach_error = getattr(controller, "gateway_auto_attach_error", None)
    if gateway_auto_attach_error is not None:
        payload["gateway_auto_attach_error"] = gateway_auto_attach_error

    emit(
        payload,
        plain_renderer=render_launch_completion_plain,
        fancy_renderer=render_launch_completion_fancy,
    )
    if not headless and controller.tmux_session_name is not None:
        if _caller_has_interactive_terminal():
            try:
                attach_tmux_session_shared(session_name=controller.tmux_session_name)
            except RuntimeError as exc:
                raise click.ClickException(
                    f"Managed agent launch succeeded, but tmux handoff failed: {exc}"
                ) from exc
        else:
            emit(
                {
                    "terminal_handoff": "skipped_non_interactive",
                    "attach_command": f"tmux attach-session -t {controller.tmux_session_name}",
                }
            )
    if gateway_auto_attach_error is not None:
        raise SystemExit(2)


@click.group(name="agents")
def agents_group() -> None:
    """Managed-agent operations across local runtime and `houmao-server` backends."""


@agents_group.command(name="launch")
@click.option(
    "--agents",
    default=None,
    help="Native launch selector to resolve the source recipe.",
)
@click.option(
    "--launch-profile",
    default=None,
    help="Explicit project launch-profile name to resolve before launch.",
)
@click.option("--agent-name", default=None, help="Optional friendly managed-agent name.")
@click.option("--agent-id", default=None, help="Optional authoritative managed-agent id.")
@click.option("--auth", default=None, help="Optional auth override for the resolved preset.")
@click.option("--model", default=None, help="Optional one-off launch-owned model override.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Optional one-off tool/model-specific reasoning preset index override (>=0).",
)
@click.option("--session-name", help="Optional tmux session name.")
@click.option("--headless", is_flag=True, help="Launch in detached mode.")
@click.option(
    "--managed-header/--no-managed-header",
    "managed_header",
    default=None,
    help="Force-enable or disable the Houmao-managed prompt header for this launch.",
)
@click.option(
    "--managed-header-section",
    "managed_header_section",
    multiple=True,
    metavar="SECTION=STATE",
    help="One-shot managed-header section override (`enabled` or `disabled`).",
)
@click.option(
    "--workdir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True, exists=True),
    default=None,
    help="Optional runtime working directory override; defaults to the invocation cwd.",
)
@click.option(
    "--headless-display-style",
    type=click.Choice(["plain", "json", "fancy"]),
    default="plain",
    show_default=True,
    help="Managed headless live output style.",
)
@click.option(
    "--headless-display-detail",
    type=click.Choice(["concise", "detail"]),
    default="concise",
    show_default=True,
    help="Managed headless live output detail level.",
)
@click.option(
    "--provider",
    default=None,
    help=(
        "Provider identifier to use for the launch. Defaults to the resolved launch-profile "
        "provider, or `claude_code` when launching directly from `--agents`."
    ),
)
@managed_launch_force_option
def launch_agents_command(
    agents: str | None,
    launch_profile: str | None,
    agent_name: str | None,
    agent_id: str | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    session_name: str | None,
    headless: bool,
    managed_header: bool | None,
    managed_header_section: tuple[str, ...],
    workdir: Path | None,
    headless_display_style: HeadlessDisplayStyle,
    headless_display_detail: HeadlessDisplayDetail,
    provider: str | None,
    force_mode: str | None,
) -> None:
    """Build and launch one managed agent locally without `houmao-server`."""

    source_working_directory = Path.cwd().resolve()
    if agents is not None and launch_profile is not None:
        raise click.ClickException("`--launch-profile` and `--agents` cannot be combined.")
    if agents is None and launch_profile is None:
        raise click.ClickException("Provide exactly one of `--agents` or `--launch-profile`.")

    resolved_agents = agents
    resolved_agent_name = agent_name
    resolved_agent_id = agent_id
    resolved_auth = auth
    resolved_provider = provider
    resolved_working_directory = (workdir or source_working_directory).resolve()
    resolved_source_working_directory = source_working_directory
    resolved_source_agent_def_dir: Path | None = None
    resolved_headless = headless
    declared_mailbox = None
    operator_prompt_mode: OperatorPromptMode | None = None
    persistent_env_records: dict[str, str] | None = None
    launch_profile_model_config: ModelConfig | None = None
    prompt_overlay_mode = None
    prompt_overlay_text = None
    launch_profile_managed_header_policy: ManagedHeaderPolicy | None = None
    launch_profile_managed_header_section_policy: (
        dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] | None
    ) = None
    launch_profile_provenance = None
    launch_profile_memo_seed = None
    gateway_auto_attach = False
    gateway_host = None
    gateway_port = None
    direct_model_config = normalize_model_config(
        name=_normalize_model_name_or_click(model),
        reasoning_level=reasoning_level,
    )
    managed_header_section_overrides = _managed_header_section_overrides_from_options(
        managed_header_section
    )

    if launch_profile is not None:
        try:
            project_roots = resolve_project_aware_local_roots(cwd=source_working_directory)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        overlay = project_roots.project_overlay
        if overlay is None:
            raise click.ClickException(
                "No project overlay is available for `agents launch --launch-profile`; "
                "select an existing project overlay first."
            )
        try:
            resolved_profile = resolve_launch_profile(
                overlay=overlay,
                name=launch_profile.strip(),
            )
        except (FileNotFoundError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
        if resolved_profile.entry.profile_lane != "launch_profile":
            raise click.ClickException(
                f"Launch profile `{resolved_profile.entry.name}` is not an explicit "
                "recipe-backed launch profile."
            )
        if (
            not resolved_profile.source_exists
            or resolved_profile.recipe_path is None
            or resolved_profile.provider is None
        ):
            raise click.ClickException(
                f"Launch profile `{resolved_profile.entry.name}` references unavailable recipe "
                f"`{resolved_profile.entry.source_name}`."
            )

        resolved_agents = str(resolved_profile.recipe_path)
        resolved_agent_name = resolved_agent_name or resolved_profile.entry.managed_agent_name
        resolved_agent_id = resolved_agent_id or resolved_profile.entry.managed_agent_id
        resolved_auth = resolved_auth or resolved_profile.entry.auth_name
        if workdir is None and resolved_profile.entry.workdir is not None:
            resolved_working_directory = Path(resolved_profile.entry.workdir).expanduser().resolve()
        operator_prompt_mode = _resolve_operator_prompt_mode_or_click(
            resolved_profile.entry.operator_prompt_mode,
            source=f"launch profile `{resolved_profile.entry.name}`",
        )
        persistent_env_records = dict(resolved_profile.entry.env_payload)
        launch_profile_model_config = normalize_model_config(
            name=resolved_profile.entry.model_name,
            reasoning_level=resolved_profile.entry.reasoning_level,
        )
        launch_profile_managed_header_policy = normalize_managed_header_policy(
            resolved_profile.entry.managed_header_policy,
            source=f"launch profile `{resolved_profile.entry.name}`",
        )
        launch_profile_managed_header_section_policy = dict(
            getattr(resolved_profile.entry, "managed_header_section_policy", {})
        )
        prompt_overlay_mode = resolved_profile.entry.prompt_overlay_mode
        prompt_overlay_text = resolved_profile.prompt_overlay_text
        launch_profile_provenance = {
            "name": resolved_profile.entry.name,
            "lane": resolved_profile.entry.profile_lane,
            "source_kind": resolved_profile.entry.source_kind,
            "source_name": resolved_profile.entry.source_name,
            "recipe_name": resolved_profile.recipe_name,
            "prompt_overlay": {
                "mode": resolved_profile.entry.prompt_overlay_mode,
                "present": resolved_profile.prompt_overlay_text is not None,
            },
            "memo_seed": (
                {
                    "present": True,
                    "source_kind": resolved_profile.memo_seed.source_kind,
                    "policy": resolved_profile.memo_seed.policy,
                    "content_ref": {
                        "content_kind": resolved_profile.memo_seed.content_ref.content_kind,
                        "storage_kind": resolved_profile.memo_seed.content_ref.storage_kind,
                        "relative_path": resolved_profile.memo_seed.content_ref.relative_path,
                    },
                }
                if resolved_profile.memo_seed is not None
                else {"present": False}
            ),
        }
        launch_profile_memo_seed = resolved_profile.memo_seed
        declared_mailbox = _parse_stored_launch_profile_mailbox_or_click(
            resolved_profile.entry.mailbox_payload,
            profile_name=resolved_profile.entry.name,
        )
        posture_payload = dict(resolved_profile.entry.posture_payload)
        resolved_headless = headless or bool(posture_payload.get("headless", False))
        if posture_payload.get("gateway_port") is not None:
            gateway_auto_attach = True
            gateway_host = str(posture_payload.get("gateway_host") or "127.0.0.1")
            gateway_port = int(posture_payload["gateway_port"])
        elif posture_payload.get("gateway_auto_attach") is False:
            gateway_auto_attach = False
            gateway_host = None
            gateway_port = None

        resolved_source_working_directory = overlay.project_root
        resolved_source_agent_def_dir = materialize_project_agent_catalog_projection(overlay)
        if resolved_provider is None:
            resolved_provider = resolved_profile.provider
        elif resolved_provider != resolved_profile.provider:
            raise click.ClickException(
                f"`--provider {resolved_provider}` conflicts with launch profile "
                f"`{resolved_profile.entry.name}`, which resolves provider "
                f"`{resolved_profile.provider}`."
            )
    else:
        assert resolved_agents is not None
        if resolved_provider is None:
            resolved_provider = _DEFAULT_PROVIDER

    assert resolved_agents is not None
    assert resolved_provider is not None
    launch_result = launch_managed_agent_locally(
        agents=resolved_agents,
        agent_name=resolved_agent_name,
        agent_id=resolved_agent_id,
        auth=resolved_auth,
        session_name=session_name,
        headless=resolved_headless,
        provider=resolved_provider,
        working_directory=resolved_working_directory,
        source_working_directory=resolved_source_working_directory,
        source_agent_def_dir=resolved_source_agent_def_dir,
        headless_display_style=headless_display_style,
        headless_display_detail=headless_display_detail,
        gateway_auto_attach=gateway_auto_attach,
        gateway_host=gateway_host,
        gateway_port=gateway_port,
        declared_mailbox=declared_mailbox,
        operator_prompt_mode=operator_prompt_mode,
        persistent_env_records=persistent_env_records,
        launch_profile_model_config=launch_profile_model_config,
        direct_model_config=direct_model_config,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        managed_header_override=managed_header,
        launch_profile_managed_header_policy=launch_profile_managed_header_policy,
        managed_header_section_overrides=managed_header_section_overrides,
        launch_profile_managed_header_section_policy=(launch_profile_managed_header_section_policy),
        launch_profile_provenance=launch_profile_provenance,
        launch_profile_memo_seed=launch_profile_memo_seed,
        force_mode=force_mode,
    )

    emit_local_launch_completion(
        launch_result=launch_result,
        agent_name=resolved_agent_name,
        session_name=session_name,
        headless=resolved_headless,
    )


@agents_group.command(name="join")
@click.option("--agent-name", required=True, help="Friendly managed-agent name.")
@click.option("--agent-id", default=None, help="Optional authoritative managed-agent id.")
@click.option("--headless", is_flag=True, help="Adopt a native headless logical session.")
@click.option(
    "--provider",
    default=None,
    help="Provider identifier to adopt (`claude_code`, `codex`, or `gemini_cli`).",
)
@click.option(
    "--launch-args",
    multiple=True,
    help="Repeatable provider launch argument for later relaunch/turn control.",
)
@click.option(
    "--launch-env",
    multiple=True,
    help="Repeatable Docker-style env spec (`NAME=value` or `NAME`).",
)
@click.option(
    "--workdir",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True, exists=True),
    default=None,
    help="Optional working directory override; defaults from tmux window `0`, pane `0`.",
)
@click.option(
    "--resume-id",
    default=None,
    help="Optional headless resume selector: omitted, `last`, or an exact provider session id.",
)
@click.option(
    "--no-install-houmao-skills",
    is_flag=True,
    help="Skip default Houmao-owned system-skill installation into the adopted tool home.",
)
def join_agents_command(
    agent_name: str,
    agent_id: str | None,
    headless: bool,
    provider: str | None,
    launch_args: tuple[str, ...],
    launch_env: tuple[str, ...],
    workdir: Path | None,
    resume_id: str | None,
    no_install_houmao_skills: bool,
) -> None:
    """Adopt an existing tmux-backed TUI or headless session into Houmao control."""

    launch_env_bindings = _parse_join_launch_env(launch_env)
    requested_provider = provider.strip() if provider is not None else None
    if requested_provider is not None and requested_provider not in _PROVIDERS:
        raise click.ClickException(
            f"Invalid provider `{requested_provider}`. Available providers: {', '.join(sorted(_PROVIDERS))}."
        )
    if headless and requested_provider is None:
        raise click.ClickException("Headless join requires `--provider`.")
    if headless and not launch_args:
        raise click.ClickException("Headless join requires at least one `--launch-args` value.")

    tmux_session_name = _require_current_tmux_session_name()
    pane = _require_join_primary_pane(tmux_session_name)
    pane_current_path = _resolve_join_pane_current_path(tmux_session_name, pane.pane_id)
    detected_provider = _detect_join_provider(pane.pane_pid)

    if headless:
        if detected_provider is not None:
            raise click.ClickException(
                "Headless join requires window `0`, pane `0` to be an idle logical console, "
                f"but detected a live `{detected_provider}` TUI there."
            )
        assert requested_provider is not None
        _validate_headless_launch_args(provider=requested_provider, launch_args=launch_args)
        resolved_resume_selection = _resolve_headless_resume_selection(resume_id)
        effective_provider = requested_provider
    else:
        effective_provider = _resolve_tui_join_provider(
            requested_provider=requested_provider,
            detected_provider=detected_provider,
        )
        resolved_resume_selection = None

    try:
        result = materialize_joined_launch(
            runtime_root=None,
            agent_name=agent_name,
            agent_id=agent_id,
            provider=effective_provider,
            headless=headless,
            tmux_session_name=tmux_session_name,
            tmux_window_name=pane.window_name,
            working_directory=(workdir or pane_current_path).resolve(),
            launch_args=launch_args,
            launch_env=launch_env_bindings,
            install_houmao_skills=not no_install_houmao_skills,
            resume_selection=resolved_resume_selection,
        )
    except (
        FileNotFoundError,
        LaunchPlanError,
        RuntimeError,
        SessionManifestError,
        TmuxCommandError,
        ValueError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc

    _emit_join_result(
        result=result,
        tmux_session_name=tmux_session_name,
        provider=effective_provider,
        headless=headless,
    )


@agents_group.command(name="list")
@pair_port_option()
def list_agents_command(port: int | None) -> None:
    """List managed agents from the shared registry, optionally enriched by the server."""

    emit(
        list_managed_agents(port=port),
        plain_renderer=render_agent_list_plain,
        fancy_renderer=render_agent_list_fancy,
    )


@agents_group.command(name="state")
@pair_port_option()
@managed_agent_selector_options
def state_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show the operational managed-agent summary view."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        managed_agent_state_payload(target),
        plain_renderer=render_agent_state_plain,
        fancy_renderer=render_agent_state_fancy,
    )


@agents_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@click.option(
    "--model",
    default=None,
    help="Request-scoped headless execution model override.",
)
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Request-scoped headless tool/model-specific reasoning preset index override (>=0).",
)
@pair_port_option(help_text="Houmao server port override; skips registry discovery when set.")
@managed_agent_selector_options
def prompt_agent_command(
    port: int | None,
    prompt: str | None,
    model: str | None,
    reasoning_level: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the default prompt path for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        prompt_managed_agent(
            target,
            prompt=resolve_prompt_text(prompt=prompt),
            model=model,
            reasoning_level=reasoning_level,
        )
    )


@agents_group.command(name="interrupt")
@pair_port_option()
@managed_agent_selector_options
def interrupt_agent_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Interrupt one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(interrupt_managed_agent(target))


@agents_group.command(name="stop")
@pair_port_option()
@managed_agent_selector_options
def stop_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Stop one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(stop_managed_agent(target))


@agents_group.command(name="relaunch")
@pair_port_option(help_text="Houmao server port override for explicit relaunch")
@managed_agent_selector_options
def relaunch_agent_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Relaunch one tmux-backed managed agent without rebuilding its home."""

    selected_agent_id, selected_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
        allow_missing=True,
    )
    if selected_agent_id is None and selected_agent_name is None:
        if port is not None:
            raise click.ClickException(
                "`--port` is only supported with an explicit `--agent-id` or `--agent-name` relaunch target."
            )
        session_name = _require_current_tmux_session_name()
        resolution = _resolve_current_session_manifest(session_name=session_name)
        agent_def_dir = _resolve_current_session_agent_def_dir(
            session_name=session_name,
            registry_record=resolution.registry_record,
        )
        controller = resume_runtime_session(
            agent_def_dir=agent_def_dir,
            session_manifest_path=resolution.manifest_path,
        )
        result = controller.relaunch()
        emit(
            {
                "success": result.status == "ok",
                "tracked_agent_id": (
                    controller.agent_id
                    or controller.agent_identity
                    or controller.manifest_path.parent.name
                ),
                "detail": result.detail,
            }
        )
        return

    target = resolve_managed_agent_target(
        agent_id=selected_agent_id,
        agent_name=selected_agent_name,
        port=port,
    )
    emit(relaunch_managed_agent(target))


agents_group.add_command(gateway_group)
agents_group.add_command(cleanup_group)
agents_group.add_command(mail_group)
agents_group.add_command(mailbox_group)
agents_group.add_command(turn_group)
agents_group.add_command(memory_group)


def _parse_join_launch_env(values: tuple[str, ...]) -> tuple[JoinedLaunchEnvBinding, ...]:
    bindings: list[JoinedLaunchEnvBinding] = []
    for raw_value in values:
        if "=" in raw_value:
            name, value = raw_value.split("=", 1)
            stripped_name = name.strip()
            if not stripped_name:
                raise click.ClickException(f"Invalid `--launch-env` literal `{raw_value}`.")
            bindings.append(JoinedLaunchEnvBinding(mode="literal", name=stripped_name, value=value))
            continue
        stripped_name = raw_value.strip()
        if not stripped_name:
            raise click.ClickException("`--launch-env` must not be blank.")
        bindings.append(JoinedLaunchEnvBinding(mode="inherit", name=stripped_name))
    return tuple(bindings)


def _require_join_primary_pane(session_name: str) -> TmuxPaneRecord:
    try:
        panes = list_tmux_panes(session_name=session_name)
    except TmuxCommandError as exc:
        raise click.ClickException(str(exc)) from exc
    pane = next(
        (
            candidate
            for candidate in panes
            if candidate.window_index == "0" and candidate.pane_index == "0"
        ),
        None,
    )
    if pane is None:
        raise click.ClickException(
            f"Join requires tmux window `0`, pane `0` in session `{session_name}`."
        )
    return pane


def _resolve_join_pane_current_path(session_name: str, pane_id: str) -> Path:
    try:
        result = subprocess.run(
            ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_current_path}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise click.ClickException(
            f"Failed to read pane current path from tmux session `{session_name}`."
        ) from exc
    value = result.stdout.strip()
    if not value:
        raise click.ClickException(
            f"Join requires a usable pane current path for `{session_name}:0.0`."
        )
    return Path(value).expanduser().resolve()


def _detect_join_provider(pane_pid: int | None) -> str | None:
    inspector = PaneProcessInspector(supported_processes=_JOIN_SUPPORTED_PROCESSES)
    matched_providers: list[str] = []
    for tool, provider in _PROVIDER_BY_TOOL.items():
        inspection = inspector.inspect(tool=tool, pane_pid=pane_pid)
        if inspection.process_state == "probe_error":
            raise click.ClickException(
                inspection.error_message or "Failed to inspect the primary pane process tree."
            )
        if inspection.process_state == "tui_up":
            matched_providers.append(provider)
    if len(matched_providers) > 1:
        raise click.ClickException(
            "Join could not auto-detect one provider because multiple supported processes were "
            f"found in window `0`, pane `0`: {', '.join(sorted(matched_providers))}."
        )
    return matched_providers[0] if matched_providers else None


def _resolve_tui_join_provider(
    *,
    requested_provider: str | None,
    detected_provider: str | None,
) -> str:
    if requested_provider is None:
        if detected_provider is None:
            raise click.ClickException(
                "Join could not auto-detect a supported TUI provider from window `0`, pane `0`; "
                "retry with `--provider`."
            )
        return detected_provider
    if detected_provider is None:
        raise click.ClickException(
            f"Requested provider `{requested_provider}` does not match any supported live TUI "
            "process in window `0`, pane `0`."
        )
    if requested_provider != detected_provider:
        raise click.ClickException(
            f"Requested provider `{requested_provider}` does not match detected provider "
            f"`{detected_provider}` in window `0`, pane `0`."
        )
    return requested_provider


def _resolve_headless_resume_selection(value: str | None) -> HeadlessResumeSelection | None:
    if value is None:
        return HeadlessResumeSelection(kind="none")
    stripped = value.strip()
    if not stripped:
        raise click.ClickException("`--resume-id` must not be blank.")
    if stripped == "last":
        return HeadlessResumeSelection(kind="last")
    return HeadlessResumeSelection(kind="exact", value=stripped)


def _validate_headless_launch_args(*, provider: str, launch_args: tuple[str, ...]) -> None:
    launch_arg_set = set(launch_args)
    if provider == "codex":
        if "exec" not in launch_arg_set:
            raise click.ClickException(
                "Codex headless join requires `--launch-args exec` in the recorded launch options."
            )
        if "--json" not in launch_arg_set:
            raise click.ClickException(
                "Codex headless join requires `--launch-args=--json` for machine-readable turns."
            )
        return
    if provider == "claude_code":
        if "-p" not in launch_arg_set and "--print" not in launch_arg_set:
            raise click.ClickException(
                "Claude headless join requires `--launch-args -p` or `--launch-args=--print`."
            )
        return
    if provider == "gemini_cli":
        if "-p" not in launch_arg_set and "--prompt" not in launch_arg_set:
            raise click.ClickException(
                "Gemini headless join requires `--launch-args -p` or `--launch-args=--prompt`."
            )
        return


def _emit_join_result(
    *,
    result: JoinedSessionArtifacts,
    tmux_session_name: str,
    provider: str,
    headless: bool,
) -> None:
    emit(
        {
            "status": "Managed agent join complete",
            "agent_name": result.agent_name,
            "agent_id": result.agent_id,
            "provider": provider,
            "backend": "headless" if headless else "local_interactive",
            "tmux_session_name": tmux_session_name,
            "manifest_path": str(result.manifest_path),
            "runtime_root": str(result.runtime_root),
            "runtime_root_detail": result.runtime_root_detail,
            "memory_root": str(result.memory_root),
            "memo_file": str(result.memo_file),
            "pages_dir": str(result.pages_dir),
            "overlay_root": str(result.overlay_root),
            "overlay_root_detail": result.overlay_root_detail,
            "project_overlay_bootstrapped": result.project_overlay_bootstrapped,
            "overlay_bootstrap_detail": result.overlay_bootstrap_detail,
        }
    )
