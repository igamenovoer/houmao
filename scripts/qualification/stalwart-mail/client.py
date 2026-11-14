#!/usr/bin/env python3
"""Qualify one explicitly selected normal Stalwart account without management access."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from uuid import uuid4

from houmao.mailbox.stalwart import StalwartError, StalwartJmapClient, StalwartMutationError
from houmao.mailbox.stalwart_models import JmapMetadataQuery


def _parser() -> argparse.ArgumentParser:
    """Require explicit endpoint, identity, private credential, and service version."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery-url", required=True)
    parser.add_argument("--login", required=True)
    parser.add_argument("--address", required=True)
    parser.add_argument("--credential-file", type=Path, required=True)
    parser.add_argument("--service-release", required=True)
    parser.add_argument(
        "--exercise-mail",
        action="store_true",
        help="Send to an explicitly selected local peer, reply, and archive the test messages.",
    )
    parser.add_argument("--peer-login")
    parser.add_argument("--peer-address")
    parser.add_argument("--peer-credential-file", type=Path)
    parser.add_argument(
        "--output", type=Path, help="Optional sanitized report outside the checkout."
    )
    return parser


def _new_client(args: argparse.Namespace, *, peer: bool = False) -> StalwartJmapClient:
    """Create a fresh credential epoch from the explicitly selected private source."""
    return StalwartJmapClient(
        jmap_url=args.discovery_url,
        login_identity=args.peer_login if peer else args.login,
        credential_file=args.peer_credential_file if peer else args.credential_file,
        sender_address=args.peer_address if peer else args.address,
    )


def _wait_for_message(client: StalwartJmapClient, subject: str, since: str) -> dict[str, Any]:
    """Find the unique sandbox delivery using bounded pages and a finite deadline."""
    deadline = monotonic() + 15
    while monotonic() < deadline:
        page = client.query_metadata_page(
            query=JmapMetadataQuery(since=since),
            limit=20,
            timeout_seconds=min(5, max(0.1, deadline - monotonic())),
        )
        for row in page.messages:
            if row["subject"] == subject:
                return row
        sleep(0.2)
    raise StalwartError(
        "Sandbox peer delivery was not observed within the finite qualification deadline."
    )


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    """Exercise bounded reads and optional peer mail, returning only sanitized evidence."""
    started = monotonic()
    client = _new_client(args)
    binding = client.validate_binding()
    boundary = client.email_state()
    query = JmapMetadataQuery()
    page = client.query_metadata_page(query=query, limit=3)
    report: dict[str, Any] = {
        "schema_version": 1,
        "service_release": args.service_release,
        "qualified_at_utc": datetime.now(UTC).isoformat(),
        "accounts_tested": 1,
        "scope": "representative normal-account client qualification; no target-scale capacity claim",
        "account_validated": True,
        "sending_identity_validated": True,
        "metadata": {
            "returned_count": len(page.messages),
            "has_more": page.has_more,
            "complete": page.complete,
            "method_calls": page.method_calls,
            "bodies_absent": all(row["body"] is None for row in page.messages),
        },
    }
    if page.messages:
        content = client.get_content(email_id=page.messages[0]["id"])
        report["explicit_content"] = {
            key: content[key]
            for key in ("content_complete", "content_limit_bytes", "content_limit_reason")
        }
    query_delta = client.query_changes(
        query=query, since_query_state=page.query_state, max_changes=5
    )
    report["query_changes"] = {
        "added": len(query_delta.added),
        "removed": len(query_delta.removed),
        "used_as_email_checkpoint": False,
    }
    report["peer_mail_exercised"] = bool(args.exercise_mail)
    peer = _new_client(args, peer=True) if args.exercise_mail else None
    if peer is not None:
        peer.validate_binding()
        report["accounts_tested"] = 2
        since = (datetime.now(UTC) - timedelta(seconds=1)).isoformat(timespec="seconds")
        subject = f"Houmao qualification {uuid4().hex}"
        sent = client.send(
            sender_address=args.address,
            to_addresses=[args.peer_address],
            cc_addresses=(),
            subject=subject,
            body_content="Sandbox mail for Houmao protocol qualification.",
            attachments=(),
        )
        delivered = _wait_for_message(peer, subject, since)
        peek = peer.get_content(email_id=delivered["id"])
        marked = peer.mark(message_ref=delivered["id"], read=True, answered=None, archived=None)
        reply = peer.reply(
            message_ref=delivered["id"],
            sender_address=args.peer_address,
            body_content="Sandbox reply for Houmao protocol qualification.",
            attachments=(),
        )
        parent = peer.get_metadata(email_ids=[delivered["id"]]).messages[0]
        archived = peer.archive(message_ref=delivered["id"])
        reply_delivery = _wait_for_message(client, "Re: " + subject, since)
        client.archive(message_ref=reply_delivery["id"])
        report["mutations"] = {
            "messages_submitted": 2,
            "send_outcome": sent["mutation_receipt"]["outcome"],
            "reply_outcome": reply["mutation_receipt"]["outcome"],
            "peek_content_complete": peek["content_complete"],
            "read_marked": marked["read"],
            "reply_parent_read": parent["read"],
            "reply_parent_answered": parent["answered"],
            "parent_archived": archived["archived"],
            "parent_inbox_membership_removed": archived["box"] == "archive",
            "sandbox_reply_archived": True,
        }
    delta = client.changes(since_state=boundary, max_changes=100)
    report["email_changes"] = {
        "created": len(delta.created),
        "updated": len(delta.updated),
        "destroyed": len(delta.destroyed),
        "has_more_changes": delta.has_more_changes,
    }
    reconnect = _new_client(args)
    fresh_binding = reconnect.validate_binding()
    report["fresh_connection"] = {
        "same_account": fresh_binding.account_id == binding.account_id,
        "same_identity": fresh_binding.identity_id == binding.identity_id,
        "checkpoint_accepted": bool(
            reconnect.changes(since_state=delta.new_state, max_changes=5).new_state
        ),
    }
    report["jmap_method_calls"] = (
        client.method_call_count
        + reconnect.method_call_count
        + (peer.method_call_count if peer is not None else 0)
    )
    report["elapsed_seconds"] = round(monotonic() - started, 3)
    return report


def main() -> int:
    """Write a sanitized qualification result and never display private credentials."""
    parser = _parser()
    args = parser.parse_args()
    if args.exercise_mail and not (
        args.peer_login and args.peer_address and args.peer_credential_file
    ):
        parser.error("--exercise-mail requires explicit peer login, address, and credential file")
    if args.exercise_mail and args.peer_address.lower() == args.address.lower():
        parser.error(
            "Use a distinct peer; Stalwart may suppress same-account delivery as a duplicate"
        )
    repo_root = Path(__file__).resolve().parents[3]
    if args.output is not None and args.output.resolve().is_relative_to(repo_root):
        parser.error("--output must be outside the checkout")
    try:
        report = qualify(args)
    except StalwartMutationError as exc:
        report = {
            "schema_version": 1,
            "success": False,
            "operation": exc.operation,
            "outcome": exc.outcome,
            "reconciliation_required": True,
        }
        print(json.dumps(report, sort_keys=True))
        return 1
    except StalwartError as exc:
        print(
            json.dumps({"schema_version": 1, "success": False, "error": str(exc)}, sort_keys=True)
        )
        return 1
    report["success"] = True
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        args.output.chmod(0o600)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
