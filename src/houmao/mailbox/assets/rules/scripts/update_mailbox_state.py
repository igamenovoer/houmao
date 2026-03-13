#!/usr/bin/env python3
"""Managed mailbox-state mutation entrypoint."""

from __future__ import annotations

from houmao.mailbox.managed import (
    StateUpdateRequest,
    run_managed_mailbox_script,
    update_mailbox_state,
)


def main() -> int:
    """Execute one managed mailbox-state mutation request."""

    return run_managed_mailbox_script(
        description=__doc__,
        request_model=StateUpdateRequest,
        handler=update_mailbox_state,
    )


if __name__ == "__main__":
    raise SystemExit(main())
