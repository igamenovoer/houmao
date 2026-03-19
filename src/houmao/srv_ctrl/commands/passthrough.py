"""Simple passthrough CAO-compatible commands for `houmao-srv-ctrl`."""

from __future__ import annotations

import click

from .common import require_supported_houmao_pair, resolve_server_base_url, run_passthrough


def passthrough_command(name: str, *, require_pair: bool = False) -> click.Command:
    """Build one passthrough click command for `cao <name> ...`."""

    @click.command(
        name=name,
        context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    )
    @click.pass_context
    def _command(ctx: click.Context) -> None:
        if require_pair:
            require_supported_houmao_pair(base_url=resolve_server_base_url())
        result = run_passthrough(command_name=name, extra_args=ctx.args)
        ctx.exit(result.returncode)

    return _command
