"""Retired standalone CAO launcher entrypoint."""

from __future__ import annotations

import sys

_MIGRATION_GUIDANCE = (
    "The standalone `houmao-cao-server` launcher has been retired. "
    "Use `houmao-server` with `houmao-srv-ctrl` instead."
)


def main(argv: list[str] | None = None) -> int:
    """Fail fast with migration guidance for the retired launcher surface."""

    del argv
    print(_MIGRATION_GUIDANCE, file=sys.stderr)
    return 2


__all__ = ["main"]
