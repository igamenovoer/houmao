"""Top-level click command tree for `houmao-srv-ctrl`."""

from __future__ import annotations

import click

from .cao import cao_group
from .install import install_command
from .launch import launch_command


@click.group(name="houmao-srv-ctrl")
def cli() -> None:
    """Houmao service-management CLI with explicit CAO compatibility namespace."""


cli.add_command(cao_group)
cli.add_command(install_command)
cli.add_command(launch_command)


def main(argv: list[str] | None = None) -> int:
    """Run the click CLI and return an exit code."""

    try:
        cli.main(args=argv, prog_name="houmao-srv-ctrl", standalone_mode=False)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    return 0
