"""Deterministic direct-path integration coverage for the mailbox roundtrip tutorial pack."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import textwrap
import uuid
from pathlib import Path
from types import ModuleType


def _repo_root() -> Path:
    """Return the tracked repository root."""

    return Path(__file__).resolve().parents[3]


def _pack_dir() -> Path:
    """Return the tracked mailbox demo pack directory."""

    return _repo_root() / "scripts" / "demo" / "mailbox-roundtrip-tutorial-pack"


def _helper_module() -> ModuleType:
    """Load the pack-local helper module from disk."""

    helper_path = _pack_dir() / "scripts" / "tutorial_pack_helpers.py"
    module_name = "mailbox_roundtrip_tutorial_pack_live_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _helper_module()


def _write(path: Path, content: str) -> None:
    """Write one UTF-8 text fixture file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload."""

    _write(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_executable(path: Path, content: str) -> None:
    """Write one executable helper script."""

    _write(path, content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _pick_unused_loopback_port() -> int:
    """Return one likely-free non-default loopback port."""

    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = int(sock.getsockname()[1])
        if port != 9889:
            return port


def _write_fake_git(fake_bin_dir: Path) -> None:
    """Install a fake git binary for demo dummy-project provisioning."""

    _write_executable(
        fake_bin_dir / "git",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import os
            import sys
            from pathlib import Path

            raw_args = sys.argv[1:]
            cwd = Path(os.getcwd()).resolve()
            if len(raw_args) >= 2 and raw_args[0] == "-C":
                cwd = Path(raw_args[1]).resolve()
                raw_args = raw_args[2:]

            repo_root = Path(os.environ["FAKE_GIT_TOPLEVEL"]).resolve()
            source_repo = cwd == repo_root or repo_root in cwd.parents

            def find_git_root(start: Path) -> Path | None:
                for candidate in (start, *start.parents):
                    git_path = candidate / ".git"
                    if git_path.is_dir() or git_path.is_file():
                        return candidate
                return None

            active_repo = find_git_root(cwd)

            if raw_args == ["rev-parse", "--show-toplevel"]:
                if active_repo is not None:
                    print(str(active_repo))
                    raise SystemExit(0)
                if source_repo:
                    print(str(repo_root))
                    raise SystemExit(0)
                raise SystemExit(1)

            if raw_args == ["rev-parse", "--is-inside-work-tree"]:
                if active_repo is not None or source_repo:
                    print("true")
                    raise SystemExit(0)
                raise SystemExit(1)

            if raw_args == ["rev-parse", "--git-common-dir"]:
                if active_repo is not None:
                    print(str((active_repo / ".git").resolve()))
                    raise SystemExit(0)
                if source_repo:
                    print(str((repo_root / ".git").resolve()))
                    raise SystemExit(0)
                raise SystemExit(1)

            if raw_args == ["init", "--initial-branch", "main"]:
                (cwd / ".git").mkdir(parents=True, exist_ok=True)
                print(f"Initialized empty Git repository in {cwd / '.git'}")
                raise SystemExit(0)

            if raw_args == ["add", "--all"]:
                raise SystemExit(0)

            if len(raw_args) == 5 and raw_args[:4] == ["commit", "--allow-empty", "--no-gpg-sign", "-m"]:
                print(f"[main (root-commit) 0000000] {raw_args[4]}")
                raise SystemExit(0)

            raise SystemExit(f"unexpected git args: {raw_args!r} (cwd={cwd})")
            """
        ),
    )


def _write_fake_cli_executables(fake_bin_dir: Path) -> None:
    """Install no-op Claude and Codex executables."""

    _write_executable(fake_bin_dir / "claude", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(fake_bin_dir / "codex", "#!/usr/bin/env bash\nexit 0\n")


def _write_fake_cao_server(fake_bin_dir: Path) -> None:
    """Install a fake `cao-server` binary that serves the CAO endpoints used here."""

    _write_executable(
        fake_bin_dir / "cao-server",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import json
            import os
            import sqlite3
            import subprocess
            import sys
            from datetime import UTC, datetime
            from http import HTTPStatus
            from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
            from pathlib import Path
            from urllib.parse import parse_qs, quote, urlparse

            from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path
            from houmao.mailbox.managed import DeliveryRequest, deliver_message
            from houmao.mailbox.protocol import (
                MailboxMessage,
                MailboxPrincipal,
                generate_message_id,
                parse_message_document,
                serialize_message_document,
            )

            MAIL_BEGIN = "AGENTSYS_MAIL_RESULT_BEGIN"
            MAIL_END = "AGENTSYS_MAIL_RESULT_END"


            def _now_utc() -> str:
                return (
                    datetime.now(UTC)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z")
                )


            def _tmux_environment(session_name: str) -> dict[str, str]:
                result = subprocess.run(
                    ["tmux", "show-environment", "-t", session_name],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"failed to read tmux environment for {session_name}: "
                        f"{result.stderr.strip() or result.stdout.strip() or 'unknown tmux error'}"
                    )
                bindings: dict[str, str] = {}
                for raw_line in result.stdout.splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("-") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    bindings[key] = value
                return bindings


            def _mailbox_root_for_session(session_name: str) -> tuple[dict[str, str], Path]:
                env = _tmux_environment(session_name)
                return env, Path(env["AGENTSYS_MAILBOX_FS_ROOT"]).resolve()


            def _parse_mail_request(prompt: str) -> dict[str, object]:
                marker = "AGENTSYS_MAIL_REQUEST:"
                if marker not in prompt:
                    raise RuntimeError("mail request marker missing from direct prompt")
                after_marker = prompt.split(marker, 1)[1]
                parts = after_marker.split("```json", 1)
                if len(parts) != 2:
                    raise RuntimeError("mail request JSON fence missing from direct prompt")
                fenced = parts[1].split("```", 1)[0].strip()
                payload = json.loads(fenced)
                if not isinstance(payload, dict):
                    raise RuntimeError("mail request payload must be a JSON object")
                return payload


            def _message_path(mailbox_root: Path, *, message_id: str) -> Path:
                matches = sorted((mailbox_root / "messages").glob(f"*/{message_id}.md"))
                if len(matches) != 1:
                    raise RuntimeError(
                        f"expected exactly one canonical message for {message_id}, found {len(matches)}"
                    )
                return matches[0]


            def _unread_count(mailbox_root: Path, *, address: str) -> int:
                local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
                    mailbox_root,
                    address=address,
                )
                with sqlite3.connect(local_sqlite_path) as connection:
                    row = connection.execute(
                        "SELECT COUNT(*) FROM message_state WHERE is_read = 0"
                    ).fetchone()
                return int(row[0]) if row is not None else 0


            def _principal_from_address(address: str) -> MailboxPrincipal:
                return MailboxPrincipal(
                    principal_id=address.split("@", 1)[0],
                    address=address,
                )


            def _prompt_excerpt(prompt: str) -> str:
                for raw_line in prompt.splitlines():
                    line = raw_line.strip()
                    if line:
                        return line[:120]
                return "mail operation"


            def _idle_output(provider: str) -> str:
                lowered = provider.strip().lower()
                if "claude" in lowered:
                    return "Claude Code v2.1.62\\n❯ \\n"
                return "OpenAI Codex (v0.98.0)\\n❯ \\n? for shortcuts\\n"


            def _completed_output(provider: str, *, prompt: str, response_text: str) -> str:
                lowered = provider.strip().lower()
                response_lines = response_text.splitlines() or [""]
                if "claude" in lowered:
                    lines = [
                        "Claude Code v2.1.62",
                        f"❯ {_prompt_excerpt(prompt)}",
                        f"● {response_lines[0]}",
                        *response_lines[1:],
                        "❯ ",
                    ]
                    return "\\n".join(lines) + "\\n"
                lines = [
                    "OpenAI Codex (v0.98.0)",
                    f"You {_prompt_excerpt(prompt)}",
                    f"assistant: {response_lines[0]}",
                    *response_lines[1:],
                    "❯ ",
                    "? for shortcuts",
                ]
                return "\\n".join(lines) + "\\n"


            def _deliver_message(
                *,
                mailbox_root: Path,
                message: MailboxMessage,
            ) -> None:
                staged_message = mailbox_root / "staging" / f"{message.message_id}.md"
                staged_message.parent.mkdir(parents=True, exist_ok=True)
                staged_message.write_text(
                    serialize_message_document(message),
                    encoding="utf-8",
                )
                request = DeliveryRequest.from_payload(
                    {
                        "staged_message_path": str(staged_message),
                        "message_id": message.message_id,
                        "thread_id": message.thread_id,
                        "in_reply_to": message.in_reply_to,
                        "references": message.references,
                        "created_at_utc": message.created_at_utc,
                        "sender": {
                            "principal_id": message.sender.principal_id,
                            "address": message.sender.address,
                        },
                        "to": [
                            {
                                "principal_id": principal.principal_id,
                                "address": principal.address,
                            }
                            for principal in message.to
                        ],
                        "cc": [],
                        "reply_to": [],
                        "subject": message.subject,
                        "attachments": [],
                        "headers": dict(message.headers),
                    }
                )
                deliver_message(mailbox_root, request)


            def _mail_result(
                *,
                provider: str,
                session_name: str,
                prompt: str,
            ) -> tuple[bool, str]:
                request = _parse_mail_request(prompt)
                request_id = str(request["request_id"])
                operation = str(request["operation"])
                args = dict(request["args"])
                env, mailbox_root = _mailbox_root_for_session(session_name)
                principal_id = env["AGENTSYS_MAILBOX_PRINCIPAL_ID"]
                address = env["AGENTSYS_MAILBOX_ADDRESS"]
                sender = MailboxPrincipal(principal_id=principal_id, address=address)
                mail_mode = os.environ.get("FAKE_CAO_MAIL_MODE", "").strip().lower()

                if operation == "send" and mail_mode == "reject_send":
                    return False, ""
                if operation == "send" and mail_mode == "malformed_send":
                    return True, _completed_output(
                        provider,
                        prompt=prompt,
                        response_text="no sentinels here",
                    )

                if operation == "check":
                    payload = {
                        "ok": True,
                        "request_id": request_id,
                        "operation": operation,
                        "transport": "filesystem",
                        "principal_id": principal_id,
                        "unread_count": _unread_count(mailbox_root, address=address),
                    }
                    return True, _completed_output(
                        provider,
                        prompt=prompt,
                        response_text=(
                            f"{MAIL_BEGIN}\\n{json.dumps(payload, sort_keys=True)}\\n{MAIL_END}"
                        ),
                    )

                created_at_utc = _now_utc()
                message_id = generate_message_id()
                attachments: list[object] = []
                headers: dict[str, object] = {}
                body_content = str(args["body_content"])

                if operation == "send":
                    to_principals = [
                        _principal_from_address(value) for value in list(args.get("to", ()))
                    ]
                    message = MailboxMessage(
                        message_id=message_id,
                        thread_id=message_id,
                        in_reply_to=None,
                        references=[],
                        created_at_utc=created_at_utc,
                        sender=sender,
                        to=to_principals,
                        cc=[],
                        reply_to=[],
                        subject=str(args["subject"]),
                        body_markdown=body_content,
                        attachments=attachments,
                        headers=headers,
                    )
                    _deliver_message(mailbox_root=mailbox_root, message=message)
                    payload = {
                        "ok": True,
                        "request_id": request_id,
                        "operation": operation,
                        "transport": "filesystem",
                        "principal_id": principal_id,
                        "message_id": message.message_id,
                        "thread_id": message.thread_id,
                        "subject": message.subject,
                    }
                    return True, _completed_output(
                        provider,
                        prompt=prompt,
                        response_text=(
                            f"{MAIL_BEGIN}\\n{json.dumps(payload, sort_keys=True)}\\n{MAIL_END}"
                        ),
                    )

                if operation == "reply":
                    parent_message_id = str(args["message_id"])
                    parent_path = _message_path(mailbox_root, message_id=parent_message_id)
                    parent_message = parse_message_document(parent_path.read_text(encoding="utf-8"))
                    message = MailboxMessage(
                        message_id=message_id,
                        thread_id=parent_message.thread_id,
                        in_reply_to=parent_message.message_id,
                        references=[*parent_message.references, parent_message.message_id],
                        created_at_utc=created_at_utc,
                        sender=sender,
                        to=[parent_message.sender],
                        cc=[],
                        reply_to=[],
                        subject=parent_message.subject,
                        body_markdown=body_content,
                        attachments=attachments,
                        headers=headers,
                    )
                    _deliver_message(mailbox_root=mailbox_root, message=message)
                    payload = {
                        "ok": True,
                        "request_id": request_id,
                        "operation": operation,
                        "transport": "filesystem",
                        "principal_id": principal_id,
                        "message_id": message.message_id,
                        "thread_id": message.thread_id,
                    }
                    return True, _completed_output(
                        provider,
                        prompt=prompt,
                        response_text=(
                            f"{MAIL_BEGIN}\\n{json.dumps(payload, sort_keys=True)}\\n{MAIL_END}"
                        ),
                    )

                raise RuntimeError(f"unsupported fake CAO mail operation: {operation!r}")


            class Handler(BaseHTTPRequestHandler):
                def do_GET(self) -> None:  # noqa: N802
                    parsed = urlparse(self.path)
                    path_parts = parsed.path.strip("/").split("/")
                    query = parse_qs(parsed.query)

                    if parsed.path == "/health":
                        self._send_json(
                            HTTPStatus.OK,
                            {"status": "ok", "service": "cli-agent-orchestrator"},
                        )
                        return

                    if (
                        len(path_parts) == 2
                        and path_parts[0] == "terminals"
                        and path_parts[1] in self.server.state["terminals"]
                    ):
                        terminal = self.server.state["terminals"][path_parts[1]]
                        self._send_json(
                            HTTPStatus.OK,
                            {
                                "id": terminal["id"],
                                "name": terminal["name"],
                                "provider": terminal["provider"],
                                "session_name": terminal["session_name"],
                                "agent_profile": terminal["agent_profile"],
                                "status": terminal["status"],
                            },
                        )
                        return

                    if (
                        len(path_parts) == 3
                        and path_parts[0] == "terminals"
                        and path_parts[2] == "output"
                        and path_parts[1] in self.server.state["terminals"]
                    ):
                        terminal = self.server.state["terminals"][path_parts[1]]
                        mode = query.get("mode", ["last"])[0]
                        self._send_json(
                            HTTPStatus.OK,
                            {"output": terminal["output"], "mode": mode},
                        )
                        return

                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

                def do_POST(self) -> None:  # noqa: N802
                    parsed = urlparse(self.path)
                    path_parts = parsed.path.strip("/").split("/")
                    query = parse_qs(parsed.query)

                    if len(path_parts) == 3 and path_parts[0] == "sessions" and path_parts[2] == "terminals":
                        session_name = path_parts[1]
                        provider = query.get("provider", ["codex"])[0]
                        agent_profile = query.get("agent_profile", ["runtime-profile"])[0]
                        terminal_id = f"term-{self.server.state['next_terminal_id']}"
                        self.server.state["next_terminal_id"] += 1
                        terminal_name = session_name
                        subprocess.run(
                            ["tmux", "rename-window", "-t", f"{session_name}:0", terminal_name],
                            check=False,
                            capture_output=True,
                            text=True,
                        )
                        terminal = {
                            "id": terminal_id,
                            "name": terminal_name,
                            "provider": provider,
                            "session_name": session_name,
                            "agent_profile": agent_profile,
                            "status": "idle",
                            "output": _idle_output(provider),
                        }
                        self.server.state["terminals"][terminal_id] = terminal
                        self.server.state["sessions"][session_name] = terminal_id
                        self._send_json(HTTPStatus.OK, terminal)
                        return

                    if (
                        len(path_parts) == 3
                        and path_parts[0] == "terminals"
                        and path_parts[2] == "input"
                        and path_parts[1] in self.server.state["terminals"]
                    ):
                        terminal = self.server.state["terminals"][path_parts[1]]
                        message = query.get("message", [""])[0]
                        success, output = _mail_result(
                            provider=str(terminal["provider"]),
                            session_name=terminal["session_name"],
                            prompt=message,
                        )
                        if success:
                            terminal["status"] = "completed"
                            terminal["output"] = output
                        self._send_json(HTTPStatus.OK, {"success": success})
                        return

                    if (
                        len(path_parts) == 3
                        and path_parts[0] == "terminals"
                        and path_parts[2] == "exit"
                        and path_parts[1] in self.server.state["terminals"]
                    ):
                        terminal = self.server.state["terminals"][path_parts[1]]
                        terminal["status"] = "idle"
                        self._send_json(HTTPStatus.OK, {"success": True})
                        return

                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

                def do_DELETE(self) -> None:  # noqa: N802
                    parsed = urlparse(self.path)
                    path_parts = parsed.path.strip("/").split("/")

                    if len(path_parts) == 2 and path_parts[0] == "terminals":
                        self.server.state["terminals"].pop(path_parts[1], None)
                        self._send_json(HTTPStatus.OK, {"success": True})
                        return

                    if len(path_parts) == 2 and path_parts[0] == "sessions":
                        session_name = path_parts[1]
                        terminal_id = self.server.state["sessions"].pop(session_name, None)
                        if terminal_id is not None:
                            self.server.state["terminals"].pop(terminal_id, None)
                        subprocess.run(
                            ["tmux", "kill-session", "-t", session_name],
                            check=False,
                            capture_output=True,
                            text=True,
                        )
                        self._send_json(HTTPStatus.OK, {"success": True})
                        return

                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

                def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                    del format, args
                    return

                def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
                    encoded = json.dumps(payload).encode("utf-8")
                    self.send_response(int(status))
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)


            def main() -> int:
                port = int(os.environ.get("CAO_PORT", "9889"))
                server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
                server.state = {
                    "next_terminal_id": 1,
                    "sessions": {},
                    "terminals": {},
                }
                server.serve_forever()
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
    )


def _seed_live_agent_def_dir(agent_def_dir: Path) -> None:
    """Copy tracked fixtures and inject deterministic test credential profiles."""

    shutil.copytree(_repo_root() / "tests" / "fixtures" / "agents", agent_def_dir)
    _write(
        agent_def_dir
        / "brains"
        / "api-creds"
        / "claude"
        / "personal-a-default"
        / "files"
        / "claude_state.template.json",
        "{}\n",
    )
    _write(
        agent_def_dir
        / "brains"
        / "api-creds"
        / "claude"
        / "personal-a-default"
        / "env"
        / "vars.env",
        "ANTHROPIC_API_KEY=fixture-anthropic-key\n",
    )
    _write(
        agent_def_dir
        / "brains"
        / "api-creds"
        / "codex"
        / "personal-a-default"
        / "env"
        / "vars.env",
        "OPENAI_API_KEY=fixture-openai-key\n",
    )


def _write_parameters(
    path: Path,
    *,
    agent_def_dir: Path,
    cao_base_url: str,
    sender_identity: str,
    receiver_identity: str,
) -> None:
    """Write one test-owned mailbox tutorial parameter file."""

    _write_json(
        path,
        {
            "schema_version": 1,
            "demo_id": "mailbox-roundtrip-tutorial-pack",
            "agent_def_dir": str(agent_def_dir.resolve()),
            "project_fixture": "tests/fixtures/dummy-projects/mailbox-demo-python",
            "backend": "cao_rest",
            "cao_base_url": cao_base_url,
            "shared_mailbox_root_template": "{demo_output_dir}/mailbox",
            "sender": {
                "blueprint": "blueprints/mailbox-demo-claude.yaml",
                "agent_identity": sender_identity,
                "mailbox_principal_id": sender_identity,
                "mailbox_address": f"{sender_identity}@agents.localhost",
            },
            "receiver": {
                "blueprint": "blueprints/mailbox-demo-codex.yaml",
                "agent_identity": receiver_identity,
                "mailbox_principal_id": receiver_identity,
                "mailbox_address": f"{receiver_identity}@agents.localhost",
            },
            "message": {
                "subject": "Mailbox tutorial roundtrip",
                "initial_body_file": "inputs/initial_message.md",
                "reply_instructions_file": "inputs/reply_instructions.md",
            },
        },
    )


def _build_env(
    *,
    tmp_path: Path,
    fake_bin_dir: Path,
    base_url: str,
    mail_mode: str = "",
) -> dict[str, str]:
    """Build subprocess environment for the live pack test."""

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
    env["PYTHONPATH"] = f"{_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(_repo_root().resolve())
    env["AGENTSYS_GLOBAL_REGISTRY_DIR"] = str((tmp_path / "registry").resolve())
    env["CAO_BASE_URL"] = base_url
    if mail_mode:
        env["FAKE_CAO_MAIL_MODE"] = mail_mode
    else:
        env.pop("FAKE_CAO_MAIL_MODE", None)
    return env


def _run_demo_command(
    *,
    command: str,
    demo_output_dir: Path,
    parameters_path: Path,
    env: dict[str, str],
    expected_report_path: Path | None = None,
    snapshot: bool = False,
    cao_parsing_mode: str | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one `run_demo.sh` command with explicit live-test overrides."""

    argv = [
        str(_pack_dir() / "run_demo.sh"),
        command,
        "--demo-output-dir",
        str(demo_output_dir),
        "--parameters",
        str(parameters_path),
    ]
    if expected_report_path is not None:
        argv.extend(["--expected-report", str(expected_report_path)])
    if snapshot:
        argv.append("--snapshot-report")
    if cao_parsing_mode is not None:
        argv.extend(["--cao-parsing-mode", cao_parsing_mode])
    if extra_args is not None:
        argv.extend(extra_args)
    return subprocess.run(
        argv,
        check=False,
        capture_output=True,
        text=True,
        cwd=str(_repo_root()),
        env=env,
    )


def _best_effort_stop_demo(
    *,
    demo_output_dir: Path,
    parameters_path: Path,
    env: dict[str, str],
) -> None:
    """Stop one demo root without raising if cleanup also fails."""

    subprocess.run(
        [
            str(_pack_dir() / "run_demo.sh"),
            "stop",
            "--demo-output-dir",
            str(demo_output_dir),
            "--parameters",
            str(parameters_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(_repo_root()),
        env=env,
    )


def _tmux_session_exists(session_name: str) -> bool:
    """Return whether one tmux session still exists."""

    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def test_mailbox_roundtrip_live_workflow_leaves_readable_mail_after_stop(tmp_path: Path) -> None:
    """The live workflow should leave readable mailbox content on disk after stop."""

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    _write_fake_git(fake_bin_dir)
    _write_fake_cli_executables(fake_bin_dir)
    _write_fake_cao_server(fake_bin_dir)

    agent_def_dir = tmp_path / "agents"
    _seed_live_agent_def_dir(agent_def_dir)

    suffix = uuid.uuid4().hex[:8]
    sender_identity = f"AGENTSYS-live-mailbox-sender-{suffix}"
    receiver_identity = f"AGENTSYS-live-mailbox-receiver-{suffix}"
    base_url = f"http://127.0.0.1:{_pick_unused_loopback_port()}"
    parameters_path = tmp_path / "demo_parameters.json"
    _write_parameters(
        parameters_path,
        agent_def_dir=agent_def_dir,
        cao_base_url=base_url,
        sender_identity=sender_identity,
        receiver_identity=receiver_identity,
    )
    env = _build_env(tmp_path=tmp_path, fake_bin_dir=fake_bin_dir, base_url=base_url)

    demo_output_dir = tmp_path / "demo"
    restart_demo_output_dir = tmp_path / "demo-restart"
    expected_report_path = tmp_path / "expected-report.json"

    try:
        layout = HELPERS.build_demo_layout(demo_output_dir=demo_output_dir)
        restart_layout = HELPERS.build_demo_layout(demo_output_dir=restart_demo_output_dir)
        start_result = _run_demo_command(
            command="start",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )
        assert start_result.returncode == 0, start_result.stderr

        sender_start = json.loads(
            (layout.control_dir / "sender_start.json").read_text(encoding="utf-8")
        )
        receiver_start = json.loads(
            (layout.control_dir / "receiver_start.json").read_text(encoding="utf-8")
        )
        assert sender_start["agent_identity"] == sender_identity
        assert receiver_start["agent_identity"] == receiver_identity
        assert sender_start["backend"] == "cao_rest"
        assert receiver_start["backend"] == "cao_rest"
        demo_state = json.loads(layout.state_path.read_text(encoding="utf-8"))
        sender_manifest = json.loads(
            Path(sender_start["session_manifest"]).read_text(encoding="utf-8")
        )
        receiver_manifest = json.loads(
            Path(receiver_start["session_manifest"]).read_text(encoding="utf-8")
        )
        assert demo_state["cao_parsing_mode"] == "shadow_only"
        assert sender_manifest["cao"]["parsing_mode"] == "shadow_only"
        assert sender_manifest["backend_state"]["parsing_mode"] == "shadow_only"
        assert receiver_manifest["cao"]["parsing_mode"] == "shadow_only"
        assert receiver_manifest["backend_state"]["parsing_mode"] == "shadow_only"

        sender_inspect_result = _run_demo_command(
            command="inspect",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
            extra_args=["--agent", "sender", "--json"],
        )
        assert sender_inspect_result.returncode == 0, sender_inspect_result.stderr
        sender_inspect = json.loads(sender_inspect_result.stdout)
        assert sender_inspect["agent_identity"] == sender_identity
        assert sender_inspect["tool_state"] == "idle"
        assert sender_inspect["project_workdir"] == str(layout.project_workdir)
        assert sender_inspect["runtime_root"] == str(layout.runtime_root)
        assert sender_inspect["terminal_log_path"].endswith(".log")

        receiver_inspect_result = _run_demo_command(
            command="inspect",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
            extra_args=["--agent", "receiver", "--json", "--with-output-text", "120"],
        )
        assert receiver_inspect_result.returncode == 0, receiver_inspect_result.stderr
        receiver_inspect = json.loads(receiver_inspect_result.stdout)
        assert receiver_inspect["agent_identity"] == receiver_identity
        assert receiver_inspect["tool_state"] == "idle"
        assert receiver_inspect["output_text_tail_chars_requested"] == 120

        roundtrip_result = _run_demo_command(
            command="roundtrip",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )
        assert roundtrip_result.returncode == 0, roundtrip_result.stderr

        verify_snapshot_result = _run_demo_command(
            command="verify",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
            expected_report_path=expected_report_path,
            snapshot=True,
        )
        assert verify_snapshot_result.returncode == 0, verify_snapshot_result.stderr

        verify_result = _run_demo_command(
            command="verify",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
            expected_report_path=expected_report_path,
        )
        assert verify_result.returncode == 0, verify_result.stderr

        stop_result = _run_demo_command(
            command="stop",
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )
        assert stop_result.returncode == 0, stop_result.stderr
        stop_payload = json.loads(stop_result.stdout)
        assert stop_payload["stopped"] is True

        inspection = HELPERS.inspect_roundtrip_mailbox(
            mailbox_root=layout.mailbox_root,
            sender_address=sender_start["mailbox"]["address"],
            receiver_address=receiver_start["mailbox"]["address"],
            send_message_id=HELPERS.extract_message_id(layout.control_dir / "mail_send.json"),
            reply_message_id=HELPERS.extract_message_id(layout.control_dir / "mail_reply.json"),
            initial_body_path=_pack_dir() / "inputs" / "initial_message.md",
        )
        chat_log = HELPERS.inspect_chat_log(
            chats_path=layout.chats_path,
            send_message_id=inspection["send_message_id"],
            reply_message_id=inspection["reply_message_id"],
            sender_address=sender_start["mailbox"]["address"],
            receiver_address=receiver_start["mailbox"]["address"],
            initial_body_path=_pack_dir() / "inputs" / "initial_message.md",
            reply_body_markdown=inspection["reply_body_markdown"],
        )

        assert (layout.mailbox_root / "mailboxes").is_dir()
        assert layout.chats_path.is_file()
        assert Path(inspection["send_message_path"]).is_file()
        assert Path(inspection["reply_message_path"]).is_file()
        assert inspection["send_body_matches_input"] is True
        assert inspection["reply_body_present"] is True
        assert inspection["sender_sent_projection_targets_send"] is True
        assert inspection["receiver_inbox_projection_targets_send"] is True
        assert inspection["receiver_sent_projection_targets_reply"] is True
        assert inspection["sender_inbox_projection_targets_reply"] is True
        assert inspection["reply_thread_matches_send"] is True
        assert inspection["reply_parent_matches_send"] is True
        assert inspection["reply_references_send"] is True
        assert inspection["sender_unread_count"] == 1
        assert inspection["receiver_unread_count"] == 1
        assert chat_log["send_event_present"] is True
        assert chat_log["reply_event_present"] is True
        assert chat_log["send_event_matches_input"] is True
        assert chat_log["reply_event_matches_mailbox_reply"] is True
        assert chat_log["reply_event_parent_matches_send"] is True

        sanitized_report_text = layout.sanitized_report_path.read_text(encoding="utf-8")
        canonical_send_text = Path(inspection["send_message_path"]).read_text(encoding="utf-8")
        canonical_reply_text = Path(inspection["reply_message_path"]).read_text(encoding="utf-8")
        assert "Please confirm that the shared mailbox is reachable" not in sanitized_report_text
        assert "Reply authored from the tracked tutorial instructions" not in sanitized_report_text
        assert "Please confirm that the shared mailbox is reachable" in canonical_send_text
        assert "Reply authored from the tracked tutorial instructions" in canonical_reply_text
        assert not _tmux_session_exists(sender_identity)
        assert not _tmux_session_exists(receiver_identity)

        restart_start_result = _run_demo_command(
            command="start",
            demo_output_dir=restart_demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )
        assert restart_start_result.returncode == 0, restart_start_result.stderr
        restart_state = json.loads(restart_layout.state_path.read_text(encoding="utf-8"))
        assert restart_state["cao_parsing_mode"] == "shadow_only"

        restart_stop_result = _run_demo_command(
            command="stop",
            demo_output_dir=restart_demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )
        assert restart_stop_result.returncode == 0, restart_stop_result.stderr
    finally:
        _best_effort_stop_demo(
            demo_output_dir=restart_demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )
        _best_effort_stop_demo(
            demo_output_dir=demo_output_dir,
            parameters_path=parameters_path,
            env=env,
        )


def test_mailbox_roundtrip_live_workflow_surfaces_direct_mail_failures(tmp_path: Path) -> None:
    """The live workflow should fail clearly on malformed or rejected direct mail turns."""

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    _write_fake_git(fake_bin_dir)
    _write_fake_cli_executables(fake_bin_dir)
    _write_fake_cao_server(fake_bin_dir)

    agent_def_dir = tmp_path / "agents"
    _seed_live_agent_def_dir(agent_def_dir)

    for mail_mode, expected_error in (
        ("malformed_send", "expected exactly one sentinel-delimited payload"),
        ("reject_send", "CAO terminal rejected input submission"),
    ):
        suffix = uuid.uuid4().hex[:8]
        sender_identity = f"AGENTSYS-live-mailbox-sender-{suffix}"
        receiver_identity = f"AGENTSYS-live-mailbox-receiver-{suffix}"
        base_url = f"http://127.0.0.1:{_pick_unused_loopback_port()}"
        parameters_path = tmp_path / f"demo_parameters_{mail_mode}.json"
        _write_parameters(
            parameters_path,
            agent_def_dir=agent_def_dir,
            cao_base_url=base_url,
            sender_identity=sender_identity,
            receiver_identity=receiver_identity,
        )
        env = _build_env(
            tmp_path=tmp_path / mail_mode,
            fake_bin_dir=fake_bin_dir,
            base_url=base_url,
            mail_mode=mail_mode,
        )
        demo_output_dir = tmp_path / f"demo-{mail_mode}"

        try:
            start_result = _run_demo_command(
                command="start",
                demo_output_dir=demo_output_dir,
                parameters_path=parameters_path,
                env=env,
            )
            assert start_result.returncode == 0, start_result.stderr

            roundtrip_result = _run_demo_command(
                command="roundtrip",
                demo_output_dir=demo_output_dir,
                parameters_path=parameters_path,
                env=env,
            )
            assert roundtrip_result.returncode == 1
            assert expected_error in roundtrip_result.stderr

            sender_start = json.loads(
                (
                    HELPERS.build_demo_layout(demo_output_dir=demo_output_dir).control_dir
                    / "sender_start.json"
                ).read_text(encoding="utf-8")
            )
            receiver_start = json.loads(
                (
                    HELPERS.build_demo_layout(demo_output_dir=demo_output_dir).control_dir
                    / "receiver_start.json"
                ).read_text(encoding="utf-8")
            )
            demo_state = json.loads(
                HELPERS.build_demo_layout(demo_output_dir=demo_output_dir).state_path.read_text(
                    encoding="utf-8"
                )
            )
            assert sender_start["agent_identity"] == sender_identity
            assert receiver_start["agent_identity"] == receiver_identity
            assert demo_state["cao_parsing_mode"] == "shadow_only"

            message_paths = sorted(
                (
                    HELPERS.build_demo_layout(demo_output_dir=demo_output_dir).mailbox_root
                    / "messages"
                ).glob("*/*.md")
            )
            assert message_paths == []
        finally:
            _best_effort_stop_demo(
                demo_output_dir=demo_output_dir,
                parameters_path=parameters_path,
                env=env,
            )
            assert not _tmux_session_exists(sender_identity)
            assert not _tmux_session_exists(receiver_identity)


def test_mailbox_roundtrip_live_workflow_rejects_cao_only(
    tmp_path: Path,
) -> None:
    """The tutorial pack should reject `cao_only` for the live workflow."""

    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    _write_fake_git(fake_bin_dir)
    _write_fake_cli_executables(fake_bin_dir)
    _write_fake_cao_server(fake_bin_dir)

    agent_def_dir = tmp_path / "agents"
    _seed_live_agent_def_dir(agent_def_dir)

    suffix = uuid.uuid4().hex[:8]
    sender_identity = f"AGENTSYS-live-mailbox-sender-{suffix}"
    receiver_identity = f"AGENTSYS-live-mailbox-receiver-{suffix}"
    base_url = f"http://127.0.0.1:{_pick_unused_loopback_port()}"
    parameters_path = tmp_path / "demo_parameters.json"
    _write_parameters(
        parameters_path,
        agent_def_dir=agent_def_dir,
        cao_base_url=base_url,
        sender_identity=sender_identity,
        receiver_identity=receiver_identity,
    )
    env = _build_env(tmp_path=tmp_path, fake_bin_dir=fake_bin_dir, base_url=base_url)
    demo_output_dir = tmp_path / "demo"

    start_result = _run_demo_command(
        command="start",
        demo_output_dir=demo_output_dir,
        parameters_path=parameters_path,
        env=env,
        cao_parsing_mode="cao_only",
    )

    assert start_result.returncode == 1
    assert "only supports `shadow_only`" in start_result.stderr
    assert not HELPERS.build_demo_layout(demo_output_dir=demo_output_dir).state_path.exists()
