"""Top-level click command tree for `houmao-srv-ctrl`."""

from __future__ import annotations

import click

from .install import install_command
from .launch import launch_command
from .passthrough import passthrough_command


@click.group(name="houmao-srv-ctrl")
def cli() -> None:
    """CAO-compatible Houmao service-management CLI."""


cli.add_command(passthrough_command("flow"))
cli.add_command(passthrough_command("info", require_pair=True))
cli.add_command(passthrough_command("init"))
cli.add_command(install_command)
cli.add_command(launch_command)
cli.add_command(passthrough_command("mcp-server"))
cli.add_command(passthrough_command("shutdown", require_pair=True))


def main(argv: list[str] | None = None) -> int:
    """Run the click CLI and return an exit code."""

    try:
        cli.main(args=argv, prog_name="houmao-srv-ctrl", standalone_mode=False)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    return 0
