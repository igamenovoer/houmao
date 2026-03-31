"""Participant bootstrap and gateway-control helpers for the demo pack."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Literal, Mapping

from houmao.agents.brain_builder import (
    BuildRequest,
    BuildResult,
    build_brain_home,
    load_brain_recipe,
)
from houmao.agents.mailbox_runtime_support import project_runtime_mailbox_system_skills
from houmao.agents.realm_controller.gateway_models import GatewayMailNotifierPutV1
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
    HOUMAO_LOCAL_JOBS_DIR_ENV_VAR,
)
from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoHeadlessLaunchMailboxOptions, HoumaoHeadlessLaunchRequest

from .models import (
    FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
    FIXED_DEMO_PROJECT_AUTHOR_NAME,
    FIXED_DEMO_PROJECT_COMMIT_MESSAGE,
    FIXED_DEMO_PROJECT_COMMIT_UTC,
    MANAGED_PROJECT_METADATA_NAME,
    PACK_NAME,
    DemoPaths,
    ParticipantParameters,
    ParticipantState,
    write_json,
)

GitRunner = Callable[[list[str], Path, dict[str, str] | None], subprocess.CompletedProcess[str]]
ParticipantRole = Literal["initiator", "responder"]


class DemoAgentError(RuntimeError):
    """Raised when participant bootstrap or control steps fail."""


def build_demo_environment(
    *,
    paths: DemoPaths,
    base_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the shared environment used by the demo-owned server."""

    env = dict(os.environ if base_env is None else base_env)
    env[HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR] = str(paths.runtime_root)
    env[HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(paths.registry_root)
    env[HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR] = str(paths.mailbox_root)
    env[HOUMAO_LOCAL_JOBS_DIR_ENV_VAR] = str(paths.jobs_root)
    env["HOME"] = str(paths.server_home_dir)
    return env


def build_participant_brain(
    *,
    agent_def_dir: Path,
    runtime_root: Path,
    participant: ParticipantParameters,
    home_id: str,
) -> BuildResult:
    """Build one runtime brain home from the tracked recipe."""

    recipe = load_brain_recipe(participant.brain_recipe_path)
    if recipe.tool != participant.tool:
        raise DemoAgentError(
            f"recipe tool mismatch for {participant.role_name}: expected {participant.tool}, got {recipe.tool}"
        )
    return build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=runtime_root,
            tool=recipe.tool,
            skills=list(recipe.skills),
            config_profile=recipe.config_profile,
            credential_profile=recipe.credential_profile,
            recipe_path=participant.brain_recipe_path,
            recipe_launch_overrides=recipe.launch_overrides,
            operator_prompt_mode=recipe.operator_prompt_mode,
            mailbox=recipe.mailbox,
            agent_name=recipe.default_agent_name,
            home_id=home_id,
            reuse_home=False,
            persistent_env_records=recipe.launch_env_records,
        )
    )


def expose_runtime_skills_in_project(
    *,
    project_workdir: Path,
    build_result: BuildResult,
) -> None:
    """Stage mailbox skill docs in the demo project workdir.

    The demo keeps a project-local visible mailbox skill tree under
    `skills/mailbox/...` instead of relying on a live symlink into the
    runtime home.
    """

    skills_target = project_workdir / "skills"
    if skills_target.exists() and not skills_target.is_dir():
        raise DemoAgentError(
            f"demo project already contains a non-directory `skills` path: {skills_target}"
        )
    skills_target.mkdir(parents=True, exist_ok=True)

    runtime_mailbox_source = build_result.home_path / "skills" / "mailbox"
    if runtime_mailbox_source.is_dir():
        _stage_project_mailbox_skill_tree(
            source_root=runtime_mailbox_source,
            skills_target=skills_target,
        )
        return

    project_runtime_mailbox_system_skills(skills_target)


def _stage_project_mailbox_skill_tree(*, source_root: Path, skills_target: Path) -> None:
    """Copy one mailbox skill tree into the visible project mailbox path."""

    visible_target = skills_target / "mailbox"
    if source_root.resolve() == visible_target.resolve():
        return
    shutil.copytree(source_root, visible_target, dirs_exist_ok=True)


def launch_participant(
    *,
    client: HoumaoServerClient,
    agent_def_dir: Path,
    layout: DemoPaths,
    participant: ParticipantParameters,
    build_result: BuildResult,
    working_directory: Path,
    role: ParticipantRole,
) -> ParticipantState:
    """Launch one managed headless participant through `houmao-server`."""

    request_model = HoumaoHeadlessLaunchRequest(
        tool=participant.tool,
        working_directory=str(working_directory.resolve()),
        agent_def_dir=str(agent_def_dir.resolve()),
        brain_manifest_path=str(build_result.manifest_path.resolve()),
        role_name=participant.role_name,
        mailbox=HoumaoHeadlessLaunchMailboxOptions(
            transport="filesystem",
            filesystem_root=str(layout.mailbox_root.resolve()),
            principal_id=participant.mailbox_principal_id,
            address=participant.mailbox_address,
        ),
    )
    response = client.launch_headless_agent(request_model)
    return ParticipantState(
        role=role,
        tool=participant.tool,
        role_name=participant.role_name,
        mailbox_principal_id=participant.mailbox_principal_id,
        mailbox_address=participant.mailbox_address,
        working_directory=working_directory.resolve(),
        brain_recipe_path=participant.brain_recipe_path.resolve(),
        brain_home_path=build_result.home_path.resolve(),
        brain_manifest_path=build_result.manifest_path.resolve(),
        launch_helper_path=build_result.launch_helper_path.resolve(),
        tracked_agent_id=response.tracked_agent_id,
        agent_name=response.identity.agent_name,
        agent_id=response.identity.agent_id,
        session_root=Path(response.session_root).resolve(),
        tmux_session_name=response.identity.tmux_session_name or response.tracked_agent_id,
        gateway_host=None,
    )


def attach_gateway_and_enable_notifier(
    *,
    client: HoumaoServerClient,
    participant: ParticipantState,
    notifier_interval_seconds: int,
) -> ParticipantState:
    """Attach one managed gateway and enable its mail notifier."""

    status = client.attach_managed_agent_gateway(participant.tracked_agent_id)
    client.put_managed_agent_gateway_mail_notifier(
        participant.tracked_agent_id,
        GatewayMailNotifierPutV1(interval_seconds=notifier_interval_seconds),
    )
    return participant.model_copy(update={"gateway_host": status.gateway_host})


def disable_notifier(*, client: HoumaoServerClient, participant: ParticipantState) -> None:
    """Disable gateway notifier polling for one participant."""

    client.delete_managed_agent_gateway_mail_notifier(participant.tracked_agent_id)


def enable_notifier(
    *,
    client: HoumaoServerClient,
    participant: ParticipantState,
    notifier_interval_seconds: int,
) -> None:
    """Re-enable gateway notifier polling for one participant."""

    client.put_managed_agent_gateway_mail_notifier(
        participant.tracked_agent_id,
        GatewayMailNotifierPutV1(interval_seconds=notifier_interval_seconds),
    )


def stop_participant(*, client: HoumaoServerClient, participant: ParticipantState) -> None:
    """Best-effort stop for one managed participant."""

    client.stop_managed_agent(participant.tracked_agent_id)


def ensure_project_workdir_from_fixture(
    *,
    project_fixture: Path,
    project_workdir: Path,
    allow_reprovision: bool,
    run_git: GitRunner | None = None,
) -> Path:
    """Provision one copied dummy-project repo under the selected output root."""

    runner = _default_git_runner if run_git is None else run_git
    resolved_fixture = project_fixture.resolve()
    resolved_project_workdir = project_workdir.resolve()
    if not resolved_fixture.is_dir():
        raise ValueError(f"dummy project fixture directory not found: {resolved_fixture}")
    if (resolved_fixture / ".git").exists():
        raise ValueError(
            "dummy project fixture must remain source-only and may not include tracked `.git`: "
            f"{resolved_fixture}"
        )
    if resolved_project_workdir.exists():
        if not allow_reprovision:
            raise ValueError(
                "demo project directory already exists before a stopped demo state was found: "
                f"{resolved_project_workdir}"
            )
        if not _is_managed_dummy_project_repo(
            project_workdir=resolved_project_workdir, run_git=runner
        ):
            raise ValueError(
                "demo project directory exists but is not a demo-managed dummy-project repo: "
                f"{resolved_project_workdir}"
            )
        shutil.rmtree(resolved_project_workdir)

    resolved_project_workdir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(resolved_fixture, resolved_project_workdir)
    _write_managed_project_metadata(
        project_workdir=resolved_project_workdir,
        fixture_dir=resolved_fixture,
    )
    _initialize_demo_git_repo(project_workdir=resolved_project_workdir, run_git=runner)
    if not is_standalone_git_repo(project_workdir=resolved_project_workdir, run_git=runner):
        raise RuntimeError(
            "dummy project provisioning finished but the resulting project directory did not validate "
            f"as a standalone git repository: {resolved_project_workdir}"
        )
    return resolved_project_workdir


def is_standalone_git_repo(
    *,
    project_workdir: Path,
    run_git: GitRunner | None = None,
) -> bool:
    """Return whether the target directory is a standalone git repository."""

    runner = _default_git_runner if run_git is None else run_git
    inside = _git_output(
        args=["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_workdir,
        run_git=runner,
    )
    if inside != "true":
        return False
    project_top = _git_output(
        args=["git", "rev-parse", "--show-toplevel"],
        cwd=project_workdir,
        run_git=runner,
    )
    project_common = _git_output(
        args=["git", "rev-parse", "--git-common-dir"],
        cwd=project_workdir,
        run_git=runner,
    )
    if project_top is None or project_common is None:
        return False
    return _resolved_git_reported_path(
        project_top, cwd=project_workdir
    ) == project_workdir.resolve() and _resolved_git_reported_path(
        project_common, cwd=project_workdir
    ) == (project_workdir.resolve() / ".git")


def _managed_project_metadata_path(project_workdir: Path) -> Path:
    """Return the marker path for a demo-managed dummy-project workdir."""

    return project_workdir / MANAGED_PROJECT_METADATA_NAME


def _is_managed_dummy_project_repo(*, project_workdir: Path, run_git: GitRunner) -> bool:
    """Return whether the existing directory is one of this pack's copied repos."""

    return _managed_project_metadata_path(project_workdir).is_file() and is_standalone_git_repo(
        project_workdir=project_workdir,
        run_git=run_git,
    )


def _write_managed_project_metadata(*, project_workdir: Path, fixture_dir: Path) -> None:
    """Write the pack-owned metadata marker for one copied repo."""

    write_json(
        _managed_project_metadata_path(project_workdir),
        {
            "schema_version": 1,
            "managed_by": PACK_NAME,
            "fixture_dir": str(fixture_dir.resolve()),
            "prepared_at": FIXED_DEMO_PROJECT_COMMIT_UTC,
        },
    )


def _initialize_demo_git_repo(*, project_workdir: Path, run_git: GitRunner) -> None:
    """Initialize one copied fixture as a pinned standalone git repo."""

    fixed_identity_env = {
        "GIT_AUTHOR_NAME": FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_AUTHOR_EMAIL": FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_COMMITTER_NAME": FIXED_DEMO_PROJECT_AUTHOR_NAME,
        "GIT_COMMITTER_EMAIL": FIXED_DEMO_PROJECT_AUTHOR_EMAIL,
        "GIT_AUTHOR_DATE": FIXED_DEMO_PROJECT_COMMIT_UTC,
        "GIT_COMMITTER_DATE": FIXED_DEMO_PROJECT_COMMIT_UTC,
    }
    _run_required_git_command(
        args=["git", "init", "--initial-branch", "main"], cwd=project_workdir, run_git=run_git
    )
    _run_required_git_command(args=["git", "add", "--all"], cwd=project_workdir, run_git=run_git)
    _run_required_git_command(
        args=[
            "git",
            "commit",
            "--allow-empty",
            "--no-gpg-sign",
            "-m",
            FIXED_DEMO_PROJECT_COMMIT_MESSAGE,
        ],
        cwd=project_workdir,
        run_git=run_git,
        env=fixed_identity_env,
    )


def _run_required_git_command(
    *,
    args: list[str],
    cwd: Path,
    run_git: GitRunner,
    env: dict[str, str] | None = None,
) -> None:
    """Run one required git command or raise with a clear failure message."""

    result = run_git(args, cwd, env)
    if result.returncode == 0:
        return
    detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
    raise RuntimeError(f"`{' '.join(args)}` failed: {detail}")


def _default_git_runner(
    args: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one git command in text mode."""

    merged_env = dict(os.environ)
    if env is not None:
        merged_env.update(env)
    return subprocess.run(
        args,
        cwd=str(cwd.resolve()),
        check=False,
        capture_output=True,
        text=True,
        env=merged_env,
    )


def _git_output(*, args: list[str], cwd: Path, run_git: GitRunner) -> str | None:
    """Return stripped git stdout when the command succeeds."""

    result = run_git(args, cwd, None)
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text or None


def _resolved_git_reported_path(raw_path: str, *, cwd: Path) -> Path:
    """Resolve one git-reported path relative to the working directory."""

    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.resolve()
    return (cwd.resolve() / candidate).resolve()
