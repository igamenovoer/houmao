#!/usr/bin/env python3
"""Managed filesystem mailbox delivery entrypoint."""

from __future__ import annotations

from houmao.mailbox.managed import (
    DeliveryRequest,
    deliver_message,
    run_managed_mailbox_script,
)


def main() -> int:
    """Execute one managed filesystem mailbox delivery request."""

    return run_managed_mailbox_script(
        description=__doc__,
        request_model=DeliveryRequest,
        handler=deliver_message,
    )


if __name__ == "__main__":
    raise SystemExit(main())
