"""Browse the operator manual bundled with the manager."""

from __future__ import annotations

from functools import partial
from importlib.resources import files

import click

from houmao.srv_ctrl.commands.output import OutputContext, emit

_CATALOGS = {
    "start": ("first-agent", "existing-project", "targets"),
    "prepare": ("credentials", "definitions", "launch"),
    "operate": ("inspect", "turns", "lifecycle", "memory"),
    "communicate": ("mail", "mailboxes", "gateway", "wakeups"),
    "coordinate": ("team", "workspaces", "loops"),
}


def _emit_document(path: tuple[str, ...], *resource_path: str) -> None:
    """Read and render a single registered manual document."""

    resource = files("houmao.srv_ctrl").joinpath("assets", "manual", *resource_path)
    try:
        content = resource.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        command = " ".join(("houmao-mgr", *path))
        raise click.ClickException(f"Manual document for `{command}` is unavailable.") from exc

    def render_fancy(_: object) -> None:
        """Render the Markdown through the shared Rich console."""

        from rich.markdown import Markdown

        output: OutputContext = click.get_current_context().obj["output"]
        output.console.print(Markdown(content))

    emit(
        {"path": list(path), "content": content},
        plain_renderer=lambda _: click.echo(content, nl=False),
        fancy_renderer=render_fancy,
    )


@click.pass_context
def _emit_index(ctx: click.Context, path: tuple[str, ...]) -> None:
    """Read the current index when no child command was selected."""

    if ctx.invoked_subcommand is None:
        _emit_document(path, *path[1:], "index.md")


def _build_manual_group() -> click.Group:
    """Register the manual's catalog groups and page commands."""

    manual = click.Group(
        name="manual",
        help="Read the packaged Houmao operator manual.",
        invoke_without_command=True,
        callback=partial(_emit_index, ("manual",)),
    )
    for catalog_name, pages in _CATALOGS.items():
        catalog_path = ("manual", catalog_name)
        catalog = click.Group(
            name=catalog_name,
            help="Browse the pages in this catalog.",
            invoke_without_command=True,
            callback=partial(_emit_index, catalog_path),
        )
        for page_name in pages:
            page = click.Command(
                name=page_name,
                help="Read this manual page.",
                callback=partial(
                    _emit_document, (*catalog_path, page_name), catalog_name, f"{page_name}.md"
                ),
            )
            catalog.add_command(page)
        manual.add_command(catalog)
    return manual


manual_group = _build_manual_group()
