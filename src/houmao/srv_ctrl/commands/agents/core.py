"""Managed-agent commands for `houmao-mgr`."""

from __future__ import annotations

from houmao.agents.realm_controller.gateway_access_runtime import load_gateway_admin_seed
from houmao.gateway.access import GatewayLaunchSeed

from collections.abc import Mapping
from dataclasses import dataclass, replace
import os
import json
import math
from pathlib import Path
from shlex import join as shell_join
import shutil
import sys
from typing import Any, Literal, cast

from houmao.execution.tmux import TmuxServer, tmux_server_scope
from houmao.execution.tmux_selection import (
    ResolvedTmuxServer,
    TmuxServerSelector,
    resolve_tmux_server,
)

import click

from houmao.agents.definition_parser import resolve_explicit_or_named_preset_path
from houmao.agents.brain_builder import (
    BuildRequest,
    BuildResult,
    PrivateSkillProjection,
    build_brain_home,
    validate_brain_inputs,
)
from houmao.agents.hermes_installation import load_prepared_hermes_installation
from houmao.agents.hermes_profile import (
    HermesProfileBinding,
    require_hermes_installation_context,
    require_hermes_profile_home,
)
from houmao.agents.hermes_profile_cleanup import (
    preview_hermes_profile_cleanup,
    preview_hermes_project_link,
    settle_hermes_profile_cleanup,
    unlink_hermes_project_home,
    verify_hermes_profile_cleanup_owner,
)
from houmao.agents.tool_params import parse_tool_params_cli_input
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
from houmao.agents.mailbox_runtime_models import MailboxesDeclarativeConfig
from houmao.agents.mailbox_runtime_support import (
    parse_declarative_mailboxes_config,
    replaceable_mailbox_cleanup_paths,
    resolved_mailbox_config_from_payload,
)
from houmao.agents.launch_profile_memo_seeds import (
    LaunchProfileMemoSeedApplication,
    apply_launch_profile_memo_seed,
)
from houmao.agents.agent_workspace import AgentMemoryPaths, resolve_agent_memory
from houmao.agents.instance_state import (
    InstancePreparationResult,
    InstanceStateStore,
    prepare_instance_state,
    render_instance_snapshot,
)
from houmao.agents.private_workspace import (
    PreparedPrivateWorkspace,
    PrivateWorkspace,
    prepare_private_workspace,
)
from houmao.agents.model_selection import ModelConfig, normalize_model_config
from houmao.agents.native_launch_resolver import (
    infer_launch_source_directory_from_agent_def_dir,
    resolve_effective_agent_def_dir,
    resolve_native_launch_target,
    resolve_preset_owner_agent_def_dir,
)
from houmao.agents.system_skills import (
    PROFILE_SYSTEM_SKILL_POLICY_MODES,
    SystemSkillError,
    SystemSkillSelectionPolicy,
    parse_system_skill_selection_policy,
)
from houmao.agents.realm_controller.agent_identity import AGENT_DEF_DIR_ENV_VAR, AgentIdMode
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.gateway_models import (
    GatewayCurrentExecutionMode,
    GatewayTuiTrackingTimingOverridesV1,
)
from houmao.agents.realm_controller.native_refresh_models import (
    CommonPluginObservationV1,
    NativeRefreshResultV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    write_gateway_mail_notifier_record,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    attach_tmux_session as attach_tmux_session_shared,
)
from houmao.agents.realm_controller.backends.headless_output import (
    HeadlessDisplayDetail,
    HeadlessDisplayStyle,
)
from houmao.agents.realm_controller.launch_plan import (
    launch_surface_for_backend,
    resolve_codex_service_executable,
    validate_dsh_launch_version,
    validate_kimi_service_launch_version,
    validate_kimi_web_launch_version,
)
from houmao.agents.realm_controller.native_surface import (
    TerminalNativeSurfaceV1,
    WebNativeSurfaceV1,
)
from houmao.agents.realm_controller.run_modes import (
    RUN_MODES,
    RunMode,
    gateway_backend_capabilities,
    resolve_run_mode,
)
from houmao.agents.realm_controller.loaders import load_brain_manifest
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.agents.realm_controller.runtime import start_runtime_session
from houmao.agents.realm_controller.boundary_models import SessionManifestTmuxSectionV1
from houmao.agents.realm_controller.errors import (
    LaunchPlanError,
    LaunchPolicyResolutionError,
    RuntimeStartupRollbackError,
    SessionManifestError,
)
from houmao.agents.realm_controller.models import (
    RelaunchChatSessionSelection,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import (
    resolve_live_agent_record_by_agent_id,
    resolve_relaunchable_managed_agent_record_by_agent_id,
)
from houmao.agents.realm_controller.self_manifest import resolve_self_manifest
from houmao.execution.context import current_execution_binding, observed_local_binding
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    resolve_mailbox_root,
    resolve_registry_root,
    resolve_runtime_root,
)
from houmao.project.overlay import (
    PROJECT_OVERLAY_DIR_ENV_VAR,
    ProjectAwareLocalRoots,
    ensure_project_aware_local_roots,
    materialize_project_agent_catalog_projection,
    resolve_project_aware_local_roots,
)
from houmao.project.agent_definitions import load_instance_contract
from houmao.project.launch_profiles import (
    ResolvedLaunchProfileMemoSeed,
    launch_profile_relaunch_payload,
    profile_run_mode,
    resolve_launch_profile,
)

from .access import self_access_group, single_access_group
from .files import self_files_group, single_files_group
from .cleanup import cleanup_group
from .external import external_group
from .gateway import (
    gateway_group,
    web_entry_gateway_command,
)
from .mail import mail_group
from .mailbox import mailbox_group
from .request import work_request_command
from .scopes import clone_scoped_command_tree
from .self_identity import identity_from_manifest
from .turn import turn_group
from .workspace import memory_group
from .instance_state import admin_instance_state_group, self_instance_state_group
from ..common import (
    ManagedAgentScopeContext,
    get_managed_agent_scope_context,
    managed_agent_selector_options,
    managed_launch_force_option,
    pair_port_option,
    resolve_prompt_text,
    resolve_managed_agent_selector,
    set_managed_agent_scope_context,
)
from ..output import emit
from ..renderers.receipts import emit_receipt
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
    _require_live_local_controller,
    interrupt_managed_agent,
    list_managed_agents,
    managed_agent_state_payload,
    managed_agent_state_policy_summary,
    managed_agent_native_home,
    managed_agent_common_plugin_state,
    open_managed_agent_browser,
    prompt_managed_agent,
    refresh_managed_agent,
    relaunch_managed_agent,
    resolve_current_session_managed_agent_target,
    resolve_relaunch_managed_agent_target,
    resolve_managed_agent_target,
    stop_managed_agent,
)

_DEFAULT_PROVIDER = "claude_code"
_PROVIDERS = frozenset(
    {
        "claude_code",
        "codex",
        "kimi",
        "dsh",
        "hermes",
    }
)
_JOIN_SUPPORTED_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "kimi": ("kimi-code", "kimi"),
}
_RELAUNCH_CHAT_SESSION_MODES: tuple[str, ...] = ("new", "tool_last_or_new", "exact")


def _resolve_relaunch_chat_session_selection_or_click(
    *,
    mode: str | None,
    session_id: str | None,
) -> RelaunchChatSessionSelection | None:
    """Resolve optional relaunch chat-session CLI flags."""

    normalized_mode = mode.strip() if mode is not None else None
    normalized_session_id = session_id.strip() if session_id is not None else None
    if normalized_session_id == "":
        normalized_session_id = None
    if normalized_mode is None:
        if normalized_session_id is not None:
            raise click.ClickException("`--chat-session-id` requires `--chat-session-mode exact`.")
        return None
    if normalized_mode != "exact" and normalized_session_id is not None:
        raise click.ClickException(
            "`--chat-session-id` is only supported with `--chat-session-mode exact`."
        )
    if normalized_mode == "exact" and normalized_session_id is None:
        raise click.ClickException("`--chat-session-mode exact` requires `--chat-session-id`.")
    try:
        return RelaunchChatSessionSelection(
            mode=cast(Any, normalized_mode),
            session_id=normalized_session_id,
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


_PROVIDER_BY_TOOL: dict[str, str] = {
    "claude": "claude_code",
    "codex": "codex",
    "kimi": "kimi",
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
class LocalManagedAgentLaunchCompletion:
    """Verified launch facts shared by the CLI and owner protocol adapters."""

    manifest: SessionManifestPayloadV4
    payload: dict[str, Any]
    gateway_auto_attach_error: str | None


@dataclass(frozen=True)
class _ManagedPredecessorHomeContext:
    """Resolved predecessor home state for one managed-agent launch."""

    agent_name: str
    agent_id: str
    record: ManagedAgentRegistryRecordV3
    home_id: str
    home_path: Path
    runtime_root: Path
    last_tmux_session_name: str | None
    force_mode: ManagedLaunchForceMode | None
    target: ManagedAgentTarget | None
    session_root: Path | None
    mailbox_cleanup_paths: tuple[Path, ...]
    tmux_binding: SessionManifestTmuxSectionV1 | None = None
    brain_manifest_path: Path | None = None
    hermes_profile: HermesProfileBinding | None = None


class ManagedTmuxPreflightError(click.ClickException):
    """Report a rejected tmux selection before any agent mutation."""


def _last_tmux_session_name_from_record(record: ManagedAgentRegistryRecordV3) -> str | None:
    """Return the normalized last tmux session name from one registry record."""

    terminal = getattr(record, "terminal", None)
    last_session_name = getattr(terminal, "last_session_name", None)
    if not isinstance(last_session_name, str) or not last_session_name.strip():
        return None
    return last_session_name.strip()


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


def _load_managed_predecessor_home_context(
    *,
    managed_launch_identity: Any,
    record: ManagedAgentRegistryRecordV3,
    resolved_runtime_root: Path,
    requested_tool: str,
    force_mode: ManagedLaunchForceMode | None,
    require_same_tool: bool,
    require_preserved_home_path: bool,
) -> _ManagedPredecessorHomeContext:
    """Load one predecessor home context from a local registry record."""

    if record.identity.backend == "houmao_server_rest":
        raise RuntimeError(
            "Managed preserved-home launch only supports locally owned agents. "
            f"Managed agent `{managed_launch_identity.agent_name}` is currently owned by "
            "retired backend `houmao_server_rest`."
        )
    if require_same_tool and record.identity.tool != requested_tool:
        raise RuntimeError(
            "Managed preserved-home launch requires the same CLI tool type. Existing managed "
            f"agent `{managed_launch_identity.agent_name}` uses tool `{record.identity.tool}`, "
            f"but this launch resolved `{requested_tool}`."
        )

    manifest_path = Path(record.runtime.manifest_path).expanduser().resolve()
    handle = load_session_manifest(manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
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
            "Managed preserved-home launch requires matching runtime roots. Existing owner "
            f"`{managed_launch_identity.agent_name}` uses runtime root "
            f"`{predecessor_runtime_root}`, but this launch resolved `{resolved_runtime_root}`."
        )
    if require_preserved_home_path and not predecessor_home_path.exists():
        raise RuntimeError(
            "Managed preserved-home launch requires an existing preserved home path, but "
            f"`{predecessor_home_path}` is missing."
        )
    profile = payload.launch_plan.hermes_profile if record.identity.tool == "hermes" else None
    if (
        requested_tool == record.identity.tool == "hermes"
        and require_preserved_home_path
        and profile is None
    ):
        raise RuntimeError(
            "The saved Hermes home uses standalone ownership. Create a fresh project launch for a named profile."
        )
    if profile is not None and require_preserved_home_path:
        saved_profile = predecessor_brain_manifest["runtime"].get("hermes_profile")
        if (
            HermesProfileBinding.model_validate(saved_profile) != profile
            or predecessor_home_path != profile.profile_home
            or brain_manifest_path
            != predecessor_runtime_root / "manifests" / f"{predecessor_home_id}.yaml"
        ):
            raise RuntimeError(
                "The preserved Hermes build differs from its recorded runtime owner."
            )

    target: ManagedAgentTarget | None = None
    session_root: Path | None = None
    mailbox_cleanup_paths: tuple[Path, ...] = ()
    if force_mode is not None:
        target = resolve_managed_agent_target(
            agent_id=managed_launch_identity.agent_id,
            agent_name=None,
            port=None,
            include_inactive=(
                record.identity.tool == "hermes" and record.lifecycle.state == "stopped"
            ),
        )
        if target.mode != "local" and not (
            target.mode == "local_stopped"
            and record.identity.tool == "hermes"
            and force_mode == "clean"
        ):
            raise RuntimeError(
                "Managed launch force takeover only supports locally owned agents. "
                f"Managed agent `{managed_launch_identity.agent_name}` resolved to `{target.mode}` "
                "control."
            )
        session_root = runtime_owned_session_root_from_manifest_path(handle.path)
        if force_mode == "clean":
            if profile is not None:
                if record.lifecycle.state == "stopped":
                    preview_hermes_profile_cleanup(profile)
                    preview_hermes_project_link(profile)
                else:
                    verify_hermes_profile_cleanup_owner(profile)
                _require_unshared_hermes_takeover_home(
                    profile, brain_manifest_path, predecessor_runtime_root, session_root
                )
            resolved_mailbox = resolved_mailbox_config_from_payload(
                payload.launch_plan.mailboxes.offline.binding,
                manifest_path=handle.path,
            )
            mailbox_cleanup_paths = replaceable_mailbox_cleanup_paths(resolved_mailbox)

    return _ManagedPredecessorHomeContext(
        agent_name=managed_launch_identity.agent_name,
        agent_id=managed_launch_identity.agent_id,
        record=record,
        home_id=predecessor_home_id,
        home_path=predecessor_home_path,
        runtime_root=predecessor_runtime_root,
        last_tmux_session_name=_last_tmux_session_name_from_record(record),
        force_mode=force_mode,
        target=target,
        session_root=session_root,
        mailbox_cleanup_paths=mailbox_cleanup_paths,
        tmux_binding=payload.tmux,
        brain_manifest_path=brain_manifest_path,
        hermes_profile=profile,
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


def _resolve_managed_predecessor_home_context(
    *,
    managed_launch_identity: Any,
    resolved_runtime_root: Path,
    requested_tool: str,
    force_mode: ManagedLaunchForceMode | None,
    reuse_home: bool,
) -> _ManagedPredecessorHomeContext | None:
    """Resolve one predecessor context for forced takeover or preserved-home reuse."""

    if reuse_home and force_mode == "clean":
        raise RuntimeError(
            "`--reuse-home` is incompatible with `--force clean` because `clean` would destroy "
            "the preserved home."
        )

    existing_record = resolve_live_agent_record_by_agent_id(managed_launch_identity.agent_id)
    if existing_record is not None:
        if reuse_home:
            raise RuntimeError(
                "Managed agent "
                f"`{managed_launch_identity.agent_name}` (agent_id "
                f"`{managed_launch_identity.agent_id}`) already owns a live registry record. "
                "Stop the live owner before attempting `--reuse-home` restart."
            )
        if force_mode is None:
            detail = (
                "Managed agent "
                f"`{managed_launch_identity.agent_name}` (agent_id "
                f"`{managed_launch_identity.agent_id}`) already owns a live registry record. "
                "Rerun with `--force` to replace it."
            )
            raise RuntimeError(detail)
        return _load_managed_predecessor_home_context(
            managed_launch_identity=managed_launch_identity,
            record=existing_record,
            resolved_runtime_root=resolved_runtime_root,
            requested_tool=requested_tool,
            force_mode=force_mode,
            require_same_tool=(reuse_home or force_mode == "keep-stale"),
            require_preserved_home_path=(reuse_home or force_mode == "keep-stale"),
        )

    if not reuse_home and force_mode != "clean":
        return None

    relaunchable_record = resolve_relaunchable_managed_agent_record_by_agent_id(
        managed_launch_identity.agent_id
    )
    if not reuse_home:
        if relaunchable_record is None or relaunchable_record.identity.tool != "hermes":
            return None
        return _load_managed_predecessor_home_context(
            managed_launch_identity=managed_launch_identity,
            record=relaunchable_record,
            resolved_runtime_root=resolved_runtime_root,
            requested_tool=requested_tool,
            force_mode=force_mode,
            require_same_tool=False,
            require_preserved_home_path=False,
        )
    if relaunchable_record is None:
        raise RuntimeError(
            "Managed launch `--reuse-home` requires one compatible stopped preserved home for "
            f"agent `{managed_launch_identity.agent_name}` (agent_id "
            f"`{managed_launch_identity.agent_id}`), but none was found."
        )
    return _load_managed_predecessor_home_context(
        managed_launch_identity=managed_launch_identity,
        record=relaunchable_record,
        resolved_runtime_root=resolved_runtime_root,
        requested_tool=requested_tool,
        force_mode=None,
        require_same_tool=True,
        require_preserved_home_path=True,
    )


def _validate_tmux_force_takeover(
    selected: ResolvedTmuxServer, predecessor: _ManagedPredecessorHomeContext | None
) -> None:
    """Keep an existing-only server alive through an approved predecessor stop."""

    if (
        selected.allow_start
        or predecessor is None
        or predecessor.target is None
        or (
            predecessor.record.identity.tool == "hermes"
            and predecessor.record.lifecycle.state == "stopped"
        )
    ):
        return
    binding = predecessor.tmux_binding
    if binding is None or binding.socket_path is None:
        return
    if binding.socket_path != selected.socket_path:
        try:
            if not Path(binding.socket_path).samefile(selected.socket_path):
                return
        except FileNotFoundError:
            return
    server = TmuxServer(selected.socket_path, allow_start=False)
    if server.list_sessions() != {binding.session_name}:
        return
    exit_empty = server.checked_command(["show-options", "-s", "-v", "exit-empty"])
    if exit_empty.stdout.strip() != "off":
        raise ManagedTmuxPreflightError(
            f"Replacing this agent would stop the existing-only tmux server at "
            f"{selected.socket_path}. Keep another session open or select a different server."
        )


def _perform_managed_force_takeover(context: _ManagedPredecessorHomeContext) -> None:
    """Stop the predecessor owner and optionally clean predecessor-owned artifacts."""

    if context.target is None:
        raise RuntimeError("Managed force takeover requires one live predecessor target.")
    if context.record.identity.tool != "hermes" or context.record.lifecycle.state != "stopped":
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

    if context.hermes_profile is not None:
        from houmao.agents.realm_controller.backends.hermes_native import (
            hermes_profile_lifecycle_lock,
        )

        profile = context.hermes_profile
        assert context.brain_manifest_path is not None
        try:
            with hermes_profile_lifecycle_lock(profile.prepared_root):
                _require_unshared_hermes_takeover_home(
                    profile, context.brain_manifest_path, context.runtime_root, context.session_root
                )
                settle_hermes_profile_cleanup(profile)
                unlink_hermes_project_home(profile)
                context.brain_manifest_path.unlink(missing_ok=True)
        except (OSError, ValueError, RuntimeError) as exc:
            raise RuntimeError(
                f"The predecessor stopped, but its Hermes home cleanup is incomplete: {exc}"
            ) from exc
    elif context.record.identity.tool == "hermes":
        if context.home_path != context.runtime_root / "homes" / context.home_id:
            raise RuntimeError(
                "The stopped standalone Hermes home is outside the managed build root."
            )
        _remove_force_takeover_path(context.home_path)

    for cleanup_path in _dedupe_force_takeover_paths(
        (
            context.session_root,
            *context.mailbox_cleanup_paths,
        )
    ):
        _remove_force_takeover_path(cleanup_path)


def _require_unshared_hermes_takeover_home(
    profile: HermesProfileBinding,
    brain_manifest_path: Path,
    runtime_root: Path,
    session_root: Path | None,
) -> None:
    """Keep any other saved runtime's profile and project link through takeover."""

    from houmao.srv_ctrl.commands.runtime_cleanup import (
        discover_runtime_session_envelopes,
        hermes_profile_has_runtime_reference,
    )

    if brain_manifest_path != runtime_root / "manifests" / f"{profile.project_home_link.name}.yaml":
        raise RuntimeError("The predecessor Hermes build is outside the saved managed build root.")
    saved = load_brain_manifest(brain_manifest_path)
    runtime = saved.get("runtime", {})
    if HermesProfileBinding.model_validate(runtime.get("hermes_profile")) != profile:
        raise RuntimeError("The predecessor Hermes build differs from its recorded runtime owner.")
    if hermes_profile_has_runtime_reference(
        profile,
        brain_manifest_path,
        discover_runtime_session_envelopes(runtime_root),
        ignoring_session=session_root,
    ):
        raise RuntimeError(
            "Another retained runtime still references the predecessor Hermes profile."
        )


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
) -> MailboxesDeclarativeConfig | None:
    """Parse one stored launch-profile mailbox payload or raise one CLI-facing error."""

    if payload is None:
        return None
    try:
        return parse_declarative_mailboxes_config(
            payload,
            source=f"launch dossier `{profile_name}`",
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


def _resolve_launch_profile_system_skill_policy_or_click(
    payload: object,
    *,
    source: str,
) -> SystemSkillSelectionPolicy | None:
    """Return one stored launch-profile system-skill policy or fail as Click error."""

    try:
        return parse_system_skill_selection_policy(
            payload,
            allowed_modes=PROFILE_SYSTEM_SKILL_POLICY_MODES,
            default_mode="inherit",
            source=source,
        )
    except SystemSkillError as exc:
        raise click.ClickException(str(exc)) from exc


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


def _seed_launch_profile_mail_notifier_appendix(
    *,
    controller: Any,
    appendix_text: str,
) -> None:
    """Persist a launch-profile mail-notifier appendix default into runtime gateway state."""

    paths = gateway_paths_from_manifest_path(Path(controller.manifest_path))
    if paths is None:
        raise SessionManifestError(
            "Launch-profile mail-notifier appendix defaults require runtime-owned gateway state."
        )
    paths.gateway_root.mkdir(parents=True, exist_ok=True)
    for channel in ("offline", "online"):
        binding = controller.launch_plan.mailboxes.binding_for(channel)
        if binding is not None:
            scope_key = json.dumps(
                [binding.agent_id, channel, binding.binding_id], separators=(",", ":")
            )
            write_gateway_mail_notifier_record(
                paths.queue_path, scope_key=scope_key, appendix_text=appendix_text
            )


def _merge_launch_skill_names(
    source_skill_names: list[str] | tuple[str, ...],
    registered_skill_names: tuple[str, ...],
) -> list[str]:
    """Return source skills plus launch-profile registered skills without duplicates."""

    if not registered_skill_names:
        return cast(list[str], source_skill_names)
    merged: list[str] = []
    seen: set[str] = set()
    for skill_name in (*source_skill_names, *registered_skill_names):
        if skill_name in seen:
            continue
        merged.append(skill_name)
        seen.add(skill_name)
    return merged


def _coerce_private_skill_projections(
    private_skills: tuple[Any, ...],
) -> tuple[PrivateSkillProjection, ...]:
    """Convert resolved launch-profile private skill records into build projections."""

    projections: list[PrivateSkillProjection] = []
    for private_skill in private_skills:
        mode = str(getattr(private_skill, "mode"))
        if mode not in {"copy", "symlink"}:
            raise ValueError(f"Unsupported launch-profile private skill mode: {mode}")
        projections.append(
            PrivateSkillProjection(
                name=str(getattr(private_skill, "name")),
                source_path=Path(getattr(private_skill, "source_path")).resolve(),
                mode=cast(Literal["copy", "symlink"], mode),
            )
        )
    return tuple(projections)


def _with_launch_profile_skill_provenance(
    *,
    launch_profile_provenance: dict[str, Any] | None,
    registered_skill_names: tuple[str, ...],
    private_skill_projections: tuple[PrivateSkillProjection, ...],
    effective_skill_names: list[str],
) -> dict[str, Any] | None:
    """Add launch-profile skill overlay provenance to a provenance payload."""

    if launch_profile_provenance is None:
        return None
    payload = dict(launch_profile_provenance)
    if not registered_skill_names and not private_skill_projections:
        return payload
    private_payloads = [
        {
            "name": private_skill.name,
            "resolved_path": str(private_skill.source_path),
            "mode": private_skill.mode,
        }
        for private_skill in private_skill_projections
    ]
    private_names = {private_skill.name for private_skill in private_skill_projections}
    payload["skills"] = {
        "registered": list(registered_skill_names),
        "private": private_payloads,
        "private_shadowed_names": sorted(private_names.intersection(effective_skill_names)),
    }
    return payload


def _settle_failed_hermes_build(result: BuildResult | None, failure: BaseException) -> str:
    """Release a failed launch's fresh build or report its retained ownership evidence."""

    if result is None or result.acquired_hermes_profile is None:
        return ""
    incomplete_runtime_cleanup = any(
        note.startswith("Incomplete launch cleanup:") for note in getattr(failure, "__notes__", ())
    )
    if isinstance(failure, RuntimeStartupRollbackError) or incomplete_runtime_cleanup:
        return f" Hermes build rollback remains pending. Evidence is at {result.manifest_path}."
    from houmao.srv_ctrl.commands.runtime_cleanup import rollback_acquired_hermes_build

    try:
        rollback_acquired_hermes_build(
            profile=result.acquired_hermes_profile,
            manifest_path=result.manifest_path,
            runtime_root=result.manifest_path.parent.parent,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return f" Hermes build rollback is incomplete. Evidence is at {result.manifest_path}. {exc}"
    return ""


def launch_managed_agent_locally(
    *,
    agents: str,
    agent_name: str | None,
    agent_id: str | None,
    auth: str | None,
    session_name: str | None,
    mode: RunMode | None,
    provider: str,
    working_directory: Path,
    tmux_selector: TmuxServerSelector | None = None,
    source_working_directory: Path | None = None,
    source_agent_def_dir: Path | None = None,
    source_project_dir: Path | None = None,
    source_env: Mapping[str, str] | None = None,
    headless_display_style: HeadlessDisplayStyle,
    headless_display_detail: HeadlessDisplayDetail,
    launch_env_overrides: dict[str, str] | None = None,
    gateway_auto_attach: bool = False,
    gateway_admin_seed: GatewayLaunchSeed | None = None,
    gateway_host: str | None = None,
    gateway_port: int | None = None,
    gateway_execution_mode: GatewayCurrentExecutionMode | None = None,
    gateway_tui_tracking_timing_overrides: GatewayTuiTrackingTimingOverridesV1 | None = None,
    mailbox_transport: str | None = None,
    mailbox_root: Path | None = None,
    mailbox_account_dir: Path | None = None,
    declared_mailboxes: MailboxesDeclarativeConfig | None = None,
    operator_prompt_mode: OperatorPromptMode | None = None,
    persistent_env_records: dict[str, str] | None = None,
    launch_profile_model_config: ModelConfig | None = None,
    direct_model_config: ModelConfig | None = None,
    launch_profile_tool_params: Mapping[str, Any] | None = None,
    direct_tool_params: Mapping[str, Any] | None = None,
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
    launch_profile_mail_notifier_appendix_text: str | None = None,
    launch_profile_registered_skill_names: tuple[str, ...] = (),
    launch_profile_private_skills: tuple[Any, ...] = (),
    launch_profile_system_skill_policy: SystemSkillSelectionPolicy | None = None,
    agent_definition_deployment: dict[str, Any] | None = None,
    instance_runtime_values: Mapping[str, Any] | None = None,
    force_mode: str | None = None,
    reuse_home: bool = False,
    agent_id_mode: AgentIdMode | None = None,
) -> LocalManagedAgentLaunchResult:
    """Resolve, build, and start one managed agent locally."""

    _validate_provider(provider)
    if (reuse_home or force_mode is not None) and agent_id is None and agent_id_mode != "name-hash":
        raise click.ClickException(
            "Existing-agent reuse/force requires --agent-id or explicit --agent-id-mode name-hash. "
            "A friendly name does not select an agent identity."
        )
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
    predecessor_context: _ManagedPredecessorHomeContext | None = None
    takeover_completed = False
    acquired_hermes_build: BuildResult | None = None
    memo_seed_application: LaunchProfileMemoSeedApplication | None = None
    instance_preparation: InstancePreparationResult | None = None
    private_workspace: PreparedPrivateWorkspace | None = None
    effective_launch_env_overrides = dict(launch_env_overrides or {})
    try:
        if resolved_source_agent_def_dir is None and _is_path_like_launch_selector(agents):
            selector_path = Path(agents).expanduser()
            invocation_agent_def_dir = (
                resolved_source_working_directory
                if selector_path.is_absolute()
                else resolve_effective_agent_def_dir(
                    working_directory=resolved_source_working_directory
                )
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
            project_dir=source_project_dir,
            env=effective_source_env,
        )
        effective_agent_def_dir = (
            resolved_source_agent_def_dir
            if resolved_source_agent_def_dir is not None
            else _materialize_source_agent_def_dir(project_roots=project_roots)
        )

        owner_env = os.environ if effective_source_env is None else effective_source_env
        owner_binding = current_execution_binding()
        resolved_runtime_root = resolve_runtime_root(
            explicit_root=owner_binding.runtime_root if owner_binding is not None else None,
            env=owner_env,
            default_root=project_roots.runtime_root,
        )
        shared_runtime_root = (
            resolved_runtime_root
            if owner_binding is not None
            or owner_env.get(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, "").strip()
            else None
        )
        target = resolve_native_launch_target(
            selector=agents,
            provider=provider,
            working_directory=resolved_working_directory,
            agent_def_dir=effective_agent_def_dir,
        )
        effective_mailboxes = declared_mailboxes or target.preset.mailboxes
        explicit_mailbox_root = mailbox_root
        if explicit_mailbox_root is None and effective_mailboxes is not None:
            offline = effective_mailboxes.offline
            if offline is not None and offline.filesystem_root is not None:
                explicit_mailbox_root = resolved_runtime_root / offline.filesystem_root
        resolved_mailbox_root = resolve_mailbox_root(
            explicit_root=explicit_mailbox_root,
            env=owner_env,
            default_root=project_roots.mailbox_root,
        )
        shared_mailbox_root = (
            resolved_mailbox_root
            if explicit_mailbox_root is not None
            or owner_env.get(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR, "").strip()
            else None
        )
        selection = resolve_run_mode(target.tool, mode=mode, entrypoint="project")
        prepared_hermes = None
        if selection.tool == "hermes":
            try:
                prepared_hermes = load_prepared_hermes_installation(owner=owner_binding)
            except (OSError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
        resolved_backend = selection.backend
        resolved_backend_name = resolved_backend
        effective_skill_names = _merge_launch_skill_names(
            target.preset.skills,
            launch_profile_registered_skill_names,
        )
        private_skill_projections = _coerce_private_skill_projections(launch_profile_private_skills)
        effective_launch_profile_provenance = _with_launch_profile_skill_provenance(
            launch_profile_provenance=launch_profile_provenance,
            registered_skill_names=launch_profile_registered_skill_names,
            private_skill_projections=private_skill_projections,
            effective_skill_names=effective_skill_names,
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
            requested_agent_id_mode=agent_id_mode,
        )
        memory = resolve_agent_memory(
            overlay_root=project_roots.overlay_root,
            agent_id=managed_launch_identity.agent_id,
        )
        predecessor_context = _resolve_managed_predecessor_home_context(
            managed_launch_identity=managed_launch_identity,
            resolved_runtime_root=resolved_runtime_root,
            requested_tool=target.preset.tool,
            force_mode=normalized_force_mode,
            reuse_home=reuse_home,
        )
        if prepared_hermes is not None:
            profile_owner = owner_binding or observed_local_binding(
                working_directory=resolved_working_directory,
                runtime_root=resolved_runtime_root,
                registry_root=resolve_registry_root(),
                tmux_socket=None,
            )
            require_hermes_installation_context(prepared_hermes.root, profile_owner.context_id)
            if predecessor_context is not None and (
                reuse_home or predecessor_context.force_mode == "keep-stale"
            ):
                profile = predecessor_context.hermes_profile
                expected_link = project_roots.runtime_root / "homes" / predecessor_context.home_id
                if (
                    profile is None
                    or profile.prepared_root != prepared_hermes.root
                    or profile.installation_build != prepared_hermes.evidence.build
                    or profile.executable != Path(prepared_hermes.executable)
                    or profile.context_id != profile_owner.context_id
                    or profile.project_home_link != expected_link
                ):
                    raise RuntimeError(
                        "The retained Hermes profile differs from the selected owner."
                    )
                require_hermes_profile_home(profile, allow_missing_link=True)
        gateway_capabilities = gateway_backend_capabilities(resolved_backend)
        if (
            not gateway_capabilities.manager_launch_timings
            and gateway_tui_tracking_timing_overrides is not None
            and gateway_tui_tracking_timing_overrides.has_values()
        ):
            raise click.ClickException(
                "Hermes TUI uses native readiness and does not support parser timing overrides."
                if gateway_capabilities.structured_tui
                else "Gateway TUI timing overrides require a terminal native surface."
            )
        build_request = BuildRequest(
            agent_def_dir=target.agent_def_dir,
            runtime_root=resolved_runtime_root,
            hermes_project_homes_dir=project_roots.runtime_root / "homes",
            tool=target.preset.tool,
            skills=effective_skill_names,
            private_skills=private_skill_projections,
            setup=target.preset.setup,
            auth=auth or target.preset.auth,
            preset_path=target.preset_path,
            preset_launch_overrides=target.preset.launch_overrides,
            preset_tool_params=target.preset.tool_params,
            launch_profile_tool_params=launch_profile_tool_params,
            direct_tool_params=direct_tool_params,
            preset_model_config=getattr(target.preset, "launch_model_config", None),
            launch_profile_model_config=launch_profile_model_config,
            direct_model_config=direct_model_config,
            source_system_skill_policy=getattr(
                target.preset,
                "launch_system_skill_policy",
                None,
            ),
            launch_profile_system_skill_policy=launch_profile_system_skill_policy,
            operator_prompt_mode=operator_prompt_mode or target.preset.operator_prompt_mode,
            persistent_env_records=effective_persistent_env_records,
            mailboxes=effective_mailboxes,
            extra=target.preset.extra,
            agent_name=managed_launch_identity.agent_name,
            agent_id=managed_launch_identity.agent_id,
            home_id=predecessor_context.home_id if predecessor_context is not None else None,
            existing_home_mode=(
                predecessor_context.force_mode if predecessor_context is not None else None
            ),
            reuse_home=reuse_home,
        )
        validated_inputs = validate_brain_inputs(
            build_request,
            backend=launch_surface_for_backend(resolved_backend),
            launch_env_overrides=effective_launch_env_overrides,
            check_policy_version=predecessor_context is not None
            and predecessor_context.target is not None,
        )
        if selection.tool == "dsh":
            validate_dsh_launch_version(
                executable=validated_inputs.adapter.launch_executable, backend=resolved_backend
            )
        elif resolved_backend == "kimi_web":
            validate_kimi_web_launch_version(executable=validated_inputs.adapter.launch_executable)
        try:
            resolved_tmux_server = resolve_tmux_server(
                tmux_selector, execution_binding=owner_binding, environment=owner_env
            )
            _validate_tmux_force_takeover(resolved_tmux_server, predecessor_context)
        except (OSError, TmuxCommandError, ValueError) as exc:
            raise ManagedTmuxPreflightError(str(exc)) from None
        if predecessor_context is not None and predecessor_context.target is not None:
            if resolved_backend == "codex_app_server":
                resolve_codex_service_executable(validated_inputs.adapter.launch_executable)
            elif resolved_backend == "kimi_acp":
                validate_kimi_service_launch_version(
                    executable=validated_inputs.adapter.launch_executable
                )
            _perform_managed_force_takeover(predecessor_context)
            takeover_completed = True
        if launch_profile_memo_seed is not None:
            memo_seed_application = apply_launch_profile_memo_seed(
                paths=memory,
                memo_seed=launch_profile_memo_seed,
            )
        effective_role_prompt = target.role_prompt
        if agent_definition_deployment is not None:
            contract_path = Path(
                str(agent_definition_deployment["instance_contract_path"])
            ).resolve()
            instance_contract_digest = str(agent_definition_deployment["instance_contract_digest"])
            instance_contract = load_instance_contract(
                contract_path,
                expected_digest=instance_contract_digest,
            )
            instance_preparation = prepare_instance_state(
                state_db=memory.state_db,
                agent_id=managed_launch_identity.agent_id,
                deployment_id=str(agent_definition_deployment["deployment_id"]),
                instance_contract_digest=instance_contract_digest,
                contract=instance_contract,
                launch_values=instance_runtime_values or {},
            )
            if bool(agent_definition_deployment.get("private_workspace_enabled", False)):
                private_workspace = prepare_private_workspace(
                    project_root=project_roots.overlay_root.parent,
                    agent_id=managed_launch_identity.agent_id,
                    deployment_id=str(agent_definition_deployment["deployment_id"]),
                    definition_id=str(agent_definition_deployment["definition_id"]),
                    contract=instance_contract.private_workspace,
                    enabled=True,
                    workdir_mode=cast(
                        Literal["project-root", "private-root"],
                        str(
                            agent_definition_deployment.get(
                                "workspace_workdir_mode", "project-root"
                            )
                        ),
                    ),
                    state_store=InstanceStateStore(instance_preparation.state_db),
                )
                assert private_workspace is not None
                resolved_working_directory = private_workspace.execution_workdir
            effective_role_prompt = render_instance_snapshot(
                effective_role_prompt,
                instance_preparation.variable_snapshot,
            )
            if memory.memo_file.is_file():
                memo_text = memory.memo_file.read_text(encoding="utf-8")
                if "{{houmao.instance." in memo_text:
                    memory.memo_file.write_text(
                        render_instance_snapshot(
                            memo_text,
                            instance_preparation.variable_snapshot,
                        ),
                        encoding="utf-8",
                    )
        prompt_payload = compose_managed_launch_prompt_payload(
            base_prompt=effective_role_prompt,
            overlay_mode=prompt_overlay_mode,
            overlay_text=prompt_overlay_text,
            managed_header_enabled=managed_header_decision.enabled,
            agent_name=managed_launch_identity.agent_name,
            agent_id=managed_launch_identity.agent_id,
            memo_file=str(memory.memo_file),
            managed_header_section_decisions=managed_header_section_decisions,
        )
        build_result = build_brain_home(
            replace(
                build_request,
                validated_inputs=validated_inputs,
                role_prompt_override=prompt_payload.prompt,
                managed_prompt_header=managed_prompt_header_metadata(
                    decision=managed_header_decision,
                    identity=managed_launch_identity,
                    section_decisions=managed_header_section_decisions,
                ),
                houmao_system_prompt_layout=prompt_payload.layout,
                launch_profile_provenance=effective_launch_profile_provenance,
            )
        )
        if selection.tool == "hermes" and build_result.acquired_hermes_profile is not None:
            acquired_hermes_build = build_result
        default_tmux_session_name = (
            predecessor_context.last_tmux_session_name
            if reuse_home and session_name is None and predecessor_context is not None
            else None
        )
        if instance_preparation is not None:
            InstanceStateStore(instance_preparation.state_db).set_launch_state(
                instance_preparation.attempt_id, "starting"
            )
        controller = start_runtime_session(
            agent_def_dir=target.agent_def_dir,
            brain_manifest_path=build_result.manifest_path.resolve(),
            role_name=target.role_name,
            runtime_root=resolved_runtime_root,
            project_overlay_dir=project_roots.overlay_root,
            shared_runtime_root=shared_runtime_root,
            shared_mailbox_root=shared_mailbox_root,
            private_workspace_root=private_workspace.root
            if private_workspace is not None
            else None,
            memory_paths=memory,
            backend=resolved_backend,
            mode=selection.mode,
            working_directory=resolved_working_directory,
            agent_name=agent_name,
            agent_id=managed_launch_identity.agent_id,
            tmux_session_name=session_name,
            resolved_tmux_server=resolved_tmux_server,
            default_tmux_session_name=default_tmux_session_name,
            launch_env_overrides=effective_launch_env_overrides,
            gateway_auto_attach=gateway_auto_attach,
            gateway_admin_seed=gateway_admin_seed,
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
            headless_display_style=headless_display_style if selection.mode == "headless" else None,
            headless_display_detail=headless_display_detail
            if selection.mode == "headless"
            else None,
            managed_force_mode=predecessor_context.force_mode
            if predecessor_context is not None and predecessor_context.target is not None
            else None,
        )
        acquired_hermes_build = None
        if launch_profile_mail_notifier_appendix_text is not None:
            _seed_launch_profile_mail_notifier_appendix(
                controller=controller,
                appendix_text=launch_profile_mail_notifier_appendix_text,
            )
        if instance_preparation is not None:
            InstanceStateStore(instance_preparation.state_db).set_launch_state(
                instance_preparation.attempt_id, "active"
            )
    except LaunchPolicyResolutionError as exc:
        raise click.ClickException(
            _format_launch_policy_resolution_error(
                runtime_backend=resolved_backend_name,
                error=exc,
            )
            + _settle_failed_hermes_build(acquired_hermes_build, exc)
        ) from exc
    except (
        OSError,
        LaunchPlanError,
        RuntimeError,
        SessionManifestError,
        ValueError,
    ) as exc:
        if instance_preparation is not None:
            try:
                state_store = InstanceStateStore(instance_preparation.state_db)
                state_store.set_launch_state(
                    instance_preparation.attempt_id,
                    "failed",
                    error=str(exc),
                )
                if private_workspace is not None and not private_workspace.reused:
                    try:
                        workspace_id = private_workspace.manifest.workspace_id
                        PrivateWorkspace(private_workspace.root).cleanup(confirmed=True)
                        state_store.clear_private_workspace_association(
                            expected_workspace_id=workspace_id
                        )
                    except (OSError, ValueError):
                        pass
            except (OSError, ValueError):
                pass
        detail = str(exc) + _settle_failed_hermes_build(acquired_hermes_build, exc)
        if takeover_completed and predecessor_context is not None:
            detail = (
                "Replacement launch failed after predecessor "
                f"`{predecessor_context.agent_name}` stood down under "
                f"`--force {predecessor_context.force_mode}`: {detail}"
            )
        raise click.ClickException(detail) from exc
    except BaseException as exc:
        if incomplete := _settle_failed_hermes_build(acquired_hermes_build, exc):
            exc.add_note(incomplete.strip())
        raise

    return LocalManagedAgentLaunchResult(
        controller=controller,
        memory=memory,
        runtime_root=resolved_runtime_root,
        mailbox_root=resolved_mailbox_root,
        runtime_root_detail=(
            "Selected shared runtime root from the admitted execution binding."
            if owner_binding is not None
            else describe_runtime_root_selection(explicit_root=None, env=owner_env)
        ),
        mailbox_root_detail=(
            "Selected shared mailbox root from the explicit `--mail-root` override."
            if mailbox_root is not None
            else "Selected shared mailbox root from the launch configuration."
            if explicit_mailbox_root is not None
            else describe_mailbox_root_selection(explicit_root=None, env=owner_env)
        ),
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


def build_local_launch_completion(
    *,
    launch_result: LocalManagedAgentLaunchResult,
    agent_name: str | None,
    session_name: str | None,
) -> LocalManagedAgentLaunchCompletion:
    """Read the saved runtime and describe its verified native interface."""

    controller = launch_result.controller
    handle = load_session_manifest(controller.manifest_path)
    manifest = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    surface = manifest.native_surface
    memory = launch_result.memory
    payload = {
        "status": "Managed agent launch complete",
        "agent_name": controller.agent_identity or agent_name,
        "agent_id": controller.agent_id or "unknown",
        "tool": manifest.tool,
        "mode": manifest.mode,
        "backend": manifest.backend,
        "native_surface": surface.model_dump(mode="json") if surface is not None else None,
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

    socket_path = manifest.tmux.socket_path if manifest.tmux is not None else None
    allow_start = manifest.tmux is None or manifest.tmux.server_allow_start is not False
    if isinstance(surface, TerminalNativeSurfaceV1):
        payload["terminal_handoff"] = "skipped_non_interactive"
        command = ["tmux", "-S", socket_path] if socket_path else ["tmux"]
        if not allow_start:
            command.append("-N")
        payload["attach_command"] = shell_join(
            [*command, "attach-session", "-t", surface.tmux_session_name]
        )
    elif isinstance(surface, WebNativeSurfaceV1):
        payload["browser_origin"] = surface.origin
        payload["native_session_id"] = surface.native_session_id
    else:
        payload["control_command"] = f"houmao-mgr agents single --agent-id {manifest.agent_id}"

    return LocalManagedAgentLaunchCompletion(
        manifest=manifest, payload=payload, gateway_auto_attach_error=gateway_auto_attach_error
    )


def render_local_launch_completion(*, completion: LocalManagedAgentLaunchCompletion) -> None:
    """Print a launch result and hand off to the verified terminal when interactive."""

    manifest = completion.manifest
    payload = dict(completion.payload)
    surface = manifest.native_surface
    terminal_handoff = (
        isinstance(surface, TerminalNativeSurfaceV1) and _caller_has_interactive_terminal()
    )
    if terminal_handoff:
        payload["terminal_handoff"] = "attach"
    emit(
        payload,
        plain_renderer=render_launch_completion_plain,
        fancy_renderer=render_launch_completion_fancy,
    )
    if terminal_handoff and isinstance(surface, TerminalNativeSurfaceV1):
        socket_path = manifest.tmux.socket_path if manifest.tmux is not None else None
        allow_start = manifest.tmux is None or manifest.tmux.server_allow_start is not False
        try:
            with tmux_server_scope(socket_path, allow_start=allow_start):
                attach_tmux_session_shared(session_name=surface.tmux_session_name)
        except RuntimeError as exc:
            raise click.ClickException(
                f"Managed agent launch succeeded, but tmux handoff failed: {exc}"
            ) from exc
    if completion.gateway_auto_attach_error is not None:
        raise SystemExit(2)


def emit_local_launch_completion(
    *,
    launch_result: LocalManagedAgentLaunchResult,
    agent_name: str | None,
    session_name: str | None,
) -> None:
    """Render completion of a local native launch."""

    render_local_launch_completion(
        completion=build_local_launch_completion(
            launch_result=launch_result, agent_name=agent_name, session_name=session_name
        )
    )


@click.group(name="agents")
def agents_group() -> None:
    """Managed-agent operations split by global, single, self, and external scope."""


@click.group(name="global")
def agents_global_group() -> None:
    """Zero-or-many local managed-agent registry and fleet operations."""


@click.group(name="single")
@click.option("--agent-id", default=None, help="Authoritative managed-agent id.")
@click.option(
    "--agent-name",
    default=None,
    help="Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix.",
)
@click.option(
    "--target-tmux-session",
    default=None,
    help="Exact registry tmux alias for a local gateway command.",
)
@click.pass_context
def agents_single_group(
    ctx: click.Context,
    agent_id: str | None,
    agent_name: str | None,
    target_tmux_session: str | None,
) -> None:
    """Operations for exactly one explicitly selected local managed agent."""

    if target_tmux_session is not None:
        if ctx.invoked_subcommand != "gateway":
            raise click.UsageError("`--target-tmux-session` requires a gateway command.")
        if agent_id is not None or agent_name is not None:
            raise click.UsageError(
                "Use exactly one of `--agent-id`, `--agent-name`, or `--target-tmux-session`."
            )
    selected_agent_id, selected_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
        allow_missing=target_tmux_session is not None,
    )
    set_managed_agent_scope_context(
        ctx=ctx,
        scope_context=ManagedAgentScopeContext(
            scope="single",
            agent_id=selected_agent_id,
            agent_name=selected_agent_name,
            target_tmux_session=target_tmux_session,
        ),
    )


@click.group(name="self")
@click.pass_context
def agents_self_group(ctx: click.Context) -> None:
    """Operations for the caller's verified managed runtime."""

    set_managed_agent_scope_context(
        ctx=ctx,
        scope_context=ManagedAgentScopeContext(scope="self"),
    )


@agents_self_group.command(name="identity")
def self_identity_agent_command() -> None:
    """Show the current managed agent's verified manifest identity."""

    try:
        manifest = resolve_self_manifest()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    emit(identity_from_manifest(manifest.path, manifest.payload))


@agents_self_group.command(name="state")
def self_state_agent_command() -> None:
    """Show the operational summary for the current managed tmux session."""

    target = resolve_current_session_managed_agent_target()
    emit(
        managed_agent_state_payload(target),
        plain_renderer=render_agent_state_plain,
        fancy_renderer=render_agent_state_fancy,
    )


@agents_self_group.command(name="prompt")
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
def self_prompt_agent_command(
    prompt: str | None,
    model: str | None,
    reasoning_level: int | None,
) -> None:
    """Submit the default prompt path to the current managed tmux session."""

    target = resolve_current_session_managed_agent_target()
    emit(
        prompt_managed_agent(
            target,
            prompt=resolve_prompt_text(prompt=prompt),
            model=model,
            reasoning_level=reasoning_level,
        )
    )


@agents_self_group.command(name="interrupt")
def self_interrupt_agent_command() -> None:
    """Interrupt the current managed tmux session."""

    target = resolve_current_session_managed_agent_target()
    emit(interrupt_managed_agent(target))


@agents_self_group.command(name="relaunch")
@click.option(
    "--chat-session-mode",
    type=click.Choice(_RELAUNCH_CHAT_SESSION_MODES),
    default=None,
    help=(
        "Provider chat-session policy for this relaunch: new, tool_last_or_new, or exact. "
        "Omitting the flag uses the launch-profile relaunch policy when present, otherwise new."
    ),
)
@click.option(
    "--chat-session-id",
    default=None,
    help="Provider chat-session id to resume when --chat-session-mode exact is selected.",
)
def self_relaunch_agent_command(
    chat_session_mode: str | None,
    chat_session_id: str | None,
) -> None:
    """Refresh the active tmux-backed surface for the current managed session."""

    relaunch_chat_session = _resolve_relaunch_chat_session_selection_or_click(
        mode=chat_session_mode,
        session_id=chat_session_id,
    )
    _emit_current_session_relaunch(relaunch_chat_session)


def _emit_current_session_relaunch(selection: RelaunchChatSessionSelection | None) -> None:
    """Relaunch the verified current session using saved launch authority."""

    target = resolve_current_session_managed_agent_target()
    controller = _require_live_local_controller(target, operation="relaunch the current agent")
    result = (
        controller.relaunch(chat_session=selection)
        if selection is not None
        else controller.relaunch()
    )
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
@click.option(
    "--agent-id-mode",
    type=click.Choice(["uuid", "name-hash"]),
    default=None,
    help="ID generation mode (default: uuid); cannot be combined with --agent-id.",
)
@click.option("--auth", default=None, help="Optional auth override for the resolved preset.")
@click.option("--model", default=None, help="Optional one-off launch-owned model override.")
@click.option("--tool-params", help="One-shot tool parameters as JSON or @path.")
@click.option(
    "--reasoning-level",
    type=click.IntRange(min=0),
    default=None,
    help="Optional one-off tool/model-specific reasoning preset index override (>=0).",
)
@click.option("--session-name", help="Optional tmux session name.")
@click.option("--mode", type=click.Choice(RUN_MODES), help="Select the native run mode.")
@click.option(
    "--gateway-admin-seed",
    "gateway_admin_seed_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Private owner-side JSON file with initial gateway admin public keys.",
)
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
@click.option(
    "--reuse-home",
    is_flag=True,
    help="Restart on one compatible stopped preserved home for the resolved managed identity.",
)
@managed_launch_force_option
def launch_agents_command(
    agents: str | None,
    launch_profile: str | None,
    agent_name: str | None,
    agent_id: str | None,
    agent_id_mode: AgentIdMode | None,
    auth: str | None,
    model: str | None,
    reasoning_level: int | None,
    session_name: str | None,
    mode: RunMode | None,
    managed_header: bool | None,
    managed_header_section: tuple[str, ...],
    workdir: Path | None,
    headless_display_style: HeadlessDisplayStyle,
    headless_display_detail: HeadlessDisplayDetail,
    provider: str | None,
    reuse_home: bool,
    force_mode: str | None,
    gateway_admin_seed_path: Path | None = None,
    tool_params: str | None = None,
) -> None:
    """Build and launch one managed agent locally without `houmao-server`."""

    source_working_directory = Path.cwd().resolve()
    gateway_admin_seed = None
    if gateway_admin_seed_path is not None:
        try:
            gateway_admin_seed = load_gateway_admin_seed(
                source_working_directory / gateway_admin_seed_path
            )
        except SessionManifestError as exc:
            raise click.ClickException(str(exc)) from None
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
    resolved_mode = mode
    declared_mailboxes = None
    operator_prompt_mode: OperatorPromptMode | None = None
    persistent_env_records: dict[str, str] | None = None
    launch_profile_model_config: ModelConfig | None = None
    launch_profile_tool_params: dict[str, Any] | None = None
    tmux_selector: TmuxServerSelector | None = None
    try:
        direct_tool_params = (
            parse_tool_params_cli_input(tool_params) if tool_params is not None else None
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from None
    prompt_overlay_mode = None
    prompt_overlay_text = None
    launch_profile_managed_header_policy: ManagedHeaderPolicy | None = None
    launch_profile_managed_header_section_policy: (
        dict[ManagedHeaderSectionName, ManagedHeaderSectionPolicy] | None
    ) = None
    launch_profile_provenance = None
    launch_profile_memo_seed = None
    launch_profile_mail_notifier_appendix_text: str | None = None
    launch_profile_registered_skill_names: tuple[str, ...] = ()
    launch_profile_private_skills: tuple[Any, ...] = ()
    launch_profile_system_skill_policy: SystemSkillSelectionPolicy | None = None
    gateway_auto_attach = False
    gateway_host = None
    gateway_port = None
    direct_model_config = normalize_model_config(
        name=_normalize_model_name_or_click(model),
        reasoning_level=reasoning_level,
    )
    if reuse_home and force_mode == "clean":
        raise click.ClickException(
            "`--reuse-home` is incompatible with `--force clean` because `clean` would destroy "
            "the preserved home."
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
                "No project overlay is available for `project agents launch --profile`; "
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
                f"Selected profile `{resolved_profile.entry.name}` is not a native "
                "recipe-backed launch dossier."
            )
        if (
            not resolved_profile.source_exists
            or resolved_profile.recipe_path is None
            or resolved_profile.provider is None
        ):
            raise click.ClickException(
                f"Native launch dossier `{resolved_profile.entry.name}` references unavailable recipe "
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
            source=f"launch dossier `{resolved_profile.entry.name}`",
        )
        persistent_env_records = dict(resolved_profile.entry.env_payload)
        launch_profile_tool_params = resolved_profile.entry.tool_params
        launch_profile_model_config = normalize_model_config(
            name=resolved_profile.entry.model_name,
            reasoning_level=resolved_profile.entry.reasoning_level,
        )
        launch_profile_managed_header_policy = normalize_managed_header_policy(
            resolved_profile.entry.managed_header_policy,
            source=f"launch dossier `{resolved_profile.entry.name}`",
        )
        launch_profile_managed_header_section_policy = dict(
            getattr(resolved_profile.entry, "managed_header_section_policy", {})
        )
        prompt_overlay_mode = resolved_profile.entry.prompt_overlay_mode
        prompt_overlay_text = resolved_profile.prompt_overlay_text
        launch_profile_registered_skill_names = tuple(
            getattr(resolved_profile.entry, "registered_skill_names", ())
        )
        launch_profile_private_skills = tuple(getattr(resolved_profile, "private_skills", ()))
        launch_profile_system_skill_policy = _resolve_launch_profile_system_skill_policy_or_click(
            getattr(resolved_profile.entry, "system_skills_payload", {}),
            source=f"launch dossier `{resolved_profile.entry.name}` system_skills",
        )
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
            "gateway_mail_notifier_appendix": {
                "present": resolved_profile.gateway_mail_notifier_appendix_text is not None,
            },
            "memo_seed": (
                {
                    "present": True,
                    "source_kind": resolved_profile.memo_seed.source_kind,
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
        system_skills_payload = getattr(resolved_profile.entry, "system_skills_payload", {})
        if system_skills_payload:
            launch_profile_provenance["system_skills"] = dict(system_skills_payload)
        relaunch_payload = launch_profile_relaunch_payload(resolved_profile)
        if relaunch_payload:
            launch_profile_provenance["relaunch"] = relaunch_payload
        launch_profile_memo_seed = resolved_profile.memo_seed
        launch_profile_mail_notifier_appendix_text = (
            resolved_profile.gateway_mail_notifier_appendix_text
        )
        declared_mailboxes = _parse_stored_launch_profile_mailbox_or_click(
            resolved_profile.entry.mailbox_payload,
            profile_name=resolved_profile.entry.name,
        )
        posture_payload = dict(resolved_profile.entry.posture_payload)
        tmux_selector = resolved_profile.entry.tmux_server_selector
        try:
            stored_mode = profile_run_mode(
                posture_payload,
                tool=resolved_profile.provider,
                source=f"launch profile `{resolved_profile.entry.name}`",
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from None
        resolved_mode = mode if mode is not None else stored_mode
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
                f"`--provider {resolved_provider}` conflicts with native launch dossier "
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
        agent_id_mode=agent_id_mode,
        auth=resolved_auth,
        session_name=session_name,
        tmux_selector=tmux_selector,
        mode=resolved_mode,
        provider=resolved_provider,
        working_directory=resolved_working_directory,
        source_working_directory=resolved_source_working_directory,
        source_agent_def_dir=resolved_source_agent_def_dir,
        headless_display_style=headless_display_style,
        headless_display_detail=headless_display_detail,
        gateway_auto_attach=gateway_auto_attach,
        gateway_admin_seed=gateway_admin_seed,
        gateway_host=gateway_host,
        gateway_port=gateway_port,
        declared_mailboxes=declared_mailboxes,
        operator_prompt_mode=operator_prompt_mode,
        persistent_env_records=persistent_env_records,
        launch_profile_model_config=launch_profile_model_config,
        direct_model_config=direct_model_config,
        launch_profile_tool_params=launch_profile_tool_params,
        direct_tool_params=direct_tool_params,
        prompt_overlay_mode=prompt_overlay_mode,
        prompt_overlay_text=prompt_overlay_text,
        managed_header_override=managed_header,
        launch_profile_managed_header_policy=launch_profile_managed_header_policy,
        managed_header_section_overrides=managed_header_section_overrides,
        launch_profile_managed_header_section_policy=(launch_profile_managed_header_section_policy),
        launch_profile_provenance=launch_profile_provenance,
        launch_profile_memo_seed=launch_profile_memo_seed,
        launch_profile_mail_notifier_appendix_text=launch_profile_mail_notifier_appendix_text,
        launch_profile_registered_skill_names=launch_profile_registered_skill_names,
        launch_profile_private_skills=launch_profile_private_skills,
        launch_profile_system_skill_policy=launch_profile_system_skill_policy,
        force_mode=force_mode,
        reuse_home=reuse_home,
    )

    emit_local_launch_completion(
        launch_result=launch_result,
        agent_name=resolved_agent_name,
        session_name=session_name,
    )


@agents_group.command(name="list")
@pair_port_option()
@click.option(
    "--state",
    "lifecycle_state",
    type=click.Choice(("active", "stopped", "relaunching", "retired", "all")),
    default="active",
    show_default=True,
    help="Filter local registry-backed results by lifecycle state. Use `all` to include every lifecycle state.",
)
def list_agents_command(port: int | None, lifecycle_state: str) -> None:
    """List managed agents from the shared registry, optionally enriched by the server."""

    payload = (
        list_managed_agents(port=port)
        if lifecycle_state == "active"
        else list_managed_agents(port=port, lifecycle_state=cast(Any, lifecycle_state))
    )
    emit(
        payload,
        plain_renderer=render_agent_list_plain,
        fancy_renderer=render_agent_list_fancy,
    )


@agents_group.command(name="state")
@pair_port_option()
@managed_agent_selector_options
def state_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show the operational managed-agent summary view."""

    target = resolve_managed_agent_target(
        agent_id=agent_id, agent_name=agent_name, port=port, include_inactive=True
    )
    emit(
        managed_agent_state_payload(target),
        plain_renderer=lambda payload: render_agent_state_plain(
            payload, owner_policy=managed_agent_state_policy_summary(target)
        ),
        fancy_renderer=lambda payload: render_agent_state_fancy(
            payload, owner_policy=managed_agent_state_policy_summary(target)
        ),
    )


def _common_check_succeeded(observation: CommonPluginObservationV1) -> bool:
    """Require confirmed common freshness and settled native readiness."""

    return (
        observation.freshness == "current"
        and observation.coverage_complete
        and observation.native_ready
        and observation.native_settled
    )


def _native_refresh_succeeded(result: NativeRefreshResultV1) -> bool:
    """Accept confirmed current scope or complete qualified future consumption."""

    if not result.native_ready or not result.native_settled:
        return False
    if result.outcome in {"already_current", "refreshed"}:
        return _common_check_succeeded(result.observation)
    if result.outcome != "automatic" or not result.observation.automatic:
        return False
    required = [item for item in result.observation.resources if item.required]
    return (
        result.observation.native_ready
        and result.observation.native_settled
        and {item.kind for item in required} == {"skills", "mcp"}
        and all(
            item.supported
            and (
                item.boundary in {"next_step", "next_turn", "next_load"}
                or (item.freshness == "current" and item.complete)
            )
            for item in required
        )
    )


def _finite_refresh_timeout(ctx: click.Context, param: click.Parameter, value: float) -> float:
    """Reject NaN before resolving authority or issuing a native request."""

    if not math.isfinite(value):
        raise click.BadParameter("must be finite", ctx=ctx, param=param)
    return value


@agents_group.command(name="home")
@pair_port_option()
@managed_agent_selector_options
def native_home_agent_command(
    port: int | None, agent_id: str | None, agent_name: str | None
) -> None:
    """Show the active agent's native home without rebuilding its material."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(
        managed_agent_native_home(target),
        plain_renderer=_render_native_home_plain,
    )


def _render_native_home_plain(payload: object) -> None:
    """Qualify foreign native homes in plain output as well as structured output."""

    home = cast(dict[str, Any], payload)
    context_id = home.get("identity", {}).get("execution_context_id")
    prefix = f"{context_id}:" if context_id else ""
    click.echo(f"{prefix}{home['home_dir']}")


@agents_group.command(name="refresh")
@click.option(
    "--check", "check_only", is_flag=True, help="Inspect common freshness without reload."
)
@click.option(
    "--timeout-seconds",
    type=click.FloatRange(min=0.0, max=120.0, min_open=True),
    default=30.0,
    show_default=True,
    callback=_finite_refresh_timeout,
    help="Bound one native refresh operation; refresh never restarts the agent.",
)
@pair_port_option()
@managed_agent_selector_options
def refresh_agent_command(
    port: int | None,
    agent_id: str | None,
    agent_name: str | None,
    check_only: bool,
    timeout_seconds: float,
) -> None:
    """Observe skills/MCP, then use qualified automatic behavior or native refresh."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    if check_only:
        observation = managed_agent_common_plugin_state(target)
        emit(observation)
        succeeded = _common_check_succeeded(observation)
    else:
        result = refresh_managed_agent(target, timeout_seconds=timeout_seconds)
        emit(result)
        succeeded = _native_refresh_succeeded(result)
    if not succeeded:
        raise click.exceptions.Exit(1)


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


@agents_group.command(name="open-browser")
@managed_agent_selector_options
def open_agent_browser_command(agent_id: str | None, agent_name: str | None) -> None:
    """Open the native browser for an active local Kimi Web owner."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=None)
    result = open_managed_agent_browser(target)
    emit_receipt({"status": result.status, "action": result.action, "detail": result.detail})


@agents_group.command(name="stop")
@pair_port_option()
@managed_agent_selector_options
def stop_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Stop one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit(stop_managed_agent(target))


@agents_group.command(name="relaunch")
@pair_port_option(help_text="Houmao server port override for explicit relaunch")
@click.option(
    "--chat-session-mode",
    type=click.Choice(_RELAUNCH_CHAT_SESSION_MODES),
    default=None,
    help=(
        "Provider chat-session policy for this relaunch: new, tool_last_or_new, or exact. "
        "Omitting the flag uses the launch-profile relaunch policy when present, otherwise new."
    ),
)
@click.option(
    "--chat-session-id",
    default=None,
    help="Provider chat-session id to resume when --chat-session-mode exact is selected.",
)
@managed_agent_selector_options
def relaunch_agent_command(
    port: int | None,
    chat_session_mode: str | None,
    chat_session_id: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Relaunch one tmux-backed managed agent without rebuilding its home."""

    relaunch_chat_session = _resolve_relaunch_chat_session_selection_or_click(
        mode=chat_session_mode,
        session_id=chat_session_id,
    )
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
        _emit_current_session_relaunch(relaunch_chat_session)
        return

    target = resolve_relaunch_managed_agent_target(
        agent_id=selected_agent_id,
        agent_name=selected_agent_name,
        port=port,
    )
    response = (
        relaunch_managed_agent(target, relaunch_chat_session=relaunch_chat_session)
        if relaunch_chat_session is not None
        else relaunch_managed_agent(target)
    )
    emit(response)


def _require_single_scope_context() -> ManagedAgentScopeContext:
    """Return the inherited `agents single` target context."""

    scope_context = get_managed_agent_scope_context()
    if scope_context is None or scope_context.scope != "single":
        raise click.ClickException(
            "`agents single` commands require exactly one group-level `--agent-id` or "
            "`--agent-name` selector."
        )
    return scope_context


def _single_selector_injections() -> Mapping[str, Any]:
    """Return callback parameters for one selected-agent command."""

    scope_context = _require_single_scope_context()
    return {
        "agent_id": scope_context.agent_id,
        "agent_name": scope_context.agent_name,
    }


def _single_gateway_injections() -> Mapping[str, Any]:
    """Return callback parameters for one selected-agent gateway command."""

    return {
        **_single_selector_injections(),
        "current_session": False,
        "target_tmux_session": _require_single_scope_context().target_tmux_session,
    }


def _self_selectorless_injections() -> Mapping[str, Any]:
    """Return callback parameters for one current-session command."""

    return {
        "agent_id": None,
        "agent_name": None,
        "port": None,
    }


def _self_gateway_injections() -> Mapping[str, Any]:
    """Return callback parameters for one current-session gateway command."""

    return {
        "agent_id": None,
        "agent_name": None,
        "current_session": True,
        "target_tmux_session": None,
        "pair_port": None,
    }


def _install_scoped_agents_commands() -> None:
    """Replace legacy root `agents` actions with explicit scoped command groups."""

    legacy_commands = dict(agents_group.commands)

    agents_global_group.add_command(legacy_commands["list"])

    selector_params = frozenset({"agent_id", "agent_name"})
    gateway_single_params = selector_params | frozenset({"current_session", "target_tmux_session"})
    selector_port_params = selector_params | frozenset({"port"})
    gateway_self_params = gateway_single_params | frozenset({"pair_port"})

    for command_name in (
        "state",
        "home",
        "refresh",
        "prompt",
        "interrupt",
        "open-browser",
        "stop",
        "relaunch",
    ):
        agents_single_group.add_command(
            clone_scoped_command_tree(
                legacy_commands[command_name],
                remove_params=selector_params,
                inject_params=_single_selector_injections,
            )
        )
    single_gateway = clone_scoped_command_tree(
        legacy_commands["gateway"],
        remove_params=gateway_single_params,
        inject_params=_single_gateway_injections,
    )
    assert isinstance(single_gateway, click.Group)
    single_gateway.add_command(web_entry_gateway_command)
    agents_single_group.add_command(single_gateway)
    for command_name in ("mail", "turn", "memory"):
        agents_single_group.add_command(
            clone_scoped_command_tree(
                legacy_commands[command_name],
                remove_params=selector_params,
                inject_params=_single_selector_injections,
            )
        )
    for command_name in ("mailbox", "cleanup"):
        agents_single_group.add_command(
            clone_scoped_command_tree(
                legacy_commands[command_name],
                remove_params=selector_params,
                inject_params=_single_selector_injections,
            )
        )

    agents_self_group.add_command(
        clone_scoped_command_tree(
            legacy_commands["gateway"],
            remove_params=gateway_self_params,
            inject_params=_self_gateway_injections,
        )
    )
    for command_name in ("home", "refresh", "mail", "turn", "memory"):
        agents_self_group.add_command(
            clone_scoped_command_tree(
                legacy_commands[command_name],
                remove_params=selector_port_params,
                inject_params=_self_selectorless_injections,
            )
        )
    agents_self_group.add_command(
        clone_scoped_command_tree(
            legacy_commands["mailbox"],
            remove_params=selector_params,
            inject_params=_self_selectorless_injections,
        )
    )

    agents_group.commands.clear()
    agents_group.add_command(agents_global_group)
    agents_group.add_command(agents_single_group)
    agents_group.add_command(agents_self_group)
    agents_group.add_command(legacy_commands["external"])


agents_group.add_command(gateway_group)
agents_group.add_command(cleanup_group)
agents_group.add_command(external_group)
agents_group.add_command(mail_group)
agents_group.add_command(mailbox_group)
agents_group.add_command(turn_group)
agents_group.add_command(memory_group)
_install_scoped_agents_commands()
agents_single_group.add_command(single_access_group)
agents_single_group.add_command(work_request_command)
agents_single_group.add_command(single_files_group)
agents_self_group.add_command(self_access_group)
agents_self_group.add_command(self_files_group)
agents_single_group.add_command(admin_instance_state_group)
agents_self_group.add_command(self_instance_state_group)
