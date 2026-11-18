"""Thin local-gateway CLI that never discovers or opens CCCC credentials."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import cast
from urllib.parse import quote, urlencode

import httpx
from pydantic import JsonValue, ValidationError
from houmao.gateway.client import (
    GatewayClient,
    GatewayHttpError,
    load_gateway_client_binding,
    managed_self_gateway_client,
)

from houmao_cccc.client import _SAFE_CODES
from houmao_cccc.configuration import (
    MAIL_MAX_BYTES,
    MAIL_MAX_LIMIT,
    normalize_endpoint,
)
from houmao_cccc.models import JSON_OBJECT


def _text_arguments(parser: argparse.ArgumentParser) -> None:
    """Declare an explicit text or file input without interpreting shell content."""

    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument("--text")
    text.add_argument("--text-file", help="UTF-8 content file, or - for stdin")


def _mutation_arguments(parser: argparse.ArgumentParser) -> None:
    """Require the selected binding and caller-owned operation identity."""

    parser.add_argument("--binding-id", required=True)
    parser.add_argument("--operation-id", required=True)


def _mail_arguments(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Declare explicit deferred operations and caller-selected consumption bounds."""

    mail = commands.add_parser("mail").add_subparsers(dest="action", required=True)
    for action in ("status", "cursor"):
        mail.add_parser(action)
    for action in ("send", "reply"):
        item = mail.add_parser(action)
        _mutation_arguments(item)
        _text_arguments(item)
        if action == "send":
            item.add_argument("--to", action="append", required=True)
        else:
            item.add_argument("--event-ref", required=True)
    for action in ("peek", "read"):
        item = mail.add_parser(action)
        item.add_argument(
            "--limit", type=int, help="Message cap; uses the gateway's negotiated default"
        )
        item.add_argument(
            "--max-bytes", type=int, help="Response budget; uses the gateway's negotiated default"
        )
        if action == "read":
            _mutation_arguments(item)
            item.add_argument("--expected-cursor", required=True)
    reads = mail.add_parser("reads")
    reads.add_argument("--operation-id", required=True)
    reads.add_argument("--read-ref")


def _parser() -> argparse.ArgumentParser:
    """Build the local HTTP command inventory."""

    parser = argparse.ArgumentParser(prog="houmao-cccc")
    parser.add_argument("--gateway-url", required=True)
    parser.add_argument("--signer-binding", type=Path, help="Private gateway signer binding JSON")
    parser.add_argument("--instance", default="cccc")
    parser.add_argument("--timeout", type=float, default=30.0)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("binding", "capabilities", "members"):
        commands.add_parser(name)
    connection = commands.add_parser("connection").add_subparsers(dest="action", required=True)
    for name in ("connect", "disconnect", "reconnect", "refresh-credentials"):
        item = connection.add_parser(name)
        item.add_argument("--binding-id", required=True)
    chat = commands.add_parser("chat").add_subparsers(dest="action", required=True)
    send = chat.add_parser("send")
    _mutation_arguments(send)
    _text_arguments(send)
    send.add_argument("--to", action="append", required=True)
    send.add_argument("--mode", choices=("send", "request_reply"), default="send")
    reply = chat.add_parser("reply")
    _mutation_arguments(reply)
    _text_arguments(reply)
    reply.add_argument("--event-ref", required=True)
    retry = chat.add_parser("retry")
    retry.add_argument("--binding-id", required=True)
    retry.add_argument("--event-ref", required=True)
    retry.add_argument("--to", action="append", required=True)
    retry.add_argument("--allow-uncertain-retry", action="store_true")
    history = chat.add_parser("history")
    history.add_argument("--limit", type=int, default=50)
    history.add_argument("--cursor")
    history.add_argument("--event-ref")
    deliveries = chat.add_parser("deliveries")
    deliveries.add_argument("--event-ref", required=True)
    deliveries.add_argument("--limit", type=int, default=50)
    _mail_arguments(commands)
    return parser


def _mail_request(arguments: argparse.Namespace) -> tuple[str, str, dict[str, JsonValue]]:
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
    body.update(expected_binding_id=arguments.binding_id, operation_id=arguments.operation_id)
    if action == "read":
        body["expected_cursor"] = arguments.expected_cursor
    else:
        text_file = arguments.text_file
        body["text"] = (
            sys.stdin.read()
            if text_file == "-"
            else Path(text_file).read_text("utf-8")
            if text_file is not None
            else arguments.text
        )
        if action == "send":
            body["to"] = arguments.to
        else:
            body["event_ref"] = arguments.event_ref
    return "POST", "/mail/" + action, body


def _request(arguments: argparse.Namespace) -> tuple[str, str, dict[str, JsonValue]]:
    """Translate one CLI action into its public gateway operation."""

    command = cast(str, arguments.command)
    if command in {"binding", "capabilities", "members"}:
        return "GET", "/" + command, {}
    if command == "mail":
        return _mail_request(arguments)
    action = cast(str, arguments.action)
    if command == "connection":
        return "POST", "/connection/" + action, {"expected_binding_id": arguments.binding_id}
    if action in {"history", "deliveries"}:
        params: dict[str, JsonValue] = {}
        if arguments.event_ref:
            params["event_ref"] = arguments.event_ref
        if not arguments.event_ref or action == "deliveries":
            if not 1 <= arguments.limit <= 100:
                raise ValueError("History limit must be between 1 and 100")
            params["limit"] = arguments.limit
        if getattr(arguments, "cursor", None):
            params["cursor"] = arguments.cursor
        return "GET", "/chat/" + action, params
    body: dict[str, JsonValue] = {"expected_binding_id": arguments.binding_id}
    if action == "retry":
        body.update(
            event_ref=arguments.event_ref,
            actor_ids=arguments.to,
            allow_uncertain_retry=arguments.allow_uncertain_retry,
        )
    else:
        body["operation_id"] = arguments.operation_id
        text_file = arguments.text_file
        text = arguments.text
        if text_file is not None:
            text = sys.stdin.read() if text_file == "-" else Path(text_file).read_text("utf-8")
        body["text"] = text
        if action == "send":
            body.update(to=arguments.to, mode=arguments.mode)
        else:
            body["event_ref"] = arguments.event_ref
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


def run(argv: list[str] | None = None, *, transport: httpx.BaseTransport | None = None) -> int:
    """Run one local operation, printing JSON and a stable exit status."""

    arguments = _parser().parse_args(argv)
    body: dict[str, JsonValue] = {}
    method = "GET"
    request_started = False
    try:
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", arguments.instance):
            raise ValueError("Invalid plugin instance")
        if not 0 < arguments.timeout <= 300:
            raise ValueError("Invalid request timeout")
        method, route, body = _request(arguments)
        path = "/v1/plugins/" + arguments.instance + route
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
            if arguments.command == "mail" and arguments.action == "read":
                invalid["expected_binding_id"] = body["expected_binding_id"]
                invalid["outcome"] = "unknown"
        if request_started and arguments.command == "mail" and arguments.action == "reads":
            invalid.update(operation_id=arguments.operation_id, outcome="unknown")
        print(json.dumps(invalid), file=sys.stderr)
        return 1


def _bound_client(arguments: argparse.Namespace) -> GatewayClient:
    """Select an explicit signer, managed self, or the current open admin path."""

    options = {
        "base_url": arguments.gateway_url,
        "timeout_seconds": arguments.timeout,
    }
    if arguments.signer_binding is not None:
        return GatewayClient(
            **options,
            binding=load_gateway_client_binding(Path.cwd() / arguments.signer_binding),
        )
    if arguments.command != "connection" and os.environ.get("HOUMAO_MANIFEST_PATH"):
        return managed_self_gateway_client(**options)
    return GatewayClient(**options)


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
