#!/usr/bin/env python3
"""Managed filesystem mailbox deregistration entrypoint."""

from __future__ import annotations

from houmao.mailbox.managed import (
    DeregisterMailboxRequest,
    deregister_mailbox,
    run_managed_mailbox_script,
)


def main() -> int:
    """Execute one managed filesystem mailbox deregistration request."""

    return run_managed_mailbox_script(
        description=__doc__,
        request_model=DeregisterMailboxRequest,
        handler=deregister_mailbox,
    )


if __name__ == "__main__":
    raise SystemExit(main())
