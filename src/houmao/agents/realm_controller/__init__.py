"""Lazy public exports for realm-controller runtime helpers."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "BackendExecutionError": ("houmao.agents.realm_controller.errors", "BackendExecutionError"),
    "BlueprintBinding": ("houmao.agents.realm_controller.loaders", "BlueprintBinding"),
    "BrainLaunchRuntimeError": (
        "houmao.agents.realm_controller.errors",
        "BrainLaunchRuntimeError",
    ),
    "GatewayAttachError": ("houmao.agents.realm_controller.errors", "GatewayAttachError"),
    "GatewayControlResult": ("houmao.agents.realm_controller.models", "GatewayControlResult"),
    "GatewayDiscoveryError": (
        "houmao.agents.realm_controller.errors",
        "GatewayDiscoveryError",
    ),
    "GatewayError": ("houmao.agents.realm_controller.errors", "GatewayError"),
    "GatewayHttpError": ("houmao.agents.realm_controller.errors", "GatewayHttpError"),
    "GatewayNoLiveInstanceError": (
        "houmao.agents.realm_controller.errors",
        "GatewayNoLiveInstanceError",
    ),
    "GatewayProtocolError": (
        "houmao.agents.realm_controller.errors",
        "GatewayProtocolError",
    ),
    "GatewayUnsupportedBackendError": (
        "houmao.agents.realm_controller.errors",
        "GatewayUnsupportedBackendError",
    ),
    "InteractiveSession": ("houmao.agents.realm_controller.models", "InteractiveSession"),
    "LaunchPlan": ("houmao.agents.realm_controller.models", "LaunchPlan"),
    "LaunchPlanError": ("houmao.agents.realm_controller.errors", "LaunchPlanError"),
    "LaunchPlanRequest": (
        "houmao.agents.realm_controller.launch_plan",
        "LaunchPlanRequest",
    ),
    "RoleInjectionPlan": ("houmao.agents.realm_controller.models", "RoleInjectionPlan"),
    "RolePackage": ("houmao.agents.realm_controller.loaders", "RolePackage"),
    "RuntimeSessionController": (
        "houmao.agents.realm_controller.runtime",
        "RuntimeSessionController",
    ),
    "SchemaValidationError": (
        "houmao.agents.realm_controller.errors",
        "SchemaValidationError",
    ),
    "SessionControlResult": ("houmao.agents.realm_controller.models", "SessionControlResult"),
    "SessionEvent": ("houmao.agents.realm_controller.models", "SessionEvent"),
    "SessionManifestError": (
        "houmao.agents.realm_controller.errors",
        "SessionManifestError",
    ),
    "SessionResult": ("houmao.agents.realm_controller.models", "SessionResult"),
    "backend_for_tool": ("houmao.agents.realm_controller.launch_plan", "backend_for_tool"),
    "build_launch_plan": ("houmao.agents.realm_controller.launch_plan", "build_launch_plan"),
    "load_blueprint": ("houmao.agents.realm_controller.loaders", "load_blueprint"),
    "load_brain_manifest": ("houmao.agents.realm_controller.loaders", "load_brain_manifest"),
    "load_brain_recipe_from_path": (
        "houmao.agents.realm_controller.loaders",
        "load_brain_recipe_from_path",
    ),
    "load_role_package": ("houmao.agents.realm_controller.loaders", "load_role_package"),
    "load_session_manifest": (
        "houmao.agents.realm_controller.manifest",
        "load_session_manifest",
    ),
    "plan_role_injection": (
        "houmao.agents.realm_controller.launch_plan",
        "plan_role_injection",
    ),
    "resume_runtime_session": (
        "houmao.agents.realm_controller.runtime",
        "resume_runtime_session",
    ),
    "start_runtime_session": (
        "houmao.agents.realm_controller.runtime",
        "start_runtime_session",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve realm-controller exports lazily to avoid package import cycles."""

    export = _EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = export
    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable package attributes for interactive inspection."""

    return sorted(list(globals()) + __all__)
