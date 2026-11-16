"""Independently installed CCCC integration for the public Houmao gateway SDK."""

from houmao.gateway.plugins import PluginDefinition
from houmao_cccc.configuration import CcccConfiguration, binding_identity
from houmao_cccc.plugin import CcccPlugin

definition = PluginDefinition(
    config_model=CcccConfiguration,
    binding_identity=binding_identity,
    create=CcccPlugin.from_config,
    sdk_version=1,
)

__all__ = ["CcccConfiguration", "CcccPlugin", "definition"]
