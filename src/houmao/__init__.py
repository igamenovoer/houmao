"""Houmao runtime package."""

from __future__ import annotations

from houmao.version import get_version

__version__ = get_version()

__all__ = ["__version__", "agents", "cao"]
