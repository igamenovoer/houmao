"""Export an explicitly provisioned CCCC Actor grant into a private owner document."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import tempfile
from urllib.parse import urlsplit

import httpx


PROJECT = Path(__file__).resolve().parents[2]


def _private_document(path: Path) -> dict[str, object]:
    """Read a selected private administrative document without ambient discovery."""

    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
        or path.resolve().is_relative_to(PROJECT)
    ):
        raise ValueError("Administrative credential file must be private and outside the checkout")
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get("token"), str):
        raise ValueError("Administrative document requires a token")
    return value


def provision(
    endpoint: str,
    group_id: str,
    actor_id: str,
    agent_id: str,
    output: Path,
    *,
    admin_credential: Path | None = None,
) -> dict[str, object]:
    """Issue a normal grant for an existing Actor and export it without printing secrets."""

    endpoint = endpoint.rstrip("/")
    parsed = urlsplit(endpoint)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Endpoint must not contain credentials")
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if parsed.scheme != "https" and not (local and parsed.scheme == "http"):
        raise ValueError("Remote service requires HTTPS")
    if not local and admin_credential is None:
        raise ValueError("Remote setup requires explicit operator credentials")
    output = output.expanduser().absolute()
    if output.resolve().is_relative_to(PROJECT) or output.exists() or output.is_symlink():
        raise ValueError("Select a fresh private output file outside the checkout")
    headers = {"Origin": endpoint, "Referer": endpoint + "/"}
    if admin_credential is not None:
        headers["Authorization"] = "Bearer " + str(_private_document(admin_credential)["token"])
    with httpx.Client(trust_env=False, timeout=15, follow_redirects=False) as client:
        response = client.post(
            endpoint + "/api/v1/external-receiver/v1/grants",
            headers=headers,
            json={"group_id": group_id, "actor_id": actor_id},
        )
        if response.status_code != 200:
            raise RuntimeError("CCCC operator grant issuance failed")
        envelope = response.json()
    grant = envelope.get("result", {})
    if not envelope.get("ok") or not isinstance(grant.get("token"), str):
        raise RuntimeError("CCCC returned an invalid grant result")
    if grant.get("group_id") != group_id or grant.get("actor_id") != actor_id:
        raise RuntimeError("CCCC returned a grant outside the requested Actor scope")
    document = {
        "schema_version": 1,
        "agent_id": agent_id,
        "endpoint": endpoint,
        "group_id": group_id,
        "actor_id": actor_id,
        "actor_generation": grant["actor_generation"],
        "token": grant["token"],
    }
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix="cccc-grant-", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(document, stream)
            stream.write("\n")
        # Link is atomic and refuses an output created by another setup process.
        os.link(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "group_id": group_id,
        "actor_id": actor_id,
        "actor_generation": grant["actor_generation"],
        "grant_id": grant.get("grant_id"),
        "credential_file": str(output),
    }


def main() -> None:
    """Perform only the explicitly selected administrative grant-export action."""

    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("endpoint", "group-id", "actor-id", "agent-id"):
        parser.add_argument("--" + argument, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--admin-credential", type=Path)
    args = parser.parse_args()
    try:
        result = provision(
            args.endpoint,
            args.group_id,
            args.actor_id,
            args.agent_id,
            args.output,
            admin_credential=args.admin_credential,
        )
        print(json.dumps(result))
    except (OSError, ValueError, KeyError, RuntimeError, httpx.HTTPError):
        parser.exit(
            1, "Actor grant setup failed; verify selected operator access and private output\n"
        )


if __name__ == "__main__":
    main()
