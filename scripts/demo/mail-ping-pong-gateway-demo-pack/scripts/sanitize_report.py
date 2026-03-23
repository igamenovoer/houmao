#!/usr/bin/env python3
"""Sanitize mail ping-pong demo reports for snapshot comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from houmao.demo.mail_ping_pong_gateway_demo_pack.reporting import sanitize_report


def main() -> int:
    """Run the sanitizer CLI."""

    parser = argparse.ArgumentParser(description="Sanitize mail ping-pong demo report output")
    parser.add_argument("actual_report", type=Path)
    parser.add_argument("sanitized_report", type=Path)
    args = parser.parse_args()

    actual = json.loads(args.actual_report.read_text(encoding="utf-8"))
    sanitized = sanitize_report(actual)
    args.sanitized_report.parent.mkdir(parents=True, exist_ok=True)
    args.sanitized_report.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.sanitized_report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
