#!/usr/bin/env python3
from __future__ import annotations

import sys

from houmao.agents.brain_builder import BuildError, main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
