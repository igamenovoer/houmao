#!/usr/bin/env python3
"""Managed mailbox header-normalization entrypoint."""

from __future__ import annotations

import json
import sys


def main() -> int:
    """Return a structured not-yet-implemented result."""

    json.dump(
        {
            "ok": False,
            "error": (
                "insert_standard_headers.py is materialized and reserved, but header "
                "normalization behavior is not implemented in this build yet"
            ),
        },
        sys.stdout,
    )
    sys.stdout.write("\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
