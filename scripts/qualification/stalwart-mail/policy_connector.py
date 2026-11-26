#!/usr/bin/env python3
"""Run the trusted Stalwart policy connector for one qualified binding."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

import uvicorn
from pydantic import BaseModel, ConfigDict

from houmao.gateway.access import read_private_access_file
from houmao.mailbox.policy import (
    initialize_mail_policy,
    read_mail_policy_receipt,
    set_mail_policy_owner,
)
from houmao.mailbox.stalwart import StalwartJmapClient
from houmao.mailbox.stalwart_policy_authority import (
    StalwartPolicyTarget,
    create_stalwart_policy_app,
)


class _Settings(BaseModel):
    """Provider-side settings supplied after independent deployment qualification."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    database: Path
    backend_id: str
    binding_id: str
    jmap_url: str
    login_identity: str
    credential_file: Path
    runtime_jmap_url: str
    runtime_login_identity: str
    runtime_credential_file: Path
    runtime_sender_address: str
    account_id: str
    archive_id: str
    active_script_blob: str
    initial_policy_blob: str


def _parser() -> argparse.ArgumentParser:
    """Select protected connector service, enrollment, or independent receipt lookup."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    action = parser.add_subparsers(dest="action", required=True)
    enroll = action.add_parser("owner-set")
    key = enroll.add_mutually_exclusive_group(required=True)
    key.add_argument("--public-key", type=Path)
    key.add_argument("--revoke", action="store_true")
    receipt = action.add_parser("receipt")
    receipt.add_argument("operation_id")
    serve = action.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=9443)
    serve.add_argument("--certificate", type=Path, required=True)
    serve.add_argument("--tls-key", type=Path, required=True)
    return parser


def main() -> None:
    """Keep provider credentials and owner enrollment inside the connector account."""

    args = _parser().parse_args()
    os.umask(0o077)
    settings = _Settings.model_validate_json(read_private_access_file(args.settings.absolute()))
    if not settings.database.is_absolute() or any(
        urlsplit(url).scheme != "https" for url in (settings.jmap_url, settings.runtime_jmap_url)
    ):
        raise ValueError("Select a private absolute database path and a provider HTTPS URL.")
    if args.action == "serve":
        read_private_access_file(settings.credential_file)
        read_private_access_file(settings.runtime_credential_file)
        provider = StalwartJmapClient(
            jmap_url=settings.jmap_url,
            login_identity=settings.login_identity,
            credential_file=settings.credential_file,
            account_id=settings.account_id,
        )
        runtime_client = StalwartJmapClient(
            jmap_url=settings.runtime_jmap_url,
            login_identity=settings.runtime_login_identity,
            credential_file=settings.runtime_credential_file,
            sender_address=settings.runtime_sender_address,
            account_id=settings.account_id,
        )
        target = StalwartPolicyTarget(
            backend_id=settings.backend_id,
            binding_id=settings.binding_id,
            account_id=settings.account_id,
            archive_id=settings.archive_id,
            active_script_blob=settings.active_script_blob,
            initial_policy_blob=settings.initial_policy_blob,
            client=provider,
            runtime_client=runtime_client,
        )
        uvicorn.run(
            create_stalwart_policy_app(database=settings.database, targets=[target]),
            host=args.host,
            port=args.port,
            ssl_certfile=str(args.certificate),
            ssl_keyfile=str(args.tls_key),
        )
        return

    if args.action == "receipt":
        database = sqlite3.connect(settings.database.as_uri() + "?mode=ro", uri=True)
    else:
        database = sqlite3.connect(settings.database)
    try:
        with database:
            if args.action == "owner-set":
                initialize_mail_policy(database)
                public_key = (
                    args.public_key.read_text(encoding="utf-8") if args.public_key else None
                )
                revision = set_mail_policy_owner(database, settings.binding_id, public_key)
                output = json.dumps({"binding_id": settings.binding_id, "revision": revision})
            else:
                receipt = read_mail_policy_receipt(
                    database, binding_id=settings.binding_id, operation_id=args.operation_id
                )
                if receipt is None:
                    raise SystemExit("No committed receipt for this operation.")
                output = receipt.model_dump_json()
    finally:
        database.close()
    print(output)


if __name__ == "__main__":
    main()
