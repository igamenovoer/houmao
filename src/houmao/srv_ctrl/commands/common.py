"""Shared helpers for `houmao-mgr`."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import shutil
import subprocess
from typing import ParamSpec, Sequence, TypeVar

import click
from pydantic import BaseModel

from houmao.cao.rest_client import CaoApiError
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.server.client import HoumaoServerClient

_CAO_DEFAULT_PORT = int(os.environ.get("CAO_PORT", "9889"))
_ParamT = ParamSpec("_ParamT")
_ReturnT = TypeVar("_ReturnT")


def require_cao_executable() -> str:
    """Return the installed `cao` executable or raise."""

    executable = shutil.which("cao")
    if executable is None:
        raise click.ClickException("`cao` is not available on PATH.")
    return executable


def resolve_server_base_url(*, port: int | None = None) -> str:
    """Return the Houmao server base URL for CAO-compatible delegation."""

    return f"http://127.0.0.1:{port or _CAO_DEFAULT_PORT}"


def resolve_pair_client(*, port: int | None = None) -> HoumaoServerClient:
    """Return one verified pair client for the requested server port."""

    return require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))


def require_supported_houmao_pair(*, base_url: str) -> HoumaoServerClient:
    """Ensure the target server is a real `houmao-server`."""

    client = HoumaoServerClient(base_url)
    try:
        health = client.health_extended()
    except Exception as exc:
        raise click.ClickException(f"Failed to reach `houmao-server` at {base_url}: {exc}") from exc
    if health.houmao_service != "houmao-server":
        raise click.ClickException(
            "The supported replacement is `houmao-server + houmao-mgr`; "
            "mixed usage with raw `cao-server` is unsupported."
        )
    return client


def run_passthrough(
    *,
    command_name: str,
    extra_args: Sequence[str],
) -> subprocess.CompletedProcess[bytes]:
    """Delegate one CAO-compatible command to the installed `cao` executable."""

    executable = require_cao_executable()
    return subprocess.run([executable, command_name, *extra_args], check=False)


def extract_option_value(args: Sequence[str], option_name: str) -> str | None:
    """Extract one CLI option value from passthrough args."""

    prefix = f"{option_name}="
    for index, value in enumerate(args):
        if value == option_name:
            if index + 1 < len(args):
                return args[index + 1]
            return None
        if value.startswith(prefix):
            return value[len(prefix) :]
    return None


def has_flag(args: Sequence[str], flag_name: str) -> bool:
    """Return whether a passthrough flag is present."""

    return any(value == flag_name for value in args)


def pair_port_option(*, help_text: str = "Houmao server port to use") -> Callable:
    """Return the shared `--port` click option decorator."""

    return click.option("--port", default=None, type=int, help=help_text)


def managed_agent_argument(function: Callable) -> Callable:
    """Attach the shared managed-agent positional argument decorator."""

    return click.argument("agent_ref")(function)


def require_managed_agent_ref(agent_ref: str) -> str:
    """Validate and normalize one managed-agent reference."""

    candidate = agent_ref.strip()
    if not candidate:
        raise click.ClickException("`agent_ref` must not be empty.")
    return candidate


def emit_json(payload: object) -> None:
    """Render one model or JSON-compatible payload with stable formatting."""

    normalized: object
    if isinstance(payload, BaseModel):
        normalized = payload.model_dump(mode="json")
    else:
        normalized = payload
    click.echo(json.dumps(normalized, indent=2, sort_keys=True))


def pair_request(
    call: Callable[_ParamT, _ReturnT], /, *args: _ParamT.args, **kwargs: _ParamT.kwargs
) -> _ReturnT:
    """Invoke one pair client call and surface API errors as click failures."""

    try:
        return call(*args, **kwargs)
    except CaoApiError as exc:
        raise click.ClickException(exc.detail) from exc


def resolve_prompt_text(*, prompt: str | None) -> str:
    """Resolve prompt text from `--prompt` or piped stdin."""

    if prompt is not None:
        value = prompt.strip()
        if not value:
            raise click.ClickException("`--prompt` must not be empty.")
        return value
    stdin = click.get_text_stream("stdin")
    if stdin.isatty():
        raise click.ClickException("Provide `--prompt` or pipe prompt text on stdin.")
    value = stdin.read()
    if not value.strip():
        raise click.ClickException("Prompt input must not be empty.")
    return value


def resolve_body_text(*, body_content: str | None, body_file: str | None) -> str:
    """Resolve body content from text, file input, or piped stdin."""

    if body_content is not None and body_file is not None:
        raise click.ClickException("Use either `--body-content` or `--body-file`, not both.")
    if body_content is not None:
        if "\x00" in body_content:
            raise click.ClickException("`--body-content` must not contain NUL bytes.")
        return body_content
    if body_file is not None:
        try:
            value = open(body_file, encoding="utf-8").read()
        except OSError as exc:
            raise click.ClickException(f"Failed to read `--body-file`: {exc}") from exc
        if "\x00" in value:
            raise click.ClickException("`--body-file` must not contain NUL bytes.")
        return value
    stdin = click.get_text_stream("stdin")
    if stdin.isatty():
        raise click.ClickException(
            "Provide `--body-content`, `--body-file`, or pipe body text on stdin."
        )
    value = stdin.read()
    if "\x00" in value:
        raise click.ClickException("Body input must not contain NUL bytes.")
    return value


def resolve_managed_agent_identity(
    client: HoumaoServerClient,
    *,
    agent_ref: str,
) -> HoumaoManagedAgentIdentity:
    """Resolve one managed-agent identity through the pair authority."""

    return pair_request(client.get_managed_agent, require_managed_agent_ref(agent_ref))
