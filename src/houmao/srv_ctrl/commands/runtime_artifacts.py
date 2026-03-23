"""Runtime-artifact helpers for delegated `houmao-srv-ctrl launch` flows."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.brain_builder import BuildRequest, build_brain_home, load_brain_recipe
from houmao.owned_paths import AGENTSYS_JOB_DIR_ENV_VAR, resolve_runtime_root, resolve_session_job_dir
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    derive_agent_id_from_name,
    normalize_agent_identity_name,
)
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import RolePackage
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
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
    new_registry_generation_id,
    publish_live_agent_record,
)
from houmao.agents.realm_controller.backends.tmux_runtime import set_tmux_session_environment
from houmao.server.models import HoumaoHeadlessLaunchRequest

_TOOL_BY_PROVIDER: dict[str, str] = {
    "claude_code": "claude",
    "codex": "codex",
    "gemini_cli": "gemini",
}
_HOME_ENV_BY_TOOL: dict[str, str] = {
    "claude": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "gemini": "GEMINI_HOME",
}


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
    """Materialize Houmao-owned manifest/session-root artifacts for one delegated launch."""

    resolved_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    session_root = default_manifest_path(
        resolved_runtime_root,
        "houmao_server_rest",
        session_name,
    ).resolve().parent
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
            "# Delegated Launch\n\n"
            "This placeholder role exists so the runtime can keep a durable manifest for "
            "`houmao-srv-ctrl launch` sessions. The live terminal was created by delegated "
            "`cao launch` behavior and is managed through `houmao-server`.\n"
        ),
        encoding="utf-8",
    )

    env_file = (session_root / "launch.env").resolve()
    env_file.write_text("", encoding="utf-8")

    tool = _TOOL_BY_PROVIDER.get(provider, provider)
    tool_home = (session_root / "tool-home").resolve()
    tool_home.mkdir(parents=True, exist_ok=True)
    brain_manifest_path = (session_root / "brain_manifest.json").resolve()
    brain_manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "inputs": {"tool": tool},
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
                            "recipe": None,
                            "direct": None,
                        },
                        "tool_metadata": {"tool_params": {}},
                        "construction_provenance": {
                            "adapter_path": None,
                            "recipe_path": None,
                            "recipe_overrides_present": False,
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

    job_dir = resolve_session_job_dir(
        session_id=session_name,
        working_directory=working_directory.resolve(),
    )
    job_dir.mkdir(parents=True, exist_ok=True)
    launch_plan = replace(
        launch_plan,
        env={**launch_plan.env, AGENTSYS_JOB_DIR_ENV_VAR: str(job_dir.resolve())},
        env_var_names=sorted({*launch_plan.env_var_names, AGENTSYS_JOB_DIR_ENV_VAR}),
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
            job_dir=job_dir,
            registry_generation_id=new_registry_generation_id(),
        )
    )
    write_session_manifest(manifest_path, manifest_payload)

    set_tmux_session_environment(
        session_name=session_name,
        env_vars={
            AGENT_MANIFEST_PATH_ENV_VAR: str(manifest_path),
            AGENT_DEF_DIR_ENV_VAR: str(agent_def_dir),
            AGENTSYS_JOB_DIR_ENV_VAR: str(job_dir),
        },
    )

    published_at = datetime.now(UTC)
    publish_live_agent_record(
        LiveAgentRegistryRecordV2(
            agent_name=canonicalize_registry_agent_name(canonical_agent_name),
            agent_id=agent_id,
            generation_id=manifest_payload["registry_generation_id"],
            published_at=published_at.isoformat(timespec="seconds"),
            lease_expires_at=(published_at + DEFAULT_REGISTRY_LEASE_TTL).isoformat(timespec="seconds"),
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


def materialize_headless_launch_request(
    *,
    runtime_root: Path | None,
    provider: str,
    agent_profile: str,
    working_directory: Path,
) -> HoumaoHeadlessLaunchRequest:
    """Resolve pair convenience inputs into a native headless launch request."""

    resolved_workdir = working_directory.resolve()
    tool = _TOOL_BY_PROVIDER.get(provider, provider)
    agent_def_dir = _resolve_headless_agent_def_dir(cwd=resolved_workdir)
    recipe_path = _resolve_headless_recipe_path(
        agent_def_dir=agent_def_dir,
        tool=tool,
        agent_profile=agent_profile,
    )
    recipe = load_brain_recipe(recipe_path)
    if recipe.tool != tool:
        raise ValueError(
            f"Resolved recipe `{recipe_path}` targets tool `{recipe.tool}`, not `{tool}`."
        )
    role_name = _safe_role_name(agent_profile)
    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=runtime_root,
            tool=recipe.tool,
            skills=recipe.skills,
            config_profile=recipe.config_profile,
            credential_profile=recipe.credential_profile,
            recipe_path=recipe_path,
            recipe_launch_overrides=recipe.launch_overrides,
            mailbox=recipe.mailbox,
            agent_name=recipe.default_agent_name,
        )
    )
    return HoumaoHeadlessLaunchRequest(
        tool=tool,
        working_directory=str(resolved_workdir),
        agent_def_dir=str(agent_def_dir),
        brain_manifest_path=str(build_result.manifest_path.resolve()),
        role_name=role_name,
        agent_name=recipe.default_agent_name,
        agent_id=None,
    )


def _safe_role_name(value: str) -> str:
    stripped = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in value)
    stripped = stripped.strip("-_")
    return stripped or "delegated-launch"


def _resolve_headless_agent_def_dir(*, cwd: Path) -> Path:
    """Resolve the agent-definition root for native headless launch translation."""

    env_value = os.environ.get(AGENT_DEF_DIR_ENV_VAR)
    if env_value is not None and env_value.strip():
        return Path(env_value).expanduser().resolve()
    return (cwd / ".agentsys" / "agents").resolve()


def _resolve_headless_recipe_path(
    *,
    agent_def_dir: Path,
    tool: str,
    agent_profile: str,
) -> Path:
    """Resolve one native headless recipe from pair convenience inputs."""

    recipe_root = (agent_def_dir / "brains" / "brain-recipes" / tool).resolve()
    candidates = [
        recipe_root / f"{agent_profile}.yaml",
        recipe_root / f"{agent_profile}-default.yaml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Could not resolve a native headless brain recipe for "
        f"`{agent_profile}` under `{recipe_root}`."
    )
