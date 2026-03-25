"""Retired standalone CAO launcher CLI surface."""

from __future__ import annotations

import sys

_MIGRATION_GUIDANCE = (
    "The standalone `houmao-cao-server` launcher has been removed from the supported "
    "Houmao workflow. Use `houmao-server` with `houmao-mgr` instead."
)


def main(argv: list[str] | None = None) -> int:
    """Fail fast with migration guidance before any launcher work begins."""

    del argv
    print(_MIGRATION_GUIDANCE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
