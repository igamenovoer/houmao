"""Agent-facing CCCC commands through the verified gateway or a selected Actor."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import re
import sys
from typing import cast
from urllib.parse import quote, unquote, urlencode, urlsplit

import httpx
from pydantic import JsonValue, ValidationError
from houmao.gateway.access import validate_gateway_base_url
from houmao.gateway.client import (
    GatewayClient,
    GatewayHttpError,
    load_gateway_client_binding,
    managed_self_agent_id,
    managed_self_gateway_client,
)

from houmao_cccc.client import MAX_BATCH_BYTES, MAX_BATCH_MESSAGES, ProviderError, _SAFE_CODES
from houmao_cccc.configuration import (
    MAIL_MAX_BYTES,
    MAIL_MAX_LIMIT,
    CcccConfiguration,
    normalize_endpoint,
)
from houmao_cccc.direct import invoke_direct, load_direct_profile
from houmao_cccc.models import JSON_OBJECT


_INSTANCE_PATTERN = r"[a-z][a-z0-9-]{0,62}"
_PLUGIN_ROUTE = re.compile(rf"^/v1/plugins/{_INSTANCE_PATTERN}(?:/|$)")
_MESSAGE_HANDLE = re.compile(rf"msg_(?P<instance>{_INSTANCE_PATTERN})\.[A-Za-z0-9_-]{{1,128}}")
_GATEWAY_URL_GUIDANCE = (
    "Use the gateway base URL, such as http://127.0.0.1:43000, with --gateway-url. "
    "Select the plugin with --instance."
)


class _GatewaySelectionError(ValueError):
    """Carry a fixed diagnostic for a failure before any gateway request."""

    def __init__(self, error_code: str, message: str) -> None:
        """Store a safe diagnostic for CLI output."""

        super().__init__(message)
        self.m_error_code: str = error_code


def _text_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare an explicit text or file input without interpreting shell content."""

    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument("--text")
    text.add_argument("--text-file", help="UTF-8 content file, or - for stdin")


def _mutation_arguments(parser: argparse.ArgumentParser, *, binding: bool = False) -> None:
    """Require caller-owned operation identity and optionally accept a gateway binding."""

    if binding:
        parser.add_argument("--binding-id", help="Current CCCC binding in gateway mode")
    parser.add_argument("--operation-id", required=True)


def _target_arguments(parser: argparse.ArgumentParser) -> None:
    """Select a gateway-signed reference or a native direct event ID."""

    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--event-ref")
    target.add_argument("--event-id")


def _mail_arguments(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Declare explicit deferred operations and caller-selected consumption bounds."""

    mail = commands.add_parser("mail").add_subparsers(dest="action", required=True)
    for action in ("status", "cursor"):
        mail.add_parser(action)
    for action in ("send", "reply"):
        item = mail.add_parser(action)
        _mutation_arguments(item, binding=True)
        _text_arguments(item)
        if action == "send":
            item.add_argument("--to", action="append", required=True)
        else:
            _target_arguments(item)
    for action in ("peek", "read"):
        item = mail.add_parser(action)
        item.add_argument(
            "--limit", type=int, help="Message cap; uses the gateway's negotiated default"
        )
        item.add_argument(
            "--max-bytes", type=int, help="Response budget; uses the gateway's negotiated default"
        )
        if action == "read":
            _mutation_arguments(item, binding=True)
            item.add_argument("--expected-cursor", required=True)
    reads = mail.add_parser("reads")
    reads.add_argument("--operation-id", required=True)
    reads.add_argument("--read-ref")


def _parser() -> argparse.ArgumentParser:
    """Build the common command inventory and explicit connection selectors."""

    parser = argparse.ArgumentParser(prog="houmao-cccc")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--gateway-url",
        help="Gateway base URL, including any configured HTTPS proxy prefix. "
        "Omit to use verified managed self. Select the plugin with --instance.",
    )
    selection.add_argument("--direct-profile", type=Path, help="Private CCCC Actor profile JSON")
    parser.add_argument("--signer-binding", type=Path, help="Private gateway signer binding JSON")
    parser.add_argument("--agent-id", help="Expected profile owner for an unmanaged direct caller")
    parser.add_argument("--instance", help="Gateway plugin instance, default cccc")
    parser.add_argument("--timeout", type=float, default=30.0)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("binding", "capabilities", "discovery", "members"):
        commands.add_parser(name)
    connection = commands.add_parser("connection").add_subparsers(dest="action", required=True)
    for name in ("connect", "disconnect", "reconnect", "refresh-credentials"):
        item = connection.add_parser(name)
        item.add_argument("--binding-id", required=True)
    chat = commands.add_parser("chat").add_subparsers(dest="action", required=True)
    send = chat.add_parser("send")
    _mutation_arguments(send)
    _text_arguments(send)
    send.add_argument("--connection-token", help="Gateway connection token from members")
    send.add_argument("--to", action="append", required=True)
    send.add_argument("--mode", choices=("send", "request_reply"), default="send")
    reply = chat.add_parser("reply")
    _mutation_arguments(reply)
    _text_arguments(reply)
    target = reply.add_mutually_exclusive_group(required=True)
    target.add_argument("--handle", help="Short gateway message handle")
    target.add_argument("--event-ref", help="Actor-scoped CCCC reference from a direct pull")
    retry = chat.add_parser("retry")
    retry.add_argument("--binding-id", help="Current CCCC binding in gateway mode")
    _target_arguments(retry)
    retry.add_argument("--to", action="append", required=True)
    retry.add_argument("--allow-uncertain-retry", action="store_true")
    history = chat.add_parser("history")
    history.add_argument("--limit", type=int, default=50)
    history.add_argument("--cursor")
    history_target = history.add_mutually_exclusive_group()
    history_target.add_argument("--event-ref")
    history_target.add_argument("--event-id")
    details = chat.add_parser("details")
    details.add_argument("--handle", required=True)
    deliveries = chat.add_parser(
        "deliveries",
        description="List delivery attempts for one event, newest first by creation. "
        "The response sets has_more when older attempts were omitted.",
    )
    _target_arguments(deliveries)
    deliveries.add_argument(
        "--limit", type=int, default=50, help="Return up to this many newest attempts (1 to 100)."
    )
    pull = chat.add_parser("pull", help="Claim one direct pull batch")
    pull.add_argument("--limit", type=int)
    pull.add_argument("--max-bytes", type=int)
    ack = chat.add_parser("ack", help="Acknowledge the receipt from a direct pull")
    ack.add_argument("--receipt", required=True)
    _mail_arguments(commands)
    return parser


def _gateway_binding(arguments: argparse.Namespace) -> str:
    """Require a current binding for gateway operations with explicit scope checks."""

    binding = cast(str | None, arguments.binding_id)
    if not binding:
        raise ValueError("Gateway mode requires the current --binding-id")
    return binding


def _text(arguments: argparse.Namespace) -> str:
    """Read caller text exactly once from the selected source."""

    source = cast(str | None, arguments.text_file)
    if source == "-":
        return sys.stdin.read()
    if source is not None:
        return Path(source).read_text("utf-8")
    return cast(str, arguments.text)


def _event_target(arguments: argparse.Namespace, direct: bool) -> dict[str, JsonValue]:
    """Use the exact target form supported by the selected connection."""

    if direct and not arguments.event_id:
        raise ValueError("Direct mode requires a native --event-id for this operation")
    if not direct and not arguments.event_ref:
        raise ValueError("Gateway mode requires a scoped --event-ref for this operation")
    if direct:
        return {"event_id": arguments.event_id}
    return {"event_ref": arguments.event_ref}


def _mail_request(
    arguments: argparse.Namespace, *, direct: bool
) -> tuple[str, str, dict[str, JsonValue]]:
    """Build one explicit deferred request without generating an operation identity."""

    action = cast(str, arguments.action)
    if action in {"status", "cursor"}:
        return "GET", "/mail/" + action, {}
    if action in {"send", "reply", "read", "reads"}:
        operation_id = cast(str, arguments.operation_id)
        if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", operation_id) or operation_id in {".", ".."}:
            raise ValueError("Invalid Mail operation identity")
    if action == "reads":
        params: dict[str, JsonValue] = {}
        if arguments.read_ref:
            if direct:
                raise ValueError("Direct Mail receipts select only --operation-id")
            params["read_ref"] = arguments.read_ref
        return "GET", "/mail/reads/" + quote(operation_id, safe=""), params
    body: dict[str, JsonValue] = {}
    if action in {"peek", "read"}:
        if arguments.limit is not None and not 1 <= arguments.limit <= MAIL_MAX_LIMIT:
            raise ValueError("Mail message limit must be between 1 and 200")
        if arguments.max_bytes is not None and not 1024 <= arguments.max_bytes <= MAIL_MAX_BYTES:
            raise ValueError("Mail byte limit must be between 1024 and 1048576")
        if arguments.limit is not None:
            body["limit"] = arguments.limit
        if arguments.max_bytes is not None:
            body["max_bytes"] = arguments.max_bytes
        if action == "peek":
            return "GET", "/mail/peek", body
    if direct:
        if arguments.binding_id is not None:
            raise ValueError("Direct Mail uses the selected Actor profile")
    else:
        body["expected_binding_id"] = _gateway_binding(arguments)
    body["operation_id"] = arguments.operation_id
    if action == "read":
        body["expected_cursor"] = arguments.expected_cursor
    else:
        body["text"] = _text(arguments)
        if action == "send":
            body["to"] = arguments.to
        else:
            body.update(_event_target(arguments, direct))
    return "POST", "/mail/" + action, body


def _request(
    arguments: argparse.Namespace, *, direct: bool = False
) -> tuple[str, str, dict[str, JsonValue]]:
    """Translate a CLI action into the selected connection's operation and fields."""

    command = cast(str, arguments.command)
    if command in {"binding", "capabilities", "discovery", "members"}:
        return "GET", "/" + command, {}
    if command == "mail":
        return _mail_request(arguments, direct=direct)
    action = cast(str, arguments.action)
    if command == "connection":
        if direct:
            raise ValueError("Connection management requires the gateway")
        return "POST", "/connection/" + action, {"expected_binding_id": arguments.binding_id}
    if action == "pull":
        if not direct:
            raise ValueError("On-demand pull requires an explicit --direct-profile")
        selected: dict[str, JsonValue] = {}
        if arguments.limit is not None:
            if not 1 <= arguments.limit <= MAX_BATCH_MESSAGES:
                raise ValueError("Invalid pull message limit")
            selected["limit"] = arguments.limit
        if arguments.max_bytes is not None:
            if not 1 <= arguments.max_bytes <= MAX_BATCH_BYTES:
                raise ValueError("Invalid pull byte limit")
            selected["max_bytes"] = arguments.max_bytes
        return "POST", "/chat/pull", selected
    if action == "ack":
        if not direct or not 1 <= len(arguments.receipt) <= 16384:
            raise ValueError("Acknowledge a direct pull using its receipt")
        return "POST", "/chat/ack", {"receipt": arguments.receipt}
    if action == "details":
        if direct:
            raise ValueError("Inspect a direct message with chat history --event-ref")
        return "GET", "/messages/" + quote(arguments.handle, safe=""), {}
    if action in {"history", "deliveries"}:
        if action == "deliveries":
            params = _event_target(arguments, direct)
        else:
            params = {
                key: value
                for key, value in (
                    ("event_ref", arguments.event_ref),
                    ("event_id", arguments.event_id),
                )
                if value is not None
            }
        if not params or action == "deliveries":
            if not 1 <= arguments.limit <= 100:
                raise ValueError("History limit must be between 1 and 100")
            params["limit"] = arguments.limit
        if getattr(arguments, "cursor", None):
            if arguments.event_ref or arguments.event_id:
                raise ValueError("Exact history selection cannot include a cursor")
            params["before_event_id" if direct else "cursor"] = arguments.cursor
        return "GET", "/chat/" + action, params
    body: dict[str, JsonValue]
    if action == "retry":
        body = _event_target(arguments, direct)
        if direct:
            if arguments.binding_id is not None:
                raise ValueError("Direct retry uses the selected Actor profile")
        else:
            body["expected_binding_id"] = _gateway_binding(arguments)
        body.update(
            actor_ids=arguments.to,
            allow_uncertain_retry=arguments.allow_uncertain_retry,
        )
    else:
        body = {"operation_id": arguments.operation_id, "text": _text(arguments)}
        if action == "send":
            if direct and arguments.connection_token is not None:
                raise ValueError("Direct send uses the selected Actor profile")
            if not direct:
                if not arguments.connection_token:
                    raise ValueError("Gateway send requires --connection-token from members")
                body["connection_token"] = arguments.connection_token
            body.update(to=arguments.to, mode=arguments.mode)
        else:
            name = "event_ref" if direct else "handle"
            target = getattr(arguments, name)
            if not target:
                raise ValueError("Select a reply target for the chosen connection")
            body[name] = target
    return "POST", "/chat/" + action, body


def _failure_detail(
    raw: dict[str, JsonValue], status: int, operation_id: JsonValue = None
) -> dict[str, JsonValue]:
    """Preserve allowlisted uncertainty metadata without echoing error bodies."""

    detail = raw.get("detail", raw.get("error", raw))
    result: dict[str, JsonValue] = {"error_code": "gateway_request_failed", "status": status}
    if isinstance(detail, dict):
        code = detail.get("error_code", detail.get("code"))
        known = _SAFE_CODES | {
            "binding_conflict",
            "connection_conflict",
            "stale_connection_token",
            "message_handle_stale",
            "reference_scope_error",
            "unsupported_query",
            "plugin_unavailable",
            "connection_retired",
            "provider_unavailable",
            "provider_error",
            "dispatch_timeout",
            "invalid_provider_response",
            "incompatible_history_parameters",
            "receiver_incompatible",
        }
        if isinstance(code, str) and code in known:
            result["error_code"] = code
            if code == "message_handle_stale":
                result["guidance"] = "Select the exact message in authorized CCCC chat history."
        if isinstance(detail.get("retryable"), bool):
            result["retryable"] = detail["retryable"]
        outcome = detail.get("dispatch_outcome")
        if isinstance(outcome, str) and outcome in {"not_sent", "unknown"}:
            result["dispatch_outcome"] = outcome
        read_ref = detail.get("read_ref")
        if (
            isinstance(read_ref, str)
            and len(read_ref) <= 16384
            and re.fullmatch(r"cccc1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", read_ref)
        ):
            result["read_ref"] = read_ref
    if isinstance(operation_id, str):
        result["operation_id"] = operation_id
    return result


def run(
    argv: list[str] | None = None,
    *,
    transport: httpx.BaseTransport | None = None,
    provider_transport: httpx.AsyncBaseTransport | None = None,
) -> int:
    """Run one selected operation, printing JSON and a stable exit status."""

    arguments = _parser().parse_args(argv)
    body: dict[str, JsonValue] = {}
    method = "GET"
    request_started = False
    try:
        if not 0 < arguments.timeout <= 300:
            raise ValueError("Invalid request timeout")
        if arguments.direct_profile is not None:
            if arguments.signer_binding is not None or arguments.instance is not None:
                raise ValueError("Direct mode uses only its selected Actor profile")
            _, route, body = _request(arguments, direct=True)
            configuration, token = _direct_profile(arguments)
            result = asyncio.run(
                invoke_direct(configuration, token, route, body, transport=provider_transport)
            )
            print(json.dumps(result, ensure_ascii=True, allow_nan=False))
            return 0
        if arguments.agent_id is not None:
            raise ValueError("--agent-id selects a direct profile owner")
        instance = _plugin_instance(arguments)
        method, route, body = _request(arguments)
        path = "/v1/plugins/" + instance + route
        if transport is None:
            client = _bound_client(arguments)
            request_started = True
            status, raw = _shared_request(client, method, path, body)
        else:
            request_started = True
            status, raw = _injected_request(transport, arguments, method, path, body)
        if not 200 <= status < 300:
            failure = _failure_detail(
                raw, status, body.get("operation_id", getattr(arguments, "operation_id", None))
            )
            if method == "POST":
                if isinstance(body.get("expected_binding_id"), str):
                    failure["expected_binding_id"] = body["expected_binding_id"]
                if isinstance(body.get("connection_token"), str):
                    failure["connection_token"] = body["connection_token"]
                if (status >= 500 or status == 408) and "dispatch_outcome" not in failure:
                    failure["dispatch_outcome"] = "unknown"
            if arguments.command == "mail" and arguments.action == "read":
                failure["expected_binding_id"] = body["expected_binding_id"]
                if failure.get("dispatch_outcome") == "unknown":
                    failure["outcome"] = "unknown"
            if arguments.command == "mail" and arguments.action == "reads":
                failure["outcome"] = "unknown"
            print(json.dumps(failure))
            return 1
        result = JSON_OBJECT.validate_python(raw, strict=True)
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except _GatewaySelectionError as exc:
        print(json.dumps({"error_code": exc.m_error_code, "message": str(exc)}), file=sys.stderr)
        return 1
    except ProviderError as exc:
        failure = _failure_detail(
            exc.to_detail(),
            exc.status_code,
            body.get("operation_id", getattr(arguments, "operation_id", None)),
        )
        failure["error_code"] = exc.code
        if arguments.command == "mail" and (
            arguments.action == "reads" or (arguments.action == "read" and exc.outcome == "unknown")
        ):
            failure["outcome"] = "unknown"
        print(json.dumps(failure), file=sys.stderr)
        return 1
    except (httpx.HTTPError, GatewayHttpError):
        connection_failure: dict[str, JsonValue] = {
            "error_code": "gateway_unavailable",
            "retryable": True,
            "dispatch_outcome": "unknown" if method == "POST" else "not_sent",
        }
        operation_id = body.get("operation_id", getattr(arguments, "operation_id", None))
        if isinstance(operation_id, str):
            connection_failure["operation_id"] = operation_id
        if method == "POST" and isinstance(body.get("expected_binding_id"), str):
            connection_failure["expected_binding_id"] = body["expected_binding_id"]
        if method == "POST" and isinstance(body.get("connection_token"), str):
            connection_failure["connection_token"] = body["connection_token"]
        if arguments.command == "mail" and arguments.action == "read" and body:
            connection_failure["expected_binding_id"] = body["expected_binding_id"]
            connection_failure["outcome"] = "unknown"
        if arguments.command == "mail" and arguments.action == "reads":
            connection_failure["outcome"] = "unknown"
        print(json.dumps(connection_failure), file=sys.stderr)
        return 1
    except (ValueError, OSError, ValidationError):
        invalid: dict[str, JsonValue] = {"error_code": "cccc_cli_failed"}
        if request_started and method == "POST":
            invalid.update(
                error_code="gateway_response_invalid", retryable=False, dispatch_outcome="unknown"
            )
            if isinstance(body.get("operation_id"), str):
                invalid["operation_id"] = body["operation_id"]
            if isinstance(body.get("expected_binding_id"), str):
                invalid["expected_binding_id"] = body["expected_binding_id"]
            if isinstance(body.get("connection_token"), str):
                invalid["connection_token"] = body["connection_token"]
            if arguments.command == "mail" and arguments.action == "read":
                invalid["expected_binding_id"] = body["expected_binding_id"]
                invalid["outcome"] = "unknown"
        if request_started and arguments.command == "mail" and arguments.action == "reads":
            invalid.update(operation_id=arguments.operation_id, outcome="unknown")
        print(json.dumps(invalid), file=sys.stderr)
        return 1


def _plugin_instance(arguments: argparse.Namespace) -> str:
    """Route handle commands to the exact instance selected by the notification."""

    explicit = cast(str | None, arguments.instance)
    if explicit is not None and not re.fullmatch(_INSTANCE_PATTERN, explicit):
        raise ValueError("Invalid plugin instance")
    handle = cast(str | None, getattr(arguments, "handle", None))
    if handle is None:
        return explicit or "cccc"
    match = _MESSAGE_HANDLE.fullmatch(handle)
    if match is None:
        raise _GatewaySelectionError("invalid_message_handle", "Use the exact message handle.")
    selected = match.group("instance")
    if explicit is not None and explicit != selected:
        raise _GatewaySelectionError(
            "handle_instance_mismatch", "Use the message handle with its own CCCC plugin instance."
        )
    return selected


def _direct_profile(arguments: argparse.Namespace) -> tuple[CcccConfiguration, str]:
    """Select a local owner and validate the explicitly named profile before CCCC access."""

    owner = cast(str | None, arguments.agent_id)
    if os.environ.get("HOUMAO_MANIFEST_PATH"):
        try:
            verified = managed_self_agent_id()
        except ValueError:
            raise _GatewaySelectionError(
                "managed_self_authority_unavailable", "Verify the current managed generation."
            ) from None
        if owner is not None and owner != verified:
            raise _GatewaySelectionError(
                "direct_owner_mismatch", "Select the current managed agent's private CCCC profile."
            )
        owner = verified
    if not owner:
        raise _GatewaySelectionError(
            "direct_owner_required", "Supply the selected profile's owner with --agent-id."
        )
    try:
        return load_direct_profile(
            Path.cwd() / arguments.direct_profile, agent_id=owner, timeout_seconds=arguments.timeout
        )
    except ValueError:
        raise _GatewaySelectionError(
            "invalid_direct_profile", "Select a valid owner-bound private CCCC profile."
        ) from None


def _bound_client(arguments: argparse.Namespace) -> GatewayClient:
    """Select an explicit signer, managed self, or the current open admin path."""

    selector = cast(str | None, arguments.gateway_url)
    base_url = None
    if selector is not None:
        try:
            base_url = validate_gateway_base_url(selector)
        except ValueError:
            raise _GatewaySelectionError("invalid_gateway_url", _GATEWAY_URL_GUIDANCE) from None
    binding = (
        load_gateway_client_binding(Path.cwd() / arguments.signer_binding)
        if arguments.signer_binding is not None
        else None
    )
    if base_url is None and binding is not None:
        base_url = binding.base_url
    if base_url is not None:
        _reject_plugin_route(base_url, binding.base_url if binding else None)
    if base_url is None or (
        binding is None
        and arguments.command != "connection"
        and os.environ.get("HOUMAO_MANIFEST_PATH")
    ):
        try:
            return managed_self_gateway_client(base_url=base_url, timeout_seconds=arguments.timeout)
        except ValueError:
            raise _GatewaySelectionError(
                "managed_self_authority_unavailable",
                "Verify the current managed generation and its owning gateway base URL. "
                "For direct CCCC use, select an Actor profile with --direct-profile.",
            ) from None
    return GatewayClient(base_url=base_url, timeout_seconds=arguments.timeout, binding=binding)


def _reject_plugin_route(base_url: str, signer_base_url: str | None) -> None:
    """Recognize a pasted plugin route while honoring an exact signer binding."""

    if base_url == signer_base_url:
        return
    endpoint = urlsplit(base_url)
    local_path = endpoint.path if endpoint.scheme == "http" else ""
    signer_suffix = base_url.removeprefix(signer_base_url) if signer_base_url else ""
    if any(_PLUGIN_ROUTE.match(unquote(path)) for path in (local_path, signer_suffix)):
        raise _GatewaySelectionError("invalid_gateway_url", _GATEWAY_URL_GUIDANCE)


def _shared_request(
    client: GatewayClient, method: str, path: str, body: dict[str, JsonValue]
) -> tuple[int, dict[str, JsonValue]]:
    """Send exact bound plugin input and retain typed provider outcomes."""

    if method == "GET" and body:
        path += "?" + urlencode(cast(dict[str, str], body))
    try:
        result = client.request_plugin_json(method, path, body=body if method != "GET" else None)
    except GatewayHttpError as exc:
        if exc.status_code is None:
            raise
        if 300 <= exc.status_code < 400:
            raise ValueError("Gateway redirect refused.") from None
        try:
            detail = json.loads(exc.detail)
        except ValueError:
            detail = {}
        return exc.status_code, {"detail": detail}
    return 200, JSON_OBJECT.validate_python(result, strict=True)


def _injected_request(
    transport: httpx.BaseTransport,
    arguments: argparse.Namespace,
    method: str,
    path: str,
    body: dict[str, JsonValue],
) -> tuple[int, dict[str, JsonValue]]:
    """Use an explicitly injected transport for isolated CLI contract tests."""

    endpoint = normalize_endpoint(arguments.gateway_url, loopback_only=True)
    with httpx.Client(
        timeout=arguments.timeout, trust_env=False, follow_redirects=False, transport=transport
    ) as client:
        with client.stream(
            method,
            endpoint + path,
            params=cast(dict[str, str], body) if method == "GET" else None,
            json=body if method != "GET" else None,
        ) as response:
            result_bytes = bytearray()
            for chunk in response.iter_bytes():
                if len(result_bytes) + len(chunk) > 1048576:
                    raise ValueError("Gateway response exceeds the supported limit")
                result_bytes.extend(chunk)
            if response.is_redirect:
                raise ValueError("Gateway redirect refused")
            try:
                raw = JSON_OBJECT.validate_python(json.loads(result_bytes), strict=True)
            except (ValueError, ValidationError):
                if response.is_success:
                    raise
                raw = {}
            return response.status_code, raw


def main() -> None:
    """Execute the installed CLI entry point."""

    raise SystemExit(run())
