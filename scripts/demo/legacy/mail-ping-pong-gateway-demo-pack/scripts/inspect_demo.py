#!/usr/bin/env python3
"""Write `inspect.json` for the selected demo output root."""

from __future__ import annotations

from houmao.demo.legacy.mail_ping_pong_gateway_demo_pack.driver import main


if __name__ == "__main__":
    raise SystemExit(main(["inspect", *(__import__("sys").argv[1:])]))
