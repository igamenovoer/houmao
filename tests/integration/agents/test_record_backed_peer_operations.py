"""Qualify peer mail and prompt dispatch through isolated managed fixture runs."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import ExitStack
from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time
from typing import Any

import pytest

from houmao.execution.tmux import TmuxServer
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR


@dataclass(frozen=True)
class _Peer:
    """One prepared fixture and its exact owner and caller locations."""

    root: Path
    workdir: Path
    agent_id: str
    session_name: str
    address: str
    server: TmuxServer
    owner_env: dict[str, str]
    caller_env: dict[str, str]
    cli: str
    socket_log: Path

    @property
    def scope(self) -> list[str]:
        """Select this peer through the shared registry."""

        return ["agents", "single", "--agent-id", self.agent_id]

    def manager(self, args: list[str], *, from_pane: bool = False) -> dict[str, Any]:
        """Invoke the real CLI from this fixture's owner or managed TUI environment."""

        result = self.invoke(args, env=self.caller_env if from_pane else self.owner_env)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert isinstance(payload, dict)
        return payload

    def invoke(
        self, args: list[str], *, env: Mapping[str, str]
    ) -> subprocess.CompletedProcess[str]:
        """Run the maintained command entrypoint without a process-wide env change."""

        return subprocess.run(
            [self.cli, "--print-json", *args],
            cwd=self.workdir,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )


def _write_fake_codex(root: Path) -> Path:
    """Run a named synthetic Codex process with a ready screen and captured input."""

    program = root / "synthetic_tui.py"
    program.write_text(
        "import json, os, pathlib, tty\n"
        "tty.setraw(0)\n"
        "os.write(1, ('\\033[?2004h\\033[1m›\\033[0m "
        "\\033[2mAsk Codex to do anything\\033[0m\\r\\n\\r\\n"
        "  GPT-6.1-Sol medium · /workspace\\r\\n  ? for shortcuts\\r\\n').encode())\n"
        "context = {key: os.environ[key] for key in ('TMUX', 'TMUX_PANE')}\n"
        "with pathlib.Path('terminal-input').open('wb', buffering=0) as output:\n"
        "    pending = pathlib.Path('terminal-context.pending')\n"
        "    pending.write_text(json.dumps(context))\n"
        "    pending.rename('terminal-context.json')\n"
        "    while chunk := os.read(0, 4096):\n"
        "        output.write(chunk)\n",
        encoding="utf-8",
    )
    executable = root / "codex"
    executable.write_text(
        "#!/bin/bash\n"
        'if [ "$1" = "--version" ]; then\n'
        "  printf 'codex-cli 0.167.2\\n'\n"
        "  exit 0\n"
        "fi\n"
        f"exec -a codex {shlex.quote(sys.executable)} {shlex.quote(str(program))}\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return executable


def _wait_for_file(path: Path, *, contents: bytes | None = None) -> bytes:
    """Wait for one fixture file or for exact bytes to arrive at its pane."""

    last = b""
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if path.is_file():
            last = path.read_bytes()
            if contents is None or last == contents:
                return last
        time.sleep(0.02)
    pytest.fail(f"Timed out waiting for {path.name}; last contents: {last!r}")


def _write_restricting_shim(shim: Path, log: Path, *, socket: str, tmux: str) -> None:
    """Allow only the test-owned socket and record attempted explicit selectors."""

    shim.parent.mkdir()
    destination = shlex.quote(str(log))
    allowed = shlex.quote(socket)
    shim.write_text(
        "#!/bin/sh\nunset TMUX TMUX_PANE\n"
        'case "$1" in\n'
        f"""  -S) printf '%s\\n' "$2" >> {destination} ;;\n"""
        f"""  -S*) printf '%s\\n' "${{1#-S}}" >> {destination} ;;\n"""
        "esac\n"
        'case "$1" in\n'
        f'  -S) [ "$2" = {allowed} ] || exit 2; shift 2 ;;\n'
        f"  -S{allowed}) shift ;;\n"
        "  -S*|-L*) exit 2 ;;\n"
        "esac\n"
        'case "$1" in -S*|-L*) exit 2 ;; esac\n'
        f'exec {shlex.quote(tmux)} -S {allowed} "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o700)


@pytest.fixture
def detached_peers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[_Peer, _Peer]]:
    """Prepare two unattended runs with one shared registry and offline authority."""

    tmux = shutil.which("tmux")
    cli = shutil.which("houmao-mgr")
    if tmux is None or cli is None or shutil.which("git") is None:
        pytest.skip("tmux, git, and houmao-mgr are required for managed fixture qualification")
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    fixture_path = Path(__file__).resolve().parents[3] / "scripts/agents/test-fixtures"
    monkeypatch.syspath_prepend(str(fixture_path))
    config = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    executable = _write_fake_codex(tmp_path)
    selection = config.resolve_config(
        case="self-hosted",
        client="codex",
        mode="tui",
        surface="manager",
        process_env={
            "HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
            "HOUMAO_TEST_SELF_HOSTED_MODEL": "synthetic-model",
        },
    )

    peers = []
    registry = tmp_path / "registry"
    mailbox = tmp_path / "mailbox"
    prepare.manager_root_call(
        ["mailbox", "init", "--mailbox-root", str(mailbox), "--registry-root", str(registry)],
        env=prepare.isolated_environment({}, run_dir=tmp_path),
    )
    with ExitStack() as cleanup:
        for name in ("sender", "recipient"):
            run = prepare.prepare_run(
                selection, run_root=tmp_path / "runs", executable=str(executable), tmux_server="new"
            )
            root = Path(run["run_dir"])
            private_env_path = root / "private-env.json"
            private_env = json.loads(private_env_path.read_text())
            private_env[HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR] = str(registry)
            prepare.write_json(private_env_path, private_env)
            launched = launch.launch_run(root)
            identity = launched["identity"]
            server = TmuxServer(launched["tmux_socket_path"], executable=tmux)
            cleanup.callback(server.command, ["kill-server"])
            cleanup.callback(launch.stop_run, root)
            socket_log = root / "tmux-sockets.log"
            _write_restricting_shim(
                root / "bin/tmux", socket_log, socket=server.socket_path, tmux=tmux
            )
            workdir = Path(run["workdir"])
            context = json.loads(_wait_for_file(workdir / "terminal-context.json"))
            assert context["TMUX"].rsplit(",", 2)[0] == server.socket_path
            owner_env = launch.run_environment(run)
            owner_env["PATH"] = str(root / "bin") + os.pathsep + owner_env["PATH"]
            peer = _Peer(
                root=root,
                workdir=workdir,
                agent_id=identity["agent_id"],
                session_name=identity["tmux_session_name"],
                address=f"{name}@houmao.localhost",
                server=server,
                owner_env=owner_env,
                caller_env={**owner_env, **context},
                cli=cli,
                socket_log=socket_log,
            )
            peer.manager([*peer.scope, "gateway", "detach"])
            join = peer.manager(
                [
                    *peer.scope,
                    "mailbox",
                    "offline",
                    "join",
                    "--mailbox-root",
                    str(mailbox),
                    "--address",
                    peer.address,
                ]
            )
            assert join["address"] == peer.address
            peers.append(peer)

        sender, recipient = peers
        assert sender.server.socket_path != recipient.server.socket_path
        yield sender, recipient


def _discover(sender: _Peer, recipient: _Peer) -> dict[str, Any]:
    """Resolve a peer from the sender's actual native tmux context."""

    result = sender.manager([*recipient.scope, "mail", "resolve-live"], from_pane=True)
    assert result["managed_agent"]["agent_id"] == recipient.agent_id
    assert result["source"] == "manifest_binding"
    assert result["mailboxes"]["offline"]["binding"]["address"] == recipient.address
    assert result["mailboxes"]["offline"]["binding"]["channel"] == "offline"
    return result


def _send_and_read(sender: _Peer, recipient: _Peer, address: str) -> None:
    """Send and retrieve one message through the agents' own mailbox authorities."""

    subject = "Two isolated peers"
    body = "Offline mail crosses the fixture sockets."
    send = sender.manager(
        [
            "agents",
            "self",
            "mail",
            "send",
            "--channel",
            "offline",
            "--to",
            address,
            "--subject",
            subject,
            "--body-content",
            body,
        ],
        from_pane=True,
    )
    assert send["authoritative"] and send["execution_path"] == "manager_direct"
    inbox = recipient.manager(
        ["agents", "self", "mail", "list", "--channel", "offline"], from_pane=True
    )
    assert inbox["authoritative"]
    message = inbox["messages"][0]
    assert message["subject"] == subject
    assert message["sender"]["address"] == sender.address
    read = recipient.manager(
        [
            "agents",
            "self",
            "mail",
            "read",
            "--channel",
            "offline",
            "--message-ref",
            message["message_ref"],
        ],
        from_pane=True,
    )
    assert read["message"]["body_text"] == body


def test_fixture_peer_mail_discovery_uses_records_and_verified_gateway(
    detached_peers: tuple[_Peer, _Peer],
) -> None:
    """Published contact and ordinary mail survive the fixture's socket restriction."""

    sender, recipient = detached_peers
    sender.socket_log.write_text("")
    contact = _discover(sender, recipient)
    assert not contact["gateway_available"]
    assert sender.socket_log.read_text() == ""
    _send_and_read(sender, recipient, contact["mailboxes"]["offline"]["binding"]["address"])
    assert set(sender.socket_log.read_text().splitlines()) == {sender.server.socket_path}

    attached = recipient.manager([*recipient.scope, "gateway", "attach", "--background"])
    run_path = recipient.root / "run.json"
    run = json.loads(run_path.read_text())
    run["identity"]["gateway_port"] = attached["gateway_port"]
    run_path.write_text(json.dumps(run), encoding="utf-8")
    sender.socket_log.write_text("")
    contact = _discover(sender, recipient)
    assert contact["gateway_available"]
    assert contact["gateway"]["port"] == attached["gateway_port"]
    assert contact["gateway"]["source"] == "current_instance_record"
    assert sender.socket_log.read_text() == ""


def test_fixture_mail_write_receipts_reference_the_owning_binding(
    detached_peers: tuple[_Peer, _Peer],
) -> None:
    """Inspect each synthetic write without repeating it or changing read state."""

    sender, recipient = detached_peers
    sender_binding = sender.manager([*sender.scope, "mail", "status"])["offline"]["binding_id"]
    recipient_binding = recipient.manager([*recipient.scope, "mail", "status"])["offline"][
        "binding_id"
    ]
    assert sender_binding != recipient_binding

    def self_mail(peer: _Peer, operation: str, binding_id: str, *args: str) -> dict[str, Any]:
        """Exercise the same scoped command an agent invokes from its pane."""

        return peer.manager(
            [
                "agents",
                "self",
                "mail",
                operation,
                "--channel",
                "offline",
                "--expected-binding-id",
                binding_id,
                *args,
            ],
            from_pane=True,
        )

    subject = "Record-backed mail receipts"
    send = self_mail(
        sender,
        "send",
        sender_binding,
        "--to",
        recipient.address,
        "--subject",
        subject,
        "--body-content",
        "One outbound message.",
    )
    assert send["binding_id"] == sender_binding
    assert send["address"] == send["sender_address"] == sender.address
    assert send["to"] == [recipient.address]
    (sent,) = self_mail(sender, "list", sender_binding, "--box", "sent")["messages"]
    assert sent["message_ref"] == send["message_ref"]
    sent_peek = self_mail(sender, "peek", sender_binding, "--message-ref", send["message_ref"])
    assert sent_peek["message"]["body_text"] == "One outbound message."
    assert sent_peek["message"]["read"] == sent["read"]
    assert self_mail(sender, "list", sender_binding, "--box", "sent")["messages"] == [sent]

    (original,) = self_mail(recipient, "list", recipient_binding, "--box", "inbox")["messages"]
    assert original["subject"] == subject and original["read"] is False
    inbox_peek = self_mail(
        recipient, "peek", recipient_binding, "--message-ref", original["message_ref"]
    )
    assert inbox_peek["message"]["read"] is False
    assert self_mail(recipient, "list", recipient_binding, "--box", "inbox")["messages"] == [
        original
    ]

    reply = self_mail(
        recipient,
        "reply",
        recipient_binding,
        "--message-ref",
        original["message_ref"],
        "--body-content",
        "One reply.",
    )
    assert reply["binding_id"] == recipient_binding
    assert reply["sender_address"] == recipient.address
    assert reply["to"] == [sender.address] and reply["subject"] == f"Re: {subject}"
    assert reply["parent_message_ref"] == original["message_ref"] != reply["message_ref"]
    (reply_sent,) = self_mail(recipient, "list", recipient_binding, "--box", "sent")["messages"]
    assert reply_sent["message_ref"] == reply["message_ref"]
    reply_peek = self_mail(
        recipient, "peek", recipient_binding, "--message-ref", reply["message_ref"]
    )
    assert reply_peek["message"]["body_text"] == "One reply."
    assert reply_peek["message"]["read"] == reply_sent["read"]
    assert self_mail(recipient, "list", recipient_binding, "--box", "sent")["messages"] == [
        reply_sent
    ]
    (received_reply,) = self_mail(sender, "list", sender_binding, "--box", "inbox")["messages"]
    assert received_reply["subject"] == reply["subject"]

    post = recipient.manager(
        [
            *recipient.scope,
            "mail",
            "post",
            "--channel",
            "offline",
            "--expected-binding-id",
            recipient_binding,
            "--subject",
            "Operator receipt",
            "--body-content",
            "One operator note.",
        ]
    )
    assert post["binding_id"] == recipient_binding
    assert post["address"] == recipient.address and post["to"] == [recipient.address]
    assert post["sender_address"] == "HOUMAO-operator@houmao.localhost"
    inbox = self_mail(recipient, "list", recipient_binding, "--box", "inbox")["messages"]
    assert len(inbox) == 2
    (note,) = [message for message in inbox if message["message_ref"] == post["message_ref"]]
    assert note["read"] is False
    post_peek = self_mail(
        recipient, "peek", recipient_binding, "--message-ref", post["message_ref"]
    )
    assert post_peek["message"]["body_text"] == "One operator note."
    assert post_peek["message"]["read"] is False
    assert self_mail(recipient, "list", recipient_binding, "--box", "inbox")["messages"] == inbox

    wrong_binding = recipient.invoke(
        [
            *recipient.scope,
            "mail",
            "peek",
            "--channel",
            "offline",
            "--expected-binding-id",
            sender_binding,
            "--message-ref",
            post["message_ref"],
        ],
        env=recipient.owner_env,
    )
    assert wrong_binding.returncode != 0 and "binding changed" in wrong_binding.stderr.lower()
    wrong_owner = sender.invoke(
        [
            *sender.scope,
            "mail",
            "peek",
            "--channel",
            "offline",
            "--expected-binding-id",
            sender_binding,
            "--message-ref",
            post["message_ref"],
        ],
        env=sender.owner_env,
    )
    assert wrong_owner.returncode != 0 and "another owner" in wrong_owner.stderr.lower()

    self_mail(recipient, "archive", recipient_binding, "--message-ref", post["message_ref"])
    archived = self_mail(recipient, "peek", recipient_binding, "--message-ref", post["message_ref"])
    assert archived["message"]["box"] == "archive"
    assert archived["message"]["body_text"] == "One operator note."
    for operation, receipt in (("send", send), ("reply", reply), ("post", post)):
        assert receipt["schema_version"] == 1
        assert receipt["operation"] == operation
        assert receipt["status"] == "verified" and receipt["authoritative"] is True
        assert receipt["execution_path"] == "manager_direct"
        assert receipt["channel"] == "offline"
        assert "message" not in receipt


def test_fixture_normal_prompt_uses_recorded_pane_across_sockets(
    detached_peers: tuple[_Peer, _Peer], tmp_path: Path
) -> None:
    """Only the addressed pane receives the prompt and mail survives a denied route."""

    sender, recipient = detached_peers
    decoy = tmp_path / "same-name"
    decoy.mkdir()
    panes = recipient.server.observe_session(recipient.session_name)
    assert panes is not None and len(panes) == 1
    sender.server.start(
        [
            "new-session",
            "-d",
            "-s",
            recipient.session_name,
            "-n",
            panes[0].window_name,
            "-c",
            str(decoy),
            shlex.quote(str(tmp_path / "codex")),
        ],
        environment=sender.owner_env,
    ).require_success()
    _wait_for_file(decoy / "terminal-context.json")

    # This test route admits exactly the peer's own fixture shim. Every other
    # selector still goes through the restrictive sender shim.
    route = tmp_path / "authorized-bin"
    route.mkdir()
    command = route / "tmux"
    recipient_socket = shlex.quote(recipient.server.socket_path)
    recipient_shim = shlex.quote(str(recipient.root / "bin/tmux"))
    sender_shim = shlex.quote(str(sender.root / "bin/tmux"))
    command.write_text(
        "#!/bin/sh\n"
        'case "$1" in\n'
        f'  -S) [ "$2" = {recipient_socket} ] && exec {recipient_shim} "$@" ;;\n'
        f'  -S{recipient_socket}) exec {recipient_shim} "$@" ;;\n'
        "esac\n"
        f'exec {sender_shim} "$@"\n',
        encoding="utf-8",
    )
    command.chmod(0o700)
    authorized = {**sender.caller_env, "PATH": str(route) + os.pathsep + sender.caller_env["PATH"]}
    prompt = "Deliver to the peer pane"
    submission = [*recipient.scope, "prompt", "--prompt", prompt]
    result = sender.invoke(submission, env=authorized)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["delivery_state"] == "handed_off"
    expected = b"\x1b[200~" + prompt.encode() + b"\x1b[201~\r"
    _wait_for_file(recipient.workdir / "terminal-input", contents=expected)
    assert (sender.workdir / "terminal-input").read_bytes() == b""
    assert (decoy / "terminal-input").read_bytes() == b""

    sender.socket_log.write_text("")
    denied = sender.invoke(submission, env=sender.caller_env)
    assert denied.returncode != 0
    assert "unavailable" in denied.stderr.lower()
    assert recipient.server.socket_path in sender.socket_log.read_text().splitlines()
    assert (recipient.workdir / "terminal-input").read_bytes() == expected
    assert (sender.workdir / "terminal-input").read_bytes() == b""
    assert (decoy / "terminal-input").read_bytes() == b""

    sender.socket_log.write_text("")
    contact = _discover(sender, recipient)
    assert not contact["gateway_available"]
    assert sender.socket_log.read_text() == ""
    _send_and_read(sender, recipient, contact["mailboxes"]["offline"]["binding"]["address"])
    assert set(sender.socket_log.read_text().splitlines()) == {sender.server.socket_path}
