"""Runtime-artifact helpers for server-backed session registration flows."""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.mailbox_runtime_support import install_runtime_mailbox_system_skills_for_tool
from houmao.agents.native_launch_resolver import resolve_native_launch_target, tool_for_provider
from houmao.owned_paths import HOUMAO_JOB_DIR_ENV_VAR
from houmao.project.overlay import (
    ensure_project_aware_local_roots,
    resolve_project_aware_local_roots,
    resolve_project_aware_runtime_root,
    resolve_project_aware_session_job_dir,
)
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    derive_agent_id_from_name,
    normalize_agent_identity_name,
    normalize_managed_agent_id,
    normalize_user_managed_agent_name,
)
from houmao.agents.realm_controller.boundary_models import (
    AgentLaunchPostureKindV1,
    JoinedLaunchEnvBindingInheritedV1,
    JoinedLaunchEnvBindingLiteralV1,
    SessionManifestAgentLaunchAuthorityV1,
)
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import RolePackage
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
    AGENT_GATEWAY_ROOT_ENV_VAR,
    GatewayCapabilityPublication,
    ensure_gateway_capability,
    publish_stable_gateway_env,
)
from houmao.agents.realm_controller.gateway_models import GatewayJsonObject
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    generate_session_id,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    BackendKind,
    HeadlessResumeSelection,
    JoinedLaunchEnvBinding,
    LaunchPlan,
)
from houmao.agents.realm_controller.registry_models import (
    LiveAgentRegistryRecordV2,
    RegistryIdentityV1,
    RegistryRuntimeV1,
    RegistryTerminalV1,
    canonicalize_registry_agent_name,
)
from houmao.agents.realm_controller.registry_storage import (
    DEFAULT_REGISTRY_LEASE_TTL,
    JOINED_REGISTRY_SENTINEL_LEASE_TTL,
    new_registry_generation_id,
    publish_live_agent_record,
    remove_live_agent_record,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    read_tmux_session_environment_value,
    set_tmux_session_environment,
    unset_tmux_session_environment,
)
from houmao.server.models import HoumaoHeadlessLaunchRequest
from houmao.srv_ctrl.commands.project_aware_wording import (
    describe_local_jobs_root_selection,
    describe_overlay_bootstrap,
    describe_overlay_root_selection_source,
    describe_runtime_root_selection,
)

_HOME_ENV_BY_TOOL: dict[str, str] = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "gemini": "GEMINI_HOME",
}
_EXECUTABLE_BY_TOOL: dict[str, str] = {
    "claude": "claude",
    "codex": "codex",
    "gemini": "gemini",
}


@dataclass(frozen=True)
class JoinedSessionArtifacts:
    """Result of materializing one joined managed-agent envelope."""

    manifest_path: Path
    session_root: Path
    agent_name: str
    agent_id: str
    runtime_root: Path
    jobs_root: Path
    runtime_root_detail: str
    jobs_root_detail: str
    overlay_root: Path
    overlay_root_detail: str
    project_overlay_bootstrapped: bool
    overlay_bootstrap_detail: str


def materialize_joined_launch(
    *,
    runtime_root: Path | None,
    agent_name: str,
    agent_id: str | None,
    provider: str,
    headless: bool,
    tmux_session_name: str,
    tmux_window_name: str | None,
    working_directory: Path,
    launch_args: Sequence[str],
    launch_env: Sequence[JoinedLaunchEnvBinding],
    install_houmao_skills: bool = True,
    resume_selection: HeadlessResumeSelection | None = None,
) -> JoinedSessionArtifacts:
    """Materialize a manifest-first runtime envelope for one joined tmux session."""

    project_roots = (
        ensure_project_aware_local_roots(cwd=working_directory)
        if runtime_root is None
        else resolve_project_aware_local_roots(cwd=working_directory)
    )
    resolved_runtime_root = resolve_project_aware_runtime_root(
        cwd=working_directory,
        explicit_root=runtime_root,
    )
    normalized_agent_name = normalize_user_managed_agent_name(agent_name)
    resolved_agent_id = (
        normalize_managed_agent_id(agent_id) if agent_id is not None else None
    ) or derive_agent_id_from_name(normalized_agent_name)
    tool = tool_for_provider(provider)
    backend = _joined_backend(provider=provider, headless=headless)
    session_id = generate_session_id(prefix=f"joined-{backend}")
    session_root = (
        default_manifest_path(
            resolved_runtime_root,
            backend,
            session_id,
        )
        .resolve()
        .parent
    )
    manifest_path = (session_root / "manifest.json").resolve()
    published_record = False
    published_gateway_env = False
    published_tmux_env = False

    try:
        session_root.mkdir(parents=True, exist_ok=False)
        role_name = _safe_role_name(normalized_agent_name)
        agent_def_dir, brain_manifest_path = _materialize_join_placeholder_files(
            session_root=session_root,
            role_name=role_name,
            tool=tool,
            executable=_executable_for_tool(tool),
        )
        resolved_home_path = _resolve_join_home_path(
            tool=tool,
            session_root=session_root,
            tmux_session_name=tmux_session_name,
            launch_env=launch_env,
            require_explicit=bool(headless or launch_args or launch_env),
        )
        if install_houmao_skills:
            install_runtime_mailbox_system_skills_for_tool(
                tool=tool,
                home_path=resolved_home_path,
            )
        launch_plan = _build_join_launch_plan(
            backend=backend,
            tool=tool,
            working_directory=working_directory.resolve(),
            role_name=role_name,
            executable=_executable_for_tool(tool),
            launch_args=list(launch_args),
            launch_env=launch_env,
            tmux_session_name=tmux_session_name,
            home_path=resolved_home_path,
            headless=headless,
            tmux_window_name=tmux_window_name,
        )
        job_dir = resolve_project_aware_session_job_dir(
            cwd=working_directory,
            session_id=session_id,
        )
        job_dir.mkdir(parents=True, exist_ok=True)
        launch_plan = replace(
            launch_plan,
            env={**launch_plan.env, HOUMAO_JOB_DIR_ENV_VAR: str(job_dir.resolve())},
            env_var_names=sorted({*launch_plan.env_var_names, HOUMAO_JOB_DIR_ENV_VAR}),
        )
        manifest_payload = build_session_manifest_payload(
            SessionManifestRequest(
                launch_plan=launch_plan,
                role_name=role_name,
                brain_manifest_path=brain_manifest_path,
                backend_state=_joined_backend_state(
                    backend=backend,
                    working_directory=working_directory.resolve(),
                    tmux_session_name=tmux_session_name,
                    tmux_window_name=tmux_window_name,
                    resume_selection=resume_selection,
                ),
                agent_name=normalized_agent_name,
                agent_id=resolved_agent_id,
                tmux_session_name=tmux_session_name,
                session_id=session_id,
                job_dir=job_dir,
                agent_def_dir=agent_def_dir,
                registry_generation_id=new_registry_generation_id(),
                registry_launch_authority="runtime",
                agent_launch_authority=_joined_launch_authority(
                    backend=backend,
                    tool=tool,
                    working_directory=working_directory.resolve(),
                    tmux_session_name=tmux_session_name,
                    session_id=session_id,
                    headless=headless,
                    launch_args=list(launch_args),
                    launch_env=launch_env,
                ),
            )
        )
        write_session_manifest(manifest_path, manifest_payload)
        gateway_paths = ensure_gateway_capability(
            GatewayCapabilityPublication(
                manifest_path=manifest_path,
                backend=backend,
                tool=tool,
                session_id=session_id,
                tmux_session_name=tmux_session_name,
                working_directory=working_directory.resolve(),
                backend_state=_joined_backend_state(
                    backend=backend,
                    working_directory=working_directory.resolve(),
                    tmux_session_name=tmux_session_name,
                    tmux_window_name=tmux_window_name,
                    resume_selection=resume_selection,
                ),
                agent_def_dir=agent_def_dir,
            )
        )
        if gateway_paths is not None:
            publish_stable_gateway_env(
                session_name=tmux_session_name,
                attach_path=gateway_paths.attach_path,
                gateway_root=gateway_paths.gateway_root,
                set_env=set_tmux_session_environment,
            )
            published_gateway_env = True
        set_tmux_session_environment(
            session_name=tmux_session_name,
            env_vars={
                AGENT_MANIFEST_PATH_ENV_VAR: str(manifest_path),
                AGENT_ID_ENV_VAR: resolved_agent_id,
                AGENT_DEF_DIR_ENV_VAR: str(agent_def_dir),
                HOUMAO_JOB_DIR_ENV_VAR: str(job_dir),
            },
        )
        published_tmux_env = True

        published_at = datetime.now(UTC)
        publish_live_agent_record(
            LiveAgentRegistryRecordV2(
                agent_name=canonicalize_registry_agent_name(normalized_agent_name),
                agent_id=resolved_agent_id,
                generation_id=manifest_payload["registry_generation_id"],
                published_at=published_at.isoformat(timespec="seconds"),
                lease_expires_at=(published_at + JOINED_REGISTRY_SENTINEL_LEASE_TTL).isoformat(
                    timespec="seconds"
                ),
                identity=RegistryIdentityV1(backend=backend, tool=tool),
                runtime=RegistryRuntimeV1(
                    manifest_path=str(manifest_path),
                    session_root=str(session_root),
                    agent_def_dir=str(agent_def_dir),
                ),
                terminal=RegistryTerminalV1(kind="tmux", session_name=tmux_session_name),
                gateway=None,
                mailbox=None,
            )
        )
        published_record = True
        return JoinedSessionArtifacts(
            manifest_path=manifest_path,
            session_root=session_root,
            agent_name=normalized_agent_name,
            agent_id=resolved_agent_id,
            runtime_root=resolved_runtime_root,
            jobs_root=job_dir.parent.resolve(),
            runtime_root_detail=describe_runtime_root_selection(explicit_root=runtime_root),
            jobs_root_detail=describe_local_jobs_root_selection(),
            overlay_root=project_roots.overlay_root,
            overlay_root_detail=describe_overlay_root_selection_source(
                overlay_root_source=project_roots.overlay_root_source,
                overlay_discovery_mode=project_roots.overlay_discovery_mode,
            ),
            project_overlay_bootstrapped=project_roots.created_overlay,
            overlay_bootstrap_detail=describe_overlay_bootstrap(
                created_overlay=project_roots.created_overlay,
                overlay_exists=project_roots.project_overlay is not None,
            ),
        )
    except Exception:
        if published_record:
            remove_live_agent_record(resolved_agent_id)
        if published_gateway_env or published_tmux_env:
            try:
                unset_tmux_session_environment(
                    session_name=tmux_session_name,
                    variable_names=[
                        AGENT_GATEWAY_ATTACH_PATH_ENV_VAR,
                        AGENT_GATEWAY_ROOT_ENV_VAR,
                        *(
                            [
                                AGENT_MANIFEST_PATH_ENV_VAR,
                                AGENT_ID_ENV_VAR,
                                AGENT_DEF_DIR_ENV_VAR,
                                HOUMAO_JOB_DIR_ENV_VAR,
                            ]
                            if published_tmux_env
                            else []
                        ),
                    ],
                )
            except Exception:
                pass
        shutil.rmtree(session_root, ignore_errors=True)
        raise


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
    """Materialize Houmao-owned manifest/session-root artifacts for one server-backed launch."""

    if runtime_root is None:
        ensure_project_aware_local_roots(cwd=working_directory)
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
    agent_id = derive_agent_id_from_name(canonical_agent_name)
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
                        "adapter_defaults": {
                            "args": [],
                            "tool_params": {},
                        },
                        "requested_overrides": {
                            "preset": None,
                            "direct": None,
                        },
                        "tool_metadata": {"tool_params": {}},
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

    job_dir = resolve_project_aware_session_job_dir(
        cwd=working_directory,
        session_id=session_name,
    )
    job_dir.mkdir(parents=True, exist_ok=True)
    launch_plan = replace(
        launch_plan,
        env={**launch_plan.env, HOUMAO_JOB_DIR_ENV_VAR: str(job_dir.resolve())},
        env_var_names=sorted({*launch_plan.env_var_names, HOUMAO_JOB_DIR_ENV_VAR}),
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
            job_dir=job_dir,
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
            HOUMAO_JOB_DIR_ENV_VAR: str(job_dir),
        },
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
        LiveAgentRegistryRecordV2(
            agent_name=canonicalize_registry_agent_name(canonical_agent_name),
            agent_id=agent_id,
            generation_id=manifest_payload["registry_generation_id"],
            published_at=published_at.isoformat(timespec="seconds"),
            lease_expires_at=(published_at + DEFAULT_REGISTRY_LEASE_TTL).isoformat(
                timespec="seconds"
            ),
            identity=RegistryIdentityV1(backend="houmao_server_rest", tool=tool),
            runtime=RegistryRuntimeV1(
                manifest_path=str(manifest_path),
                session_root=str(session_root),
                agent_def_dir=str(agent_def_dir),
            ),
            terminal=RegistryTerminalV1(kind="tmux", session_name=session_name),
            gateway=None,
            mailbox=None,
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
            operator_prompt_mode=target.preset.operator_prompt_mode,
            persistent_env_records=target.preset.launch_env_records,
            mailbox=target.preset.mailbox,
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
    )


def _joined_backend(*, provider: str, headless: bool) -> BackendKind:
    if not headless:
        return "local_interactive"
    if provider == "codex":
        return "codex_headless"
    if provider == "claude_code":
        return "claude_headless"
    if provider == "gemini_cli":
        return "gemini_headless"
    raise SessionManifestError(f"Unsupported joined headless provider `{provider}`.")


def _executable_for_tool(tool: str) -> str:
    executable = _EXECUTABLE_BY_TOOL.get(tool)
    if executable is None:
        raise SessionManifestError(f"Unsupported joined-session tool `{tool}`.")
    return executable


def _materialize_join_placeholder_files(
    *,
    session_root: Path,
    role_name: str,
    tool: str,
    executable: str,
) -> tuple[Path, Path]:
    agent_def_dir = (session_root / "agent_def").resolve()
    role_prompt_path = (agent_def_dir / "roles" / role_name / "system-prompt.md").resolve()
    role_prompt_path.parent.mkdir(parents=True, exist_ok=True)
    role_prompt_path.write_text(
        (
            "# Joined Session Placeholder\n\n"
            "This placeholder role keeps a durable manifest for a tmux session adopted into "
            "Houmao. The live provider process was not launched by Houmao.\n"
        ),
        encoding="utf-8",
    )
    env_file = (session_root / "launch.env").resolve()
    env_file.write_text("", encoding="utf-8")
    brain_manifest_path = (session_root / "brain_manifest.json").resolve()
    brain_manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "inputs": {"tool": tool},
                "launch_policy": {"operator_prompt_mode": "as_is"},
                "runtime": {
                    "launch_executable": executable,
                    "launch_home_selector": {
                        "env_var": _HOME_ENV_BY_TOOL.get(tool, "HOME"),
                        "value": str((session_root / "tool-home").resolve()),
                    },
                    "launch_contract": {
                        "adapter_defaults": {"args": [], "tool_params": {}},
                        "requested_overrides": {"preset": None, "direct": None},
                        "tool_metadata": {"tool_params": {}},
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
    return agent_def_dir, brain_manifest_path


def _resolve_join_home_path(
    *,
    tool: str,
    session_root: Path,
    tmux_session_name: str,
    launch_env: Sequence[JoinedLaunchEnvBinding],
    require_explicit: bool,
) -> Path:
    home_env_var = _HOME_ENV_BY_TOOL.get(tool)
    if home_env_var is None:
        raise SessionManifestError(f"Unsupported joined-session tool `{tool}`.")
    for binding in launch_env:
        if binding.name != home_env_var:
            continue
        if binding.mode == "literal":
            assert binding.value is not None
            return Path(binding.value).expanduser().resolve()
        value = read_tmux_session_environment_value(
            session_name=tmux_session_name,
            variable_name=home_env_var,
        )
        if value is None or not value.strip():
            raise SessionManifestError(
                "Joined-session launch env inheritance could not resolve "
                f"`{home_env_var}` from tmux session `{tmux_session_name}`."
            )
        return Path(value).expanduser().resolve()

    inherited_value = read_tmux_session_environment_value(
        session_name=tmux_session_name,
        variable_name=home_env_var,
    )
    if inherited_value is not None and inherited_value.strip():
        return Path(inherited_value).expanduser().resolve()
    if require_explicit:
        raise SessionManifestError(
            "Joined-session launch requires a resolvable tool home via tmux env or "
            f"`--launch-env {home_env_var}`."
        )
    fallback = (session_root / "tool-home").resolve()
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _resolve_join_env_values(
    *,
    tmux_session_name: str,
    launch_env: Sequence[JoinedLaunchEnvBinding],
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for binding in launch_env:
        if binding.mode == "literal":
            assert binding.value is not None
            resolved[binding.name] = binding.value
            continue
        value = read_tmux_session_environment_value(
            session_name=tmux_session_name,
            variable_name=binding.name,
        )
        if value is None or not value.strip():
            raise SessionManifestError(
                "Joined-session launch env inheritance could not resolve "
                f"`{binding.name}` from tmux session `{tmux_session_name}`."
            )
        resolved[binding.name] = value
    return resolved


def _build_join_launch_plan(
    *,
    backend: BackendKind,
    tool: str,
    working_directory: Path,
    role_name: str,
    executable: str,
    launch_args: list[str],
    launch_env: Sequence[JoinedLaunchEnvBinding],
    tmux_session_name: str,
    home_path: Path,
    headless: bool,
    tmux_window_name: str | None,
) -> LaunchPlan:
    return LaunchPlan.for_joined_session(
        backend=backend,
        tool=tool,
        executable=executable,
        args=launch_args,
        working_directory=working_directory,
        home_env_var=_HOME_ENV_BY_TOOL[tool],
        home_path=home_path,
        env=_resolve_join_env_values(
            tmux_session_name=tmux_session_name,
            launch_env=launch_env,
        ),
        env_var_names=sorted(binding.name for binding in launch_env),
        role_name=role_name,
        role_prompt="",
        metadata={
            "session_origin": "joined_tmux",
            "joined_launch_mode": "headless" if headless else "tui",
            **({"tmux_window_name": tmux_window_name} if tmux_window_name is not None else {}),
        },
    )


def _joined_backend_state(
    *,
    backend: BackendKind,
    working_directory: Path,
    tmux_session_name: str,
    tmux_window_name: str | None,
    resume_selection: HeadlessResumeSelection | None,
) -> GatewayJsonObject:
    payload: GatewayJsonObject = {
        "turn_index": 0,
        "role_bootstrap_applied": True,
        "working_directory": str(working_directory.resolve()),
        "tmux_session_name": tmux_session_name,
        "tmux_window_name": tmux_window_name,
    }
    if backend in {"codex_headless", "claude_headless", "gemini_headless"}:
        payload["session_id"] = None
        payload["resume_selection_kind"] = (
            resume_selection.kind if resume_selection is not None else "none"
        )
        payload["resume_selection_value"] = (
            resume_selection.value if resume_selection is not None else None
        )
    return payload


def _joined_launch_authority(
    *,
    backend: BackendKind,
    tool: str,
    working_directory: Path,
    tmux_session_name: str,
    session_id: str,
    headless: bool,
    launch_args: list[str],
    launch_env: Sequence[JoinedLaunchEnvBinding],
) -> SessionManifestAgentLaunchAuthorityV1:
    posture_kind: AgentLaunchPostureKindV1
    if headless:
        posture_kind = "headless_launch_options"
    elif launch_args or launch_env:
        posture_kind = "tui_launch_options"
    else:
        posture_kind = "unavailable"
    launch_env_payload = [
        (
            JoinedLaunchEnvBindingLiteralV1(
                mode="literal",
                name=binding.name,
                value=binding.value or "",
            )
            if binding.mode == "literal"
            else JoinedLaunchEnvBindingInheritedV1(mode="inherit", name=binding.name)
        )
        for binding in launch_env
    ]
    return SessionManifestAgentLaunchAuthorityV1(
        backend=backend,
        tool=tool,
        tmux_session_name=tmux_session_name,
        primary_window_index="0",
        working_directory=str(working_directory.resolve()),
        session_id=session_id,
        session_origin="joined_tmux",
        posture_kind=posture_kind,
        launch_args=launch_args or None,
        launch_env=launch_env_payload or None,
    )
