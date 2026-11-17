"""Opt-in execution-owner fixtures with explicit, fixture-owned OS resources.

Account and policy provisioning belongs to test setup. Product code must not
import this module or create operating-system users. Every resource uses one
random fixture namespace, and all tmux commands select its private socket.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
import grp
import os
from pathlib import Path
import pwd
import re
import shlex
import shutil
import socket
import subprocess
import tempfile
import time
import uuid

import pytest

_EXECUTION_SCRATCH_ROOT = Path("/tmp")


@dataclass(frozen=True)
class TestExecutionAccount:
    """Identify one account created exclusively by this fixture."""

    name: str
    uid: int
    gid: int
    home: Path


@dataclass(frozen=True)
class TestExecutionSsh:
    """Describe the fixture's loopback SSH endpoint and pinned host identity."""

    owner: TestExecutionAccount
    port: int
    identity_file: Path
    known_hosts_file: Path

    def client_argv(self, command: Sequence[str]) -> list[str]:
        """Build an explicit non-interactive client invocation."""

        return [
            "/usr/bin/ssh",
            "-T",
            "-o",
            "BatchMode=yes",
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "ForwardAgent=no",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            f"UserKnownHostsFile={self.known_hosts_file}",
            "-o",
            "GlobalKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=5",
            "-i",
            str(self.identity_file),
            "-p",
            str(self.port),
            f"{self.owner.name}@127.0.0.1",
            shlex.join(command),
        ]


class ExecutionSandbox:
    """Own temporary users, policy, processes, and isolated tmux resources."""

    def __init__(self) -> None:
        """Initialize an empty resource ledger."""

        self.m_root: Path | None = None
        self.m_accounts: list[TestExecutionAccount] = []
        self.m_sudoers_path: Path | None = None
        self.m_processes: list[subprocess.Popen[bytes]] = []
        self.m_helper_arguments: tuple[str, ...] = ()
        self.m_closed: bool = False

    @classmethod
    def create(cls) -> ExecutionSandbox:
        """Provision a unique test namespace after explicit prerequisite checks."""

        sandbox = cls()
        sandbox.m_root = Path(
            tempfile.mkdtemp(prefix="houmao-execution-", dir=_EXECUTION_SCRATCH_ROOT)
        )
        try:
            sandbox.root_command(["/usr/bin/chown", "0:0", str(sandbox.root)])
            sandbox.root_command(["/usr/bin/chmod", "0755", str(sandbox.root)])
            token = uuid.uuid4().hex[:10]
            for suffix in ("operator", "owner", "sibling"):
                name = f"hmx_{token}_{suffix}"
                account_home = sandbox.root / suffix
                sandbox.root_command(
                    [
                        "/usr/sbin/useradd",
                        "--no-create-home",
                        "--no-log-init",
                        "--user-group",
                        "--home-dir",
                        str(account_home),
                        "--shell",
                        "/bin/sh",
                        name,
                    ]
                )
                account = pwd.getpwnam(name)
                sandbox.m_accounts.append(
                    TestExecutionAccount(
                        name=name,
                        uid=account.pw_uid,
                        gid=account.pw_gid,
                        home=account_home,
                    )
                )
                sandbox.root_command(
                    [
                        "/usr/bin/install",
                        "-d",
                        "-m",
                        "0700",
                        "-o",
                        str(account.pw_uid),
                        "-g",
                        str(account.pw_gid),
                        str(account_home),
                    ]
                )
                # A non-password hash permits public-key login with UsePAM=no.
                # PasswordAuthentication is disabled on the fixture SSH server.
                sandbox.root_command(["/usr/sbin/usermod", "--password", "*", name])
            sandbox.install_helper("#!/bin/sh\nexec /usr/bin/id\n")
            policy = (
                f"{sandbox.operator.name} ALL=({sandbox.owner.name}, "
                f'{sandbox.second_owner.name}) NOPASSWD: {sandbox.helper} ""\n'
            )
            candidate = sandbox.root / "restricted.sudoers"
            sandbox.write_root_file(candidate, policy, mode="0440")
            sandbox.root_command(["/usr/sbin/visudo", "-c", "-f", str(candidate)])
            sandbox.m_sudoers_path = Path("/etc/sudoers.d") / f"houmao-exec-{token}"
            if sandbox.m_sudoers_path.exists():
                sandbox.m_sudoers_path = None
                raise RuntimeError("refusing to overwrite an existing test policy")
            sandbox.root_command(
                [
                    "/usr/bin/install",
                    "-m",
                    "0440",
                    "-o",
                    "0",
                    "-g",
                    "0",
                    str(candidate),
                    str(sandbox.m_sudoers_path),
                ]
            )
            return sandbox
        except BaseException:
            sandbox.close()
            raise

    @property
    def root(self) -> Path:
        """Return the outside-checkout scratch root."""

        assert self.m_root is not None
        return self.m_root

    @property
    def helper(self) -> Path:
        """Return the root-owned no-argument delegation entrypoint."""

        return self.root / "owner-entrypoint"

    @property
    def operator(self) -> TestExecutionAccount:
        """Return the account with restricted delegation authority."""

        return self.m_accounts[0]

    @property
    def owner(self) -> TestExecutionAccount:
        """Return the first unprivileged execution owner."""

        return self.m_accounts[1]

    @property
    def second_owner(self) -> TestExecutionAccount:
        """Return the second designated owner, independent from the first."""

        return self.m_accounts[2]

    @property
    def sudoers_path(self) -> Path:
        """Return the exact policy file owned by this fixture."""

        assert self.m_sudoers_path is not None
        return self.m_sudoers_path

    @staticmethod
    def clean_environment() -> dict[str, str]:
        """Avoid ambient auth, delegation, paths, and inherited tmux selectors."""

        return {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C.UTF-8"}

    def root_command(
        self,
        argv: Sequence[str],
        *,
        input: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run test setup or exact-resource cleanup with existing admin authority."""

        return subprocess.run(
            ["/usr/bin/sudo", "-n", "--", *argv],
            input=input,
            text=True,
            capture_output=True,
            check=check,
            env=self.clean_environment(),
            timeout=15,
        )

    def run_as(
        self,
        account: TestExecutionAccount,
        argv: Sequence[str],
        *,
        input: str | None = None,
        check: bool = True,
        timeout: float = 20,
    ) -> subprocess.CompletedProcess[str]:
        """Run a setup/probe command in one fixture-owned account."""

        self._require_owned_account(account)
        return subprocess.run(
            ["/usr/bin/sudo", "-n", "-H", "-u", account.name, "--", *argv],
            input=input,
            text=True,
            capture_output=True,
            check=check,
            env=self.clean_environment(),
            timeout=timeout,
        )

    def delegated(
        self,
        owner: TestExecutionAccount,
        *,
        input: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Invoke the allowed helper as the genuinely restricted operator."""

        self._require_owned_account(owner)
        return self.run_as(
            self.operator,
            [
                "/usr/bin/sudo",
                "-n",
                "-H",
                "-u",
                owner.name,
                "--",
                str(self.helper),
                *self.m_helper_arguments,
            ],
            input=input,
            check=check,
        )

    def install_helper(self, script: str) -> None:
        """Install a fixed root-owned helper rather than granting arbitrary argv."""

        self.write_root_file(self.helper, script, mode="0755")

    def authorize_helper_arguments(self, arguments: Sequence[str]) -> None:
        """Permit one exact fixed helper invocation for native-transport tests."""

        if any(re.fullmatch(r"[A-Za-z0-9_./-]+", argument) is None for argument in arguments):
            raise ValueError("fixture sudo arguments must be literal safe CLI words")
        suffix = " ".join(arguments) if arguments else '""'
        policy = (
            f"{self.operator.name} ALL=({self.owner.name}, {self.second_owner.name}) "
            f"NOPASSWD: {self.helper} {suffix}\n"
        )
        candidate = self.root / "restricted.sudoers"
        self.write_root_file(candidate, policy, mode="0440")
        self.root_command(["/usr/sbin/visudo", "-c", "-f", str(candidate)])
        self.root_command(
            [
                "/usr/bin/install",
                "-m",
                "0440",
                "-o",
                "0",
                "-g",
                "0",
                str(candidate),
                str(self.sudoers_path),
            ]
        )
        self.m_helper_arguments = tuple(arguments)

    def write_root_file(self, path: Path, text: str, *, mode: str = "0644") -> None:
        """Write one root-owned fixture file without shell interpolation."""

        canonical = Path(
            self.root_command(["/usr/bin/realpath", "-m", "--", str(path)]).stdout.strip()
        )
        if not canonical.is_relative_to(self.root):
            raise ValueError("fixture files must remain within its scratch root")
        self.root_command(["/usr/bin/tee", "--", str(path)], input=text)
        self.root_command(["/usr/bin/chown", "0:0", str(path)])
        self.root_command(["/usr/bin/chmod", mode, str(path)])

    def tmux(
        self,
        account: TestExecutionAccount,
        argv: Sequence[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Address only this account's explicit fixture-private tmux socket."""

        self._require_owned_account(account)
        return self.run_as(
            account,
            [
                "/usr/bin/tmux",
                "-f",
                "/dev/null",
                "-S",
                str(account.home / "tmux.sock"),
                *argv,
            ],
            check=check,
        )

    def start_ssh(self) -> TestExecutionSsh:
        """Start an isolated loopback sshd without touching the system service."""

        ssh_root = self.root / "ssh"
        self.root_command(["/usr/bin/install", "-d", "-m", "0755", str(ssh_root)])
        host_key, client_key = ssh_root / "host-key", ssh_root / "client-key"
        for key in (host_key, client_key):
            self.root_command(
                [
                    "/usr/bin/ssh-keygen",
                    "-q",
                    "-t",
                    "ed25519",
                    "-N",
                    "",
                    "-f",
                    str(key),
                ]
            )
        self.root_command(
            [
                "/usr/bin/chown",
                f"{self.operator.uid}:{self.operator.gid}",
                str(client_key),
            ]
        )
        public_client = self.root_command(["/usr/bin/cat", str(client_key) + ".pub"]).stdout
        owner_ssh = self.owner.home / ".ssh"
        self.root_command(
            [
                "/usr/bin/install",
                "-d",
                "-m",
                "0700",
                "-o",
                str(self.owner.uid),
                "-g",
                str(self.owner.gid),
                str(owner_ssh),
            ]
        )
        self.write_root_file(owner_ssh / "authorized_keys", public_client, mode="0600")
        self.root_command(
            [
                "/usr/bin/chown",
                f"{self.owner.uid}:{self.owner.gid}",
                str(owner_ssh / "authorized_keys"),
            ]
        )
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        public_host = self.root_command(["/usr/bin/cat", str(host_key) + ".pub"]).stdout
        key_kind, key_blob, *_ = public_host.split()
        known_hosts = ssh_root / "known_hosts"
        self.write_root_file(known_hosts, f"[127.0.0.1]:{port} {key_kind} {key_blob}\n")
        config = ssh_root / "sshd_config"
        self.write_root_file(
            config,
            "\n".join(
                [
                    f"Port {port}",
                    "ListenAddress 127.0.0.1",
                    f"HostKey {host_key}",
                    f"PidFile {ssh_root / 'sshd.pid'}",
                    "UsePAM no",
                    "PasswordAuthentication no",
                    "KbdInteractiveAuthentication no",
                    "AuthenticationMethods publickey",
                    "PubkeyAuthentication yes",
                    "PermitRootLogin no",
                    "PermitEmptyPasswords no",
                    "AllowAgentForwarding no",
                    "AllowTcpForwarding no",
                    "X11Forwarding no",
                    "PermitTunnel no",
                    "PermitUserEnvironment no",
                    "StrictModes yes",
                    "AuthorizedKeysFile .ssh/authorized_keys",
                    "LoginGraceTime 5",
                    f"AllowUsers {self.owner.name}",
                    "LogLevel ERROR",
                    "",
                ]
            ),
        )
        self.root_command(["/usr/sbin/sshd", "-t", "-f", str(config)])
        log = tempfile.TemporaryFile()
        process = subprocess.Popen(
            ["/usr/bin/sudo", "-n", "--", "/usr/sbin/sshd", "-D", "-e", "-f", str(config)],
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            env=self.clean_environment(),
            start_new_session=True,
        )
        self.m_processes.append(process)
        deadline = time.monotonic() + 5
        try:
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(f"fixture sshd exited: {log.read().decode()}")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        return TestExecutionSsh(self.owner, port, client_key, known_hosts)
                except OSError:
                    time.sleep(0.05)
            raise RuntimeError("fixture sshd did not listen within five seconds")
        finally:
            log.close()

    def close(self) -> None:
        """Delete only recorded fixture resources, preserving pre-existing state."""

        if self.m_closed:
            return
        failures: list[str] = []
        if self.m_sudoers_path is not None:
            self.root_command(["/usr/bin/rm", "-f", "--", str(self.m_sudoers_path)])
        for process in reversed(self.m_processes):
            if process.poll() is None:
                # Each subprocess owns a new session. Never kill by username or
                # match a process name, which could include unrelated work.
                self.root_command(
                    [
                        "/usr/bin/kill",
                        "--signal",
                        "TERM",
                        "--",
                        f"-{process.pid}",
                    ],
                    check=False,
                )
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.root_command(
                        [
                            "/usr/bin/kill",
                            "--signal",
                            "KILL",
                            "--",
                            f"-{process.pid}",
                        ],
                        check=False,
                    )
                    process.wait(timeout=5)
        for account in reversed(self.m_accounts):
            try:
                current = pwd.getpwnam(account.name)
            except KeyError:
                continue
            if (current.pw_uid, current.pw_gid, current.pw_dir) != (
                account.uid,
                account.gid,
                str(account.home),
            ):
                failures.append(f"refused cleanup of replaced account {account.name}")
                continue
            self.tmux(account, ["kill-server"], check=False)
            result = self.root_command(["/usr/sbin/userdel", account.name], check=False)
            if result.returncode:
                failures.append(f"userdel {account.name}: {result.stderr.strip()}")
                continue
            try:
                group = grp.getgrnam(account.name)
            except KeyError:
                continue
            if group.gr_gid == account.gid and not group.gr_mem:
                self.root_command(["/usr/sbin/groupdel", account.name], check=False)
        if self.m_root is not None:
            if self.m_root.parent != _EXECUTION_SCRATCH_ROOT or not self.m_root.name.startswith(
                "houmao-execution-"
            ):
                failures.append("refused cleanup of invalid scratch root")
            elif not failures:
                self.root_command(["/usr/bin/rm", "-rf", "--", str(self.m_root)])
        self.m_closed = not failures
        if failures:
            raise RuntimeError("; ".join(failures))

    def _require_owned_account(self, account: TestExecutionAccount) -> None:
        """Prevent a fixture API typo from targeting a pre-existing account."""

        if account not in self.m_accounts:
            raise ValueError("account is not owned by this fixture")


@pytest.fixture
def execution_accounts() -> Iterator[ExecutionSandbox]:
    """Create real users only after explicit integration-test opt-in."""

    if os.environ.get("HOUMAO_EXECUTION_INTEGRATION") != "1":
        pytest.skip("Set HOUMAO_EXECUTION_INTEGRATION=1 to provision temporary test accounts")
    required = ("sudo", "useradd", "userdel", "usermod", "visudo", "tmux")
    if any(shutil.which(name) is None for name in required):
        pytest.skip("execution-owner integration requires sudo/account tools and tmux")
    check = subprocess.run(
        ["sudo", "-n", "--", "/usr/bin/id", "-u"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if check.returncode or check.stdout.strip() != "0":
        pytest.skip("execution-owner fixture setup requires passwordless sudo root authority")
    sandbox = ExecutionSandbox.create()
    try:
        yield sandbox
    finally:
        sandbox.close()


@pytest.fixture
def execution_ssh(execution_accounts: ExecutionSandbox) -> TestExecutionSsh:
    """Use only a fixture-owned daemon, keys, and known-hosts file."""

    if any(shutil.which(name) is None for name in ("sshd", "ssh", "ssh-keygen")):
        pytest.skip("execution SSH qualification requires installed OpenSSH client/server")
    return execution_accounts.start_ssh()
