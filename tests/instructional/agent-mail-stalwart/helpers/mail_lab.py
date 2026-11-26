#!/usr/bin/env python3
"""Instructional harness for managed-agent mail over a selected Stalwart service.

The helper attaches normal accounts to live managed agents, observes provider
truth through JMAP, drives operator mail, and records only secret-free run
metadata. It never starts, stops, resets, or reconfigures the mail service.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.mailbox.stalwart import (
    StalwartError,
    StalwartJmapClient,
    StalwartManagementClient,
    build_stalwart_credential_ref,
    ensure_stalwart_mailbox,
    jmap_origin,
    normalize_jmap_origins,
    runtime_stalwart_credential_path,
)

DEFAULT_MANAGER = Path.home() / ".local/share/uv/tools/houmao/bin/houmao-mgr"
_TMUX_ENV_KEYS = ("TMUX", "TMUX_PANE", "TMUX_TMPDIR")
_MAIL_CHANNEL = "online"
_PROVIDER = "stalwart"


class LabError(RuntimeError):
    """Report one actionable harness failure."""


def utc_now() -> str:
    """Return a compact UTC timestamp for run evidence."""

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def manager_path() -> Path:
    """Resolve the selected manager binary without ambient project state."""

    configured = os.environ.get("HOUMAO_MGR")
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
        raise LabError(f"HOUMAO_MGR is not a file: {path}")
    found = shutil.which("houmao-mgr")
    if found:
        return Path(found)
    if DEFAULT_MANAGER.is_file():
        return DEFAULT_MANAGER
    raise LabError("Set HOUMAO_MGR to the selected houmao-mgr binary.")


def run_env(run_dir: Path) -> dict[str, str]:
    """Build the isolated manager environment for one prepared fixture run."""

    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("HOUMAO_") and key not in _TMUX_ENV_KEYS
    }
    env.update(
        {
            "HOUMAO_GLOBAL_REGISTRY_DIR": str(run_dir / "registry"),
            "HOUMAO_GLOBAL_RUNTIME_DIR": str(run_dir / "runtime"),
            "HOUMAO_PROJECT_OVERLAY_DIR": str(run_dir / "workdir/.houmao"),
            "HOUMAO_GLOBAL_MAILBOX_DIR": str(run_dir / "workdir/.houmao/mailbox"),
            "HOUMAO_CLI_PRINT_STYLE": "json",
        }
    )
    return env


def manager_json(env: dict[str, str], arguments: list[str]) -> dict[str, Any]:
    """Run one maintained manager command and parse its JSON payload."""

    command = [str(manager_path()), "--print-json", *arguments]
    result = subprocess.run(
        command,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        message = detail[-1] if detail else "no output"
        raise LabError(f"houmao-mgr failed with exit {result.returncode}: {message}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise LabError("houmao-mgr returned non-JSON output") from exc
    if not isinstance(payload, dict):
        raise LabError("houmao-mgr returned an unexpected JSON shape")
    return payload


def read_json(path: Path, *, label: str) -> dict[str, Any]:
    """Read one JSON object and report the selected label on failure."""

    try:
        payload = json.loads(path.read_text())
    except OSError as exc:
        raise LabError(f"Cannot read {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LabError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise LabError(f"{label} must be a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    """Write one owner-private JSON document atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
        try:
            temporary.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            temporary.flush()
            os.chmod(temporary.name, mode)
            Path(temporary.name).replace(path)
        finally:
            Path(temporary.name).unlink(missing_ok=True)


def load_run(run_dir: Path) -> dict[str, Any]:
    """Load one launched fixture run and require its managed identity."""

    payload = read_json(run_dir / "run.json", label="fixture run")
    identity = payload.get("identity")
    if not isinstance(identity, dict) or not identity.get("agent_id"):
        raise LabError(f"Run is not launched: {run_dir}")
    return payload


def load_meta(path: Path) -> dict[str, Any]:
    """Load one run handle and reject an incomplete identity set."""

    payload = read_json(path, label="run metadata")
    required = (
        "run_a",
        "run_b",
        "mail",
        "tag",
    )
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise LabError(f"Run metadata is missing: {', '.join(missing)}")
    payload.setdefault("online", {})
    payload.setdefault("tmux_sockets", {})
    return payload


def _private_file(path: Path, *, label: str) -> Path:
    """Require a regular credential file readable only by its owner."""

    path = path.resolve()
    if not path.is_file():
        raise LabError(f"{label} is not a file: {path}")
    info = path.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise LabError(f"{label} needs owner-only permissions: {path}")
    return path


def _selected_path(value: object, *, base: Path, label: str) -> Path:
    """Resolve a configured credential reference relative to its private config."""

    if not isinstance(value, str) or not value.strip():
        raise LabError(f"{label} must name a credential file.")
    selected = Path(value).expanduser()
    return _private_file(base / selected, label=label)


def load_mail_config(path: Path, *, require_accounts: bool = True) -> dict[str, Any]:
    """Load an explicitly selected provider and its private credential references."""

    path = _private_file(path, label="Mail service config")
    config = read_json(path, label="mail service config")
    endpoint = config.get("jmap_url")
    if not isinstance(endpoint, str):
        raise LabError("Mail service config requires an HTTP(S) jmap_url.")
    jmap_origin(endpoint)
    origins = config.get("trusted_jmap_origins", [])
    if not isinstance(origins, list) or not all(isinstance(origin, str) for origin in origins):
        raise LabError("trusted_jmap_origins must be a list of exact origin strings.")
    config["trusted_jmap_origins"] = list(normalize_jmap_origins(origins))
    if config.get("admin_credential_file") is not None:
        if not isinstance(config.get("management_url"), str):
            raise LabError("Select management_url explicitly when using admin credentials.")
        jmap_origin(config["management_url"])
        config["admin_credential_file"] = str(
            _selected_path(
                config["admin_credential_file"], base=path.parent, label="Admin credential"
            )
        )

    if not require_accounts:
        return config

    accounts = config.get("accounts")
    if not isinstance(accounts, dict):
        raise LabError("Mail service config requires accounts a and b.")
    for role in ("a", "b"):
        account = accounts.get(role)
        if not isinstance(account, dict) or not all(
            isinstance(account.get(key), str) and account[key] for key in ("login", "address")
        ):
            raise LabError(f"Account {role} requires login, address, and credential_file.")
        account["credential_file"] = str(
            _selected_path(
                account.get("credential_file"), base=path.parent, label=f"Account {role} credential"
            )
        )
    return config


def _mail_account(meta: dict[str, Any], role: str) -> dict[str, Any]:
    """Return one selected account contract from the run handle."""

    if role not in ("a", "b"):
        raise LabError(f"Unknown role: {role}")
    return meta["mail"]["accounts"][role]


def _role_run(meta: dict[str, Any], role: str) -> tuple[Path, str]:
    """Return the selected role's fixture run directory and agent id."""

    if role == "a":
        run_dir = Path(str(meta["run_a"]))
        configured = meta.get("agent_a_id")
    elif role == "b":
        run_dir = Path(str(meta["run_b"]))
        configured = meta.get("agent_b_id")
    else:
        raise LabError(f"Unknown role: {role}")
    agent_id = str(configured) if configured else str(load_run(run_dir)["identity"]["agent_id"])
    return run_dir, agent_id


def _jmap_client(meta: dict[str, Any], role: str) -> StalwartJmapClient:
    """Build the product JMAP client for one selected account."""

    account = _mail_account(meta, role)
    mail = meta["mail"]
    return StalwartJmapClient(
        jmap_url=mail["jmap_url"],
        login_identity=account["login"],
        credential_file=Path(account["credential_file"]),
        timeout_seconds=15.0,
        sender_address=account["address"],
        account_id=account.get("account_id"),
        identity_id=account.get("identity_id"),
        allowed_api_origins=tuple(mail["trusted_jmap_origins"]),
        api_origin=account.get("api_origin"),
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Keep test management requests on the selected endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Reject redirected management commands."""

        return None


def _http_status(url: str, *, headers: dict[str, str] | None = None, method: str = "GET") -> int:
    """Return one HTTP response status without exposing response bodies."""

    request = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.build_opener(_NoRedirect()).open(request, timeout=10.0) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)
    except (urllib.error.URLError, TimeoutError) as error:
        raise LabError(f"Cannot reach the selected provider for {method}.") from error


def _admin_headers(mail: dict[str, Any]) -> dict[str, str]:
    """Build management headers from the explicitly selected private source."""

    source = mail.get("admin_credential_file")
    if not source:
        raise LabError("Provisioning and deprovisioning require an explicit admin_credential_file.")
    admin = read_json(Path(source), label="admin credential")
    if not all(isinstance(admin.get(key), str) and admin[key] for key in ("user", "password")):
        raise LabError("Admin credential requires nonempty user and password strings.")
    token = base64.b64encode(f"{admin['user']}:{admin['password']}".encode()).decode("ascii")
    return {"Accept": "application/json", "Authorization": f"Basic {token}"}


def _principal_index(management: StalwartManagementClient) -> dict[str, dict[str, Any]]:
    """Index provider individuals by canonical principal name."""

    return {
        principal["name"].casefold(): principal
        for principal in management.list_principals(types=("individual",))
        if isinstance(principal.get("name"), str)
    }


def _record_matches(principal: dict[str, Any], address: str) -> bool:
    """Require the provider's one address to equal the recorded run address."""

    emails = principal.get("emails")
    return isinstance(emails, list) and emails == [address.lower()]


def _deprovision(mail: dict[str, Any]) -> dict[str, Any]:
    """Delete confirmed run-owned principals and verify absence."""

    confirmed = mail.get("provisioned_accounts", [])
    pending = mail.get("pending_accounts", [])
    if not confirmed and not pending:
        return {"status": "skipped", "reason": "no provisioned accounts"}
    admin_headers = _admin_headers(mail)
    management = StalwartManagementClient(
        base_url=mail["management_url"], auth_headers=admin_headers
    )
    actual = _principal_index(management)

    results: dict[str, Any] = {}
    for recorded in [*confirmed, *pending]:
        name = recorded["name"]
        address = recorded["address"]
        principal = actual.get(name.casefold())
        if principal is None:
            results[name] = {"status": "already-absent"}
            continue
        expected_id = recorded.get("principal_id")
        if not _record_matches(principal, address) or (
            expected_id is not None and str(principal.get("id")) != expected_id
        ):
            results[name] = {"status": "ownership-mismatch"}
            continue
        if expected_id is None:
            # Product provisioning retains its generated credential before an
            # account creation request. Authenticate with it to verify a
            # pending write belongs to this run, even if readiness failed.
            try:
                StalwartJmapClient(
                    jmap_url=mail["jmap_url"],
                    login_identity=principal.get("login", principal["name"]),
                    credential_file=Path(recorded["credential_file"]),
                    allowed_api_origins=tuple(mail["trusted_jmap_origins"]),
                ).primary_account_id()
            except StalwartError:
                results[name] = {"status": "ownership-unverified"}
                continue
        try:
            management.delete_mailbox_account(
                name=principal["name"], provider_id=str(principal["id"])
            )
        except StalwartError:
            results[name] = {"principal": principal["name"], "status": "delete-failed"}
        else:
            results[name] = {"principal": principal["name"], "status": "delete-requested"}

    remaining = _principal_index(management)
    for name, result in results.items():
        result["absent"] = name.casefold() not in remaining
    return {
        "status": "deleted" if all(item["absent"] for item in results.values()) else "failed",
        "accounts": results,
    }


def command_provision(args: argparse.Namespace) -> int:
    """Provision one run-owned pair through the product provisioning entry point."""

    mail = load_mail_config(args.mail_config, require_accounts=False)
    admin_headers = _admin_headers(mail)
    management = StalwartManagementClient(
        base_url=mail["management_url"], auth_headers=admin_headers
    )
    domain = args.domain.strip().lower()
    prefix = args.prefix.strip()
    if not prefix or not all(char.isascii() and (char.isalnum() or char == "-") for char in prefix):
        raise LabError("Use a nonempty ASCII letter, digit, and hyphen account prefix.")
    output_path = args.output_config.resolve()
    if output_path.exists():
        raise LabError("Output config already exists. Select a new path for this pair.")

    names = {role: f"{prefix}-{role}" for role in ("a", "b")}
    existing = _principal_index(management)
    if any(name.casefold() in existing for name in names.values()):
        raise LabError("Select a unique prefix for the run-owned account pair.")
    domain_present = any(
        principal.get("name") == domain
        for principal in management.list_principals(types=("domain",))
    )
    runtime_root = args.accounts_dir.resolve()
    runtime_root.mkdir(parents=True, exist_ok=False, mode=0o700)
    output: dict[str, Any] = {
        "jmap_url": mail["jmap_url"],
        "management_url": mail["management_url"],
        "trusted_jmap_origins": mail["trusted_jmap_origins"],
        "admin_credential_file": mail["admin_credential_file"],
        "accounts": {},
        "provisioned_accounts": [],
        "pending_accounts": [],
        "provisioned_domain": domain,
        "provisioned_domain_created": None,
    }
    write_json(output_path, output)
    try:
        for role, name in names.items():
            address = f"{name.lower()}@{domain}"
            credential_ref = build_stalwart_credential_ref(
                address=address, jmap_url=mail["jmap_url"]
            )
            output["pending_accounts"] = [
                {
                    "name": name,
                    "address": address,
                    "credential_file": str(
                        runtime_stalwart_credential_path(runtime_root, credential_ref)
                    ),
                }
            ]
            write_json(output_path, output)
            binding = ensure_stalwart_mailbox(
                runtime_root=runtime_root,
                session_root=runtime_root / role,
                principal_id=name,
                address=address,
                jmap_url=mail["jmap_url"],
                management_url=mail["management_url"],
                trusted_jmap_origins=tuple(mail["trusted_jmap_origins"]),
                allow_create_domain=not args.require_existing_domain,
                management_auth_headers=admin_headers,
            )
            output["provisioned_accounts"].append(
                {
                    "name": binding.principal_name,
                    "address": address,
                    "principal_id": binding.management_principal_id,
                }
            )
            output["pending_accounts"] = []
            output["accounts"][role] = {
                "login": binding.login_identity,
                "address": address,
                "credential_file": str(binding.credential_file),
                "account_id": binding.account_id,
                "identity_id": binding.identity_id,
                "api_origin": binding.api_origin,
                "mailbox_roles": dict(binding.mailbox_roles),
            }
            output["provisioned_domain_created"] = not domain_present
            write_json(output_path, output)
    except (LabError, OSError, StalwartError) as exc:
        try:
            cleaned = _deprovision(output)["status"] != "failed"
        except (StalwartError, LabError):
            cleaned = False
        if not cleaned:
            raise LabError(
                f"Provisioning failed: {exc} Recover using deprovision with {output_path}."
            ) from exc
        raise

    print(
        json.dumps(
            {
                "status": "provisioned",
                "domain": domain,
                "domain_created": output["provisioned_domain_created"],
                "discovery_origin": jmap_origin(mail["jmap_url"]),
                "accounts": {
                    role: {key: value for key, value in account.items() if key != "credential_file"}
                    for role, account in output["accounts"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_deprovision(args: argparse.Namespace) -> int:
    """Recover run-owned provider accounts after partial setup."""

    result = _deprovision(load_mail_config(args.mail_config, require_accounts=False))
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["status"] == "failed")


def _page_messages(
    client: StalwartJmapClient, *, limit: int, box: str = "inbox"
) -> tuple[list[dict[str, Any]], bool]:
    """Read one bounded inbox page and report whether more records exist."""

    from houmao.mailbox.stalwart_models import JmapMetadataQuery

    page = client.query_metadata_page(
        query=JmapMetadataQuery(
            box=box,
            read_state="any",
            answered_state="any",
            archived=box == "archive",
            since=None,
        ),
        limit=limit,
    )
    return list(page.messages), bool(page.has_more)


def _message_summary(message: dict[str, Any]) -> dict[str, Any]:
    """Project one metadata record without bodies or foreign content."""

    keys = (
        "id",
        "threadId",
        "messageId",
        "receivedAt",
        "subject",
        "from",
        "to",
        "read",
        "answered",
        "archived",
        "box",
        "inReplyTo",
        "references",
        "preview",
    )
    result = {key: message.get(key) for key in keys}
    if "mutation_receipt" in message:
        result["mutation_receipt"] = message["mutation_receipt"]
    return result


def _tagged_messages(messages: list[dict[str, Any]], tag: str) -> list[dict[str, Any]]:
    """Keep only messages that carry this run's subject tag."""

    return [
        message
        for message in messages
        if isinstance(message.get("subject"), str) and tag in message["subject"]
    ]


def command_configure(args: argparse.Namespace) -> int:
    """Attach the selected accounts and write one secret-free run handle."""

    mail = load_mail_config(args.mail_config)
    run_a = args.run_a.resolve()
    run_b = args.run_b.resolve()
    handle: dict[str, Any] = {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "tag": args.tag,
        "run_a": str(run_a),
        "run_b": str(run_b),
        "mail": {
            "jmap_url": mail["jmap_url"],
            "trusted_jmap_origins": mail["trusted_jmap_origins"],
            "accounts": {
                role: {
                    key: value
                    for key, value in account.items()
                    if key
                    in {
                        "login",
                        "address",
                        "credential_file",
                        "account_id",
                        "identity_id",
                        "api_origin",
                    }
                }
                for role, account in mail["accounts"].items()
            },
        },
        "mail_config_path": str(args.mail_config.resolve()),
        "provisioned_domain": mail.get("provisioned_domain") or mail.get("provision_domain"),
        "provisioned_domain_created": mail.get("provisioned_domain_created"),
        "online": {},
        "tmux_sockets": {},
        "evidence_root": str(args.evidence_root.resolve()),
    }

    for role, run_dir in (("a", run_a), ("b", run_b)):
        run = load_run(run_dir)
        handle[f"agent_{role}_id"] = str(run["identity"]["agent_id"])
        socket = run.get("tmux_socket_path")
        if run.get("tmux_server_mode") != "new" or not isinstance(socket, str) or not socket:
            raise LabError(f"Prepare {role} with --tmux-server new before attaching mail.")
        if socket in handle["tmux_sockets"].values():
            raise LabError("Each agent requires a distinct private tmux server.")
        handle["tmux_sockets"][role] = socket
    write_json(args.run_meta.resolve(), handle)

    for role, run_dir in (("a", run_a), ("b", run_b)):
        run = load_run(run_dir)
        identity = run["identity"]
        agent_id = identity["agent_id"]
        env = run_env(run_dir)
        scope = ["agents", "single", "--agent-id", agent_id, "mailbox", "online"]
        status = manager_json(env, [*scope, "status"])
        account = handle["mail"]["accounts"][role]
        if status.get("binding_id") and status.get("address") != account["address"]:
            raise LabError(f"Agent {agent_id} already has a different online address.")
        arguments = [
            *scope,
            "attach",
            "--provider",
            _PROVIDER,
            "--jmap-url",
            mail["jmap_url"],
            "--login-identity",
            account["login"],
            "--address",
            account["address"],
            "--credential-source",
            account["credential_file"],
            "--expected-revision",
            str(status["revision"]),
        ]
        if account.get("account_id"):
            arguments.extend(["--account-id", account["account_id"]])
        for origin in mail["trusted_jmap_origins"]:
            arguments.extend(["--trust-jmap-origin", origin])
        status = manager_json(env, arguments)
        if status.get("state") != "configured" or not status.get("available"):
            raise LabError(
                f"Online binding for {agent_id} is unavailable with state {status.get('state')}."
            )
        handle["online"][role] = {
            "agent_id": agent_id,
            "agent_name": identity.get("agent_name"),
            "gateway": f"http://127.0.0.1:{identity['gateway_port']}",
            "revision": status.get("revision"),
            "binding_id": status.get("binding_id"),
            "address": status.get("address"),
            "provider": status.get("provider"),
            "discovery_origin": status.get("discovery_origin"),
            "api_origin": status.get("api_origin"),
            "trusted_jmap_origins": status.get("trusted_jmap_origins"),
        }
        write_json(args.run_meta.resolve(), handle)

    handle["agent_a_id"] = handle["online"]["a"]["agent_id"]
    handle["agent_b_id"] = handle["online"]["b"]["agent_id"]
    write_json(args.run_meta.resolve(), handle)
    print(json.dumps({"status": "configured", "run_meta": str(args.run_meta.resolve())}, indent=2))
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    """Check the service, both JMAP accounts, both agents, and both bindings."""

    meta = load_meta(args.run_meta.resolve())
    origin = jmap_origin(meta["mail"]["jmap_url"])
    result: dict[str, Any] = {
        "service": {"origin": origin, "live": _http_status(f"{origin}/healthz/live") == 200},
        "admin": {"checked": False},
        "accounts": {},
        "agents": {},
        "ok": True,
    }
    config_path = args.mail_config or Path(meta["mail_config_path"])
    mail = load_mail_config(config_path)
    if mail.get("admin_credential_file"):
        target = mail["management_url"].rstrip("/")
        status_code = _http_status(
            f"{target}/principal?types=domain&count=1&limit=1",
            headers=_admin_headers(mail),
        )
        result["admin"] = {"checked": True, "status": status_code, "ok": status_code == 200}
        result["ok"] = result["ok"] and result["admin"]["ok"]

    tag = str(meta["tag"])
    for role in ("a", "b"):
        account = _mail_account(meta, role)
        client = _jmap_client(meta, role)
        binding = client.validate_binding()
        messages, has_more = _page_messages(client, limit=200)
        tagged = _tagged_messages(messages, tag)
        unread = [message for message in messages if message.get("read") is not True]
        result["accounts"][role] = {
            "address": account["address"],
            "account_id": binding.account_id,
            "identity_id": binding.identity_id,
            "api_origin": jmap_origin(binding.api_url),
            "mailbox_roles": binding.mailbox_roles,
            "inbox_sample_count": len(messages),
            "inbox_has_more": has_more,
            "inbox_unread_sample_count": len(unread),
            "tagged_count": len(tagged),
        }
        if unread and not tagged:
            result["accounts"][role]["notifier_contamination_risk"] = True

        run_dir, agent_id = _role_run(meta, role)
        env = run_env(run_dir)
        state = manager_json(env, ["agents", "single", "--agent-id", agent_id, "state"])
        online = manager_json(
            env, ["agents", "single", "--agent-id", agent_id, "mailbox", "online", "status"]
        )
        expected_binding = str(meta["online"][role]["binding_id"])
        agent_ok = (
            state.get("availability") == "available"
            and (state.get("gateway") or {}).get("gateway_health") == "healthy"
            and online.get("state") == "configured"
            and online.get("available") is True
            and online.get("binding_id") == expected_binding
            and online.get("account_id") == binding.account_id
            and online.get("api_origin") == jmap_origin(binding.api_url)
        )
        result["agents"][role] = {
            "agent_id": agent_id,
            "availability": state.get("availability"),
            "gateway_health": (state.get("gateway") or {}).get("gateway_health"),
            "binding_id": online.get("binding_id"),
            "online_state": online.get("state"),
            "online_available": online.get("available"),
            "ok": agent_ok,
        }
        result["ok"] = result["ok"] and agent_ok

    result["ok"] = result["ok"] and result["service"]["live"]
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


def command_notifier(args: argparse.Namespace) -> int:
    """Enable, disable, or inspect the online gateway notifier for one role."""

    meta = load_meta(args.run_meta.resolve())
    run_dir, agent_id = _role_run(meta, args.role)
    env = run_env(run_dir)
    arguments = [
        "agents",
        "single",
        "--agent-id",
        agent_id,
        "gateway",
        "mail-notifier",
        args.action,
        "--channel",
        _MAIL_CHANNEL,
    ]
    if args.action == "enable":
        arguments.extend(
            [
                "--interval-seconds",
                str(args.interval_seconds),
                "--mode",
                args.mode,
            ]
        )
        if args.appendix_text is not None:
            arguments.extend(["--appendix-text", args.appendix_text])
    payload = manager_json(env, arguments)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_send(args: argparse.Namespace) -> int:
    """Send one run-tagged message through the selected agent's online binding."""

    meta = load_meta(args.run_meta.resolve())
    run_dir, agent_id = _role_run(meta, args.sender)
    recipient = _mail_account(meta, args.recipient)
    subject = (
        args.subject if str(meta["tag"]) in args.subject else f"[{meta['tag']}] {args.subject}"
    )
    env = run_env(run_dir)
    payload = manager_json(
        env,
        [
            "agents",
            "single",
            "--agent-id",
            agent_id,
            "mail",
            "send",
            "--channel",
            _MAIL_CHANNEL,
            "--expected-binding-id",
            str(meta["online"][args.sender]["binding_id"]),
            "--to",
            str(recipient["address"]),
            "--subject",
            subject,
            "--body-content",
            args.body,
        ],
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_peer_send(args: argparse.Namespace) -> int:
    """Send one run-tagged message from a scripted provider account."""

    meta = load_meta(args.run_meta.resolve())
    sender = _mail_account(meta, args.sender)
    recipient = _mail_account(meta, args.recipient)
    subject = (
        args.subject if str(meta["tag"]) in args.subject else f"[{meta['tag']}] {args.subject}"
    )
    client = _jmap_client(meta, args.sender)
    receipt = client.send(
        sender_address=str(sender["address"]),
        to_addresses=[str(recipient["address"])],
        cc_addresses=[],
        subject=subject,
        body_content=args.body,
        attachments=[],
    )
    print(json.dumps(_message_summary(receipt), indent=2, sort_keys=True))
    return 0


def command_observe(args: argparse.Namespace) -> int:
    """List provider-side inbox records carrying this run's subject tag."""

    meta = load_meta(args.run_meta.resolve())
    tag = args.tag or str(meta["tag"])
    client = _jmap_client(meta, args.role)
    messages, has_more = _page_messages(client, limit=args.limit, box=args.box)
    tagged = _tagged_messages(messages, tag)
    print(
        json.dumps(
            {
                "role": args.role,
                "address": _mail_account(meta, args.role)["address"],
                "tag": tag,
                "box": args.box,
                "sample_count": len(messages),
                "has_more": has_more,
                "count": len(tagged),
                "messages": [_message_summary(message) for message in tagged],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_content(args: argparse.Namespace) -> int:
    """Read one selected run-tagged message body for evidence."""

    meta = load_meta(args.run_meta.resolve())
    client = _jmap_client(meta, args.role)
    content = client.get_content(
        email_id=args.email_id,
        max_body_value_bytes=args.max_body_value_bytes,
    )
    print(
        json.dumps(
            {
                "role": args.role,
                "id": content.get("id"),
                "subject": content.get("subject"),
                "from": content.get("from"),
                "to": content.get("to"),
                "receivedAt": content.get("receivedAt"),
                "body": content.get("body"),
                "content_complete": content.get("content_complete"),
                "content_limit_reason": content.get("content_limit_reason"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def command_wait(args: argparse.Namespace) -> int:
    """Poll provider metadata until the selected tagged message appears."""

    meta = load_meta(args.run_meta.resolve())
    tag = args.tag or str(meta["tag"])
    client = _jmap_client(meta, args.role)
    deadline = time.monotonic() + args.timeout
    last_count = 0
    while time.monotonic() < deadline:
        messages, _ = _page_messages(client, limit=args.limit, box=args.box)
        tagged = _tagged_messages(messages, tag)
        last_count = len(tagged)
        if last_count >= args.min_count:
            print(
                json.dumps(
                    {
                        "role": args.role,
                        "tag": tag,
                        "box": args.box,
                        "count": last_count,
                        "messages": [_message_summary(message) for message in tagged],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        time.sleep(args.interval)
    raise LabError(
        f"Timed out after {args.timeout}s waiting for {args.min_count} tagged message(s) "
        f"in {args.role}'s {args.box}; last count={last_count}."
    )


def command_prompt(args: argparse.Namespace) -> int:
    """Submit one operator prompt through the selected live agent."""

    meta = load_meta(args.run_meta.resolve())
    run_dir, agent_id = _role_run(meta, args.role)
    payload = manager_json(
        run_env(run_dir),
        ["agents", "single", "--agent-id", agent_id, "prompt", "--prompt", args.prompt],
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_transcript(args: argparse.Namespace) -> int:
    """Copy the selected agent's DSH session transcript into evidence."""

    meta = load_meta(args.run_meta.resolve())
    run_dir, _ = _role_run(meta, args.role)
    sessions = sorted(
        (run_dir / "runtime" / "homes").rglob("session.v4.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not sessions:
        raise LabError(f"No DSH session transcript found under {run_dir}/runtime/homes")
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for index, source in enumerate(sessions[: args.max_files]):
        target = output_dir / f"{args.role}-transcript-{index}{source.suffix}"
        shutil.copy2(source, target)
        copied.append(str(target))
    print(json.dumps({"role": args.role, "copied": copied}, indent=2, sort_keys=True))
    return 0


def _kill_private_tmux(run_dir: Path, socket_path: str | None) -> dict[str, str]:
    """Stop one recorded private tmux server and remove its stale socket."""

    if not socket_path:
        return {"socket": "", "status": "not-recorded"}
    run = load_run(run_dir)
    if run.get("tmux_server_mode") != "new" or run.get("tmux_socket_path") != socket_path:
        return {"socket": "", "status": "unverified"}
    socket = Path(socket_path)
    if not socket.exists():
        return {"socket": str(socket), "status": "already-absent"}
    result = subprocess.run(
        ["tmux", "-S", str(socket), "kill-server"],
        env={key: value for key, value in os.environ.items() if key not in _TMUX_ENV_KEYS},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and "no server running" not in result.stderr.lower():
        return {"socket": str(socket), "status": "failed", "error": result.stderr.strip()}
    if socket.exists():
        try:
            socket.unlink()
        except OSError:
            pass
    return {"socket": str(socket), "status": "killed"}


def command_stop(args: argparse.Namespace) -> int:
    """Stop only the pair recorded in the run handle and preserve evidence."""

    meta = load_meta(args.run_meta.resolve())
    stopped: dict[str, Any] = {}
    for role in ("a", "b"):
        run_dir, agent_id = _role_run(meta, role)
        try:
            receipt = manager_json(
                run_env(run_dir), ["agents", "single", "--agent-id", agent_id, "stop"]
            )
            stopped[role] = {"agent_id": agent_id, "receipt": receipt}
        except LabError as exc:
            detail = str(exc)
            already_stopped = "relaunch" in detail and "cleanup" in detail
            stopped[role] = {
                "agent_id": agent_id,
                "already_stopped": already_stopped,
                "error": None if already_stopped else detail,
            }
    sockets = meta.get("tmux_sockets") or {}
    for role in ("a", "b"):
        if not sockets.get(role):
            try:
                run_dir, _ = _role_run(meta, role)
                sockets[role] = load_run(run_dir).get("tmux_socket_path")
            except LabError:
                sockets[role] = None
    private_tmux = {
        role: _kill_private_tmux(_role_run(meta, role)[0], sockets.get(role)) for role in ("a", "b")
    }
    mail = load_mail_config(Path(meta["mail_config_path"]), require_accounts=False)
    keep_accounts = bool(args.keep_accounts)
    deprovision = (
        {"status": "retained", "reason": "--keep-accounts selected"}
        if keep_accounts
        else _deprovision(mail)
    )
    cleaned = (
        (keep_accounts or deprovision["status"] != "failed")
        and all(
            result["status"] in {"killed", "already-absent"} for result in private_tmux.values()
        )
        and all(not result.get("error") for result in stopped.values())
    )
    account_retention = (
        {
            "action": "retained",
            "reason": "--keep-accounts selected; accounts and mail are left for review",
            "mail_config": str(meta["mail_config_path"]),
            "accounts": {
                role: {
                    "address": _mail_account(meta, role)["address"],
                    "login": _mail_account(meta, role)["login"],
                    "credential_file": _mail_account(meta, role)["credential_file"],
                }
                for role in ("a", "b")
            },
        }
        if keep_accounts
        else {"action": "deleted"}
    )
    domain = meta.get("provisioned_domain")
    domain_retention = (
        {
            "domain": domain,
            "created_by_run": meta.get("provisioned_domain_created"),
            "action": "retained",
            "reason": (
                "The mail domain is shared service state; the run deletes only its recorded "
                "accounts and leaves the domain in place."
            ),
        }
        if domain
        else {"status": "not-recorded"}
    )
    print(
        json.dumps(
            {
                "status": "stopped" if cleaned else "cleanup-incomplete",
                "run_meta": str(args.run_meta.resolve()),
                "agents": stopped,
                "private_tmux_servers_cleaned": private_tmux,
                "provisioned_accounts": deprovision,
                "account_retention": account_retention,
                "domain_retention": domain_retention,
                "evidence_root": meta.get("evidence_root"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return int(not cleaned)


def _add_run_meta(parser: argparse.ArgumentParser) -> None:
    """Add the shared run-handle argument."""

    parser.add_argument("--run-meta", type=Path, required=True, help="Run handle JSON path.")


def _add_mail_config(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    """Add the optional service-contract argument."""

    parser.add_argument(
        "--mail-config",
        type=Path,
        required=required,
        help="Explicitly selected private mail-service config JSON.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line surface used by the instructional cases."""

    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    provision = subparsers.add_parser(
        "provision", help="Create one run-owned account pair through the admin contract."
    )
    _add_mail_config(provision, required=True)
    provision.add_argument("--accounts-dir", type=Path, required=True)
    provision.add_argument("--output-config", type=Path, required=True)
    provision.add_argument("--prefix", required=True)
    provision.add_argument("--domain", required=True)
    provision.add_argument(
        "--require-existing-domain",
        action="store_true",
        help="Fail instead of creating the selected domain when it is absent.",
    )
    provision.set_defaults(func=command_provision)

    deprovision = subparsers.add_parser(
        "deprovision", help="Remove run-owned provider accounts after interrupted setup."
    )
    _add_mail_config(deprovision, required=True)
    deprovision.set_defaults(func=command_deprovision)

    configure = subparsers.add_parser(
        "configure", help="Attach the selected accounts and write one run handle."
    )
    configure.add_argument("--run-a", type=Path, required=True)
    configure.add_argument("--run-b", type=Path, required=True)
    configure.add_argument("--run-meta", type=Path, required=True)
    configure.add_argument("--evidence-root", type=Path, required=True)
    configure.add_argument("--tag", default=None)
    _add_mail_config(configure, required=True)
    configure.set_defaults(
        func=command_configure,
        tag=None,
    )

    doctor = subparsers.add_parser("doctor", help="Check service, accounts, agents, and bindings.")
    _add_run_meta(doctor)
    _add_mail_config(doctor)
    doctor.set_defaults(func=command_doctor)

    notifier = subparsers.add_parser("notifier", help="Control one online mail notifier.")
    _add_run_meta(notifier)
    notifier.add_argument("--role", choices=("a", "b"), required=True)
    notifier.add_argument("--action", choices=("enable", "disable", "status"), required=True)
    notifier.add_argument("--interval-seconds", type=int, default=20)
    notifier.add_argument("--mode", choices=("any_inbox", "unread_only"), default="unread_only")
    notifier.add_argument("--appendix-text", default=None)
    notifier.set_defaults(func=command_notifier)

    send = subparsers.add_parser("send", help="Send through one agent's online binding.")
    _add_run_meta(send)
    send.add_argument("--sender", choices=("a", "b"), required=True)
    send.add_argument("--recipient", choices=("a", "b"), required=True)
    send.add_argument("--subject", required=True)
    send.add_argument("--body", required=True)
    send.set_defaults(func=command_send)

    peer_send = subparsers.add_parser("peer-send", help="Send directly through JMAP.")
    _add_run_meta(peer_send)
    peer_send.add_argument("--sender", choices=("a", "b"), required=True)
    peer_send.add_argument("--recipient", choices=("a", "b"), required=True)
    peer_send.add_argument("--subject", required=True)
    peer_send.add_argument("--body", required=True)
    peer_send.set_defaults(func=command_peer_send)

    observe = subparsers.add_parser("observe", help="List tagged provider-side inbox records.")
    _add_run_meta(observe)
    observe.add_argument("--role", choices=("a", "b"), required=True)
    observe.add_argument("--tag", default=None)
    observe.add_argument("--box", choices=("inbox", "archive"), default="inbox")
    observe.add_argument("--limit", type=int, default=50)
    observe.set_defaults(func=command_observe)

    content = subparsers.add_parser("content", help="Read one selected message body.")
    _add_run_meta(content)
    content.add_argument("--role", choices=("a", "b"), required=True)
    content.add_argument("--email-id", required=True)
    content.add_argument("--max-body-value-bytes", type=int, default=4096)
    content.set_defaults(func=command_content)

    wait = subparsers.add_parser("wait", help="Wait for tagged provider-side delivery.")
    _add_run_meta(wait)
    wait.add_argument("--role", choices=("a", "b"), required=True)
    wait.add_argument("--tag", default=None)
    wait.add_argument("--box", choices=("inbox", "archive"), default="inbox")
    wait.add_argument("--min-count", type=int, default=1)
    wait.add_argument("--timeout", type=float, default=120.0)
    wait.add_argument("--interval", type=float, default=3.0)
    wait.add_argument("--limit", type=int, default=50)
    wait.set_defaults(func=command_wait)

    prompt = subparsers.add_parser("prompt", help="Submit one operator prompt.")
    _add_run_meta(prompt)
    prompt.add_argument("--role", choices=("a", "b"), required=True)
    prompt.add_argument("--prompt", required=True)
    prompt.set_defaults(func=command_prompt)

    transcript = subparsers.add_parser("transcript", help="Copy one agent's session transcript.")
    _add_run_meta(transcript)
    transcript.add_argument("--role", choices=("a", "b"), required=True)
    transcript.add_argument("--output", type=Path, required=True)
    transcript.add_argument("--max-files", type=int, default=1)
    transcript.set_defaults(func=command_transcript)

    stop = subparsers.add_parser("stop", help="Stop only the recorded agent pair.")
    _add_run_meta(stop)
    stop.add_argument(
        "--keep-accounts",
        action="store_true",
        help="Stop agents but retain the run-owned accounts and mail for review.",
    )
    stop.set_defaults(func=command_stop)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse one command and translate harness failures into exit code 2."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "configure" and args.tag is None:
        run_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        args.tag = f"houmao-e2e-{run_stamp}-{secrets.token_hex(3)}"
    try:
        return int(args.func(args))
    except (LabError, OSError, StalwartError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
