"""Module entrypoint for `python -m houmao.srv_ctrl`."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
