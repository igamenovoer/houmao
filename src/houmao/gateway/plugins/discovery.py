"""Resolve only explicitly selected installed plugin definitions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import cast

from pydantic import BaseModel

from houmao.gateway.plugins.contracts import PluginDefinition
from houmao.gateway.plugins.models import PLUGIN_ENTRY_POINT_GROUP, PLUGIN_SDK_VERSION


class PluginLoadError(RuntimeError):
    """Report a safe selected-package load failure without provider exceptions."""

    def __init__(
        self, error_code: str, message: str, *, distributions: tuple[str, ...] = ()
    ) -> None:
        """Initialize a sanitized implementation-resolution failure."""

        super().__init__(message)
        self.m_error_code: str = error_code
        self.m_message: str = message
        self.m_distributions: tuple[str, ...] = distributions

    @property
    def error_code(self) -> str:
        """Return the machine-readable failure category."""

        return self.m_error_code

    @property
    def message(self) -> str:
        """Return a safe diagnostic without configuration or exception values."""

        return self.m_message

    @property
    def distributions(self) -> tuple[str, ...]:
        """Return distributions competing for the selected entry-point name."""

        return self.m_distributions


@dataclass(frozen=True)
class LoadedPluginDefinition:
    """Pair a validated selected definition with distribution provenance."""

    definition: PluginDefinition[BaseModel]
    distribution: str
    distribution_version: str


def load_plugin_definition(
    implementation: str, *, candidates: Sequence[EntryPoint] | None = None
) -> LoadedPluginDefinition:
    """Load one selected implementation without importing unselected packages."""

    available = entry_points(group=PLUGIN_ENTRY_POINT_GROUP) if candidates is None else candidates
    selected = [
        entry
        for entry in available
        if entry.name == implementation and entry.group == PLUGIN_ENTRY_POINT_GROUP
    ]
    if not selected:
        raise PluginLoadError("implementation_missing", "Selected plugin is not installed.")
    if len(selected) != 1:
        names = tuple(sorted(_distribution_identity(entry)[0] for entry in selected))
        raise PluginLoadError(
            "implementation_ambiguous",
            "Multiple distributions provide the selected plugin.",
            distributions=names,
        )
    entry = selected[0]
    try:
        value: object = entry.load()
    except Exception:
        raise PluginLoadError(
            "implementation_load_failed", "Selected plugin could not load."
        ) from None
    if not isinstance(value, PluginDefinition):
        raise PluginLoadError(
            "invalid_definition", "Entry point does not provide a plugin definition."
        )
    if type(value.sdk_version) is not int or value.sdk_version != PLUGIN_SDK_VERSION:
        raise PluginLoadError("sdk_version_unsupported", "Plugin SDK version is unsupported.")
    if (
        not isinstance(value.config_model, type)
        or not issubclass(value.config_model, BaseModel)
        or not callable(value.binding_identity)
        or not callable(value.create)
    ):
        raise PluginLoadError(
            "invalid_definition", "Plugin definition has invalid author contracts."
        )
    if (
        value.config_model.model_config.get("strict") is not True
        or value.config_model.model_config.get("extra") != "forbid"
    ):
        raise PluginLoadError(
            "invalid_definition",
            "Plugin configuration model must be strict and forbid extra fields.",
        )
    distribution, version = _distribution_identity(entry)
    return LoadedPluginDefinition(
        definition=cast(PluginDefinition[BaseModel], value),
        distribution=distribution,
        distribution_version=version,
    )


def _distribution_identity(entry: EntryPoint) -> tuple[str, str]:
    """Read non-secret package identity from entry-point metadata."""

    distribution = entry.dist
    if distribution is None:
        return "unknown", "unknown"
    try:
        name = distribution.metadata["Name"]
    except KeyError:
        name = "unknown"
    return name, distribution.version
