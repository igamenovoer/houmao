"""Standalone dual-agent shadow-watch demo helpers."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from houmao.demo.cao_dual_shadow_watch.driver import main as driver_main
    from houmao.demo.cao_dual_shadow_watch.monitor import main as monitor_main
    from houmao.demo.cao_dual_shadow_watch.models import (
        AgentDashboardState,
        AgentSessionState,
        DemoLauncherState,
        DemoPaths,
        DualShadowWatchDemoState,
        MonitorObservation,
        MonitorSessionState,
        MonitorTransitionEvent,
        load_demo_state,
        save_demo_state,
    )

__all__ = [
    "AgentDashboardState",
    "AgentSessionState",
    "DemoLauncherState",
    "DemoPaths",
    "DualShadowWatchDemoState",
    "MonitorObservation",
    "MonitorSessionState",
    "MonitorTransitionEvent",
    "driver_main",
    "load_demo_state",
    "monitor_main",
    "save_demo_state",
]


def __getattr__(name: str) -> Any:
    """Resolve demo package exports lazily to avoid importing the driver at package import time."""

    export_map = {
        "AgentDashboardState": (".models", "AgentDashboardState"),
        "AgentSessionState": (".models", "AgentSessionState"),
        "DemoLauncherState": (".models", "DemoLauncherState"),
        "DemoPaths": (".models", "DemoPaths"),
        "DualShadowWatchDemoState": (".models", "DualShadowWatchDemoState"),
        "MonitorObservation": (".models", "MonitorObservation"),
        "MonitorSessionState": (".models", "MonitorSessionState"),
        "MonitorTransitionEvent": (".models", "MonitorTransitionEvent"),
        "driver_main": (".driver", "main"),
        "load_demo_state": (".models", "load_demo_state"),
        "monitor_main": (".monitor", "main"),
        "save_demo_state": (".models", "save_demo_state"),
    }
    if name not in export_map:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = export_map[name]
    module = import_module(module_name, __name__)
    return getattr(module, attribute_name)
