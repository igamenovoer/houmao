"""Documentation drift tests for direct per-agent AG-UI gateway routes."""

from __future__ import annotations

from pathlib import Path
import re

from houmao.agents.realm_controller.gateway_service import create_app


_ROUTE_PATTERN = re.compile(r"- `(?P<method>GET|POST|DELETE) (?P<path>/v1/ag-ui/[^`]+)`")


def test_documented_ag_ui_routes_match_gateway_route_inventory() -> None:
    """Assert documented direct AG-UI routes match the live gateway route inventory."""

    repo_root = Path(__file__).resolve().parents[3]
    docs_path = repo_root / "docs" / "reference" / "gateway" / "ag-ui.md"
    docs_text = docs_path.read_text(encoding="utf-8")
    documented_routes = {
        (match.group("method"), match.group("path")) for match in _ROUTE_PATTERN.finditer(docs_text)
    }
    expected_routes = {
        ("GET", "/v1/ag-ui/capabilities"),
        ("POST", "/v1/ag-ui/connect"),
        ("POST", "/v1/ag-ui/runs"),
        ("DELETE", "/v1/ag-ui/connections/{connection_id}"),
    }
    app = create_app(runtime=object())  # type: ignore[arg-type]
    live_routes = {
        (method, route.path) for route in app.routes for method in getattr(route, "methods", set())
    }

    assert expected_routes <= documented_routes
    assert expected_routes <= live_routes
    assert "/houmao/agents/{agent_ref}/ag-ui/runs" not in docs_text
