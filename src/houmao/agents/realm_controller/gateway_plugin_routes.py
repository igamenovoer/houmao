"""Validate namespaced plugin HTTP routes before any plugin is activated."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import re
from typing import cast

from fastapi import APIRouter
from starlette.routing import BaseRoute, Route


_PARAMETER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)(?::(str|path))?\}")


class PluginRouteError(ValueError):
    """Describe an unsupported plugin declaration without exposing handler data."""

    def __init__(self, error_code: str, message: str) -> None:
        """Initialize a safe registration error."""

        super().__init__(message)
        self.m_error_code: str = error_code
        self.m_message: str = message

    @property
    def error_code(self) -> str:
        """Return the stable registration error code."""

        return self.m_error_code

    @property
    def message(self) -> str:
        """Return the safe registration explanation."""

        return self.m_message


@dataclass(frozen=True)
class PluginRouteDeclaration:
    """An effective HTTP path and method set owned by a plugin or the core."""

    owner: str | None
    path: str
    methods: frozenset[str]


def plugin_route_declarations(
    instance_id: str, router: APIRouter
) -> tuple[PluginRouteDeclaration, ...]:
    """Validate a resource-free plugin router and return its prefixed routes.

    Parameters
    ----------
    instance_id:
        Validated gateway instance identifier.
    router:
        Router prepared by the external plugin factory.

    Returns
    -------
    tuple[PluginRouteDeclaration, ...]
        Effective HTTP registrations for global conflict checking.
    """

    if not isinstance(router, APIRouter):
        raise PluginRouteError("invalid_router", "Plugin must supply an HTTP router")
    if router.on_startup or router.on_shutdown or not _default_lifespan(router.lifespan_context):
        raise PluginRouteError(
            "unsupported_router_lifecycle", "Plugin resources must use the supervised lifespan"
        )
    if (
        router.callbacks
        or getattr(router, "user_middleware", None)
        or getattr(router, "exception_handlers", None)
    ):
        raise PluginRouteError(
            "unsupported_router_mutation", "Global router mutations are unsupported"
        )
    prefix = f"/v1/plugins/{instance_id}"
    declarations: list[PluginRouteDeclaration] = []
    for route in router.routes:
        if not isinstance(route, Route):
            raise PluginRouteError(
                "unsupported_route_type", "Only ordinary HTTP routes are supported"
            )
        if getattr(route, "callbacks", None):
            raise PluginRouteError("unsupported_route_callback", "Route callbacks are unsupported")
        _segments(route.path)
        if paths_overlap(route.path, "/_status/{reserved:path}"):
            raise PluginRouteError(
                "reserved_route_path", "Plugin routes overlap the reserved status subtree"
            )
        if not route.methods:
            raise PluginRouteError(
                "invalid_route_methods", "Plugin routes require explicit methods"
            )
        declarations.append(
            PluginRouteDeclaration(
                owner=instance_id,
                path=prefix + route.path,
                methods=frozenset(method.upper() for method in route.methods),
            )
        )
    return tuple(declarations)


def core_route_declarations(routes: list[BaseRoute]) -> tuple[PluginRouteDeclaration, ...]:
    """Describe existing core HTTP routes without imposing plugin grammar on them."""

    return tuple(
        PluginRouteDeclaration(None, route.path, frozenset(route.methods or ()))
        for route in routes
        if isinstance(route, Route)
    )


def route_conflicts(
    declarations: tuple[PluginRouteDeclaration, ...],
) -> dict[str, list[dict[str, str]]]:
    """Return every participating plugin and its deterministic conflict evidence."""

    failures: dict[str, list[dict[str, str]]] = {}
    for index, first in enumerate(declarations):
        for second in declarations[index + 1 :]:
            if first.owner is None and second.owner is None:
                continue
            methods = sorted(first.methods & second.methods)
            if not methods or not paths_overlap(first.path, second.path):
                continue
            for declaration, counterpart in ((first, second), (second, first)):
                if declaration.owner is None:
                    continue
                failures.setdefault(declaration.owner, []).append(
                    {
                        "method": ",".join(methods),
                        "path": declaration.path,
                        "counterpart_instance": counterpart.owner or "core",
                        "counterpart_path": counterpart.path,
                    }
                )
    return {
        owner: sorted(
            evidence,
            key=lambda item: (
                item["method"],
                item["path"],
                item["counterpart_instance"],
                item["counterpart_path"],
            ),
        )
        for owner, evidence in sorted(failures.items())
    }


def paths_overlap(first: str, second: str) -> bool:
    """Return whether two supported path patterns can address one request."""

    left = _segments(first, core=True)
    right = _segments(second, core=True)
    for index in range(max(len(left), len(right)) + 1):
        left_item = left[index] if index < len(left) else None
        right_item = right[index] if index < len(right) else None
        if left_item == "**" or right_item == "**":
            return True
        if left_item is None or right_item is None:
            return left_item is right_item
        if left_item != "*" and right_item != "*" and left_item != right_item:
            return False
    return True


def _segments(path: str, *, core: bool = False) -> tuple[str, ...]:
    """Normalize the deliberately restricted registration path grammar."""

    if (
        not path.startswith("/")
        or "//" in path
        or "\\" in path
        or "%" in path
        or "?" in path
        or "#" in path
        or "\x00" in path
    ):
        raise PluginRouteError("invalid_route_path", "Plugin path syntax is unsupported")
    pieces = path.rstrip("/").split("/")[1:]
    result: list[str] = []
    for index, piece in enumerate(pieces):
        if piece in {".", ".."}:
            raise PluginRouteError("invalid_route_path", "Plugin path traversal is unsupported")
        if "{" in piece or "}" in piece:
            match = _PARAMETER.fullmatch(piece)
            if match is None:
                if core:
                    result.append("*")
                    continue
                raise PluginRouteError(
                    "unsupported_path_converter", "Plugin path converter is unsupported"
                )
            if match.group(2) == "path":
                if index != len(pieces) - 1:
                    raise PluginRouteError(
                        "invalid_catch_all", "A plugin path catch-all must be terminal"
                    )
                result.append("**")
            else:
                result.append("*")
        elif piece:
            result.append(piece)
    return tuple(result)


def _default_lifespan(lifespan: object) -> bool:
    """Recognize default router lifespans, including flattened default routers."""

    default_type = type(APIRouter().lifespan_context)
    if type(lifespan) is default_type:
        router = getattr(lifespan, "_router", None)
        return not getattr(router, "on_startup", ()) and not getattr(router, "on_shutdown", ())
    wrapped = getattr(lifespan, "__wrapped__", None)
    if (
        inspect.isfunction(wrapped)
        and wrapped.__module__ == "fastapi.routing"
        and wrapped.__name__ == "merged_lifespan"
    ):
        values = inspect.getclosurevars(wrapped).nonlocals
        original = values.get("original_context")
        nested = values.get("nested_context")
        return _default_lifespan(cast(object, original)) and _default_lifespan(cast(object, nested))
    return False
