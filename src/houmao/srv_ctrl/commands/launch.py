"""Launch command for `houmao-srv-ctrl`."""

from __future__ import annotations

from pathlib import Path
import subprocess

import click

from houmao.agents.realm_controller.manifest import load_session_manifest
from houmao.cao.models import CaoSessionTerminalSummary, CaoTerminal
from houmao.cao.rest_client import CaoApiError
from houmao.server.models import HoumaoRegisterLaunchRequest

from .common import (
    require_supported_houmao_pair,
    resolve_server_base_url,
)
from .runtime_artifacts import (
    materialize_delegated_launch,
    materialize_headless_launch_request,
)

_DEFAULT_PROVIDER = "kiro_cli"
_PROVIDERS = frozenset(
    {
        "kiro_cli",
        "claude_code",
        "codex",
        "gemini_cli",
        "kimi_cli",
        "q_cli",
    }
)
_PROVIDERS_REQUIRING_WORKSPACE_ACCESS = frozenset(
    {
        "claude_code",
        "codex",
        "kiro_cli",
        "kimi_cli",
        "gemini_cli",
    }
)


@click.command(name="launch")
@click.option("--agents", required=True, help="Agent profile to launch")
@click.option("--session-name", help="Name of the session (default: auto-generated)")
@click.option("--headless", is_flag=True, help="Launch in detached mode")
@click.option(
    "--provider",
    default=_DEFAULT_PROVIDER,
    help=f"Provider to use (default: {_DEFAULT_PROVIDER})",
)
@click.option("--port", default=None, type=int, help="Server port to use")
@click.option("--yolo", is_flag=True, help="Skip workspace trust confirmation")
def launch_command(
    agents: str,
    session_name: str | None,
    headless: bool,
    provider: str,
    port: int | None,
    yolo: bool,
) -> None:
    """Launch through the supported Houmao pair."""

    if provider not in _PROVIDERS:
        raise click.ClickException(
            f"Invalid provider '{provider}'. Available providers: {', '.join(sorted(_PROVIDERS))}"
        )

    working_directory = Path.cwd().resolve()
    if provider in _PROVIDERS_REQUIRING_WORKSPACE_ACCESS and not yolo:
        click.echo(
            f"The underlying provider ({provider}) will be trusted to perform all actions "
            f"(read, write, and execute) in:\n"
            f"  {working_directory}\n\n"
            f"To skip this confirmation, use: houmao-srv-ctrl launch --yolo\n"
        )
        if not click.confirm("Do you trust all the actions in this folder?", default=True):
            raise click.ClickException("Launch cancelled by user")

    if headless:
        base_url = resolve_server_base_url(port=port)
        client = require_supported_houmao_pair(base_url=base_url)
        try:
            request_model = materialize_headless_launch_request(
                runtime_root=None,
                provider=provider,
                agent_profile=agents,
                working_directory=working_directory,
            )
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc

        response = client.launch_headless_agent(request_model)
        click.echo(
            "Houmao native headless launch complete: "
            f"agent={response.tracked_agent_id} manifest={response.manifest_path}"
        )
        return

    _launch_session_backed_pair_command(
        agents=agents,
        session_name=session_name,
        provider=provider,
        port=port,
        working_directory=working_directory,
        attach_to_tmux=True,
        emit_created_messages=False,
    )


def _tool_from_provider(provider: str) -> str:
    if provider == "claude_code":
        return "claude"
    if provider == "codex":
        return "codex"
    if provider == "gemini_cli":
        return "gemini"
    return provider


def _optional_terminal_string(value: object) -> str | None:
    """Return one stripped optional terminal metadata string."""

    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _launch_session_backed_pair_command(
    *,
    agents: str,
    session_name: str | None,
    provider: str,
    port: int | None,
    working_directory: Path,
    attach_to_tmux: bool,
    emit_created_messages: bool,
) -> None:
    """Create one TUI-backed CAO-compatible session through `houmao-server`."""

    base_url = resolve_server_base_url(port=port)
    client = require_supported_houmao_pair(base_url=base_url)

    try:
        terminal = client.create_session(
            provider=provider,
            agent_profile=agents,
            session_name=session_name,
            working_directory=str(working_directory),
        )
        session_detail = client.get_session(terminal.session_name)
    except CaoApiError as exc:
        raise click.ClickException(
            f"Failed to connect to `houmao-server` at {base_url}: {exc.detail}"
        ) from exc

    terminal_summary = _find_terminal_summary(session_detail.terminals, terminal)
    tmux_window_name = _optional_terminal_string(terminal_summary.tmux_window)

    manifest_path, session_root, canonical_agent_name, agent_id = materialize_delegated_launch(
        runtime_root=None,
        api_base_url=base_url,
        session_name=terminal.session_name,
        terminal_id=terminal.id,
        tmux_window_name=tmux_window_name,
        provider=provider,
        agent_profile=agents,
        working_directory=working_directory,
    )
    observed_tool_version = _observed_tool_version_from_manifest_path(manifest_path)
    client.register_launch(
        request_model=HoumaoRegisterLaunchRequest(
            session_name=terminal.session_name,
            terminal_id=terminal.id,
            tool=_tool_from_provider(provider),
            observed_tool_version=observed_tool_version,
            manifest_path=str(manifest_path),
            session_root=str(session_root),
            agent_name=canonical_agent_name,
            agent_id=agent_id,
            tmux_session_name=terminal.session_name,
            tmux_window_name=tmux_window_name,
        )
    )

    if emit_created_messages:
        click.echo(f"Session created: {terminal.session_name}")
        click.echo(f"Terminal created: {terminal.name}")

    if attach_to_tmux:
        subprocess.run(["tmux", "attach-session", "-t", terminal.session_name], check=False)


def _find_terminal_summary(
    terminals: list[CaoSessionTerminalSummary],
    terminal: CaoTerminal,
) -> CaoSessionTerminalSummary:
    """Return the session terminal summary that matches the created terminal."""

    for candidate in terminals:
        if candidate.id == terminal.id:
            return candidate
    if terminals:
        return terminals[0]
    raise click.ClickException(
        f"`houmao-server` did not return terminals for session `{terminal.session_name}`."
    )


def _observed_tool_version_from_manifest_path(manifest_path: Path) -> str | None:
    """Return one optional observed tool version from a session manifest."""

    try:
        payload = load_session_manifest(manifest_path).payload
    except Exception:
        return None

    top_level = payload.get("launch_policy_provenance")
    if isinstance(top_level, dict):
        detected_tool_version = top_level.get("detected_tool_version")
        if isinstance(detected_tool_version, str) and detected_tool_version.strip():
            return detected_tool_version

    launch_plan = payload.get("launch_plan")
    if isinstance(launch_plan, dict):
        launch_policy_provenance = launch_plan.get("launch_policy_provenance")
        if isinstance(launch_policy_provenance, dict):
            detected_tool_version = launch_policy_provenance.get("detected_tool_version")
            if isinstance(detected_tool_version, str) and detected_tool_version.strip():
                return detected_tool_version

    return None
