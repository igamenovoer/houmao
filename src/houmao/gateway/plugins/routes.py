"""Explicit route action declarations for independently installed gateway plugins."""

PLUGIN_ROUTE_ACTION_FIELD = "x-houmao-gateway-action"


def plugin_route_action(action: str) -> dict[str, str]:
    """Declare a `plugin.<implementation>.<action>` for an HTTP route.

    The gateway host validates the declaration and selects the resource for
    the installed instance.
    """

    return {PLUGIN_ROUTE_ACTION_FIELD: action}
