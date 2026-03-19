"""Install command for `houmao-srv-ctrl`."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import click

from houmao.cao.rest_client import CaoApiError
from houmao.server.models import HoumaoInstallAgentProfileRequest

from .common import (
    extract_option_value,
    require_supported_houmao_pair,
    resolve_server_base_url,
    run_passthrough,
)

_DEFAULT_PROVIDER = "kiro_cli"


@click.command(
    name="install",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
)
@click.pass_context
def install_command(ctx: click.Context) -> None:
    """Install an agent profile locally or through a targeted Houmao pair."""

    port_value = extract_option_value(ctx.args, "--port")
    if port_value is None:
        result = run_passthrough(command_name="install", extra_args=ctx.args)
        ctx.exit(result.returncode)

    try:
        port = int(port_value)
    except ValueError as exc:
        raise click.ClickException(f"Invalid `--port` value: `{port_value}`.") from exc

    agent_source, provider = _parse_pair_install_args(ctx.args)
    base_url = resolve_server_base_url(port=port)
    client = require_supported_houmao_pair(base_url=base_url)
    try:
        response = client.install_agent_profile(
            request_model=HoumaoInstallAgentProfileRequest(
                agent_source=agent_source,
                provider=provider,
                working_directory=str(Path.cwd().resolve()),
            )
        )
    except CaoApiError as exc:
        raise click.ClickException(
            f"Pair-owned install failed via `{base_url}`: {exc.detail}"
        ) from exc

    click.echo(response.detail)
    ctx.exit(0)


def _parse_pair_install_args(args: Sequence[str]) -> tuple[str, str]:
    """Parse the supported pair-owned install arguments from raw passthrough args."""

    provider = _DEFAULT_PROVIDER
    agent_source: str | None = None
    index = 0
    while index < len(args):
        value = args[index]
        if value == "--provider":
            if index + 1 >= len(args):
                raise click.ClickException("`--provider` requires a value.")
            provider = args[index + 1]
            index += 2
            continue
        if value.startswith("--provider="):
            provider = value.split("=", 1)[1]
            index += 1
            continue
        if value == "--port":
            if index + 1 >= len(args):
                raise click.ClickException("`--port` requires a value.")
            index += 2
            continue
        if value.startswith("--port="):
            index += 1
            continue
        if value.startswith("-"):
            raise click.ClickException(f"Unsupported option for pair-targeted install: `{value}`.")
        if agent_source is not None:
            raise click.ClickException(
                "Pair-targeted install accepts exactly one `agent_source` argument."
            )
        agent_source = value
        index += 1

    if agent_source is None:
        raise click.ClickException("Missing required `agent_source` argument.")
    if not provider.strip():
        raise click.ClickException("`--provider` must not be empty.")
    return agent_source, provider
