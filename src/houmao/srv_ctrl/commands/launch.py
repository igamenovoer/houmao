"""Launch command for `houmao-srv-ctrl`."""

from __future__ import annotations

from pathlib import Path

import click

from houmao.server.models import HoumaoRegisterLaunchRequest

from .common import (
    extract_option_value,
    has_flag,
    require_supported_houmao_pair,
    resolve_server_base_url,
    run_passthrough,
)
from .runtime_artifacts import (
    materialize_delegated_launch,
    materialize_headless_launch_request,
)


@click.command(
    name="launch",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def launch_command(ctx: click.Context) -> None:
    """Launch through delegated CAO or native Houmao headless flow."""

    port_value = extract_option_value(ctx.args, "--port")
    port = int(port_value) if port_value is not None else None
    base_url = resolve_server_base_url(port=port)
    client = require_supported_houmao_pair(base_url=base_url)

    if has_flag(ctx.args, "--headless"):
        provider = extract_option_value(ctx.args, "--provider") or "kiro_cli"
        agent_profile = extract_option_value(ctx.args, "--agents")
        if agent_profile is None:
            raise click.ClickException("Headless launch must include `--agents`.")
        try:
            request_model = materialize_headless_launch_request(
                runtime_root=None,
                provider=provider,
                agent_profile=agent_profile,
                working_directory=Path.cwd().resolve(),
            )
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc

        response = client.launch_headless_agent(request_model)
        click.echo(
            "Houmao native headless launch complete: "
            f"agent={response.tracked_agent_id} manifest={response.manifest_path}"
        )
        ctx.exit(0)

    before_sessions = {session.id for session in client.list_sessions()}
    result = run_passthrough(command_name="launch", extra_args=ctx.args)
    if result.returncode != 0:
        ctx.exit(result.returncode)

    after_sessions = {session.id for session in client.list_sessions()}
    session_name = _resolve_session_name(
        ctx.args, before_sessions=before_sessions, after_sessions=after_sessions
    )
    session_detail = client.get_session(session_name)
    terminals = session_detail.terminals
    if not terminals:
        raise click.ClickException(
            f"`houmao-server` did not return terminals for session `{session_name}`."
        )
    first_terminal = terminals[0]
    terminal_id = first_terminal.id
    tmux_window_name = _optional_terminal_string(first_terminal.tmux_window)

    provider = extract_option_value(ctx.args, "--provider") or "kiro_cli"
    agent_profile = extract_option_value(ctx.args, "--agents")
    if agent_profile is None:
        raise click.ClickException("Delegated launch must include `--agents`.")

    manifest_path, session_root, canonical_agent_name, agent_id = materialize_delegated_launch(
        runtime_root=None,
        api_base_url=base_url,
        session_name=session_name,
        terminal_id=terminal_id,
        tmux_window_name=tmux_window_name,
        provider=provider,
        agent_profile=agent_profile,
        working_directory=Path.cwd().resolve(),
    )
    client.register_launch(
        request_model=HoumaoRegisterLaunchRequest(
            session_name=session_name,
            terminal_id=terminal_id,
            tool=_tool_from_provider(provider),
            manifest_path=str(manifest_path),
            session_root=str(session_root),
            agent_name=canonical_agent_name,
            agent_id=agent_id,
            tmux_session_name=session_name,
            tmux_window_name=tmux_window_name,
        )
    )

    ctx.exit(0)


def _resolve_session_name(
    args: list[str],
    *,
    before_sessions: set[str],
    after_sessions: set[str],
) -> str:
    requested = extract_option_value(args, "--session-name")
    if requested is not None:
        candidate = requested if requested.startswith("cao-") else f"cao-{requested}"
        if candidate in after_sessions:
            return candidate

    created = sorted(after_sessions - before_sessions)
    if len(created) == 1:
        return created[0]
    if requested is not None and requested in after_sessions:
        return requested
    raise click.ClickException(
        "Could not determine which session was created by delegated `cao launch`; "
        "pass `--session-name` explicitly."
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
