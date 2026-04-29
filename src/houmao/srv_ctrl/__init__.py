"""CAO-compatible Houmao service-management CLI package."""

from __future__ import annotations

__all__ = ["main"]


def main() -> int:
    """Run the service-management CLI entrypoint."""

    from .commands.main import main as _main

    return _main()
