"""Check conservative plugin routing without depending on registration order."""

from __future__ import annotations

from contextlib import asynccontextmanager
from itertools import permutations
from typing import AsyncIterator

from fastapi import APIRouter
import pytest
from starlette.routing import Mount, Route, WebSocketRoute

from houmao.agents.realm_controller.gateway_plugin_routes import (
    PluginRouteDeclaration,
    PluginRouteError,
    PluginRoutePermission,
    declared_plugin_action,
    paths_overlap,
    plugin_route_declarations,
    route_conflicts,
)
from houmao.gateway.plugins import plugin_route_action


def _declarations(instance: str, router: APIRouter) -> tuple[PluginRouteDeclaration, ...]:
    """Validate fixture routes for their exact configured instance."""

    return plugin_route_declarations(
        instance, router, implementation="fixture", resource=f"plugin:{instance}:binding"
    )


def test_route_action_is_bound_to_selected_instance() -> None:
    """Two instances of the same implementation use different policy resources."""

    router = APIRouter()
    router.add_api_route(
        "/ordinary",
        lambda: None,
        methods=["GET"],
        openapi_extra=plugin_route_action("plugin.fixture.observe"),
    )
    assert _declarations("one", router)[0].permission == PluginRoutePermission(
        action="plugin.fixture.observe", resource="plugin:one:binding"
    )
    assert _declarations("two", router)[0].permission == PluginRoutePermission(
        action="plugin.fixture.observe", resource="plugin:two:binding"
    )


@pytest.mark.parametrize(
    "metadata",
    [
        None,
        {"x-houmao-gateway-access": "admin"},
        {"x-houmao-gateway-action": "public"},
        {"x-houmao-gateway-action": "plugin.fixture"},
        {"x-houmao-gateway-action": "plugin.fixture.bad..name"},
        {"x-houmao-gateway-action": "plugin.other.observe"},
        {"x-houmao-gateway-action": None},
    ],
)
def test_missing_or_invalid_plugin_route_action_is_rejected(
    metadata: dict[str, object] | None,
) -> None:
    """Reject an invalid plugin route before it can register resources."""

    router = APIRouter()
    router.add_api_route(
        "/invalid",
        lambda: None,
        methods=["GET"],
        openapi_extra=metadata,
    )
    with pytest.raises(PluginRouteError, match="namespac") as caught:
        _declarations("fixture", router)
    assert caught.value.error_code == "invalid_route_action"


def test_plugin_cannot_declare_host_status_action() -> None:
    """Reserve the host status permission independently of plugin namespaces."""

    router = APIRouter()
    router.add_api_route(
        "/custom",
        lambda: None,
        methods=["POST"],
        openapi_extra=plugin_route_action("plugin.status.read"),
    )
    with pytest.raises(PluginRouteError, match="namespaced"):
        declared_plugin_action(router.routes[0])


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("/items/{id}", "/items/{name}", True),
        ("/items/{id}", "/items/latest", True),
        ("/items", "/items/", True),
        ("/items/{tail:path}", "/items/latest/more", True),
        ("/items/{tail:path}", "/items", True),
        ("/a/{tail:path}", "/b/{id}", False),
        ("/a/{id}", "/a/{id}/more", False),
        ("/a/{id}/last", "/a/literal/other", False),
    ],
)
def test_overlap_uses_path_language(first: str, second: str, expected: bool) -> None:
    """Normalize names and aliases while keeping disjoint paths separate."""

    assert paths_overlap(first, second) is expected
    assert paths_overlap(second, first) is expected


def test_conflict_graph_rejects_every_participant_independent_of_order() -> None:
    """All vertices on an overlap edge fail, including a transitive chain."""

    declarations = (
        PluginRouteDeclaration("one", "/same/{id}", frozenset({"GET"})),
        PluginRouteDeclaration("two", "/same/literal", frozenset({"GET", "POST"})),
        PluginRouteDeclaration("three", "/same/literal/", frozenset({"POST"})),
        PluginRouteDeclaration("safe", "/different", frozenset({"GET"})),
    )
    expected = route_conflicts(declarations)
    assert set(expected) == {"one", "two", "three"}
    for ordering in permutations(declarations):
        assert route_conflicts(ordering) == expected


def test_core_remains_authoritative_and_actual_methods_are_compared() -> None:
    """Core collisions fail a plugin, while distinct HTTP methods coexist."""

    declarations = (
        PluginRouteDeclaration(None, "/reserved", frozenset({"GET", "HEAD"})),
        PluginRouteDeclaration("one", "/reserved/", frozenset({"HEAD"})),
        PluginRouteDeclaration("two", "/reserved", frozenset({"POST"})),
    )
    assert route_conflicts(declarations) == {
        "one": [
            {
                "method": "HEAD",
                "path": "/reserved/",
                "counterpart_instance": "core",
                "counterpart_path": "/reserved",
            }
        ]
    }


def test_default_nested_routers_and_automatic_head_are_supported() -> None:
    """Ordinary flattened HTTP routes preserve their effective method set."""

    router = APIRouter()
    nested = APIRouter()
    nested.routes.append(Route("/items/{id}", endpoint=lambda request: None, methods=["GET"]))
    router.include_router(nested)
    setattr(router.routes[0], "openapi_extra", plugin_route_action("plugin.fixture.observe"))
    assert _declarations("one", router) == (
        PluginRouteDeclaration(
            "one",
            "/v1/plugins/one/items/{id}",
            frozenset({"GET", "HEAD"}),
            PluginRoutePermission(action="plugin.fixture.observe", resource="plugin:one:binding"),
        ),
    )


@pytest.mark.parametrize(
    "path",
    [
        "/../escape",
        "/a//b",
        "/a\\b",
        "/a%2fb",
        "/a?query",
        "/a#fragment",
        "/a/{id:int}",
        "/a/{remaining:path}/last",
        "/_status/private",
        "/{value}",
        "/{remaining:path}",
    ],
)
def test_unsupported_or_reserved_paths_fail_before_mount(path: str) -> None:
    """Reject routes outside the restricted, host-reserved grammar."""

    router = APIRouter()
    router.routes.append(Route(path, endpoint=lambda request: None, methods=["POST"]))
    with pytest.raises(PluginRouteError):
        _declarations("one", router)


@pytest.mark.parametrize(
    "kind", ["mount", "websocket", "startup", "lifespan", "callback", "middleware", "exception"]
)
def test_unsupported_router_mutations_fail(kind: str) -> None:
    """Resources and global mutation have only the supervised SDK path."""

    @asynccontextmanager
    async def lifespan(_app: object) -> AsyncIterator[None]:
        """Supply a forbidden router-owned lifecycle."""

        yield

    router = APIRouter(lifespan=lifespan) if kind == "lifespan" else APIRouter()
    if kind == "mount":
        router.routes.append(Mount("/nested", app=APIRouter()))
    elif kind == "websocket":
        router.routes.append(WebSocketRoute("/ws", endpoint=lambda socket: None))
    elif kind == "startup":
        router.on_startup.append(lambda: None)
    elif kind == "callback":
        router.callbacks.append(Route("/callback", endpoint=lambda request: None))
    elif kind == "middleware":
        setattr(router, "user_middleware", [object()])
    elif kind == "exception":
        setattr(router, "exception_handlers", {ValueError: lambda request, error: None})
    with pytest.raises(PluginRouteError):
        _declarations("one", router)
