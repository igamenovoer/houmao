"""Real OS probes for the opt-in execution-owner fixture boundaries."""

from __future__ import annotations

import json
import os
import pwd
from typing import Any

import pytest


def test_restricted_operator_can_only_delegate_the_fixed_helper(execution_accounts: Any) -> None:
    """Exercise designated RunAs users without granting general sudo access."""

    sandbox = execution_accounts
    assert sandbox.operator.uid != sandbox.owner.uid
    assert sandbox.owner.uid != sandbox.second_owner.uid
    assert sandbox.owner.uid != os.getuid()
    result = sandbox.delegated(sandbox.owner)
    assert f"uid={sandbox.owner.uid}({sandbox.owner.name})" in result.stdout
    assert f"uid={sandbox.second_owner.uid}" in sandbox.delegated(sandbox.second_owner).stdout
    for argv in (
        ["sudo", "-n", "-H", "-u", "root", "--", str(sandbox.helper)],
        ["sudo", "-n", "-H", "-u", sandbox.owner.name, "--", "/usr/bin/id"],
        ["sudo", "-n", "-H", "-u", sandbox.owner.name, "--", str(sandbox.helper), "extra"],
    ):
        denied = sandbox.run_as(sandbox.operator, argv, check=False)
        assert denied.returncode != 0
    assert sandbox.helper.stat().st_uid == 0
    assert not (sandbox.helper.stat().st_mode & 0o022)
    assert sandbox.root.stat().st_uid == 0
    assert not (sandbox.root.stat().st_mode & 0o022)


def test_owner_home_and_environment_do_not_use_operator_context(execution_accounts: Any) -> None:
    """Probe actual ownership and identity values through the allowed route."""

    sandbox = execution_accounts
    sandbox.install_helper(
        "#!/bin/sh\n"
        "unset TMUX TMUX_PANE SSH_AUTH_SOCK SUDO_USER SUDO_UID SUDO_GID SUDO_COMMAND\n"
        "umask 077\n"
        'printf owner-material > "$HOME/material"\n'
        'printf \'{"home":"%s","user":"%s","tmux":"%s","ssh_auth":"%s"}\\n\' '
        '"$HOME" "$USER" "${TMUX-}" "${SSH_AUTH_SOCK-}"\n'
    )
    result = sandbox.delegated(sandbox.owner)
    payload = json.loads(result.stdout)
    assert payload == {
        "home": str(sandbox.owner.home),
        "user": sandbox.owner.name,
        "tmux": "",
        "ssh_auth": "",
    }
    observed = sandbox.run_as(
        sandbox.owner,
        [
            "/usr/bin/stat",
            "-c",
            "%u:%g:%a",
            str(sandbox.owner.home / "material"),
        ],
    )
    assert observed.stdout.strip() == f"{sandbox.owner.uid}:{sandbox.owner.gid}:600"
    denied = sandbox.run_as(
        sandbox.operator,
        [
            "/usr/bin/cat",
            str(sandbox.owner.home / "material"),
        ],
        check=False,
    )
    assert denied.returncode != 0


def test_tmux_servers_with_identical_session_names_remain_distinct(execution_accounts: Any) -> None:
    """Verify private sockets isolate names and selected-server teardown."""

    sandbox = execution_accounts
    for account in (sandbox.operator, sandbox.owner, sandbox.second_owner):
        sandbox.tmux(account, ["new-session", "-d", "-s", "same-name", "sleep", "60"])
        sandbox.tmux(account, ["new-session", "-d", "-s", "sibling", "sleep", "60"])
    sandbox.tmux(sandbox.owner, ["kill-session", "-t", "same-name"])
    assert sandbox.tmux(sandbox.owner, ["has-session", "-t", "same-name"], check=False).returncode
    sandbox.tmux(sandbox.owner, ["has-session", "-t", "sibling"])
    sandbox.tmux(sandbox.operator, ["has-session", "-t", "same-name"])
    sandbox.tmux(sandbox.second_owner, ["has-session", "-t", "same-name"])


def test_fixture_ssh_observes_owner_and_pinned_host_key(
    execution_accounts: Any,
    execution_ssh: Any,
) -> None:
    """Use a real fixture sshd and reject an invalid host trust file."""

    sandbox, endpoint = execution_accounts, execution_ssh
    observed = sandbox.run_as(sandbox.operator, endpoint.client_argv(["/usr/bin/id", "-u"]))
    assert observed.stdout.strip() == str(sandbox.owner.uid)
    argv = endpoint.client_argv(["/usr/bin/id", "-u"])
    index = argv.index(f"UserKnownHostsFile={endpoint.known_hosts_file}")
    argv[index] = "UserKnownHostsFile=/dev/null"
    assert sandbox.run_as(sandbox.operator, argv, check=False).returncode != 0


def test_teardown_after_probe_failure_removes_only_fixture_state(execution_accounts: Any) -> None:
    """Make teardown idempotent and inspect its exact account/policy effects."""

    sandbox = execution_accounts
    names = [sandbox.operator.name, sandbox.owner.name, sandbox.second_owner.name]
    root, sudoers = sandbox.root, sandbox.sudoers_path
    unrelated = pwd.getpwnam("nobody")
    sandbox.tmux(sandbox.owner, ["new-session", "-d", "-s", "fixture", "sleep", "60"])
    with pytest.raises(RuntimeError, match="deliberate fixture probe failure"):
        try:
            raise RuntimeError("deliberate fixture probe failure")
        finally:
            sandbox.close()
    sandbox.close()
    assert not root.exists()
    assert not sudoers.exists()
    for name in names:
        with pytest.raises(KeyError):
            pwd.getpwnam(name)
    assert pwd.getpwnam("nobody") == unrelated
