"""Managed-agent commands for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import click

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.native_launch_resolver import resolve_native_launch_target
from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    TmuxPaneRecord,
    attach_tmux_session as attach_tmux_session_shared,
    list_tmux_panes,
)
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.runtime import resume_runtime_session, start_runtime_session
from houmao.agents.realm_controller.errors import (
    LaunchPlanError,
    LaunchPolicyResolutionError,
    SessionManifestError,
)
from houmao.agents.realm_controller.models import HeadlessResumeSelection, JoinedLaunchEnvBinding
from houmao.server.tui.process import PaneProcessInspector

from .gateway import (
    _require_current_tmux_session_name,
    _resolve_current_session_agent_def_dir,
    _resolve_current_session_manifest,
    gateway_group,
)
from .mail import mail_group
from .turn import turn_group
from ..runtime_artifacts import JoinedSessionArtifacts, materialize_joined_launch
from ..common import (
    emit_json,
    managed_agent_selector_options,
    pair_port_option,
    resolve_prompt_text,
    resolve_managed_agent_selector,
)
from ..managed_agents import (
    interrupt_managed_agent,
    list_managed_agents,
    managed_agent_detail_payload,
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
_PROVIDERS_REQUIRING_WORKSPACE_ACCESS = frozenset(
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


@click.group(name="agents")
def agents_group() -> None:
    """Managed-agent operations across local runtime and `houmao-server` backends."""


@agents_group.command(name="launch")
@click.option("--agents", required=True, help="Native launch selector to resolve the brain recipe.")
@click.option("--agent-name", required=True, help="Friendly managed-agent name.")
@click.option("--agent-id", default=None, help="Optional authoritative managed-agent id.")
@click.option("--session-name", help="Optional tmux session name.")
@click.option("--headless", is_flag=True, help="Launch in detached mode.")
@click.option(
    "--provider",
    default=_DEFAULT_PROVIDER,
    show_default=True,
    help="Provider identifier to use for the launch.",
)
@click.option("--yolo", is_flag=True, help="Skip workspace trust confirmation.")
def launch_agents_command(
    agents: str,
    agent_name: str,
    agent_id: str | None,
    session_name: str | None,
    headless: bool,
    provider: str,
    yolo: bool,
) -> None:
    """Build and launch one managed agent locally without `houmao-server`."""

    if provider not in _PROVIDERS:
        raise click.ClickException(
            f"Invalid provider `{provider}`. Available providers: {', '.join(sorted(_PROVIDERS))}."
        )

    working_directory = Path.cwd().resolve()
    if provider in _PROVIDERS_REQUIRING_WORKSPACE_ACCESS and not yolo:
        click.echo(
            f"The underlying provider ({provider}) will be trusted to perform all actions "
            f"(read, write, and execute) in:\n"
            f"  {working_directory}\n\n"
            f"To skip this confirmation, use: houmao-mgr agents launch --yolo\n"
        )
        if not click.confirm("Do you trust all the actions in this folder?", default=True):
            raise click.ClickException("Launch cancelled by user.")

    resolved_backend_name = "unknown"
    try:
        target = resolve_native_launch_target(
            selector=agents,
            provider=provider,
            working_directory=working_directory,
        )
        build_result = build_brain_home(
            BuildRequest(
                agent_def_dir=target.agent_def_dir,
                runtime_root=None,
                tool=target.recipe.tool,
                skills=target.recipe.skills,
                config_profile=target.recipe.config_profile,
                credential_profile=target.recipe.credential_profile,
                recipe_path=target.recipe_path,
                recipe_launch_overrides=target.recipe.launch_overrides,
                operator_prompt_mode=target.recipe.operator_prompt_mode,
                mailbox=target.recipe.mailbox,
                agent_name=agent_name,
                agent_id=agent_id,
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
            backend=resolved_backend,
            working_directory=working_directory,
            agent_name=agent_name,
            agent_id=agent_id,
            tmux_session_name=session_name,
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
        raise click.ClickException(str(exc)) from exc

    click.echo("Managed agent launch complete:")
    click.echo(f"agent_name={controller.agent_identity or agent_name}")
    click.echo(f"agent_id={controller.agent_id or agent_id or 'unknown'}")
    click.echo(f"tmux_session_name={controller.tmux_session_name or session_name or 'unknown'}")
    click.echo(f"manifest_path={controller.manifest_path}")
    if not headless and controller.tmux_session_name is not None:
        if _caller_has_interactive_terminal():
            try:
                attach_tmux_session_shared(session_name=controller.tmux_session_name)
            except RuntimeError as exc:
                raise click.ClickException(
                    f"Managed agent launch succeeded, but tmux handoff failed: {exc}"
                ) from exc
        else:
            click.echo("terminal_handoff=skipped_non_interactive")
            click.echo(f"attach_command=tmux attach-session -t {controller.tmux_session_name}")


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
    "--working-directory",
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True, exists=True),
    default=None,
    help="Optional working directory override; defaults from tmux window `0`, pane `0`.",
)
@click.option(
    "--resume-id",
    default=None,
    help="Optional headless resume selector: omitted, `last`, or an exact provider session id.",
)
def join_agents_command(
    agent_name: str,
    agent_id: str | None,
    headless: bool,
    provider: str | None,
    launch_args: tuple[str, ...],
    launch_env: tuple[str, ...],
    working_directory: Path | None,
    resume_id: str | None,
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
            working_directory=(working_directory or pane_current_path).resolve(),
            launch_args=launch_args,
            launch_env=launch_env_bindings,
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

    emit_json(list_managed_agents(port=port))


@agents_group.command(name="show")
@pair_port_option()
@managed_agent_selector_options
def show_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show the detail-oriented managed-agent view."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(managed_agent_detail_payload(target))


@agents_group.command(name="state")
@pair_port_option()
@managed_agent_selector_options
def state_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Show the operational managed-agent summary view."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(managed_agent_state_payload(target))


@agents_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@pair_port_option(help_text="Houmao server port override; skips registry discovery when set.")
@managed_agent_selector_options
def prompt_agent_command(
    port: int | None,
    prompt: str | None,
    agent_id: str | None,
    agent_name: str | None,
) -> None:
    """Submit the default prompt path for one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(prompt_managed_agent(target, prompt=resolve_prompt_text(prompt=prompt)))


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
    emit_json(interrupt_managed_agent(target))


@agents_group.command(name="stop")
@pair_port_option()
@managed_agent_selector_options
def stop_agent_command(port: int | None, agent_id: str | None, agent_name: str | None) -> None:
    """Stop one managed agent."""

    target = resolve_managed_agent_target(agent_id=agent_id, agent_name=agent_name, port=port)
    emit_json(stop_managed_agent(target))


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
        emit_json(
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
    emit_json(relaunch_managed_agent(target))


agents_group.add_command(gateway_group)
agents_group.add_command(mail_group)
agents_group.add_command(turn_group)


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
    click.echo("Managed agent join complete:")
    click.echo(f"agent_name={result.agent_name}")
    click.echo(f"agent_id={result.agent_id}")
    click.echo(f"provider={provider}")
    click.echo(f"backend={'headless' if headless else 'local_interactive'}")
    click.echo(f"tmux_session_name={tmux_session_name}")
    click.echo(f"manifest_path={result.manifest_path}")
