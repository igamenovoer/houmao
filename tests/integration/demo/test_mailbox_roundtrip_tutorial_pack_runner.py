"""Integration coverage for the mailbox roundtrip tutorial-pack runner."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _source_repo_root() -> Path:
    """Return the source repository root."""

    return Path(__file__).resolve().parents[3]


def _source_demo_pack_dir() -> Path:
    """Return the source mailbox tutorial-pack directory."""

    return _source_repo_root() / "scripts" / "demo" / "mailbox-roundtrip-tutorial-pack"


def _write_executable(path: Path, content: str) -> None:
    """Write one executable helper into the fake tool directory."""

    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _copy_demo_pack(repo_root: Path) -> Path:
    """Copy the demo pack into the isolated repository root."""

    demo_pack_dir = repo_root / "scripts" / "demo" / "mailbox-roundtrip-tutorial-pack"
    shutil.copytree(_source_demo_pack_dir(), demo_pack_dir)
    return demo_pack_dir


def _copy_agent_defs(repo_root: Path) -> None:
    """Copy tracked agent and dummy-project fixtures into the isolated repo."""

    shutil.copytree(
        _source_repo_root() / "tests" / "fixtures" / "agents",
        repo_root / "tests" / "fixtures" / "agents",
    )
    shutil.copytree(
        _source_repo_root() / "tests" / "fixtures" / "dummy-projects",
        repo_root / "tests" / "fixtures" / "dummy-projects",
    )


def _write_launcher_context(repo_root: Path, *, base_url: str, launcher_home_dir: Path) -> None:
    """Write one repo-local launcher config plus ownership artifact."""

    config_dir = repo_root / "config" / "cao-server-launcher"
    runtime_root = repo_root / "config" / "cao-server-launcher" / "tmp" / "agents-runtime"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "local.toml").write_text(
        textwrap.dedent(
            f"""\
            base_url = "{base_url}"
            runtime_root = "tmp/agents-runtime"
            home_dir = "{launcher_home_dir}"
            proxy_policy = "clear"
            startup_timeout_seconds = 15
            """
        ),
        encoding="utf-8",
    )

    parsed = urlparse(base_url)
    assert parsed.hostname is not None
    assert parsed.port is not None
    host = parsed.hostname
    port = parsed.port
    ownership_path = runtime_root / "cao_servers" / f"{host}-{port}" / "launcher" / "ownership.json"
    ownership_path.parent.mkdir(parents=True, exist_ok=True)
    ownership_path.write_text(
        json.dumps(
            {
                "managed_by": "houmao.cao.server_launcher",
                "launch_mode": "detached",
                "base_url": base_url,
                "runtime_root": str(runtime_root),
                "artifact_dir": str(ownership_path.parent),
                "home_dir": str(launcher_home_dir),
                "config_path": str(config_dir / "local.toml"),
                "proxy_policy": "clear",
                "pid": 1234,
                "process_group_id": 1234,
                "executable_path": str(repo_root / "fake-bin" / "cao-server"),
                "started_at_utc": "2026-03-16T09:00:00+00:00",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_fake_tools(fake_bin_dir: Path) -> None:
    """Create fake CLI tools for the shell-runner integration test."""

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
    _write_executable(fake_bin_dir / "tmux", "#!/usr/bin/env bash\nexit 0\n")
    _write_executable(
        fake_bin_dir / "pixi",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import json
            import os
            import sqlite3
            import subprocess
            import sys
            from pathlib import Path

            state_path = Path(os.environ["FAKE_PIXI_STATE"])
            log_path = Path(os.environ["FAKE_PIXI_COMMAND_LOG"])
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
            else:
                state = {
                    "messages": {},
                    "sessions": {},
                    "request_index": 0,
                    "send_message_id": "msg-20260316T120000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "reply_message_id": "msg-20260316T120500Z-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                }

            args = sys.argv[1:]
            if args == ["run", "python", "-V"]:
                print("Python 3.11.0")
                raise SystemExit(0)
            if args[:2] != ["run", "python"]:
                raise SystemExit(f"unexpected pixi args: {args!r}")

            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"args": args}) + "\\n")

            if args[2] != "-m":
                process = subprocess.run(
                    [sys.executable, args[2], *args[3:]],
                    check=False,
                    env=os.environ.copy(),
                )
                raise SystemExit(process.returncode)

            module = args[3]
            if module == "houmao.cao.tools.cao_server_launcher":
                command = args[4]

                def arg_value(flag: str) -> str:
                    index = args.index(flag)
                    return args[index + 1]

                def save_state() -> None:
                    state_path.write_text(json.dumps(state), encoding="utf-8")

                def load_launcher_context(config_path: Path) -> tuple[str, Path, Path]:
                    config_values: dict[str, str] = {}
                    for line in config_path.read_text(encoding="utf-8").splitlines():
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        key, raw_value = stripped.split("=", 1)
                        config_values[key.strip()] = raw_value.strip().strip('"')
                    base_url = config_values["base_url"].rstrip("/")
                    runtime_root_raw = config_values["runtime_root"]
                    runtime_root = (
                        (config_path.parent / runtime_root_raw).resolve()
                        if not Path(runtime_root_raw).is_absolute()
                        else Path(runtime_root_raw).resolve()
                    )
                    host_port = base_url.removeprefix("http://")
                    host, port = host_port.split(":", 1)
                    server_root = runtime_root / "cao_servers" / f"{host}-{port}"
                    return base_url, server_root / "launcher", server_root / "home"

                config_path = Path(arg_value("--config")).resolve()
                base_url, artifact_dir, home_dir = load_launcher_context(config_path)
                ownership = {
                    "managed_by": "houmao.cao.server_launcher",
                    "base_url": base_url,
                    "artifact_dir": str(artifact_dir),
                }

                if command == "start":
                    state["cao"] = {"healthy": True}
                    reused_existing = os.environ.get("FAKE_CAO_REUSE") == "1"
                    print(
                        json.dumps(
                            {
                                "healthy": True,
                                "started_new_process": not reused_existing,
                                "reused_existing_process": reused_existing,
                                "message": "reused fake CAO" if reused_existing else "started fake CAO",
                                "ownership": ownership,
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)

                if command == "status":
                    healthy = bool(state.get("cao", {}).get("healthy"))
                    print(
                        json.dumps(
                            {
                                "healthy": healthy,
                                "service": "cli-agent-orchestrator" if healthy else None,
                                "error": None if healthy else "connection refused",
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0 if healthy else 2)

                if command == "stop":
                    healthy = bool(state.get("cao", {}).get("healthy"))
                    state["cao"] = {"healthy": False}
                    print(
                        json.dumps(
                            {
                                "stopped": healthy,
                                "already_stopped": not healthy,
                                "message": "stopped fake CAO" if healthy else "fake CAO already stopped",
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)

                raise SystemExit(f"unexpected launcher command: {command!r}")

            if module != "houmao.agents.realm_controller":
                process = subprocess.run(
                    [sys.executable, "-m", module, *args[4:]],
                    check=False,
                    env=os.environ.copy(),
                )
                raise SystemExit(process.returncode)

            command = args[4]

            def arg_value(flag: str) -> str:
                index = args.index(flag)
                return args[index + 1]

            def next_request_id() -> str:
                state["request_index"] = int(state.get("request_index", 0)) + 1
                return f"req-{state['request_index']}"

            def save_state() -> None:
                state_path.write_text(json.dumps(state), encoding="utf-8")

            def find_session_by_address(address: str) -> dict[str, str]:
                for payload in state["sessions"].values():
                    if payload["address"] == address:
                        return payload
                raise SystemExit(f"unexpected mailbox address: {address}")

            def unread_count(mailbox_root: Path, *, address: str) -> int:
                from houmao.mailbox.filesystem import resolve_active_mailbox_local_sqlite_path

                local_sqlite_path = resolve_active_mailbox_local_sqlite_path(
                    mailbox_root,
                    address=address,
                )
                with sqlite3.connect(local_sqlite_path) as connection:
                    row = connection.execute(
                        '''
                        SELECT COUNT(*)
                        FROM message_state
                        WHERE is_read = 0
                        '''
                    ).fetchone()
                if row is None:
                    return 0
                return int(row[0])

            def deliver_mail_message(
                *,
                mailbox_root: Path,
                message_id: str,
                thread_id: str,
                in_reply_to: str | None,
                references: list[str],
                created_at_utc: str,
                sender: dict[str, str],
                recipients: list[dict[str, str]],
                subject: str,
                body_markdown: str,
            ) -> dict[str, object]:
                from houmao.mailbox.managed import DeliveryRequest, deliver_message
                from houmao.mailbox.protocol import MailboxMessage, serialize_message_document

                staged_message = mailbox_root / "staging" / f"{message_id}.md"
                request = DeliveryRequest.from_payload(
                    {
                        "staged_message_path": str(staged_message),
                        "message_id": message_id,
                        "thread_id": thread_id,
                        "in_reply_to": in_reply_to,
                        "references": references,
                        "created_at_utc": created_at_utc,
                        "sender": {
                            "principal_id": sender["principal_id"],
                            "address": sender["address"],
                        },
                        "to": [
                            {
                                "principal_id": recipient["principal_id"],
                                "address": recipient["address"],
                            }
                            for recipient in recipients
                        ],
                        "cc": [],
                        "reply_to": [],
                        "subject": subject,
                        "attachments": [],
                        "headers": {},
                    }
                )
                message = MailboxMessage(
                    message_id=request.message_id,
                    thread_id=request.thread_id,
                    in_reply_to=request.in_reply_to,
                    references=list(request.references),
                    created_at_utc=request.created_at_utc,
                    sender=request.sender.to_mailbox_principal(),
                    to=[principal.to_mailbox_principal() for principal in request.to],
                    cc=[principal.to_mailbox_principal() for principal in request.cc],
                    reply_to=[principal.to_mailbox_principal() for principal in request.reply_to],
                    subject=request.subject,
                    body_markdown=body_markdown,
                    attachments=[attachment.to_mailbox_attachment() for attachment in request.attachments],
                    headers=dict(request.headers),
                )
                staged_message.parent.mkdir(parents=True, exist_ok=True)
                staged_message.write_text(
                    serialize_message_document(message),
                    encoding="utf-8",
                )
                return deliver_message(mailbox_root, request)

            if command == "build-brain":
                blueprint = arg_value("--blueprint")
                runtime_root = Path(arg_value("--runtime-root"))
                tool = "claude" if "claude" in blueprint else "codex"
                blueprint_id = Path(blueprint).stem
                home_path = runtime_root / "homes" / tool / blueprint_id
                manifest_path = runtime_root / "manifests" / f"{blueprint_id}.yaml"
                launch_helper_path = home_path / "launch.sh"
                home_path.mkdir(parents=True, exist_ok=True)
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_text("manifest: true\\n", encoding="utf-8")
                launch_helper_path.write_text("#!/usr/bin/env bash\\n", encoding="utf-8")
                print(
                    json.dumps(
                        {
                            "home_id": f"{blueprint_id}-home",
                            "home_path": str(home_path),
                            "manifest_path": str(manifest_path),
                            "launch_helper_path": str(launch_helper_path),
                        }
                    )
                )
                save_state()
                raise SystemExit(0)

            if command == "start-session":
                agent_identity = arg_value("--agent-identity")
                if (
                    os.environ.get("FAKE_RECEIVER_START_FAIL") == "1"
                    and agent_identity == "AGENTSYS-mailbox-receiver"
                ):
                    print("synthetic receiver startup failure", file=sys.stderr)
                    save_state()
                    raise SystemExit(2)

                blueprint = arg_value("--blueprint")
                runtime_root = Path(arg_value("--runtime-root"))
                tool = "claude" if "claude" in blueprint else "codex"
                mailbox_root = Path(arg_value("--mailbox-root"))
                principal_id = arg_value("--mailbox-principal-id")
                mailbox_address = arg_value("--mailbox-address")
                workdir = Path(arg_value("--workdir"))
                session_manifest = runtime_root / "sessions" / f"{agent_identity}.json"
                session_manifest.parent.mkdir(parents=True, exist_ok=True)
                terminal_id = f"term-{len(state['sessions']) + 1:03d}"
                session_manifest.write_text(
                    json.dumps(
                        {
                            "tmux_session_name": agent_identity,
                            "cao": {
                                "session_name": agent_identity,
                                "terminal_id": terminal_id,
                                "parsing_mode": "shadow_only",
                            },
                            "backend_state": {
                                "session_name": agent_identity,
                                "terminal_id": terminal_id,
                                "parsing_mode": "shadow_only",
                            },
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + "\\n",
                    encoding="utf-8",
                )
                from houmao.mailbox.filesystem import bootstrap_filesystem_mailbox
                from houmao.mailbox.protocol import MailboxPrincipal

                bootstrap_filesystem_mailbox(
                    mailbox_root,
                    principal=MailboxPrincipal(
                        principal_id=principal_id,
                        address=mailbox_address,
                    ),
                )
                jobs_root = os.environ.get("AGENTSYS_LOCAL_JOBS_DIR")
                if jobs_root:
                    job_dir = Path(jobs_root) / agent_identity
                else:
                    job_dir = workdir / ".houmao" / "jobs" / agent_identity
                state["sessions"][agent_identity] = {
                    "tool": tool,
                    "mailbox_root": str(mailbox_root),
                    "principal_id": principal_id,
                    "address": mailbox_address,
                }
                print(
                    json.dumps(
                        {
                            "session_manifest": str(session_manifest),
                            "backend": arg_value("--backend"),
                            "tool": tool,
                            "agent_identity": agent_identity,
                            "agent_name": agent_identity,
                            "tmux_session_name": agent_identity,
                            "job_dir": str(job_dir),
                            "mailbox": {
                                "transport": "filesystem",
                                "principal_id": principal_id,
                                "address": mailbox_address,
                                "filesystem_root": str(mailbox_root),
                                "bindings_version": "2026-03-16T12:00:00Z",
                            },
                        }
                    )
                )
                save_state()
                raise SystemExit(0)

            if command == "mail":
                operation = args[5]
                agent_identity = arg_value("--agent-identity")
                session = state["sessions"][agent_identity]
                request_id = next_request_id()

                def body_markdown() -> str:
                    if "--body-file" in args:
                        return Path(arg_value("--body-file")).resolve().read_text(encoding="utf-8")
                    return arg_value("--body-content")

                if operation == "send":
                    recipient = find_session_by_address(arg_value("--to"))
                    mailbox_root = Path(session["mailbox_root"])
                    subject = arg_value("--subject")
                    deliver_result = deliver_mail_message(
                        mailbox_root=mailbox_root,
                        message_id=state["send_message_id"],
                        thread_id=state["send_message_id"],
                        in_reply_to=None,
                        references=[],
                        created_at_utc="2026-03-16T12:00:00Z",
                        sender=session,
                        recipients=[recipient],
                        subject=subject,
                        body_markdown=body_markdown(),
                    )
                    state["messages"][state["send_message_id"]] = {
                        "canonical_path": str(deliver_result["canonical_path"]),
                        "sender_address": session["address"],
                        "sender_principal_id": session["principal_id"],
                        "subject": subject,
                        "thread_id": state["send_message_id"],
                    }
                    print(
                        json.dumps(
                            {
                                "ok": True,
                                "operation": "send",
                                "transport": "filesystem",
                                "principal_id": session["principal_id"],
                                "request_id": request_id,
                                "message_id": state["send_message_id"],
                                "thread_id": state["send_message_id"],
                                "subject": arg_value("--subject"),
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)
                if operation == "check":
                    mailbox_root = Path(session["mailbox_root"])
                    print(
                        json.dumps(
                            {
                                "ok": True,
                                "operation": "check",
                                "transport": "filesystem",
                                "principal_id": session["principal_id"],
                                "request_id": request_id,
                                "unread_count": unread_count(mailbox_root, address=session["address"]),
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)
                if operation == "reply":
                    if arg_value("--message-id") != state["send_message_id"]:
                        print("reply parent mismatch", file=sys.stderr)
                        save_state()
                        raise SystemExit(2)
                    parent_message = state["messages"][state["send_message_id"]]
                    recipient = find_session_by_address(parent_message["sender_address"])
                    mailbox_root = Path(session["mailbox_root"])
                    deliver_result = deliver_mail_message(
                        mailbox_root=mailbox_root,
                        message_id=state["reply_message_id"],
                        thread_id=state["send_message_id"],
                        in_reply_to=state["send_message_id"],
                        references=[state["send_message_id"]],
                        created_at_utc="2026-03-16T12:05:00Z",
                        sender=session,
                        recipients=[recipient],
                        subject=parent_message["subject"],
                        body_markdown=body_markdown(),
                    )
                    state["messages"][state["reply_message_id"]] = {
                        "canonical_path": str(deliver_result["canonical_path"]),
                        "sender_address": session["address"],
                        "sender_principal_id": session["principal_id"],
                        "subject": parent_message["subject"],
                        "thread_id": state["send_message_id"],
                    }
                    print(
                        json.dumps(
                            {
                                "ok": True,
                                "operation": "reply",
                                "transport": "filesystem",
                                "principal_id": session["principal_id"],
                                "request_id": request_id,
                                "message_id": state["reply_message_id"],
                                "thread_id": state["send_message_id"],
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)
                raise SystemExit(f"unexpected mail operation: {operation!r}")

            if command == "stop-session":
                agent_identity = arg_value("--agent-identity")
                state["sessions"].pop(agent_identity, None)
                print(json.dumps({"status": "ok", "action": "terminate", "detail": "stopped"}))
                save_state()
                raise SystemExit(0)

            raise SystemExit(f"unexpected realm-controller command: {command!r}")
            """
        ),
    )


def _demo_output_dir(repo_root: Path, relative_path: str | None = None) -> Path:
    """Return the expected demo output directory."""

    if relative_path is None:
        return repo_root / "scripts" / "demo" / "mailbox-roundtrip-tutorial-pack" / "outputs"
    return repo_root / relative_path


def _load_command_log(path: Path) -> list[dict[str, object]]:
    """Load the fake pixi command log."""

    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _realm_controller_calls(command_log: list[dict[str, object]]) -> list[list[str]]:
    """Return logged `houmao.agents.realm_controller` invocations."""

    calls: list[list[str]] = []
    for entry in command_log:
        args = [str(item) for item in entry["args"]]
        if args[:4] == ["run", "python", "-m", "houmao.agents.realm_controller"]:
            calls.append(args)
    return calls


def _launcher_calls(command_log: list[dict[str, object]]) -> list[list[str]]:
    """Return logged `cao_server_launcher` invocations."""

    calls: list[list[str]] = []
    for entry in command_log:
        args = [str(item) for item in entry["args"]]
        if args[:4] == ["run", "python", "-m", "houmao.cao.tools.cao_server_launcher"]:
            calls.append(args)
    return calls


def _base_env(
    *,
    fake_bin_dir: Path,
    repo_root: Path,
    state_path: Path,
    log_path: Path,
) -> dict[str, str]:
    """Build one shared fake-tool environment for mailbox demo tests."""

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(repo_root)
    env["FAKE_PIXI_STATE"] = str(state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(log_path)
    for key in (
        "CAO_PROFILE_STORE",
        "DEMO_EXTERNAL_CAO",
        "FAKE_CAO_REUSE",
        "FAKE_RECEIVER_START_FAIL",
        "MAILBOX_ROUNDTRIP_DEMO_FAULT",
    ):
        env.pop(key, None)
    return env


def _run_scenario_runner(
    *,
    repo_root: Path,
    demo_pack_dir: Path,
    automation_root: Path,
    env: dict[str, str],
    scenarios: list[str],
) -> subprocess.CompletedProcess[str]:
    """Run the pack-local scenario runner for one selected scenario set."""

    argv = [
        "pixi",
        "run",
        "python",
        str(demo_pack_dir / "scripts" / "run_automation_scenarios.py"),
        "--automation-root",
        str(automation_root),
    ]
    for scenario_id in scenarios:
        argv.extend(["--scenario", scenario_id])
    return subprocess.run(
        argv,
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _scenario_result(automation_root: Path, scenario_id: str) -> dict[str, Any]:
    """Load one persisted scenario result payload."""

    return json.loads(
        (automation_root / scenario_id / "scenario-result.json").read_text(encoding="utf-8")
    )


def test_mailbox_roundtrip_scenario_runner_covers_contract_and_ownership_cases(
    tmp_path: Path,
) -> None:
    """The pack-local scenario runner should cover the core success and ownership cases."""

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "demo").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    demo_pack_dir = _copy_demo_pack(repo_root)
    _copy_agent_defs(repo_root)

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"
    automation_root = tmp_path / "automation"
    env = _base_env(
        fake_bin_dir=fake_bin_dir,
        repo_root=repo_root,
        state_path=state_path,
        log_path=log_path,
    )

    result = _run_scenario_runner(
        repo_root=repo_root,
        demo_pack_dir=demo_pack_dir,
        automation_root=automation_root,
        env=env,
        scenarios=[
            "auto-implicit-jobs-dir",
            "auto-explicit-jobs-dir",
            "rerun-valid-project-reuse",
            "incompatible-project-dir",
            "cleanup-ownership-reused-managed-cao",
        ],
    )

    assert result.returncode == 0, result.stderr
    suite_summary = json.loads((automation_root / "suite-summary.json").read_text(encoding="utf-8"))
    assert suite_summary["failed"] == 0

    implicit = _scenario_result(automation_root, "auto-implicit-jobs-dir")
    explicit = _scenario_result(automation_root, "auto-explicit-jobs-dir")
    rerun = _scenario_result(automation_root, "rerun-valid-project-reuse")
    incompatible = _scenario_result(automation_root, "incompatible-project-dir")
    ownership = _scenario_result(automation_root, "cleanup-ownership-reused-managed-cao")

    assert implicit["ok"] is True
    assert explicit["ok"] is True
    assert rerun["ok"] is True
    assert incompatible["ok"] is True
    assert ownership["ok"] is True
    assert implicit["checks"]["sender_job_dir"].endswith(
        "/project/.houmao/jobs/AGENTSYS-mailbox-sender"
    )
    assert explicit["checks"]["sender_job_dir"].endswith("/jobs-root/AGENTSYS-mailbox-sender")
    assert implicit["checks"]["send_body_matches_input"] is True
    assert implicit["checks"]["reply_body_present"] is True
    assert implicit["checks"]["reply_parent_matches_send"] is True
    assert implicit["checks"]["sender_sent_projection_targets_send"] is True
    assert implicit["checks"]["receiver_inbox_projection_targets_send"] is True
    assert implicit["checks"]["receiver_sent_projection_targets_reply"] is True
    assert implicit["checks"]["sender_inbox_projection_targets_reply"] is True
    assert implicit["checks"]["chat_log_has_send_event"] is True
    assert implicit["checks"]["chat_log_has_reply_event"] is True
    assert implicit["checks"]["chat_log_send_matches_input"] is True
    assert implicit["checks"]["chat_log_reply_matches_mailbox_reply"] is True
    assert implicit["checks"]["send_message_path"].endswith(
        "/msg-20260316T120000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md"
    )
    assert implicit["checks"]["reply_message_path"].endswith(
        "/msg-20260316T120500Z-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.md"
    )
    assert explicit["checks"]["send_body_matches_input"] is True
    assert explicit["checks"]["reply_body_present"] is True
    assert rerun["checks"]["reuse_marker_preserved"] is False
    assert incompatible["checks"]["sender_start_created"] is False
    assert ownership["checks"]["cao_ownership"] == "reused-existing-process"


def test_mailbox_roundtrip_scenario_runner_covers_stepwise_snapshot_and_cleanup_cases(
    tmp_path: Path,
) -> None:
    """The scenario runner should cover stepwise verify and failure cleanup paths."""

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "demo").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    demo_pack_dir = _copy_demo_pack(repo_root)
    _copy_agent_defs(repo_root)

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"
    automation_root = tmp_path / "automation"
    env = _base_env(
        fake_bin_dir=fake_bin_dir,
        repo_root=repo_root,
        state_path=state_path,
        log_path=log_path,
    )

    result = _run_scenario_runner(
        repo_root=repo_root,
        demo_pack_dir=demo_pack_dir,
        automation_root=automation_root,
        env=env,
        scenarios=[
            "stepwise-start-roundtrip-verify-stop",
            "verify-snapshot-refresh",
            "partial-failure-cleanup",
            "interrupted-run-cleanup",
        ],
    )

    assert result.returncode == 0, result.stderr
    suite_summary = json.loads((automation_root / "suite-summary.json").read_text(encoding="utf-8"))
    assert suite_summary["failed"] == 0

    stepwise = _scenario_result(automation_root, "stepwise-start-roundtrip-verify-stop")
    snapshot = _scenario_result(automation_root, "verify-snapshot-refresh")
    failure = _scenario_result(automation_root, "partial-failure-cleanup")
    interrupted = _scenario_result(automation_root, "interrupted-run-cleanup")

    assert stepwise["ok"] is True
    assert snapshot["ok"] is True
    assert failure["ok"] is True
    assert interrupted["ok"] is True
    assert stepwise["checks"]["verify_result_path"].endswith("/control/verify_result.json")
    assert stepwise["checks"]["sender_inspect_tool_state"] == "unknown"
    assert stepwise["checks"]["receiver_inspect_has_tail_request"] is True
    assert stepwise["checks"]["send_body_matches_input"] is True
    assert stepwise["checks"]["reply_body_present"] is True
    assert stepwise["checks"]["reply_thread_matches_send"] is True
    assert stepwise["checks"]["reply_parent_matches_send"] is True
    assert stepwise["checks"]["sender_sent_projection_targets_send"] is True
    assert stepwise["checks"]["receiver_inbox_projection_targets_send"] is True
    assert stepwise["checks"]["receiver_sent_projection_targets_reply"] is True
    assert stepwise["checks"]["sender_inbox_projection_targets_reply"] is True
    assert stepwise["checks"]["chat_log_has_send_event"] is True
    assert stepwise["checks"]["chat_log_has_reply_event"] is True
    assert snapshot["checks"]["snapshot_refreshed"] is True
    assert snapshot["checks"]["snapshot_excludes_raw_body_content"] is True
    assert failure["checks"]["cleanup_mode"] is True
    assert interrupted["checks"]["cleanup_mode"] is True
    assert interrupted["checks"]["mail_reply_present"] is False


def test_mailbox_roundtrip_runner_honors_agent_def_dir_env_override(tmp_path: Path) -> None:
    """The shell runner should preserve the documented `AGENT_DEF_DIR` override."""

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "demo").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    demo_pack_dir = _copy_demo_pack(repo_root)
    custom_agent_def_dir = repo_root / "custom-agent-defs"
    shutil.copytree(
        _source_repo_root() / "tests" / "fixtures" / "agents",
        custom_agent_def_dir,
    )
    shutil.copytree(
        _source_repo_root() / "tests" / "fixtures" / "dummy-projects",
        repo_root / "tests" / "fixtures" / "dummy-projects",
    )

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"

    env = _base_env(
        fake_bin_dir=fake_bin_dir,
        repo_root=repo_root,
        state_path=state_path,
        log_path=log_path,
    )
    env["AGENT_DEF_DIR"] = str(custom_agent_def_dir)

    result = subprocess.run(
        [str(demo_pack_dir / "run_demo.sh")],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "verification passed" in result.stdout

    calls = _realm_controller_calls(_load_command_log(log_path))
    assert calls
    assert all("--agent-def-dir" in call for call in calls)
    assert all(
        call[call.index("--agent-def-dir") + 1] == str(custom_agent_def_dir) for call in calls
    )


def test_mailbox_roundtrip_runner_skips_external_cao_without_explicit_profile_store(
    tmp_path: Path,
) -> None:
    """External CAO mode should skip instead of guessing profile-store state."""

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "demo").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    demo_pack_dir = _copy_demo_pack(repo_root)
    _copy_agent_defs(repo_root)

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"

    env = _base_env(
        fake_bin_dir=fake_bin_dir,
        repo_root=repo_root,
        state_path=state_path,
        log_path=log_path,
    )
    env["CAO_BASE_URL"] = "http://cao.example.com:9889"

    result = subprocess.run(
        [str(demo_pack_dir / "run_demo.sh")],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "SKIP: external CAO requires explicit CAO_PROFILE_STORE" in result.stdout
    assert _launcher_calls(_load_command_log(log_path)) == []


def test_mailbox_roundtrip_autotest_harness_runs_roundtrip_case(tmp_path: Path) -> None:
    """The real-agent autotest harness should dispatch the canonical roundtrip case."""

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "demo").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    demo_pack_dir = _copy_demo_pack(repo_root)
    _copy_agent_defs(repo_root)

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"
    env = _base_env(
        fake_bin_dir=fake_bin_dir,
        repo_root=repo_root,
        state_path=state_path,
        log_path=log_path,
    )
    demo_output_dir = tmp_path / "autotest-demo"
    result = subprocess.run(
        [
            str(demo_pack_dir / "autotest" / "run_autotest.sh"),
            "--case",
            "real-agent-roundtrip",
            "--demo-output-dir",
            str(demo_output_dir),
            "--phase-timeout-seconds",
            "30",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    case_result = json.loads(
        (
            demo_output_dir / "control" / "testplans" / "case-real-agent-roundtrip.result.json"
        ).read_text(encoding="utf-8")
    )
    assert case_result["status"] == "success"
    assert case_result["ok"] is True
    assert case_result["mailbox_persistence_ok"] is True
    assert case_result["mailbox_evidence"]["send_message_path"].endswith(
        "/msg-20260316T120000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.md"
    )
    assert case_result["mailbox_evidence"]["reply_message_path"].endswith(
        "/msg-20260316T120500Z-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.md"
    )
    assert "inspect --demo-output-dir" in case_result["inspect_commands"]["sender"]
    assert (
        demo_output_dir / "control" / "testplans" / "case-real-agent-roundtrip.preflight.json"
    ).is_file()
    assert (
        demo_output_dir
        / "control"
        / "testplans"
        / "logs"
        / "case-real-agent-roundtrip"
        / "01-start.stdout.txt"
    ).is_file()


def test_mailbox_roundtrip_autotest_preflight_fails_for_external_cao(tmp_path: Path) -> None:
    """The real-agent autotest harness should fail fast on unsupported external CAO."""

    repo_root = tmp_path / "repo"
    (repo_root / "scripts" / "demo").mkdir(parents=True)
    (repo_root / "tests" / "fixtures").mkdir(parents=True)
    demo_pack_dir = _copy_demo_pack(repo_root)
    _copy_agent_defs(repo_root)

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"
    env = _base_env(
        fake_bin_dir=fake_bin_dir,
        repo_root=repo_root,
        state_path=state_path,
        log_path=log_path,
    )
    env["CAO_BASE_URL"] = "http://cao.example.com:9889"

    demo_output_dir = tmp_path / "autotest-demo"
    result = subprocess.run(
        [
            str(demo_pack_dir / "autotest" / "run_autotest.sh"),
            "--case",
            "real-agent-preflight",
            "--demo-output-dir",
            str(demo_output_dir),
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    preflight_result = json.loads(
        (
            demo_output_dir / "control" / "testplans" / "case-real-agent-preflight.result.json"
        ).read_text(encoding="utf-8")
    )
    assert preflight_result["ok"] is False
    assert any("loopback CAO URLs" in blocker for blocker in preflight_result["blockers"])
