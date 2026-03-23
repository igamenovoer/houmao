#!/usr/bin/env python3
"""Wrapper for the TUI mail gateway demo `inspect` command."""

from __future__ import annotations

import sys

from houmao.demo.tui_mail_gateway_demo_pack.driver import main


if __name__ == "__main__":
    raise SystemExit(main(["inspect", *sys.argv[1:]]))
