"""Houmao HTTP server package."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import create_app
    from .client import HoumaoServerClient
    from .config import HoumaoServerConfig

__all__ = ["HoumaoServerClient", "HoumaoServerConfig", "create_app"]


def __getattr__(name: str) -> Any:
    """Resolve server package exports lazily to avoid import-side-effect cycles."""

    export_map = {
        "create_app": (".app", "create_app"),
        "HoumaoServerClient": (".client", "HoumaoServerClient"),
        "HoumaoServerConfig": (".config", "HoumaoServerConfig"),
    }
    if name not in export_map:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute_name = export_map[name]
    module = import_module(module_name, __name__)
    return getattr(module, attribute_name)
