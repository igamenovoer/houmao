#!/usr/bin/env python3
"""Managed filesystem mailbox registration entrypoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from gig_agents.mailbox.managed import (
    ManagedMailboxOperationError,
    RegisterMailboxRequest,
    load_json_payload,
    register_mailbox,
)


def main() -> int:
    """Execute one managed filesystem mailbox registration request."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mailbox-root", required=True)
    parser.add_argument("--payload-file", required=True)
    args = parser.parse_args()

    try:
        payload = load_json_payload(Path(args.payload_file))
        request = RegisterMailboxRequest.from_payload(payload)
        result = register_mailbox(Path(args.mailbox_root), request)
    except ManagedMailboxOperationError as exc:
        json.dump({"ok": False, "error": str(exc)}, sys.stdout)
        sys.stdout.write("\n")
        return 1

    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
