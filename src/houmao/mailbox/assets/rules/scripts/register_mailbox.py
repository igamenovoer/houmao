#!/usr/bin/env python3
"""Managed filesystem mailbox registration entrypoint."""

from __future__ import annotations

from houmao.mailbox.managed import (
    RegisterMailboxRequest,
    register_mailbox,
    run_managed_mailbox_script,
)


def main() -> int:
    """Execute one managed filesystem mailbox registration request."""

    return run_managed_mailbox_script(
        description=__doc__,
        request_model=RegisterMailboxRequest,
        handler=register_mailbox,
    )


if __name__ == "__main__":
    raise SystemExit(main())
