#!/usr/bin/env python3
"""Sanitize one demo-pack report for reproducible verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from houmao.demo.legacy.houmao_server_agent_api_demo_pack.reporting import sanitize_report


def main() -> int:
    """Run the sanitizer CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("actual_report", type=Path)
    parser.add_argument("sanitized_report", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.actual_report.read_text(encoding="utf-8"))
    sanitized = sanitize_report(payload)
    args.sanitized_report.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_report.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.sanitized_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
