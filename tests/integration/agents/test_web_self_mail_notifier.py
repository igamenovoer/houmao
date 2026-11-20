"""Verify fresh managed Web fixtures can finish their own notifier mail round."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any

import pytest

from houmao.agents.realm_controller.gateway_models import GatewayMailNotifierPutV1
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_manifest_path
from houmao.execution.tmux import tmux_server_scope
from houmao.gateway.client import GatewayClient

_APPENDIX = "Verify one manifest-backed self mail round."
_SUBJECT = "Manifest-backed Web mailbox probe"


@contextmanager
def _controlled_chat(command: str) -> Iterator[tuple[str, list[str]]]:
    """Ask the native provider to run one local probe, then finish the notified turn."""

    notifications: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        """Serve a credential-free synthetic Chat Completions stream on loopback."""

        def do_POST(self) -> None:
            """Return a Bash tool call on the first completion for each mail wake."""

            assert self.path.endswith("/chat/completions")
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            messages = request["messages"]
            notifier_index = next(
                (
                    index
                    for index in reversed(range(len(messages)))
                    if messages[index]["role"] == "user"
                    and _APPENDIX in json.dumps(messages[index])
                ),
                None,
            )
            shell = next(
                (
                    tool["function"]
                    for tool in request.get("tools", [])
                    if tool["function"]["name"].lower() == "bash"
                ),
                None,
            )
            delta: dict[str, Any] = {"role": "assistant", "content": "Mail round settled."}
            if (
                notifier_index is not None
                and shell is not None
                and not any(message["role"] == "tool" for message in messages[notifier_index + 1 :])
            ):
                notifications.append(json.dumps(messages[notifier_index]))
                args = {"command": command, "description": "Exercise the managed self mailbox CLI"}
                delta = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "call-web-self-mail",
                            "type": "function",
                            "function": {"name": shell["name"], "arguments": json.dumps(args)},
                        }
                    ],
                }
            terminal = "tool_calls" if "tool_calls" in delta else "stop"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for choice in (
                {"index": 0, "delta": delta, "finish_reason": None},
                {"index": 0, "delta": {}, "finish_reason": terminal},
            ):
                chunk = {
                    "id": "chatcmpl-web-self-mail",
                    "object": "chat.completion.chunk",
                    "created": 1,
                    "model": "controlled-self-mail",
                    "choices": [choice],
                }
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")

        def log_message(self, format: str, *args: Any) -> None:
            """Keep the synthetic provider quiet."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1", notifications
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _write_child_probe(path: Path, *, manager: str, output: Path) -> None:
    """Invoke the maintained CLI from the native tool shell's own environment."""

    path.write_text(
        f"""import json, os, shutil, subprocess
from pathlib import Path

def cli(*args):
    completed = subprocess.run(
        [{manager!r}, '--print-json', 'agents', 'self', *args],
        text=True, capture_output=True, timeout=12,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip())
    return json.loads(completed.stdout)

path = Path({str(output)!r})
try:
    context = {{name: os.environ.get(name) for name in (
        'TMUX', 'TMUX_PANE', 'HOUMAO_AGENT_DEF_DIR',
        'HOUMAO_SELF_TMUX_SESSION', 'HOUMAO_SELF_TMUX_SOCKET',
    )}}
    results = [cli('identity'), cli('mail', 'status')]
    binding = results[-1]['offline']['binding_id']
    scope = ('--channel', 'offline', '--expected-binding-id', binding)
    results.append(cli('mail', 'list', '--box', 'inbox', *scope))
    message, = results[-1]['messages']
    reference = ('--message-ref', message['message_ref'])
    assert message['subject'] == {_SUBJECT!r}
    results.append(cli('mail', 'read', *reference, *scope))
    results.append(cli('mail', 'reply', *reference, *scope, '--body-content', 'Round receipt.'))
    results.append(cli('mail', 'archive', *reference, *scope))
    payload = {{'context': context, 'tmux_executable': shutil.which('tmux'), 'results': results}}
except Exception as error:
    payload = {{'error': str(error)}}
pending = path.with_suffix('.pending')
pending.write_text(json.dumps(payload))
pending.replace(path)
""",
        encoding="utf-8",
    )


def _audit_outcomes(queue_path: Path) -> list[str]:
    """Read notifier outcomes without opening a writable queue connection."""

    with sqlite3.connect(f"{queue_path.as_uri()}?mode=ro", uri=True, timeout=5) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT outcome FROM gateway_notifier_audit ORDER BY audit_id"
            )
        ]


@pytest.mark.parametrize("tool", ["kimi", "dsh"])
def test_web_notifier_round_uses_manifest_without_definition_directory(
    tool: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run real native tools using explicitly selected binaries and synthetic local data."""

    binary = os.environ.get(f"HOUMAO_{tool.upper()}_EXECUTABLE")
    if not binary:
        pytest.skip(f"Set HOUMAO_{tool.upper()}_EXECUTABLE to a qualified native build")
    tmux = shutil.which("tmux")
    manager = shutil.which("houmao-mgr")
    if tmux is None or manager is None:
        pytest.skip("This managed Web qualification requires tmux and houmao-mgr")
    repo = Path(__file__).resolve().parents[3]
    helper = repo / "scripts/agents/test-fixtures"
    monkeypatch.syspath_prepend(str(helper))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.delenv("TMUX_PANE", raising=False)
    monkeypatch.chdir(tmp_path)
    prepare = importlib.import_module("fixturelib.prepare")
    report = tmp_path / "probe-results.json"
    probe = tmp_path / "probe.py"
    _write_child_probe(probe, manager=manager, output=report)
    command = shlex.join([sys.executable, str(probe)])
    with _controlled_chat(command) as (endpoint, notifications):
        selected_env = {
            key: value for key, value in os.environ.items() if not key.startswith("HOUMAO_TEST_")
        }
        selected_env["HOUMAO_TEST_SELF_HOSTED_API_KEY"] = "synthetic-local-test-key"
        args = [
            sys.executable,
            str(helper / "fixture.py"),
            "prepare",
            "--case",
            "self-hosted",
            "--client",
            tool,
            "--mode",
            "web",
            "--surface",
            "manager",
            "--model",
            "controlled-self-mail",
            "--base-url",
            endpoint,
            "--context-window",
            "16384",
            "--max-output-tokens",
            "1024",
            "--run-root",
            str(tmp_path / "runs"),
            "--executable",
            binary,
        ]
        if tool == "dsh":
            args += ["--dsh-reasoning", "false"]
        prepared = subprocess.run(
            args,
            env=selected_env,
            text=True,
            capture_output=True,
            check=True,
            timeout=30,
        )
        run_dir = Path(json.loads(prepared.stdout)["run_dir"])
        run = prepare.load_run(run_dir)
        assert run["configuration"]["system_skill_policy"] == "default"
        selected = json.loads((run_dir / "private-env.json").read_text())
        env = prepare.isolated_environment(selected, run_dir=run_dir)
        mailbox_root = tmp_path / "mailbox"
        with tempfile.TemporaryDirectory(prefix="houmao-web-self-") as socket_dir:
            socket = Path(socket_dir) / "server.sock"
            tmux_cmd = [tmux, "-S", str(socket)]
            with tmux_server_scope(socket):
                try:
                    subprocess.run(
                        [*tmux_cmd, "-f", os.devnull, "new-session", "-d", "-s", "anchor"],
                        check=True,
                        timeout=10,
                    )
                    prepare.manager_root_call(
                        ["mailbox", "init", "--mailbox-root", str(mailbox_root)], env=env
                    )
                    launch = prepare.manager_call(
                        Path(run["project_dir"]),
                        [
                            "agents",
                            "launch",
                            "--specialist",
                            "fixture-agent",
                            "--mode",
                            "web",
                            "--name",
                            f"{tool}-web-self",
                            "--workdir",
                            run["workdir"],
                            "--gateway-background",
                            "--mail-transport",
                            "filesystem",
                            "--mail-root",
                            str(mailbox_root),
                        ],
                        env=env,
                    )
                    scope = ["agents", "single", "--agent-id", launch["agent_id"]]
                    manifest_path = Path(launch["manifest_path"])
                    manifest = json.loads(manifest_path.read_text())
                    runtime_home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
                    assert (runtime_home / "skills/houmao-agent-entrypoint/SKILL.md").is_file()
                    paths = gateway_paths_from_manifest_path(manifest_path)
                    assert paths is not None
                    definition_dir = Path(manifest["runtime"]["agent_def_dir"])
                    assert definition_dir.is_relative_to(run_dir)
                    hidden = definition_dir.with_name("hidden-test-definitions")
                    try:
                        subprocess.run(
                            [*tmux_cmd, "new-session", "-d", "-s", "decoy"],
                            check=True,
                            timeout=10,
                        )
                        selected_session = subprocess.check_output(
                            [*tmux_cmd, "display-message", "-p", "#S"], text=True, timeout=10
                        )
                        assert selected_session.strip() == "decoy"
                        prepare.manager_root_call(
                            [
                                *scope,
                                "mail",
                                "post",
                                "--channel",
                                "offline",
                                "--subject",
                                _SUBJECT,
                                "--body-content",
                                "Reply once, then archive this fixture message.",
                            ],
                            env=env,
                        )
                        definition_dir.rename(hidden)
                        gateway = GatewayClient(
                            base_url=f"http://127.0.0.1:{launch['gateway_port']}"
                        )
                        gateway.put_mail_notifier(
                            GatewayMailNotifierPutV1(
                                interval_seconds=10, mode="unread_only", appendix_text=_APPENDIX
                            ),
                            channel="offline",
                        )
                        deadline = time.monotonic() + 50
                        while time.monotonic() < deadline:
                            if report.is_file():
                                result = json.loads(report.read_text())
                                assert "error" not in result, result.get("error")
                                outcomes = _audit_outcomes(paths.queue_path)
                                if (
                                    "empty" in outcomes[outcomes.index("enqueued") + 1 :]
                                    and gateway.status().active_execution == "idle"
                                ):
                                    break
                            time.sleep(0.05)
                        else:
                            pytest.fail(f"The native notifier round did not settle for {tool}")
                        result = json.loads(report.read_text())
                        context = result["context"]
                        assert not context["TMUX"] and not context["TMUX_PANE"]
                        assert not context["HOUMAO_AGENT_DEF_DIR"]
                        assert context["HOUMAO_SELF_TMUX_SOCKET"] == str(socket)
                        assert context["HOUMAO_SELF_TMUX_SESSION"] == launch["tmux_session_name"]
                        assert result["tmux_executable"] == tmux
                        identity, *operations = result["results"]
                        assert identity["agent_id"] == launch["agent_id"]
                        assert [op["operation"] for op in operations] == [
                            "status",
                            "list",
                            "read",
                            "reply",
                            "archive",
                        ]
                        assert all(op["authoritative"] for op in operations)
                        (archived,) = operations[-1]["messages"]
                        assert archived["answered"] and archived["archived"]
                        assert _audit_outcomes(paths.queue_path).count("enqueued") == 1
                        assert len(notifications) == 1
                        assert "houmao-agent-entrypoint" in notifications[0]
                        replies = prepare.manager_root_call(
                            [
                                "mailbox",
                                "messages",
                                "list",
                                "--mailbox-root",
                                str(mailbox_root),
                                "--address",
                                "HOUMAO-operator@houmao.localhost",
                            ],
                            env=env,
                        )
                        (reply,) = (
                            message
                            for message in replies["messages"]
                            if message["folder"] == "inbox"
                        )
                        assert reply["subject"] == f"Re: {_SUBJECT}"
                    finally:
                        if hidden.exists():
                            hidden.rename(definition_dir)
                        prepare.manager_root_call([*scope, "stop"], env=env)
                finally:
                    subprocess.run(
                        [*tmux_cmd, "kill-server"], check=False, capture_output=True, timeout=10
                    )
