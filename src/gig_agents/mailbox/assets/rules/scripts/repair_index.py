#!/usr/bin/env python3
"""Managed filesystem mailbox repair and reindex entrypoint."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from gig_agents.mailbox.managed import (
    ManagedMailboxOperationError,
    RepairRequest,
    load_json_payload,
    repair_mailbox_index,
)


def main() -> int:
    """Execute one managed filesystem mailbox repair or reindex request."""

    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox-root", required=True)
    parser.add_argument("--payload-file", required=False)
    args = parser.parse_args()

    try:
        payload: object = {}
        if args.payload_file is not None:
            payload = load_json_payload(Path(args.payload_file))
        request = RepairRequest.from_payload(payload)
        result = repair_mailbox_index(Path(args.mailbox_root), request)
    except ManagedMailboxOperationError as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 1

    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
