"""Click CLI entrypoint for ``houmao-passive-server``."""

from __future__ import annotations

import os
from pathlib import Path

import click
import uvicorn

from houmao.owned_paths import HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.project.overlay import ensure_project_aware_local_roots


@click.group(name="houmao-passive-server")
def cli() -> None:
    """Registry-first passive server for distributed agent coordination."""


@cli.command(name="serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=9891, type=int, show_default=True, help="Bind port.")
@click.option(
    "--runtime-root",
    default=None,
    type=click.Path(path_type=Path),
    help=(
        "Override the Houmao runtime root directory. Defaults to "
        "`HOUMAO_GLOBAL_RUNTIME_DIR` or the active project runtime root."
    ),
)
def serve_command(host: str, port: int, runtime_root: Path | None) -> None:
    """Start the passive server."""

    api_base_url = f"http://{host}:{port}"
    if runtime_root is None and not os.environ.get(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR):
        ensure_project_aware_local_roots(cwd=Path.cwd().resolve())
    kwargs: dict[str, object] = {"api_base_url": api_base_url}
    if runtime_root is not None:
        kwargs["runtime_root"] = runtime_root

    config = PassiveServerConfig(**kwargs)  # type: ignore[arg-type]
    app = create_app(config=config)
    uvicorn.run(app, host=config.public_host, port=config.public_port, log_level="info")


def main(argv: list[str] | None = None) -> int:
    """Run the click CLI and return an exit code."""

    try:
        cli.main(args=argv, prog_name="houmao-passive-server", standalone_mode=False)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 1
    return 0
