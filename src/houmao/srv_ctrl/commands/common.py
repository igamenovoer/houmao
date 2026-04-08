"""Shared helpers for `houmao-mgr`."""

from __future__ import annotations

from collections.abc import Callable
import os
import shutil
import subprocess
from typing import Any, ParamSpec, Sequence, TypeVar, cast

import click

from houmao.agents.managed_launch_force import (
    MANAGED_LAUNCH_FORCE_MODE_KEEP_STALE,
    MANAGED_LAUNCH_FORCE_MODE_VALUES,
)
from houmao.agents.realm_controller.agent_identity import normalize_user_managed_agent_name
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.cao.rest_client import CaoApiError
from houmao.server.client import HoumaoServerClient
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.server.pair_client import (
    PairAuthorityClientProtocol,
    PairAuthorityConnectionError,
    UnsupportedPairAuthorityError,
    resolve_pair_authority_client,
)

_CAO_DEFAULT_PORT = int(os.environ.get("CAO_PORT", "9889"))
_COMPAT_HTTP_TIMEOUT_ENV_VAR = "HOUMAO_COMPAT_HTTP_TIMEOUT_SECONDS"
_COMPAT_CREATE_TIMEOUT_ENV_VAR = "HOUMAO_COMPAT_CREATE_TIMEOUT_SECONDS"
_FC = TypeVar("_FC", bound=Callable[..., Any])
_ParamT = ParamSpec("_ParamT")
_ReturnT = TypeVar("_ReturnT")


class OptionalValueOption(click.Option):
    """Click option that accepts either a bare flag or one explicit value."""

    def __init__(self, *args: object, optional_flag_value: str, **kwargs: object) -> None:
        self.m_optional_flag_value = optional_flag_value
        super().__init__(*cast(Any, args), **cast(Any, kwargs))

    def add_to_parser(self, parser: Any, ctx: click.Context) -> Any:
        """Install parser behavior that fills the default flag value when omitted."""

        result = super().add_to_parser(parser, ctx)
        our_parser = None
        for option_name in (*self.opts, *self.secondary_opts):
            our_parser = parser._long_opt.get(option_name) or parser._short_opt.get(option_name)
            if our_parser is not None:
                break
        if our_parser is None:
            return result

        previous_process = our_parser.process
        our_parser.nargs = 0

        def _parser_process(value: Any, state: Any) -> None:
            """Consume one optional value when present, otherwise use the flag default."""

            next_value: str | None
            if isinstance(value, str):
                next_value = value
            elif value in (None, ()):
                next_value = None
            else:
                next_value = str(value)
            if next_value is None:
                if state.rargs and not state.rargs[0].startswith("-"):
                    next_value = state.rargs.pop(0)
                else:
                    next_value = self.m_optional_flag_value
            previous_process(next_value, state)

        our_parser.process = _parser_process
        return result


def require_cao_executable() -> str:
    """Return the installed `cao` executable or raise."""

    executable = shutil.which("cao")
    if executable is None:
        raise click.ClickException("`cao` is not available on PATH.")
    return executable


def resolve_server_base_url(*, port: int | None = None) -> str:
    """Return the Houmao pair-authority base URL for pair-compatible delegation."""

    return f"http://127.0.0.1:{port or _CAO_DEFAULT_PORT}"


def resolve_pair_client(*, port: int | None = None) -> PairAuthorityClientProtocol:
    """Return one verified pair client for the requested server port."""

    return require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))


def require_supported_houmao_pair(
    *,
    base_url: str,
    timeout_seconds: float | None = None,
    create_timeout_seconds: float | None = None,
) -> PairAuthorityClientProtocol:
    """Ensure the target server is one supported Houmao pair authority."""

    try:
        return resolve_pair_authority_client(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            create_timeout_seconds=create_timeout_seconds,
        ).client
    except (PairAuthorityConnectionError, UnsupportedPairAuthorityError) as exc:
        raise click.ClickException(str(exc)) from exc


def require_houmao_server_pair(
    *,
    base_url: str,
    timeout_seconds: float | None = None,
    create_timeout_seconds: float | None = None,
) -> HoumaoServerClient:
    """Ensure the target pair authority is specifically `houmao-server`."""

    try:
        resolution = resolve_pair_authority_client(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            create_timeout_seconds=create_timeout_seconds,
        )
    except (PairAuthorityConnectionError, UnsupportedPairAuthorityError) as exc:
        raise click.ClickException(str(exc)) from exc
    if resolution.health.houmao_service != "houmao-server":
        raise click.ClickException(
            "This command requires `houmao-server`; `houmao-passive-server` does not expose "
            "the legacy session-backed pair control surface."
        )
    return cast(HoumaoServerClient, resolution.client)


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


def pair_port_option(
    *,
    help_text: str = "Houmao pair authority port to use",
    option_name: str = "--port",
) -> Callable[[_FC], _FC]:
    """Return one shared pair-authority port click option decorator."""

    return click.option(option_name, default=None, type=int, help=help_text)


def compatibility_launch_timeout_options(function: _FC) -> _FC:
    """Attach shared compatibility launch timeout controls."""

    function = click.option(
        "--compat-create-timeout-seconds",
        default=None,
        type=click.FloatRange(min=0.0, min_open=True),
        help=(
            "Compatibility create timeout budget for session-backed launch. "
            f"Falls back to `{_COMPAT_CREATE_TIMEOUT_ENV_VAR}`."
        ),
    )(function)
    function = click.option(
        "--compat-http-timeout-seconds",
        default=None,
        type=click.FloatRange(min=0.0, min_open=True),
        help=(
            "Compatibility request timeout budget for non-create requests during "
            f"session-backed launch. Falls back to `{_COMPAT_HTTP_TIMEOUT_ENV_VAR}`."
        ),
    )(function)
    return function


def resolve_compatibility_launch_timeouts(
    *,
    compat_http_timeout_seconds: float | None,
    compat_create_timeout_seconds: float | None,
) -> tuple[float | None, float | None]:
    """Resolve compatibility launch timeouts from flags or environment."""

    return (
        _resolve_optional_timeout_from_env(
            explicit_value=compat_http_timeout_seconds,
            env_var_name=_COMPAT_HTTP_TIMEOUT_ENV_VAR,
        ),
        _resolve_optional_timeout_from_env(
            explicit_value=compat_create_timeout_seconds,
            env_var_name=_COMPAT_CREATE_TIMEOUT_ENV_VAR,
        ),
    )


def managed_agent_argument(function: _FC) -> _FC:
    """Attach the shared managed-agent positional argument decorator."""

    return click.argument("agent_ref")(function)


def managed_agent_selector_options(function: _FC) -> _FC:
    """Attach the shared managed-agent selector options."""

    function = click.option(
        "--agent-name",
        default=None,
        help=(
            "Raw creation-time friendly managed-agent name. Do not include the `HOUMAO-` prefix."
        ),
    )(function)
    function = click.option(
        "--agent-id",
        default=None,
        help="Authoritative managed-agent id.",
    )(function)
    return function


def overwrite_confirm_option(function: _FC) -> _FC:
    """Attach the shared destructive overwrite confirmation flag."""

    return click.option(
        "--yes",
        is_flag=True,
        help="Confirm destructive overwrite non-interactively when required.",
    )(function)


def managed_launch_force_option(function: _FC) -> _FC:
    """Attach the shared managed-launch force takeover option."""

    return click.option(
        "--force",
        "force_mode",
        cls=OptionalValueOption,
        optional_flag_value=MANAGED_LAUNCH_FORCE_MODE_KEEP_STALE,
        default=None,
        type=click.Choice(MANAGED_LAUNCH_FORCE_MODE_VALUES),
        metavar="[keep-stale|clean]",
        help=(
            "Replace an existing fresh live owner of the resolved managed identity for "
            "this launch. Bare `--force` defaults to `keep-stale`."
        ),
    )(function)


def require_managed_agent_ref(agent_ref: str) -> str:
    """Validate and normalize one managed-agent reference."""

    candidate = agent_ref.strip()
    if not candidate:
        raise click.ClickException("`agent_ref` must not be empty.")
    return candidate


def resolve_managed_agent_selector(
    *,
    agent_id: str | None,
    agent_name: str | None,
    allow_missing: bool = False,
) -> tuple[str | None, str | None]:
    """Validate the shared managed-agent selector contract."""

    normalized_agent_id = _normalize_optional_selector_value(
        option_name="--agent-id",
        value=agent_id,
    )
    normalized_agent_name = _normalize_optional_selector_value(
        option_name="--agent-name",
        value=agent_name,
        raw_managed_agent_name=True,
    )
    if normalized_agent_id is not None and normalized_agent_name is not None:
        raise click.ClickException("Use exactly one of `--agent-id` or `--agent-name`.")
    if not allow_missing and normalized_agent_id is None and normalized_agent_name is None:
        raise click.ClickException("Exactly one of `--agent-id` or `--agent-name` is required.")
    return normalized_agent_id, normalized_agent_name


def pair_request(
    call: Callable[_ParamT, _ReturnT], /, *args: _ParamT.args, **kwargs: _ParamT.kwargs
) -> _ReturnT:
    """Invoke one pair client call and surface API errors as click failures."""

    try:
        return call(*args, **kwargs)
    except CaoApiError as exc:
        raise click.ClickException(exc.detail) from exc


def has_interactive_terminal(*streams: Any) -> bool:
    """Return whether the provided streams appear interactive."""

    resolved_streams = streams or (click.get_text_stream("stdin"), click.get_text_stream("stdout"))
    for stream in resolved_streams:
        isatty = getattr(stream, "isatty", None)
        if isatty is None or not callable(isatty) or not bool(isatty()):
            return False
    return True


def confirm_destructive_action(
    *,
    prompt: str,
    yes: bool,
    non_interactive_message: str,
    cancelled_message: str,
) -> None:
    """Confirm one destructive CLI action or raise an operator-facing error."""

    if yes:
        return
    if not has_interactive_terminal():
        raise click.ClickException(non_interactive_message)
    if not click.confirm(prompt, default=False):
        raise click.ClickException(cancelled_message)


def build_destructive_confirmation_callback(
    *,
    yes: bool,
    non_interactive_message: str,
    cancelled_message: str = "Mailbox registration cancelled.",
) -> Callable[[str], bool]:
    """Build one managed-mailbox replacement confirmation callback."""

    def _confirm(prompt: str) -> bool:
        confirm_destructive_action(
            prompt=prompt,
            yes=yes,
            non_interactive_message=non_interactive_message,
            cancelled_message=cancelled_message,
        )
        return True

    return _confirm


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
    client: PairAuthorityClientProtocol,
    *,
    agent_ref: str,
) -> HoumaoManagedAgentIdentity:
    """Resolve one managed-agent identity through the pair authority."""

    return pair_request(client.get_managed_agent, require_managed_agent_ref(agent_ref))


def _normalize_optional_selector_value(
    *,
    option_name: str,
    value: str | None,
    raw_managed_agent_name: bool = False,
) -> str | None:
    """Normalize one optional selector value or fail clearly."""

    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        raise click.ClickException(f"`{option_name}` must not be empty.")
    if raw_managed_agent_name:
        try:
            return normalize_user_managed_agent_name(stripped)
        except SessionManifestError as exc:
            raise click.ClickException(str(exc)) from exc
    return stripped


def _resolve_optional_timeout_from_env(
    *,
    explicit_value: float | None,
    env_var_name: str,
) -> float | None:
    """Resolve one positive timeout override from CLI or environment."""

    if explicit_value is not None:
        return explicit_value
    raw_value = os.environ.get(env_var_name)
    if raw_value is None:
        return None
    stripped = raw_value.strip()
    if not stripped:
        return None
    try:
        resolved = float(stripped)
    except ValueError as exc:
        raise click.ClickException(f"`{env_var_name}` must be a positive float.") from exc
    if resolved <= 0:
        raise click.ClickException(f"`{env_var_name}` must be > 0.")
    return resolved
