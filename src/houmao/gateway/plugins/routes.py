"""Route access declarations for independently installed gateway plugins."""

from typing import Literal


PluginRouteAccess = Literal["private", "admin"]
PLUGIN_ROUTE_ACCESS_FIELD = "x-houmao-gateway-access"


def plugin_route_access(access: PluginRouteAccess) -> dict[str, str]:
    """Return the `openapi_extra` metadata for one plugin HTTP route."""

    return {PLUGIN_ROUTE_ACCESS_FIELD: access}
