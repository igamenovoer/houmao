"""Canonical permissions for the AG-UI routes and their resolved destinations."""

from __future__ import annotations

from hashlib import sha256
import json
import re

from houmao.gateway._access_storage import GatewayAccessError
from houmao.gateway.authorization_models import Permission

AG_UI = "ag-ui"
SINK = "ag-ui:sink"
OBSERVE = "ag-ui.output.read"
SUBMIT = "ag-ui.input.submit"
PUBLISH = "ag-ui.event.publish"
CLOSE = "ag-ui.connection.close"
UPDATE_DESTINATION = "ag-ui.destination.update"

_RESOURCE = re.compile(r"ag-ui:(thread|run|thread-run|connection):[0-9a-f]{64}")
_ACTIONS = {
    "thread": frozenset({OBSERVE, SUBMIT, PUBLISH, UPDATE_DESTINATION}),
    "run": frozenset({PUBLISH}),
    "thread-run": frozenset({PUBLISH}),
    "connection": frozenset({PUBLISH, CLOSE}),
}


def thread_resource(thread_id: str) -> str:
    """Name one exact AG-UI thread."""

    return _resource("thread", thread_id)


def connection_resource(connection_id: str) -> str:
    """Name one exact AG-UI connection."""

    return _resource("connection", connection_id)


def publish_resource(
    *, thread_id: str | None, run_id: str | None, connection_id: str | None
) -> str:
    """Name the actual destination selected by AG-UI event routing."""

    if connection_id is not None:
        return connection_resource(connection_id)
    if thread_id is not None and run_id is not None:
        _utf8(thread_id)
        _utf8(run_id)
        pair = json.dumps([thread_id, run_id], ensure_ascii=True, separators=(",", ":"))
        return _resource("thread-run", pair)
    if thread_id is not None:
        return thread_resource(thread_id)
    if run_id is not None:
        return _resource("run", run_id)
    return SINK


def supports_ag_ui_permission(permission: Permission) -> bool:
    """Recognize only the declared AG-UI destinations and compatible actions."""

    if permission.resource == AG_UI:
        return permission.action == UPDATE_DESTINATION
    if permission.resource == SINK:
        return permission.action == PUBLISH
    match = _RESOURCE.fullmatch(permission.resource)
    return match is not None and permission.action in _ACTIONS[match.group(1)]


def _resource(kind: str, value: str) -> str:
    """Hash identifiers so Unicode and delimiters cannot alter resource structure."""

    return f"ag-ui:{kind}:{sha256(_utf8(value)).hexdigest()}"


def _utf8(value: str) -> bytes:
    """Reject malformed Unicode in a selected destination."""

    try:
        return value.encode("utf-8")
    except UnicodeEncodeError:
        raise GatewayAccessError(422, "invalid_ag_ui_destination") from None
