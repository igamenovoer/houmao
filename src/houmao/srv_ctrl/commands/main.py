"""Top-level click command tree for `houmao-mgr`."""

from __future__ import annotations

import click

from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.version import get_version

from .admin import admin_group
from .agents import agents_group
from .brains import brains_group
from .credentials import credentials_group
from .mailbox import mailbox_group
from .output import OutputContext, output_options, resolve_print_style
from .project import project_group
from .server import server_group
from .system_skills import system_skills_group

_HOUMAO_DOCS_URL = "https://igamenovoer.github.io/houmao/"
_ROOT_HELP_EPILOG = f"More detailed docs: {_HOUMAO_DOCS_URL}"

@click.group(name="houmao-mgr", invoke_without_command=True, epilog=_ROOT_HELP_EPILOG)
@click.version_option(version=get_version())
@output_options
@click.pass_context
def cli(ctx: click.Context, print_style: str | None) -> None:
    """Houmao pair CLI with native server and managed-agent command families."""

    ctx.ensure_object(dict)
    ctx.obj["output"] = OutputContext(style=resolve_print_style(print_style))
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


cli.add_command(admin_group)
cli.add_command(agents_group)
cli.add_command(brains_group)
cli.add_command(credentials_group)
cli.add_command(mailbox_group)
cli.add_command(project_group)
cli.add_command(server_group)
cli.add_command(system_skills_group)


def main(argv: list[str] | None = None) -> int:
    """Run the click CLI and return an exit code."""

    try:
        cli.main(args=argv, prog_name="houmao-mgr", standalone_mode=False)
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
    except SessionManifestError as exc:
        rendered = click.ClickException(str(exc))
        rendered.show()
        return rendered.exit_code
    except click.Abort:
        click.echo("Aborted!", err=True)
        return 1
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    return 0
