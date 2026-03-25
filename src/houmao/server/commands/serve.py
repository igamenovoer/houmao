"""Serve command for `houmao-server`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

import click
import uvicorn

from houmao.server.app import create_app

from .common import build_config, path_option_help

_FC = TypeVar("_FC", bound=Callable[..., Any])


def server_serve_options(function: _FC) -> _FC:
    """Attach the shared `houmao-server serve` option surface."""

    function = click.option("--api-base-url", default="http://127.0.0.1:9889", show_default=True)(
        function
    )
    function = click.option("--runtime-root", default=None, help=path_option_help())(function)
    function = click.option(
        "--watch-poll-interval-seconds",
        default=0.5,
        type=float,
        show_default=True,
    )(function)
    function = click.option(
        "--recent-transition-limit",
        default=24,
        type=int,
        show_default=True,
    )(function)
    function = click.option(
        "--stability-threshold-seconds",
        default=1.0,
        type=float,
        show_default=True,
    )(function)
    function = click.option(
        "--completion-stability-seconds",
        default=1.0,
        type=float,
        show_default=True,
    )(function)
    function = click.option(
        "--unknown-to-stalled-timeout-seconds",
        default=30.0,
        type=float,
        show_default=True,
    )(function)
    function = click.option(
        "--supported-tui-process",
        "supported_tui_processes",
        multiple=True,
        help="Repeat `tool=name1,name2` to override supported live TUI process detection.",
    )(function)
    function = click.option(
        "--compat-shell-ready-timeout-seconds",
        default=10.0,
        type=click.FloatRange(min=0.0, min_open=True),
        show_default=True,
    )(function)
    function = click.option(
        "--compat-shell-ready-poll-interval-seconds",
        default=0.5,
        type=click.FloatRange(min=0.0, min_open=True),
        show_default=True,
    )(function)
    function = click.option(
        "--compat-provider-ready-timeout-seconds",
        default=45.0,
        type=click.FloatRange(min=0.0, min_open=True),
        show_default=True,
    )(function)
    function = click.option(
        "--compat-provider-ready-poll-interval-seconds",
        default=1.0,
        type=click.FloatRange(min=0.0, min_open=True),
        show_default=True,
    )(function)
    function = click.option(
        "--compat-codex-warmup-seconds",
        default=2.0,
        type=click.FloatRange(min=0.0),
        show_default=True,
    )(function)
    function = click.option(
        "--startup-child/--no-startup-child",
        default=True,
        show_default=True,
    )(function)
    return function


def run_server(
    *,
    api_base_url: str,
    runtime_root: str | None,
    watch_poll_interval_seconds: float,
    recent_transition_limit: int,
    stability_threshold_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    supported_tui_processes: tuple[str, ...],
    compat_shell_ready_timeout_seconds: float,
    compat_shell_ready_poll_interval_seconds: float,
    compat_provider_ready_timeout_seconds: float,
    compat_provider_ready_poll_interval_seconds: float,
    compat_codex_warmup_seconds: float,
    startup_child: bool,
) -> None:
    """Run the shared `houmao-server` startup path."""

    config = build_config(
        api_base_url=api_base_url,
        runtime_root=runtime_root,
        watch_poll_interval_seconds=watch_poll_interval_seconds,
        recent_transition_limit=recent_transition_limit,
        stability_threshold_seconds=stability_threshold_seconds,
        completion_stability_seconds=completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        supported_tui_processes=supported_tui_processes,
        compat_shell_ready_timeout_seconds=compat_shell_ready_timeout_seconds,
        compat_shell_ready_poll_interval_seconds=compat_shell_ready_poll_interval_seconds,
        compat_provider_ready_timeout_seconds=compat_provider_ready_timeout_seconds,
        compat_provider_ready_poll_interval_seconds=compat_provider_ready_poll_interval_seconds,
        compat_codex_warmup_seconds=compat_codex_warmup_seconds,
        startup_child=startup_child,
    )
    uvicorn.run(
        create_app(config=config),
        host=config.public_host,
        port=config.public_port,
        log_level="info",
    )


@click.command(name="serve")
@server_serve_options
def serve_command(
    api_base_url: str,
    runtime_root: str | None,
    watch_poll_interval_seconds: float,
    recent_transition_limit: int,
    stability_threshold_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    supported_tui_processes: tuple[str, ...],
    compat_shell_ready_timeout_seconds: float,
    compat_shell_ready_poll_interval_seconds: float,
    compat_provider_ready_timeout_seconds: float,
    compat_provider_ready_poll_interval_seconds: float,
    compat_codex_warmup_seconds: float,
    startup_child: bool,
) -> None:
    """Run the local Houmao HTTP server."""

    run_server(
        api_base_url=api_base_url,
        runtime_root=runtime_root,
        watch_poll_interval_seconds=watch_poll_interval_seconds,
        recent_transition_limit=recent_transition_limit,
        stability_threshold_seconds=stability_threshold_seconds,
        completion_stability_seconds=completion_stability_seconds,
        unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
        supported_tui_processes=supported_tui_processes,
        compat_shell_ready_timeout_seconds=compat_shell_ready_timeout_seconds,
        compat_shell_ready_poll_interval_seconds=compat_shell_ready_poll_interval_seconds,
        compat_provider_ready_timeout_seconds=compat_provider_ready_timeout_seconds,
        compat_provider_ready_poll_interval_seconds=compat_provider_ready_poll_interval_seconds,
        compat_codex_warmup_seconds=compat_codex_warmup_seconds,
        startup_child=startup_child,
    )
