#!/usr/bin/env python3
"""Sanitize one TUI mail gateway demo report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from houmao.demo.legacy.tui_mail_gateway_demo_pack.reporting import sanitize_report


def main() -> int:
    """Run the sanitize-report CLI."""

    parser = argparse.ArgumentParser(description="Sanitize TUI mail gateway demo report")
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    sanitized = sanitize_report(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sanitized, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
