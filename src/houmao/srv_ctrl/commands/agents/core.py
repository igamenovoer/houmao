"""Managed-agent commands for `houmao-mgr`."""

from __future__ import annotations

from pathlib import Path
import subprocess

import click

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.native_launch_resolver import resolve_native_launch_target
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.runtime import start_runtime_session
from houmao.agents.realm_controller.errors import LaunchPlanError, SessionManifestError

from .gateway import gateway_group
from .mail import mail_group
from .turn import turn_group
from ..common import emit_json, pair_port_option, resolve_prompt_text
from ..managed_agents import (
    interrupt_managed_agent,
    list_managed_agents,
    managed_agent_detail_payload,
    managed_agent_state_payload,
    managed_agent_history_payload,
    prompt_managed_agent,
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


@click.group(name="agents")
def agents_group() -> None:
    """Managed-agent operations across local runtime and `houmao-server` backends."""


@agents_group.command(name="launch")
@click.option("--agents", required=True, help="Native launch selector to resolve the brain recipe.")
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
                mailbox=target.recipe.mailbox,
                agent_name=target.recipe.default_agent_name,
            )
        )
        controller = start_runtime_session(
            agent_def_dir=target.agent_def_dir,
            brain_manifest_path=build_result.manifest_path.resolve(),
            role_name=target.role_name,
            backend=backend_for_tool(target.tool),
            working_directory=working_directory,
            agent_identity=target.recipe.default_agent_name,
            agent_id=None,
            tmux_session_name=session_name,
        )
    except (
        FileNotFoundError,
        LaunchPlanError,
        RuntimeError,
        SessionManifestError,
        ValueError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(
        "Managed agent launch complete: "
        f"agent={controller.agent_id or controller.agent_identity or controller.manifest_path.parent.name} "
        f"manifest={controller.manifest_path}"
    )
    if not headless and controller.tmux_session_name is not None:
        subprocess.run(
            ["tmux", "attach-session", "-t", controller.tmux_session_name],
            check=False,
        )


@agents_group.command(name="list")
@pair_port_option()
def list_agents_command(port: int | None) -> None:
    """List managed agents from the shared registry, optionally enriched by the server."""

    emit_json(list_managed_agents(port=port))


@agents_group.command(name="show")
@pair_port_option()
@click.argument("agent_ref")
def show_agent_command(port: int | None, agent_ref: str) -> None:
    """Show the detail-oriented managed-agent view."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(managed_agent_detail_payload(target))


@agents_group.command(name="state")
@pair_port_option()
@click.argument("agent_ref")
def state_agent_command(port: int | None, agent_ref: str) -> None:
    """Show the operational managed-agent summary view."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(managed_agent_state_payload(target))


@agents_group.command(name="history")
@click.option("--limit", default=20, type=int, show_default=True, help="History entry limit.")
@pair_port_option()
@click.argument("agent_ref")
def history_agent_command(port: int | None, limit: int, agent_ref: str) -> None:
    """Show bounded managed-agent history."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(managed_agent_history_payload(target, limit=limit))


@agents_group.command(name="prompt")
@click.option(
    "--prompt",
    default=None,
    help="Prompt text to submit. If omitted, piped stdin is used.",
)
@pair_port_option(help_text="Houmao server port override; skips registry discovery when set.")
@click.argument("agent_ref")
def prompt_agent_command(port: int | None, prompt: str | None, agent_ref: str) -> None:
    """Submit the default prompt path for one managed agent."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(prompt_managed_agent(target, prompt=resolve_prompt_text(prompt=prompt)))


@agents_group.command(name="interrupt")
@pair_port_option()
@click.argument("agent_ref")
def interrupt_agent_command(port: int | None, agent_ref: str) -> None:
    """Interrupt one managed agent."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(interrupt_managed_agent(target))


@agents_group.command(name="stop")
@pair_port_option()
@click.argument("agent_ref")
def stop_agent_command(port: int | None, agent_ref: str) -> None:
    """Stop one managed agent."""

    target = resolve_managed_agent_target(agent_ref=agent_ref, port=port)
    emit_json(stop_managed_agent(target))


agents_group.add_command(gateway_group)
agents_group.add_command(mail_group)
agents_group.add_command(turn_group)
