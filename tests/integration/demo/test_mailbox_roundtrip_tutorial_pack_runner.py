"""Integration coverage for the mailbox roundtrip tutorial-pack runner."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path
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
    """Copy the tracked fixture agent definitions into the isolated repo."""

    shutil.copytree(
        _source_repo_root() / "tests" / "fixtures" / "agents",
        repo_root / "tests" / "fixtures" / "agents",
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
            common_dir = repo_root / ".git"
            in_repo_root = cwd == repo_root or repo_root in cwd.parents
            in_worktree = (cwd / ".git").exists()

            if raw_args == ["rev-parse", "--show-toplevel"]:
                if in_worktree:
                    print(str(cwd))
                    raise SystemExit(0)
                if in_repo_root:
                    print(str(repo_root))
                    raise SystemExit(0)
                raise SystemExit(1)

            if raw_args == ["rev-parse", "--is-inside-work-tree"]:
                if in_repo_root or in_worktree:
                    print("true")
                    raise SystemExit(0)
                raise SystemExit(1)

            if raw_args == ["rev-parse", "--git-common-dir"]:
                if in_repo_root or in_worktree:
                    print(str(common_dir))
                    raise SystemExit(0)
                raise SystemExit(1)

            if len(raw_args) == 5 and raw_args[:3] == ["worktree", "add", "--detach"] and raw_args[4] == "HEAD":
                target = Path(raw_args[3]).expanduser()
                if not target.is_absolute():
                    target = (cwd / target).resolve()
                target.mkdir(parents=True, exist_ok=True)
                (target / ".git").write_text("gitdir: fake\\n", encoding="utf-8")
                print(f"Preparing worktree (detached HEAD) at '{target}'")
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
            import subprocess
            import sys
            from pathlib import Path

            state_path = Path(os.environ["FAKE_PIXI_STATE"])
            log_path = Path(os.environ["FAKE_PIXI_COMMAND_LOG"])
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
            else:
                state = {
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
                    print(
                        json.dumps(
                            {
                                "healthy": True,
                                "started_new_process": True,
                                "reused_existing_process": False,
                                "message": "started fake CAO",
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
                session_manifest.write_text("{}", encoding="utf-8")
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
                if operation == "send":
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
                    print(
                        json.dumps(
                            {
                                "ok": True,
                                "operation": "check",
                                "transport": "filesystem",
                                "principal_id": session["principal_id"],
                                "request_id": request_id,
                                "unread_count": 1,
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
        return repo_root / "tmp" / "demo" / "mailbox-roundtrip-tutorial-pack"
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


def test_mailbox_roundtrip_runner_honors_demo_output_dir_and_jobs_dir(tmp_path: Path) -> None:
    """The shell runner should honor the revised output-dir and jobs-dir contract."""

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
    output_relative = "demos/manual-mailbox-run"
    jobs_relative = "tmp/demo/mailbox-jobs"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(repo_root)
    env["FAKE_PIXI_STATE"] = str(state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(log_path)
    env.pop("CAO_PROFILE_STORE", None)
    env.pop("DEMO_EXTERNAL_CAO", None)

    result = subprocess.run(
        [
            str(demo_pack_dir / "run_demo.sh"),
            "--demo-output-dir",
            output_relative,
            "--jobs-dir",
            jobs_relative,
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "verification passed" in result.stdout

    demo_output_dir = _demo_output_dir(repo_root, output_relative)
    jobs_root = _demo_output_dir(repo_root, jobs_relative)
    assert (demo_output_dir / "project" / ".git").is_file()
    actual_sanitized = json.loads(
        (demo_output_dir / "report.sanitized.json").read_text(encoding="utf-8")
    )
    expected_sanitized = json.loads(
        (demo_pack_dir / "expected_report" / "report.json").read_text(encoding="utf-8")
    )
    assert actual_sanitized == expected_sanitized

    command_log = _load_command_log(log_path)
    calls = _realm_controller_calls(command_log)
    launcher_calls = _launcher_calls(command_log)
    build_calls = [call for call in calls if call[4] == "build-brain"]
    start_calls = [call for call in calls if call[4] == "start-session"]
    mail_calls = [call for call in calls if call[4:6] == ["mail", "send"]]
    mail_calls += [call for call in calls if call[4:6] == ["mail", "check"]]
    mail_calls += [call for call in calls if call[4:6] == ["mail", "reply"]]
    stop_calls = [call for call in calls if call[4] == "stop-session"]

    assert len(build_calls) == 2
    assert all("--blueprint" in call for call in build_calls)

    assert len(start_calls) == 2
    for call in start_calls:
        assert "--backend" in call
        assert call[call.index("--backend") + 1] == "cao_rest"
        assert "--blueprint" in call
        assert "--workdir" in call
        assert call[call.index("--workdir") + 1] == str(demo_output_dir / "project")
        assert "--mailbox-transport" in call
        assert call[call.index("--mailbox-transport") + 1] == "filesystem"
        assert "--mailbox-root" in call
        assert call[call.index("--mailbox-root") + 1] == str(demo_output_dir / "shared-mailbox")
        assert "--mailbox-principal-id" in call
        assert "--mailbox-address" in call
        assert "--cao-profile-store" in call
        assert (
            call[call.index("--cao-profile-store") + 1]
            == str(
                demo_output_dir
                / "cao"
                / "runtime"
                / "cao_servers"
                / "localhost-9889"
                / "home"
                / ".aws"
                / "cli-agent-orchestrator"
                / "agent-store"
            )
        )

    assert [call[4] for call in launcher_calls] == ["start", "stop"]

    sender_start = json.loads((demo_output_dir / "sender_start.json").read_text(encoding="utf-8"))
    receiver_start = json.loads((demo_output_dir / "receiver_start.json").read_text(encoding="utf-8"))
    assert sender_start["job_dir"] == str(jobs_root / "AGENTSYS-mailbox-sender")
    assert receiver_start["job_dir"] == str(jobs_root / "AGENTSYS-mailbox-receiver")

    assert [call[5] for call in calls if call[4] == "mail"] == ["send", "check", "reply", "check"]
    assert len(mail_calls) == 4

    assert len(stop_calls) == 2
    stop_identities = {call[call.index("--agent-identity") + 1] for call in stop_calls}
    assert stop_identities == {"AGENTSYS-mailbox-sender", "AGENTSYS-mailbox-receiver"}


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

    fake_bin_dir = tmp_path / "fake-bin"
    fake_bin_dir.mkdir()
    _write_fake_tools(fake_bin_dir)

    state_path = tmp_path / "pixi-state.json"
    log_path = tmp_path / "pixi-command-log.jsonl"

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(repo_root)
    env["FAKE_PIXI_STATE"] = str(state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(log_path)
    env["AGENT_DEF_DIR"] = str(custom_agent_def_dir)
    env.pop("CAO_PROFILE_STORE", None)
    env.pop("DEMO_EXTERNAL_CAO", None)

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
    assert all(call[call.index("--agent-def-dir") + 1] == str(custom_agent_def_dir) for call in calls)


def test_mailbox_roundtrip_runner_cleans_up_sender_when_receiver_start_fails(tmp_path: Path) -> None:
    """Trap cleanup should stop the already-started sender if receiver startup fails."""

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

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(repo_root)
    env["FAKE_PIXI_STATE"] = str(state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(log_path)
    env["FAKE_RECEIVER_START_FAIL"] = "1"
    env.pop("CAO_PROFILE_STORE", None)
    env.pop("DEMO_EXTERNAL_CAO", None)

    result = subprocess.run(
        [str(demo_pack_dir / "run_demo.sh")],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "receiver_start" in result.stdout

    command_log = _load_command_log(log_path)
    calls = _realm_controller_calls(command_log)
    launcher_calls = _launcher_calls(command_log)
    stop_calls = [call for call in calls if call[4] == "stop-session"]
    assert len(stop_calls) == 1
    assert stop_calls[0][stop_calls[0].index("--agent-identity") + 1] == "AGENTSYS-mailbox-sender"
    assert [call[4] for call in launcher_calls] == ["start", "stop"]

    demo_output_dir = _demo_output_dir(repo_root)
    assert (demo_output_dir / "cleanup_sender_stop.json").is_file()
    assert (demo_output_dir / "cleanup_cao_stop.json").is_file()


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

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env['PATH']}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(repo_root)
    env["FAKE_PIXI_STATE"] = str(state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(log_path)
    env["CAO_BASE_URL"] = "http://cao.example.com:9889"
    env.pop("CAO_PROFILE_STORE", None)
    env.pop("DEMO_EXTERNAL_CAO", None)

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
