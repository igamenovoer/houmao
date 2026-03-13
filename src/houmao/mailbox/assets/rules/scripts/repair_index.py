#!/usr/bin/env python3
"""Managed filesystem mailbox repair and reindex entrypoint."""

from __future__ import annotations

from houmao.mailbox.managed import (
    RepairRequest,
    repair_mailbox_index,
    run_managed_mailbox_script,
)


def main() -> int:
    """Execute one managed filesystem mailbox repair or reindex request."""

    return run_managed_mailbox_script(
        description=__doc__,
        request_model=RepairRequest,
        handler=repair_mailbox_index,
        payload_required=False,
        default_payload={},
    )


if __name__ == "__main__":
    raise SystemExit(main())
