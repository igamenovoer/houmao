"""Package version helpers."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    """Return the installed Houmao package version."""

    try:
        return version("Houmao")
    except PackageNotFoundError:
        return "0+unknown"


__all__ = ["get_version"]

