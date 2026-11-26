"""Provision Stalwart principals for the local development email stack."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from houmao.mailbox.protocol import validate_mailbox_address
from houmao.mailbox.stalwart import StalwartError, StalwartManagementClient

OPERATOR_MAILBOX_NAME = "houmao-operator"


@dataclass(frozen=True)
class StackConfig:
    """Configuration loaded from the compose-local env file."""

    env_file: Path
    http_port: int
    webadmin_port: int
    hostname: str
    imap_port: int
    submission_port: int
    bootstrap_user: str
    bootstrap_password: str
    admin_user: str
    admin_password: str
    mail_domain: str
    seed_mailbox_name: str
    seed_mailbox_password: str
    seed_mailbox_email: str
    operator_mailbox_password: str

    @property
    def http_origin(self) -> str:
        """Return the published Stalwart HTTP origin."""

        return f"http://127.0.0.1:{self.http_port}"

    @property
    def api_base_url(self) -> str:
        """Return the Stalwart management API base URL."""

        return self.http_origin + "/jmap"

    @property
    def operator_mailbox_email(self) -> str:
        """Return the operator address on the configured mail domain."""

        return f"{OPERATOR_MAILBOX_NAME}@{self.mail_domain}"


def _strip_inline_comment(value: str) -> str:
    """Strip an unquoted inline comment from an env value."""

    in_single = False
    in_double = False
    result: list[str] = []

    for char in value:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            break
        result.append(char)

    stripped = "".join(result).strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def _load_env_file(env_file: Path) -> dict[str, str]:
    """Load simple KEY=VALUE pairs from an env file."""

    values: dict[str, str] = {}

    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise ValueError(f"Invalid env line in {env_file}: {line!r}")
        key, raw_value = stripped.split("=", 1)
        values[key.strip()] = _strip_inline_comment(raw_value)

    return values


def _require_value(values: dict[str, str], key: str) -> str:
    """Return a required env value or raise a clear error."""

    try:
        return values[key]
    except KeyError as exc:
        raise ValueError(f"Missing required env value: {key}") from exc


def load_stack_config(env_file: Path) -> StackConfig:
    """Build the stack configuration from the env file and process environment."""

    values = _load_env_file(env_file)
    values.update({key: value for key, value in os.environ.items() if key in values})

    admin_user = _require_value(values, "STALWART_ADMIN_USER")
    admin_password = _require_value(values, "STALWART_ADMIN_PASSWORD")
    seed_mailbox_name = _require_value(values, "SEED_MAILBOX_NAME")
    seed_mailbox_password = _require_value(values, "SEED_MAILBOX_PASSWORD")
    configured_passwords = {seed_mailbox_name: seed_mailbox_password, admin_user: admin_password}

    return StackConfig(
        env_file=env_file,
        http_port=int(_require_value(values, "STALWART_HTTP_PORT")),
        webadmin_port=int(values.get("STALWART_WEBADMIN_PORT", "10082")),
        hostname=_require_value(values, "STALWART_HOSTNAME"),
        imap_port=int(_require_value(values, "STALWART_IMAP_PORT")),
        submission_port=int(_require_value(values, "STALWART_SUBMISSION_PORT")),
        bootstrap_user=_require_value(values, "STALWART_BOOTSTRAP_USER"),
        bootstrap_password=_require_value(values, "STALWART_BOOTSTRAP_PASSWORD"),
        admin_user=admin_user,
        admin_password=admin_password,
        mail_domain=_require_value(values, "MAIL_DOMAIN"),
        seed_mailbox_name=seed_mailbox_name,
        seed_mailbox_password=seed_mailbox_password,
        seed_mailbox_email=_require_value(values, "SEED_MAILBOX_EMAIL"),
        operator_mailbox_password=configured_passwords.get(
            OPERATOR_MAILBOX_NAME, values.get("OPERATOR_MAILBOX_PASSWORD", admin_password)
        ),
    )


def _authorization_header(user: str, password: str) -> str:
    """Build the HTTP Basic authorization header value."""

    token = f"{user}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(token).decode("ascii")


def management(
    config: StackConfig, *, auth_user: str | None = None, auth_password: str | None = None
) -> StalwartManagementClient:
    """Make a local registry client using the chosen account."""
    return StalwartManagementClient(
        base_url=config.api_base_url,
        auth_headers={
            "Authorization": _authorization_header(
                auth_user if auth_user is not None else config.bootstrap_user,
                auth_password if auth_password is not None else config.bootstrap_password,
            )
        },
    )


def wait_for_api(config: StackConfig, timeout_seconds: int) -> None:
    """Wait until the Stalwart registry responds."""
    client = management(config)
    deadline = time.monotonic() + timeout_seconds
    last_error: StalwartError | None = None
    while time.monotonic() < deadline:
        try:
            client.registry_request("Domain/query", {"limit": 1})
            return
        except StalwartError as exc:
            last_error = exc
            time.sleep(1)
    raise StalwartError(f"Timed out waiting for the Stalwart registry: {last_error}")


def ensure_domain(config: StackConfig, domain_name: str) -> dict[str, Any]:
    """Ensure the target domain exists without changing an existing domain."""
    return management(config).ensure_domain(domain_name)


def configure_server(config: StackConfig) -> None:
    """Apply the development settings in recovery mode on a fresh store."""
    wait_for_api(config, 60)
    client = management(config)
    domain = client.ensure_domain(config.mail_domain)
    settings = {
        "SystemSettings": {"defaultHostname": config.hostname, "defaultDomainId": domain["id"]},
        "Imap": {"allowPlainTextAuth": True},
        "MtaStageAuth": {"saslMechanisms/else": "[plain, login]"},
        "Authentication": {"minPasswordLength": 5, "minPasswordStrength": "zero"},
    }
    for object_name, fields in settings.items():
        client.registry_request(f"{object_name}/set", {"update": {"singleton": fields}})

    existing = {
        row["name"]: row["id"]
        for row in client.list_registry_objects("NetworkListener", properties=("id", "name"))
    }
    listeners = {
        "http": (config.http_port, "http", False),
        "https": (config.webadmin_port, "http", True),
        "imap": (config.imap_port, "imap", False),
        "submission": (config.submission_port, "smtp", False),
    }
    for name, (port, protocol, tls) in listeners.items():
        fields = {
            "bind": {f"[::]:{port}": True},
            "protocol": protocol,
            "useTls": tls,
            "implicitTls": tls,
        }
        if name in existing:
            client.registry_request("NetworkListener/set", {"update": {existing[name]: fields}})
        else:
            client.registry_request(
                "NetworkListener/set", {"create": {"listener": {"name": name, **fields}}}
            )
    print("Configured the loopback development listeners and domain.")


def ensure_account(
    config: StackConfig,
    name: str,
    email: str,
    password: str,
    description: str,
    *,
    administrator: bool = False,
    reset_password: bool = False,
) -> bool:
    """Ensure one mailbox and preserve its password unless explicitly resetting it."""
    client = management(config)
    email = validate_mailbox_address(email)
    alias, domain = email.rsplit("@", 1)
    login = name if "@" in name else f"{name}@{domain}"
    existing = next(
        (
            account
            for account in client.list_principals(types=("individual",))
            if account["login"].casefold() == login.casefold()
        ),
        None,
    )
    if existing is None:
        client.create_principal(
            {
                "type": "individual",
                "name": name,
                "description": description or None,
                "emails": [email],
                "secrets": [password],
                "roles": ["admin" if administrator else "user"],
            }
        )
        print(f"Created mailbox account: {name} ({email})")
        return True

    changes: dict[str, object] = {}
    if email.casefold() not in {address.casefold() for address in existing["emails"]}:
        alias_domain = client.ensure_domain(domain, allow_create=False)
        aliases = dict(existing.get("aliases") or {})
        index = max((int(key) for key in aliases), default=-1) + 1
        aliases[str(index)] = {"name": alias, "domainId": alias_domain["id"]}
        changes["aliases"] = aliases
    if administrator and existing.get("roles") != {"@type": "Admin"}:
        changes["roles"] = {"@type": "Admin"}
    if description and description != existing.get("description"):
        changes["description"] = description
    if reset_password:
        changes["credentials"] = {"0": {"@type": "Password", "secret": password}}
    if changes:
        client.registry_request("Account/set", {"update": {existing["id"]: changes}})
        print(f"Updated mailbox account: {name} ({email})")
    return bool(changes)


def admin_mailbox_email(config: StackConfig) -> str:
    """Return the configured admin mailbox address."""
    if config.admin_user == config.seed_mailbox_name:
        return config.seed_mailbox_email
    return f"{config.admin_user}@{config.mail_domain}"


def require_account(config: StackConfig, name: str, address: str) -> dict[str, Any]:
    """Return the selected account and verify its expected address."""
    account = management(config).find_mailbox_account(name, address)
    if account is None:
        raise StalwartError(f"Missing development mailbox {name} ({address}).")
    return account


def ensure_operator_share(config: StackConfig) -> None:
    """Give the admin lookup and read access to the seeded operator's folders."""
    if config.admin_user == OPERATOR_MAILBOX_NAME:
        return
    admin = require_account(config, config.admin_user, admin_mailbox_email(config))
    operator = require_account(config, OPERATOR_MAILBOX_NAME, config.operator_mailbox_email)
    client = management(config)
    mailbox_id = operator["id"]
    folders = client.jmap_request(
        "Mailbox/get", {"accountId": mailbox_id, "properties": ["id", "shareWith"]}
    )
    rights = {"mayReadItems": True}
    admin_id = admin["id"]
    updates = {
        folder["id"]: {f"shareWith/{admin_id}": rights}
        for folder in folders["list"]
        if {
            key: value
            for key, value in ((folder.get("shareWith") or {}).get(admin_id) or {}).items()
            if value
        }
        != rights
    }
    if updates:
        client.jmap_request("Mailbox/set", {"accountId": mailbox_id, "update": updates})
    permissions = admin.get("permissions") or {"@type": "Inherit"}
    denied = permissions.get("disabledPermissions", {})
    if not denied.get("impersonate"):
        updated_permissions = {
            **permissions,
            "@type": "Merge" if permissions["@type"] == "Inherit" else permissions["@type"],
            "disabledPermissions": {**denied, "impersonate": True},
        }
        client.registry_request(
            "Account/set", {"update": {admin_id: {"permissions": updated_permissions}}}
        )


def verify_defaults(config: StackConfig) -> None:
    """Verify the domain, mailbox addresses, and admin management authorization."""
    management(config).ensure_domain(config.mail_domain, allow_create=False)
    admin = require_account(config, config.admin_user, admin_mailbox_email(config))
    require_account(config, config.seed_mailbox_name, config.seed_mailbox_email)
    operator = require_account(config, OPERATOR_MAILBOX_NAME, config.operator_mailbox_email)
    if admin.get("roles") != {"@type": "Admin"}:
        raise StalwartError(f"The seeded mailbox {config.admin_user} is missing the admin role.")
    admin_client = management(
        config, auth_user=config.admin_user, auth_password=config.admin_password
    )
    admin_client.registry_request("Domain/query", {"limit": 1})
    if admin["id"] != operator["id"]:
        folders = admin_client.jmap_request(
            "Mailbox/get",
            {"accountId": operator["id"], "properties": ["role", "myRights"]},
        )["list"]
        if not any(row.get("role") == "inbox" for row in folders) or any(
            {name for name, enabled in row["myRights"].items() if enabled} != {"mayReadItems"}
            for row in folders
        ):
            raise StalwartError("The operator mailbox is missing its read-only share to admin.")
    print(f"Verified seeded mailboxes on {config.mail_domain}.")


def verify_jmap_origin(config: StackConfig) -> None:
    """Check which API and upload origins the published JMAP session advertises."""

    discovery_url = config.http_origin + "/.well-known/jmap"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(discovery_url, timeout=5) as response:
            session_url = response.geturl()
            session = json.load(response)
    except (OSError, ValueError) as exc:
        raise StalwartError(f"Unable to read the JMAP session at {discovery_url}.") from exc

    if not isinstance(session, dict):
        raise StalwartError("Stalwart JMAP discovery returned an invalid session document.")

    expected = urllib.parse.urlsplit(config.http_origin)
    for name, url in (
        ("session URL", session_url),
        ("apiUrl", session.get("apiUrl")),
        ("uploadUrl", session.get("uploadUrl")),
    ):
        parts = urllib.parse.urlsplit(url) if isinstance(url, str) else None
        if parts is None or (parts.scheme, parts.netloc) != (expected.scheme, expected.netloc):
            raise StalwartError(
                f"Stalwart JMAP {name} must use {config.http_origin}. "
                "Check the active Stalwart configuration and published port."
            )

    print(f"Verified JMAP API and upload origin at {config.http_origin}.")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=Path(__file__).with_name(".env"),
        type=Path,
        help="Path to the compose-local env file.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "configure-server", help="Configure a fresh Stalwart store in recovery mode."
    )
    wait_parser = subparsers.add_parser("wait-api", help="Wait for the Stalwart API to respond.")
    wait_parser.add_argument(
        "--timeout-seconds",
        default=60,
        type=int,
        help="Maximum time to wait for the API.",
    )

    ensure_domain_parser = subparsers.add_parser(
        "ensure-domain",
        help="Create the target Stalwart domain if it does not already exist.",
    )
    ensure_domain_parser.add_argument("--name", required=False, help="Domain principal name.")

    ensure_account_parser = subparsers.add_parser(
        "ensure-account",
        help="Create or update a Stalwart mailbox principal.",
    )
    ensure_account_parser.add_argument("--name", required=True, help="Principal name.")
    ensure_account_parser.add_argument("--email", required=True, help="Primary mailbox address.")
    ensure_account_parser.add_argument("--password", required=True, help="Mailbox password.")
    ensure_account_parser.add_argument(
        "--description",
        default="Development mailbox account",
        help="Human-readable principal description.",
    )
    ensure_account_parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset the principal secret even when the account already exists.",
    )

    ensure_defaults_parser = subparsers.add_parser(
        "ensure-defaults",
        help="Ensure the configured development domain and default mailboxes exist.",
    )
    ensure_defaults_parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for the API before applying defaults.",
    )
    ensure_defaults_parser.add_argument(
        "--timeout-seconds",
        default=60,
        type=int,
        help="Maximum time to wait for the API when --wait is used.",
    )
    ensure_defaults_parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset the passwords of existing default mailboxes.",
    )

    subparsers.add_parser(
        "verify-defaults",
        help="Verify the configured development domain and default mailboxes.",
    )

    subparsers.add_parser(
        "verify-jmap-origin",
        help="Verify the origins advertised by the published JMAP discovery endpoint.",
    )

    return parser


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    config = load_stack_config(args.env_file)

    try:
        if args.command == "configure-server":
            configure_server(config)
        elif args.command == "wait-api":
            wait_for_api(config, args.timeout_seconds)
        elif args.command == "ensure-domain":
            ensure_domain(config, args.name or config.mail_domain)
        elif args.command == "ensure-account":
            ensure_domain(config, config.mail_domain)
            ensure_account(
                config,
                name=args.name,
                email=args.email,
                password=args.password,
                description=args.description,
                reset_password=args.reset_password,
            )
        elif args.command == "ensure-defaults":
            if args.wait:
                wait_for_api(config, args.timeout_seconds)
            ensure_domain(config, config.mail_domain)
            ensure_account(
                config,
                name=config.admin_user,
                email=admin_mailbox_email(config),
                password=config.admin_password,
                description="Development admin mailbox",
                administrator=True,
                reset_password=args.reset_password,
            )
            if config.seed_mailbox_name != config.admin_user:
                ensure_account(
                    config,
                    name=config.seed_mailbox_name,
                    email=config.seed_mailbox_email,
                    password=config.seed_mailbox_password,
                    description="Default development mailbox",
                    reset_password=args.reset_password,
                )
            configured_names = {config.admin_user, config.seed_mailbox_name}
            ensure_account(
                config,
                name=OPERATOR_MAILBOX_NAME,
                email=config.operator_mailbox_email,
                password=config.operator_mailbox_password,
                description=(
                    "" if OPERATOR_MAILBOX_NAME in configured_names else "Houmao operator mailbox"
                ),
                administrator=OPERATOR_MAILBOX_NAME == config.admin_user,
                reset_password=args.reset_password,
            )
            ensure_operator_share(config)
        elif args.command == "verify-defaults":
            wait_for_api(config, 30)
            verify_defaults(config)
        elif args.command == "verify-jmap-origin":
            verify_jmap_origin(config)
        else:
            parser.error(f"Unsupported command: {args.command}")
    except (StalwartError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
