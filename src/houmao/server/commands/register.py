"""Registration commands for `houmao-server`."""

from __future__ import annotations

import click

from houmao.server.models import HoumaoRegisterLaunchRequest

from .common import client_for_base_url, echo_json


@click.command(name="register-launch")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
@click.option("--session-name", required=True)
@click.option("--tool", required=True)
@click.option("--terminal-id", default=None)
@click.option("--observed-tool-version", default=None)
@click.option("--manifest-path", default=None)
@click.option("--session-root", default=None)
@click.option("--agent-name", default=None)
@click.option("--agent-id", default=None)
@click.option("--tmux-session-name", default=None)
@click.option("--tmux-window-name", default=None)
def register_launch_command(
    api_base_url: str,
    session_name: str,
    tool: str,
    terminal_id: str | None,
    observed_tool_version: str | None,
    manifest_path: str | None,
    session_root: str | None,
    agent_name: str | None,
    agent_id: str | None,
    tmux_session_name: str | None,
    tmux_window_name: str | None,
) -> None:
    """Register a delegated CLI launch into `houmao-server`."""

    client = client_for_base_url(api_base_url)
    response = client.register_launch(
        HoumaoRegisterLaunchRequest(
            session_name=session_name,
            terminal_id=terminal_id,
            tool=tool,
            observed_tool_version=observed_tool_version,
            manifest_path=manifest_path,
            session_root=session_root,
            agent_name=agent_name,
            agent_id=agent_id,
            tmux_session_name=tmux_session_name,
            tmux_window_name=tmux_window_name,
        )
    )
    echo_json(response.model_dump(mode="json"))
