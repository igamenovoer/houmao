#!/usr/bin/env python3
"""Inspect the durable gateway wake-up demo artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tutorial_pack_helpers import build_demo_layout, inspect_demo


def main() -> int:
    """Run the inspection CLI."""

    parser = argparse.ArgumentParser(description="Inspect gateway wake-up demo artifacts")
    parser.add_argument("demo_output_dir", type=Path)
    args = parser.parse_args()

    layout = build_demo_layout(demo_output_dir=args.demo_output_dir)
    payload = inspect_demo(state_path=layout.state_path)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
