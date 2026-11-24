"""Versioned public SDK for independently installed trusted gateway plugins."""

from houmao.gateway.plugins.configuration import load_plugin_configuration
from houmao.gateway.plugins.contracts import (
    GatewayPlugin,
    PluginContext,
    PluginCredentialReader,
    PluginDefinition,
    PluginEventDispatcher,
    PluginState,
    PluginWorkerSupervisor,
)
from houmao.gateway.plugins.discovery import (
    LoadedPluginDefinition,
    PluginLoadError,
    load_plugin_definition,
)
from houmao.gateway.plugins.errors import PluginConfigurationError, PluginDispatchError
from houmao.gateway.plugins.models import (
    PLUGIN_ENTRY_POINT_GROUP,
    PLUGIN_SDK_VERSION,
    GatewayPluginConfiguration,
    GatewayPluginStatusResponse,
    PluginConnectionState,
    PluginCredentialReference,
    PluginDispatchResult,
    PluginEvent,
    PluginInstanceConfiguration,
    PluginLifecycleState,
    PluginListener,
    PluginOwner,
    PluginStatus,
)
from houmao.gateway.plugins.routes import plugin_route_action

__all__ = [
    "PLUGIN_ENTRY_POINT_GROUP",
    "PLUGIN_SDK_VERSION",
    "GatewayPlugin",
    "GatewayPluginConfiguration",
    "GatewayPluginStatusResponse",
    "LoadedPluginDefinition",
    "PluginConfigurationError",
    "PluginConnectionState",
    "PluginContext",
    "PluginCredentialReader",
    "PluginCredentialReference",
    "PluginDefinition",
    "PluginDispatchError",
    "PluginDispatchResult",
    "PluginEvent",
    "PluginEventDispatcher",
    "PluginInstanceConfiguration",
    "PluginLifecycleState",
    "PluginListener",
    "PluginLoadError",
    "PluginOwner",
    "PluginState",
    "PluginStatus",
    "PluginWorkerSupervisor",
    "load_plugin_configuration",
    "load_plugin_definition",
    "plugin_route_action",
]
