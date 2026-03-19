"""Serve command for `houmao-server`."""

from __future__ import annotations

import click
import uvicorn

from houmao.server.app import create_app

from .common import build_config, path_option_help


@click.command(name="serve")
@click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)
@click.option("--runtime-root", default=None, help=path_option_help())
@click.option(
    "--watch-poll-interval-seconds",
    default=1.0,
    type=float,
    show_default=True,
)
@click.option(
    "--recent-transition-limit",
    default=24,
    type=int,
    show_default=True,
)
@click.option(
    "--completion-stability-seconds",
    default=1.0,
    type=float,
    show_default=True,
)
@click.option(
    "--unknown-to-stalled-timeout-seconds",
    default=30.0,
    type=float,
    show_default=True,
)
@click.option(
    "--supported-tui-process",
    "supported_tui_processes",
    multiple=True,
    help="Repeat `tool=name1,name2` to override supported live TUI process detection.",
)
@click.option(
    "--startup-child/--no-startup-child",
    default=True,
    show_default=True,
)
def serve_command(
    api_base_url: str,
    runtime_root: str | None,
    watch_poll_interval_seconds: float,
    recent_transition_limit: int,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    supported_tui_processes: tuple[str, ...],
    startup_child: bool,
) -> None:
    """Run the local Houmao HTTP server."""

    config = build_config(
        api_base_url=api_base_url,
        runtime_root=runtime_root,
        watch_poll_interval_seconds=watch_poll_interval_seconds,
        recent_transition_limit=recent_transition_limit,
        completion_stability_seconds=completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        supported_tui_processes=supported_tui_processes,
        startup_child=startup_child,
    )
    uvicorn.run(
        create_app(config=config),
        host=config.public_host,
        port=config.public_port,
        log_level="info",
    )
