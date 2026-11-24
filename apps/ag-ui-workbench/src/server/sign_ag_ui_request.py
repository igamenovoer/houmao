"""Return exact AG-UI caller proof to the local workbench over bounded stdio."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from houmao.gateway.client import GatewayClient, GatewayHttpError, load_gateway_client_binding

_MAX_BODY_BYTES = 2 * 1024 * 1024
_MAX_INPUT_BYTES = 4 * ((_MAX_BODY_BYTES + 2) // 3) + 16384
_AG_UI_ROUTES = {
    "GET": {"/v1/ag-ui/capabilities", "/v1/ag-ui/destination", "/v1/ag-ui/active-thread"},
    "POST": {"/v1/ag-ui/connect", "/v1/ag-ui/runs"},
    "PUT": {"/v1/ag-ui/active-thread"},
}
_CONNECTION_ROUTE = re.compile(r"/v1/ag-ui/connections/[A-Za-z0-9_.:-]{1,256}")
_THREAD_QUERY = re.compile(r"threadId=[^&]*")


def _operation_allowed(method: str, path: str) -> bool:
    """Accept only the built-in AG-UI bridge operations."""
    route, _, query = path.partition("?")
    if method == "DELETE":
        if route == "/v1/ag-ui/active-thread":
            return not query or _THREAD_QUERY.fullmatch(query) is not None
        return not query and _CONNECTION_ROUTE.fullmatch(route) is not None
    return not query and route in _AG_UI_ROUTES.get(method, set())


def _main() -> None:
    """Match the live descriptor to the operator binding and sign one request."""
    try:
        raw = sys.stdin.buffer.read(_MAX_INPUT_BYTES + 1)
        if len(raw) > _MAX_INPUT_BYTES:
            raise ValueError("Proof input too large.")
        request = json.loads(raw)
        method = request["method"]
        path = request["path"]
        if not _operation_allowed(method, path):
            raise ValueError("Operation outside AG-UI.")
        body = base64.b64decode(request["bodyBase64"], validate=True)
        if len(body) > _MAX_BODY_BYTES:
            raise ValueError("Proof body too large.")
        original = load_gateway_client_binding(Path(request["clientBindingPath"]))
        if original.purpose != "caller" or original.owner.agent_id != request["agentId"]:
            raise ValueError("Invalid signer binding.")
        selected = urlsplit(request["baseUrl"])
        configured = urlsplit(original.base_url)
        if (
            selected.scheme != configured.scheme
            or selected.hostname != configured.hostname
            or selected.path != configured.path
            or selected.username is not None
            or selected.password is not None
            or selected.query
            or selected.fragment
            or (
                request["discovered"] is not True
                and (selected.port or _default_port(selected.scheme))
                != (configured.port or _default_port(configured.scheme))
            )
        ):
            raise ValueError("Gateway differs from the approved source.")
        binding = type(original).model_validate(
            {**original.model_dump(), "base_url": request["baseUrl"]}
        )
        discovery = GatewayClient(binding=binding, timeout_seconds=3, respect_proxy_env=False)
        endpoint = discovery.describe_endpoint()
        if endpoint.protocol != "v1" or endpoint.target.owner != binding.owner:
            raise ValueError("Gateway owner differs from the binding.")
        if endpoint.admin_mode == "unavailable":
            print(json.dumps({"status": 503}))
            return
        if request.get("generationId") not in {None, endpoint.target.incarnation}:
            print(json.dumps({"status": 409}))
            return
        client = GatewayClient(
            binding=binding,
            target_incarnation=endpoint.target.incarnation,
            target_presence_id=endpoint.presence_id,
            timeout_seconds=3,
            respect_proxy_env=False,
        )
        headers = client.caller_proof_headers(method, path, body)
        print(json.dumps({"status": 200, "headers": dict(headers)}))
    except GatewayHttpError as exc:
        status = exc.status_code
        if status not in {401, 403, 409}:
            status = 403 if status is not None and 300 <= status < 500 else 502
        print(json.dumps({"status": status}))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(json.dumps({"status": 403}))


def _default_port(scheme: str) -> int:
    """Return the default port for a validated HTTP scheme."""
    return 443 if scheme == "https" else 80


if __name__ == "__main__":
    _main()
