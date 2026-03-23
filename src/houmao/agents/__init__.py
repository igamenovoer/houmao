"""Lazy public exports for agent helpers and runtime control."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "BackendExecutionError": ("houmao.agents.realm_controller", "BackendExecutionError"),
    "BrainLaunchRuntimeError": ("houmao.agents.realm_controller", "BrainLaunchRuntimeError"),
    "BuildError": ("houmao.agents.brain_builder", "BuildError"),
    "BuildRequest": ("houmao.agents.brain_builder", "BuildRequest"),
    "BuildResult": ("houmao.agents.brain_builder", "BuildResult"),
    "LaunchPlan": ("houmao.agents.realm_controller", "LaunchPlan"),
    "LaunchPlanError": ("houmao.agents.realm_controller", "LaunchPlanError"),
    "LaunchPlanRequest": ("houmao.agents.realm_controller", "LaunchPlanRequest"),
    "LaunchPolicyProvenance": (
        "houmao.agents.launch_policy",
        "LaunchPolicyProvenance",
    ),
    "RoleInjectionPlan": ("houmao.agents.realm_controller", "RoleInjectionPlan"),
    "RolePackage": ("houmao.agents.realm_controller", "RolePackage"),
    "RuntimeSessionController": (
        "houmao.agents.realm_controller",
        "RuntimeSessionController",
    ),
    "SchemaValidationError": ("houmao.agents.realm_controller", "SchemaValidationError"),
    "SessionControlResult": ("houmao.agents.realm_controller", "SessionControlResult"),
    "SessionEvent": ("houmao.agents.realm_controller", "SessionEvent"),
    "SessionManifestError": ("houmao.agents.realm_controller", "SessionManifestError"),
    "SessionResult": ("houmao.agents.realm_controller", "SessionResult"),
    "backend_for_tool": ("houmao.agents.realm_controller", "backend_for_tool"),
    "build_brain_home": ("houmao.agents.brain_builder", "build_brain_home"),
    "build_launch_plan": ("houmao.agents.realm_controller", "build_launch_plan"),
    "load_blueprint": ("houmao.agents.realm_controller", "load_blueprint"),
    "load_brain_manifest": ("houmao.agents.realm_controller", "load_brain_manifest"),
    "load_brain_recipe": ("houmao.agents.brain_builder", "load_brain_recipe"),
    "load_role_package": ("houmao.agents.realm_controller", "load_role_package"),
    "load_session_manifest": ("houmao.agents.realm_controller", "load_session_manifest"),
    "main": ("houmao.agents.brain_builder", "main"),
    "plan_role_injection": ("houmao.agents.realm_controller", "plan_role_injection"),
    "resume_runtime_session": ("houmao.agents.realm_controller", "resume_runtime_session"),
    "start_runtime_session": ("houmao.agents.realm_controller", "start_runtime_session"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve package re-exports lazily to avoid import cycles."""

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
