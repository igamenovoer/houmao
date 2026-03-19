"""Provision Stalwart principals for the local development email stack."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StackConfig:
    """Configuration loaded from the compose-local env file."""

    env_file: Path
    http_port: int
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

    @property
    def api_base_url(self) -> str:
        """Return the Stalwart management API base URL."""

        return f"http://127.0.0.1:{self.http_port}/api"


class ApiRequestError(RuntimeError):
    """Raised when a Stalwart API request fails."""


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

    return StackConfig(
        env_file=env_file,
        http_port=int(_require_value(values, "STALWART_HTTP_PORT")),
        imap_port=int(_require_value(values, "STALWART_IMAP_PORT")),
        submission_port=int(_require_value(values, "STALWART_SUBMISSION_PORT")),
        bootstrap_user=_require_value(values, "STALWART_BOOTSTRAP_USER"),
        bootstrap_password=_require_value(values, "STALWART_BOOTSTRAP_PASSWORD"),
        admin_user=_require_value(values, "STALWART_ADMIN_USER"),
        admin_password=_require_value(values, "STALWART_ADMIN_PASSWORD"),
        mail_domain=_require_value(values, "MAIL_DOMAIN"),
        seed_mailbox_name=_require_value(values, "SEED_MAILBOX_NAME"),
        seed_mailbox_password=_require_value(values, "SEED_MAILBOX_PASSWORD"),
        seed_mailbox_email=_require_value(values, "SEED_MAILBOX_EMAIL"),
    )


def _authorization_header(user: str, password: str) -> str:
    """Build the HTTP Basic authorization header value."""

    token = f"{user}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(token).decode("ascii")


def api_request(
    config: StackConfig,
    method: str,
    path: str,
    payload: Any | None = None,
    ok_statuses: tuple[int, ...] = (200,),
    auth_user: str | None = None,
    auth_password: str | None = None,
) -> Any:
    """Send a JSON request to the Stalwart management API."""

    url = config.api_base_url + path
    body: bytes | None = None
    headers = {
        "Accept": "application/json",
        "Authorization": _authorization_header(
            auth_user or config.bootstrap_user,
            auth_password or config.bootstrap_password,
        ),
    }

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            status = response.getcode()
            raw_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
        if status not in ok_statuses:
            raise ApiRequestError(
                f"{method} {path} failed with HTTP {status}: {raw_body or exc.reason}"
            ) from exc
        return json.loads(raw_body) if raw_body else None
    except urllib.error.URLError as exc:
        raise ApiRequestError(f"{method} {path} failed: {exc.reason}") from exc

    if status not in ok_statuses:
        raise ApiRequestError(f"{method} {path} returned unexpected status {status}: {raw_body}")

    return json.loads(raw_body) if raw_body else None


def get_principal(config: StackConfig, principal_name: str) -> dict[str, Any] | None:
    """Fetch a principal by name, returning None when it does not exist."""

    encoded_name = urllib.parse.quote(principal_name, safe="")
    try:
        response = api_request(
            config,
            method="GET",
            path=f"/principal/{encoded_name}",
            ok_statuses=(200, 404),
        )
    except ApiRequestError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise

    if not response or "data" not in response:
        return None
    return response["data"]


def normalize_list(value: Any) -> list[str]:
    """Normalize Stalwart response values that may be scalars or arrays."""

    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return [str(value)]


def wait_for_api(config: StackConfig, timeout_seconds: int) -> None:
    """Wait until the Stalwart management API responds."""

    deadline = time.monotonic() + timeout_seconds
    last_error: str | None = None

    while time.monotonic() < deadline:
        try:
            api_request(
                config,
                method="GET",
                path="/principal?types=domain&count=1&limit=1",
                ok_statuses=(200,),
            )
            return
        except ApiRequestError as exc:
            last_error = str(exc)
            time.sleep(1)

    raise ApiRequestError(f"Timed out waiting for Stalwart API: {last_error}")


def ensure_domain(config: StackConfig, domain_name: str) -> bool:
    """Ensure that the target domain principal exists."""

    existing = get_principal(config, domain_name)
    if existing is not None:
        if existing.get("type") != "domain":
            raise ApiRequestError(f"Principal {domain_name!r} exists but is not a domain")
        print(f"Domain already exists: {domain_name}")
        return False

    payload = {
        "type": "domain",
        "name": domain_name,
        "description": f"Development domain {domain_name}",
        "secrets": [],
        "emails": [],
        "urls": [],
        "memberOf": [],
        "roles": [],
        "lists": [],
        "members": [],
        "enabledPermissions": [],
        "disabledPermissions": [],
        "externalMembers": [],
    }
    api_request(config, method="POST", path="/principal", payload=payload, ok_statuses=(200,))
    print(f"Created domain: {domain_name}")
    return True


def ensure_account(
    config: StackConfig,
    name: str,
    email: str,
    password: str,
    description: str,
    roles: list[str] | None = None,
    reset_password: bool = False,
) -> bool:
    """Ensure that an individual mailbox principal exists."""

    desired_roles = roles or ["user"]
    existing = get_principal(config, name)
    if existing is None:
        payload = {
            "type": "individual",
            "name": name,
            "description": description,
            "secrets": [password],
            "emails": [email],
            "memberOf": [],
            "roles": desired_roles,
            "lists": [],
            "members": [],
            "enabledPermissions": [],
            "disabledPermissions": [],
            "externalMembers": [],
        }
        api_request(config, method="POST", path="/principal", payload=payload, ok_statuses=(200,))
        print(f"Created mailbox account: {name} ({email})")
        return True

    if existing.get("type") != "individual":
        raise ApiRequestError(f"Principal {name!r} exists but is not an individual account")

    updates: list[dict[str, Any]] = []
    existing_emails = normalize_list(existing.get("emails"))
    existing_roles = normalize_list(existing.get("roles"))

    if email not in existing_emails:
        updates.append({"action": "addItem", "field": "emails", "value": email})
    for role in desired_roles:
        if role not in existing_roles:
            updates.append({"action": "addItem", "field": "roles", "value": role})
    if description and existing.get("description") != description:
        updates.append({"action": "set", "field": "description", "value": description})
    if reset_password:
        updates.append({"action": "set", "field": "secrets", "value": [password]})

    if updates:
        encoded_name = urllib.parse.quote(name, safe="")
        api_request(
            config,
            method="PATCH",
            path=f"/principal/{encoded_name}",
            payload=updates,
            ok_statuses=(200,),
        )
        print(f"Updated mailbox account: {name}")
        return True

    print(f"Mailbox account already exists: {name} ({email})")
    return False


def admin_mailbox_email(config: StackConfig) -> str:
    """Return the email address that should be assigned to the provisioned admin mailbox."""

    if config.admin_user == config.seed_mailbox_name:
        return config.seed_mailbox_email
    return f"{config.admin_user}@{config.mail_domain}"


def verify_defaults(config: StackConfig) -> None:
    """Verify that the default domain and seeded mailbox principal exist."""

    domain = get_principal(config, config.mail_domain)
    if domain is None or domain.get("type") != "domain":
        raise ApiRequestError(f"Missing expected domain principal: {config.mail_domain}")

    admin_account = get_principal(config, config.admin_user)
    if admin_account is None or admin_account.get("type") != "individual":
        raise ApiRequestError(f"Missing expected admin principal: {config.admin_user}")

    admin_roles = normalize_list(admin_account.get("roles"))
    if "admin" not in admin_roles:
        raise ApiRequestError(f"Admin principal {config.admin_user!r} is missing the admin role")

    expected_admin_email = admin_mailbox_email(config)
    admin_emails = normalize_list(admin_account.get("emails"))
    if expected_admin_email not in admin_emails:
        raise ApiRequestError(
            f"Admin principal {config.admin_user!r} is missing email {expected_admin_email!r}"
        )

    api_request(
        config,
        method="GET",
        path="/principal?types=domain&count=1&limit=1",
        ok_statuses=(200,),
        auth_user=config.admin_user,
        auth_password=config.admin_password,
    )

    account = get_principal(config, config.seed_mailbox_name)
    if account is None or account.get("type") != "individual":
        raise ApiRequestError(f"Missing expected mailbox principal: {config.seed_mailbox_name}")

    emails = normalize_list(account.get("emails"))
    if config.seed_mailbox_email not in emails:
        raise ApiRequestError(
            f"Mailbox principal {config.seed_mailbox_name!r} is missing email "
            f"{config.seed_mailbox_email!r}"
        )

    print(
        "Verified default principals: "
        f"domain={config.mail_domain}, "
        f"admin={config.admin_user}, "
        f"mailbox={config.seed_mailbox_name}, "
        f"email={config.seed_mailbox_email}"
    )


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
        help="Wait for the API and ensure the configured development domain and mailbox exist.",
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
        help="Reset the seeded mailbox password when the account already exists.",
    )

    subparsers.add_parser(
        "verify-defaults",
        help="Verify that the configured development domain and mailbox exist.",
    )

    return parser


def main() -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args()
    config = load_stack_config(args.env_file)

    try:
        if args.command == "wait-api":
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
                roles=["user"],
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
                roles=["admin"],
                reset_password=args.reset_password,
            )
            if config.seed_mailbox_name != config.admin_user:
                ensure_account(
                    config,
                    name=config.seed_mailbox_name,
                    email=config.seed_mailbox_email,
                    password=config.seed_mailbox_password,
                    description="Default development mailbox",
                    roles=["user"],
                    reset_password=args.reset_password,
                )
        elif args.command == "verify-defaults":
            wait_for_api(config, 30)
            verify_defaults(config)
        else:
            parser.error(f"Unsupported command: {args.command}")
    except (ApiRequestError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
