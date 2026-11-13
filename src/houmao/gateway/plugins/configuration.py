"""Read explicit plugin configuration without duplicate-key overwrite."""

from __future__ import annotations

from collections.abc import Hashable
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError
import yaml

from houmao.gateway.plugins.errors import PluginConfigurationError
from houmao.gateway.plugins.models import GatewayPluginConfiguration


class _UniqueMappingLoader(yaml.SafeLoader):
    """Reject duplicate keys instead of silently choosing a mapping value."""


def _construct_unique_mapping(
    loader: _UniqueMappingLoader, node: yaml.MappingNode
) -> dict[Hashable, Any]:
    """Construct a safe mapping while retaining duplicate-key evidence."""

    loader.flatten_mapping(node)
    result: dict[Hashable, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise PluginConfigurationError("Plugin configuration keys must be strings.")
        if key in result:
            raise PluginConfigurationError("Duplicate plugin configuration key.")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_UniqueMappingLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject repeated JSON keys before a dictionary can discard them."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PluginConfigurationError("Duplicate plugin configuration key.")
        result[key] = value
    return result


def load_plugin_configuration(path: Path) -> GatewayPluginConfiguration:
    """Load an explicit versioned gateway configuration document.

    Parameters
    ----------
    path : Path
        YAML or JSON file containing ``schema_version`` and ``gateway``.

    Returns
    -------
    GatewayPluginConfiguration
        Complete replacement selection, including explicit empty selections.

    Raises
    ------
    PluginConfigurationError
        If the document is unreadable, ambiguous, or violates the public schema.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise PluginConfigurationError("Cannot read plugin configuration document.") from None
    try:
        if path.suffix.lower() == ".json":
            document = json.loads(text, object_pairs_hook=_unique_json_object)
        else:
            document = yaml.load(text, Loader=_UniqueMappingLoader)
    except PluginConfigurationError:
        raise
    except (ValueError, yaml.YAMLError, TypeError):
        raise PluginConfigurationError("Invalid plugin configuration document.") from None
    if not isinstance(document, dict) or set(document) != {"schema_version", "gateway"}:
        raise PluginConfigurationError("Expected schema_version and gateway configuration fields.")
    gateway = document["gateway"]
    if not isinstance(gateway, dict) or "plugins" not in gateway or "schema_version" in gateway:
        raise PluginConfigurationError("Expected an explicit gateway.plugins mapping.")
    payload = {"schema_version": document["schema_version"], **gateway}
    try:
        return GatewayPluginConfiguration.model_validate(payload)
    except ValidationError:
        raise PluginConfigurationError("Plugin configuration schema validation failed.") from None
