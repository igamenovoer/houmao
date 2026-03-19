"""Top-level click command tree for `houmao-server`."""

from __future__ import annotations

import click

from .query import (
    current_instance_command,
    health_command,
    sessions_group,
    terminals_group,
)
from .register import register_launch_command
from .serve import serve_command


@click.group(name="houmao-server")
def cli() -> None:
    """Houmao-owned CAO-compatible HTTP service."""


cli.add_command(serve_command)
cli.add_command(health_command)
cli.add_command(current_instance_command)
cli.add_command(register_launch_command)
cli.add_command(sessions_group)
cli.add_command(terminals_group)


def main(argv: list[str] | None = None) -> int:
    """Run the click CLI and return an exit code."""

    try:
        cli.main(args=argv, prog_name="houmao-server", standalone_mode=False)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    return 0
