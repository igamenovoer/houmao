"""Standalone Houmao-server dual shadow-watch demo package."""

from houmao.demo.houmao_server_dual_shadow_watch.driver import main as driver_main
from houmao.demo.houmao_server_dual_shadow_watch.monitor import main as monitor_main

__all__ = ["driver_main", "monitor_main"]
