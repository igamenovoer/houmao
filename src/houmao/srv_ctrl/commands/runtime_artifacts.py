"""Runtime-artifact helpers for server-backed session registration flows."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path


from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.mailbox_runtime_support import safe_registry_mailboxes_projection
from houmao.agents.agent_workspace import (
    AgentMemoryPaths,
    ensure_agent_memory,
    memory_env,
    resolve_agent_memory,
)
from houmao.agents.native_launch_resolver import resolve_native_launch_target, tool_for_provider
from houmao.project.overlay import (
    ensure_project_aware_local_roots,
    resolve_project_aware_local_roots,
    resolve_project_aware_runtime_root,
)
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    AgentIdentityCreation,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import RolePackage
from houmao.agents.realm_controller.gateway_storage import (
    GatewayCapabilityPublication,
    ensure_gateway_capability,
    publish_stable_gateway_env,
)
from houmao.agents.realm_controller.gateway_models import GatewayJsonObject
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    parse_session_manifest_payload,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
)
from houmao.agents.realm_controller.registry_models import (
    ManagedAgentRegistryRecordV3,
    RegistryIdentityV1,
    RegistryLifecycleV1,
    RegistryLivenessV1,
    RegistryMailboxesV1,
    RegistryRuntimeV1,
    RegistryTerminalV2,
    canonicalize_registry_agent_name,
)
from houmao.agents.realm_controller.registry_storage import (
    TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL,
    new_registry_generation_id,
    publish_live_agent_record,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    set_tmux_session_environment,
    unset_tmux_session_environment,
)
from houmao.agents.realm_controller.backends.headless_output import (
    resolve_headless_display_detail,
    resolve_headless_display_style,
)
from houmao.server.models import HoumaoHeadlessLaunchRequest

_HOME_ENV_BY_TOOL: dict[str, str] = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "kimi": "KIMI_CODE_HOME",
}


def _launch_plan_env_with_memory(
    *,
    launch_plan: LaunchPlan,
    memory: AgentMemoryPaths,
) -> dict[str, str]:
    """Return one launch env mapping with memory bindings applied."""

    updated_env = dict(launch_plan.env)
    for name in {
        "HOUMAO_AGENT_MEMORY_DIR",
        "HOUMAO_AGENT_STATE_DIR",
        "HOUMAO_AGENT_MEMO_FILE",
        "HOUMAO_AGENT_PAGES_DIR",
        "HOUMAO_AGENT_SCRATCH_DIR",
        "HOUMAO_AGENT_PERSIST_DIR",
        "HOUMAO_JOB_DIR",
        "HOUMAO_MEMORY_DIR",
    }:
        updated_env.pop(name, None)
    updated_env.update(memory_env(memory))
    return updated_env


def _launch_plan_env_var_names_with_memory(
    *,
    launch_plan: LaunchPlan,
    memory: AgentMemoryPaths,
) -> list[str]:
    """Return launch env-var names after memory binding injection."""

    updated_names = set(launch_plan.env_var_names)
    updated_names.difference_update(
        {
            "HOUMAO_AGENT_MEMORY_DIR",
            "HOUMAO_AGENT_STATE_DIR",
            "HOUMAO_AGENT_MEMO_FILE",
            "HOUMAO_AGENT_PAGES_DIR",
            "HOUMAO_AGENT_SCRATCH_DIR",
            "HOUMAO_AGENT_PERSIST_DIR",
            "HOUMAO_JOB_DIR",
            "HOUMAO_MEMORY_DIR",
        }
    )
    updated_names.update(memory_env(memory))
    return sorted(updated_names)


def _safe_role_name(value: str) -> str:
    """Return a filesystem-safe role name for server-backed registration artifacts."""

    normalized = "".join(char if (char.isalnum() or char in {"-", "_"}) else "-" for char in value)
    trimmed = normalized.strip("-_")
    return trimmed.lower() or "delegated-role"


def materialize_delegated_launch(
    *,
    runtime_root: Path | None,
    api_base_url: str,
    session_name: str,
    terminal_id: str,
    tmux_window_name: str | None,
    provider: str,
    agent_profile: str,
    working_directory: Path,
) -> tuple[Path, Path, str, str]:
    """Materialize artifacts for a retired delegated old-server launch path."""

    raise RuntimeError(
        "Delegated `houmao_server_rest` launch artifact materialization is retired. "
        "Use `houmao-passive-server` managed-headless launch APIs instead."
    )

    project_roots = (
        ensure_project_aware_local_roots(cwd=working_directory)
        if runtime_root is None
        else resolve_project_aware_local_roots(cwd=working_directory)
    )
    resolved_runtime_root = resolve_project_aware_runtime_root(
        cwd=working_directory,
        explicit_root=runtime_root,
    )
    session_root = (
        default_manifest_path(
            resolved_runtime_root,
            "houmao_server_rest",
            session_name,
        )
        .resolve()
        .parent
    )
    session_root.mkdir(parents=True, exist_ok=True)

    normalized_agent_name = normalize_agent_identity_name(session_name)
    canonical_agent_name = normalized_agent_name.canonical_name
    agent_id = AgentIdentityCreation(agent_name=canonical_agent_name).resolve().agent_id
    role_name = _safe_role_name(agent_profile)
    agent_def_dir = (session_root / "agent_def").resolve()
    role_prompt_path = (agent_def_dir / "roles" / role_name / "system-prompt.md").resolve()
    role_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    role_prompt_path.write_text(
        (
            "# Server-Backed Session\n\n"
            "This placeholder role exists so the runtime can keep a durable manifest for "
            "one server-backed managed session. The live terminal is managed through "
            "`houmao-server`.\n"
        ),
        encoding="utf-8",
    )

    env_file = (session_root / "launch.env").resolve()
    env_file.write_text("", encoding="utf-8")

    tool = tool_for_provider(provider)
    tool_home = (session_root / "tool-home").resolve()
    tool_home.mkdir(parents=True, exist_ok=True)
    brain_manifest_path = (session_root / "brain_manifest.json").resolve()
    brain_manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "inputs": {"tool": tool},
                "launch_policy": {"operator_prompt_mode": "as_is"},
                "runtime": {
                    "launch_executable": "cao",
                    "launch_home_selector": {
                        "env_var": _HOME_ENV_BY_TOOL.get(tool, "HOME"),
                        "value": str(tool_home),
                    },
                    "launch_contract": {
                        "adapter_defaults": {"args": []},
                        "requested_overrides": {
                            "preset": None,
                            "direct": None,
                        },
                        "construction_provenance": {
                            "adapter_path": None,
                            "preset_path": None,
                            "preset_overrides_present": False,
                            "direct_overrides_present": False,
                        },
                    },
                },
                "credentials": {
                    "env_contract": {
                        "source_file": str(env_file),
                        "allowlisted_env_vars": [],
                    }
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=json.loads(brain_manifest_path.read_text(encoding="utf-8")),
            role_package=RolePackage(
                role_name=role_name,
                system_prompt=role_prompt_path.read_text(encoding="utf-8"),
                path=role_prompt_path,
            ),
            backend="houmao_server_rest",
            working_directory=working_directory.resolve(),
        )
    )

    memory = resolve_agent_memory(
        overlay_root=project_roots.overlay_root,
        agent_id=agent_id,
    )
    ensure_agent_memory(memory)
    launch_plan = replace(
        launch_plan,
        env=_launch_plan_env_with_memory(launch_plan=launch_plan, memory=memory),
        env_var_names=_launch_plan_env_var_names_with_memory(
            launch_plan=launch_plan,
            memory=memory,
        ),
    )

    manifest_path = default_manifest_path(
        resolved_runtime_root,
        "houmao_server_rest",
        session_name,
    ).resolve()
    manifest_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name=role_name,
            brain_manifest_path=brain_manifest_path,
            backend_state={
                "api_base_url": api_base_url,
                "session_name": session_name,
                "terminal_id": terminal_id,
                "profile_name": f"delegated:{agent_profile}",
                "profile_path": str(role_prompt_path),
                "tmux_window_name": tmux_window_name,
                "parsing_mode": "shadow_only" if tool in {"claude", "codex"} else "cao_only",
                "turn_index": 0,
            },
            agent_name=canonical_agent_name,
            agent_id=agent_id,
            tmux_session_name=session_name,
            session_id=session_root.name,
            memory_root=memory.memory_root,
            memo_file=memory.memo_file,
            pages_dir=memory.pages_dir,
            agent_def_dir=agent_def_dir,
            registry_generation_id=new_registry_generation_id(),
            registry_launch_authority="external",
        )
    )
    write_session_manifest(manifest_path, manifest_payload)

    set_tmux_session_environment(
        session_name=session_name,
        env_vars={
            AGENT_MANIFEST_PATH_ENV_VAR: str(manifest_path),
            AGENT_ID_ENV_VAR: agent_id,
            AGENT_DEF_DIR_ENV_VAR: str(agent_def_dir),
            **memory_env(memory),
        },
    )
    unset_tmux_session_environment(
        session_name=session_name,
        variable_names=[
            "HOUMAO_JOB_DIR",
            "HOUMAO_MEMORY_DIR",
            "HOUMAO_AGENT_STATE_DIR",
            "HOUMAO_AGENT_SCRATCH_DIR",
            "HOUMAO_AGENT_PERSIST_DIR",
        ],
    )
    gateway_paths = ensure_gateway_capability(
        GatewayCapabilityPublication(
            manifest_path=manifest_path,
            backend="houmao_server_rest",
            tool=tool,
            session_id=session_root.name,
            tmux_session_name=session_name,
            working_directory=working_directory.resolve(),
            backend_state=_backend_state_for_delegated_launch(
                api_base_url=api_base_url,
                session_name=session_name,
                terminal_id=terminal_id,
                tmux_window_name=tmux_window_name,
                tool=tool,
            ),
            agent_def_dir=agent_def_dir,
        )
    )
    if gateway_paths is not None:
        publish_stable_gateway_env(
            session_name=session_name,
            attach_path=gateway_paths.attach_path,
            gateway_root=gateway_paths.gateway_root,
            set_env=set_tmux_session_environment,
        )

    published_at = datetime.now(UTC)
    publish_live_agent_record(
        ManagedAgentRegistryRecordV3(
            mode=launch_plan.mode,
            agent_name=canonicalize_registry_agent_name(canonical_agent_name),
            agent_id=agent_id,
            generation_id=manifest_payload["registry_generation_id"],
            lifecycle=RegistryLifecycleV1(
                state="active",
                relaunchable=False,
                state_updated_at=published_at.isoformat(timespec="seconds"),
            ),
            liveness=RegistryLivenessV1(
                published_at=published_at.isoformat(timespec="seconds"),
                lease_expires_at=(published_at + TMUX_BACKED_REGISTRY_SENTINEL_LEASE_TTL).isoformat(
                    timespec="seconds"
                ),
            ),
            identity=RegistryIdentityV1(backend="houmao_server_rest", tool=tool),
            native_surface=parse_session_manifest_payload(
                manifest_payload, source=str(manifest_path)
            ).native_surface,
            runtime=RegistryRuntimeV1(
                manifest_path=str(manifest_path),
                session_root=str(session_root),
                agent_def_dir=str(agent_def_dir),
            ),
            terminal=RegistryTerminalV2(
                kind="tmux",
                current_session_name=session_name,
                last_session_name=session_name,
            ),
            gateway=None,
            mailboxes=RegistryMailboxesV1.model_validate(
                safe_registry_mailboxes_projection(launch_plan.mailboxes)
            ),
            canonical_mail_identity=launch_plan.mailboxes.canonical_mail_identity,
        )
    )
    return manifest_path, session_root, canonical_agent_name, agent_id


def _backend_state_for_delegated_launch(
    *,
    api_base_url: str,
    session_name: str,
    terminal_id: str,
    tmux_window_name: str | None,
    tool: str,
) -> GatewayJsonObject:
    """Return strict backend state for delegated `houmao_server_rest` launches."""

    return {
        "api_base_url": api_base_url,
        "session_name": session_name,
        "terminal_id": terminal_id,
        "parsing_mode": "shadow_only" if tool in {"claude", "codex"} else "cao_only",
        **({"tmux_window_name": tmux_window_name} if tmux_window_name is not None else {}),
    }


def materialize_headless_launch_request(
    *,
    runtime_root: Path | None,
    provider: str,
    agent_profile: str,
    working_directory: Path,
    headless_display_style: str | None = None,
    headless_display_detail: str | None = None,
) -> HoumaoHeadlessLaunchRequest:
    """Resolve pair convenience inputs into a native headless launch request."""

    resolved_workdir = working_directory.resolve()
    if runtime_root is None:
        ensure_project_aware_local_roots(cwd=resolved_workdir)
    target = resolve_native_launch_target(
        selector=agent_profile,
        provider=provider,
        working_directory=resolved_workdir,
    )
    resolved_runtime_root = resolve_project_aware_runtime_root(
        cwd=resolved_workdir,
        explicit_root=runtime_root,
    )
    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=target.agent_def_dir,
            runtime_root=resolved_runtime_root,
            tool=target.preset.tool,
            skills=target.preset.skills,
            setup=target.preset.setup,
            auth=target.preset.auth,
            preset_path=target.preset_path,
            preset_launch_overrides=target.preset.launch_overrides,
            preset_tool_params=target.preset.tool_params,
            preset_model_config=target.preset.launch_model_config,
            source_system_skill_policy=target.preset.launch_system_skill_policy,
            operator_prompt_mode=target.preset.operator_prompt_mode,
            persistent_env_records=target.preset.launch_env_records,
            mailboxes=target.preset.mailboxes,
            extra=target.preset.extra,
        )
    )
    return HoumaoHeadlessLaunchRequest(
        tool=target.tool,
        working_directory=str(resolved_workdir),
        agent_def_dir=str(target.agent_def_dir),
        brain_manifest_path=str(build_result.manifest_path.resolve()),
        role_name=target.role_name,
        agent_name=None,
        agent_id=None,
        headless_display_style=resolve_headless_display_style(headless_display_style),
        headless_display_detail=resolve_headless_display_detail(headless_display_detail),
    )
