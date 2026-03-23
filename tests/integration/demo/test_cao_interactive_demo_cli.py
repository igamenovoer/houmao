"""Integration coverage for the interactive CAO demo wrappers."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import textwrap
from pathlib import Path

from houmao.demo.cao_interactive_demo import (
    FIXED_CAO_BASE_URL,
    TEST_LOOPBACK_PORT_LISTENING_ENV,
)


def _source_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _source_demo_pack_dir() -> Path:
    return _source_repo_root() / "scripts" / "demo" / "cao-interactive-full-pipeline-demo"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _copy_demo_pack(repo_root: Path) -> Path:
    demo_pack_dir = repo_root / "scripts" / "demo" / "cao-interactive-full-pipeline-demo"
    shutil.copytree(_source_demo_pack_dir(), demo_pack_dir)
    return demo_pack_dir


def _copy_agent_defs(repo_root: Path) -> None:
    shutil.copytree(
        _source_repo_root() / "tests" / "fixtures" / "agents",
        repo_root / "tests" / "fixtures" / "agents",
    )


def _write_fake_tools(fake_bin_dir: Path) -> None:
    _write_executable(
        fake_bin_dir / "cao-server",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        fake_bin_dir / "git",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import os
            import sys
            from pathlib import Path

            args = sys.argv[1:]
            if args[:3] == ["-C", args[1], "rev-parse"] and args[3:] == ["--show-toplevel"]:
                print(os.environ["FAKE_GIT_TOPLEVEL"])
                raise SystemExit(0)

            if args[:3] == ["worktree", "add", "--detach"] and len(args) >= 5:
                worktree_path = Path(args[3])
                worktree_path.mkdir(parents=True, exist_ok=True)
                (worktree_path / ".git").write_text("gitdir: fake\\n", encoding="utf-8")
                raise SystemExit(0)

            raise SystemExit(f"unexpected git args: {args!r}")
            """
        ),
    )
    _write_executable(
        fake_bin_dir / "tmux",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import json
            import os
            import sys
            from pathlib import Path

            state_path = Path(os.environ["FAKE_PIXI_STATE"])
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
            else:
                state = {"tmux_sessions": []}
            state.setdefault("tmux_sessions", [])

            args = sys.argv[1:]
            if args[:2] == ["has-session", "-t"]:
                raise SystemExit(0 if args[2] in state["tmux_sessions"] else 1)
            if args[:2] == ["kill-session", "-t"]:
                state["tmux_sessions"] = [
                    session for session in state["tmux_sessions"] if session != args[2]
                ]
                state_path.write_text(json.dumps(state), encoding="utf-8")
                raise SystemExit(0)

            raise SystemExit(f"unexpected tmux args: {args!r}")
            """
        ),
    )
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
                state = {}
            state.setdefault("turn_count", 0)
            state.setdefault("control_count", 0)
            state.setdefault("tmux_sessions", [])
            state.setdefault("cao_stop_count", 0)

            args = sys.argv[1:]
            if args[:2] != ["run", "python"]:
                raise SystemExit(f"unexpected pixi args: {args!r}")

            module = args[3] if len(args) > 3 and args[2] == "-m" else args[2]
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "module": module,
                            "args": args,
                        }
                    )
                    + "\\n"
                )

            if args[2] != "-m":
                proc = subprocess.run(
                    [sys.executable, args[2], *args[3:]],
                    env=os.environ.copy(),
                    check=False,
                )
                raise SystemExit(proc.returncode)

            def arg_value(flag: str) -> str:
                index = args.index(flag)
                return args[index + 1]

            def save_state() -> None:
                state_path.write_text(json.dumps(state), encoding="utf-8")

            def set_loopback_port_state(value: str) -> None:
                override = os.environ.get(
                    "AGENTSYS_TEST_INTERACTIVE_DEMO_FIXED_PORT_LISTENING", ""
                )
                if not override.startswith("file:"):
                    return
                loopback_state_path = Path(override.removeprefix("file:"))
                loopback_state_path.write_text(value, encoding="utf-8")

            if module == "houmao.demo.cao_interactive_demo.cli":
                proc = subprocess.run(
                    [sys.executable, "-m", module, *args[4:]],
                    env=os.environ.copy(),
                    check=False,
                )
                raise SystemExit(proc.returncode)

            status_mode = os.environ.get("FAKE_CAO_STATUS_MODE", "unhealthy")
            stop_session_mode = os.environ.get("FAKE_STOP_SESSION_MODE", "ok")
            stop_plan = [
                item.strip()
                for item in os.environ.get("FAKE_CAO_STOP_PLAN", "success").split(",")
                if item.strip()
            ]
            if module == "houmao.cao.tools.cao_server_launcher":
                subcommand = args[4]
                if subcommand == "status":
                    if status_mode == "verified":
                        payload = {
                            "operation": "status",
                            "base_url": "http://127.0.0.1:9889",
                            "healthy": True,
                            "health_status": "ok",
                            "service": "cli-agent-orchestrator",
                            "error": None,
                        }
                        exit_code = 0
                    elif status_mode == "wrong-service":
                        payload = {
                            "operation": "status",
                            "base_url": "http://127.0.0.1:9889",
                            "healthy": True,
                            "health_status": "ok",
                            "service": "other-service",
                            "error": None,
                        }
                        exit_code = 0
                    else:
                        payload = {
                            "operation": "status",
                            "base_url": "http://127.0.0.1:9889",
                            "healthy": False,
                            "health_status": None,
                            "service": None,
                            "error": "connection refused",
                        }
                        exit_code = 2
                    print(json.dumps(payload))
                    save_state()
                    raise SystemExit(exit_code)

                if subcommand == "start":
                    print(
                        json.dumps(
                            {
                                "started_new_process": True,
                                "reused_existing_process": False,
                                "pid": 5151,
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)

                if subcommand == "stop":
                    stop_mode = stop_plan[min(state["cao_stop_count"], len(stop_plan) - 1)]
                    state["cao_stop_count"] = int(state.get("cao_stop_count", 0)) + 1
                    if stop_mode == "malformed":
                        set_loopback_port_state("1")
                        save_state()
                        print(
                            "Traceback (most recent call last): "
                            "FileNotFoundError: launcher_result.json",
                            file=sys.stderr,
                        )
                        raise SystemExit(2)
                    if stop_mode == "not-stopped":
                        print(
                            json.dumps(
                                {
                                    "stopped": False,
                                    "already_stopped": False,
                                    "verification_passed": False,
                                    "pid": 5151,
                                    "signal_sent": None,
                                }
                            )
                        )
                        set_loopback_port_state("1")
                        save_state()
                        raise SystemExit(2)
                    if stop_mode != "success":
                        raise SystemExit(f"unexpected stop mode: {stop_mode!r}")
                    set_loopback_port_state("0")
                    print(
                        json.dumps(
                            {
                                "stopped": True,
                                "already_stopped": False,
                                "verification_passed": True,
                                "pid": 5151,
                                "signal_sent": "SIGTERM",
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)

            if module == "houmao.agents.realm_controller":
                subcommand = args[4]
                if subcommand == "build-brain":
                    runtime_root = Path(arg_value("--runtime-root"))
                    recipe_path = Path(arg_value("--recipe"))
                    state["last_built_tool"] = (
                        "codex" if "codex" in recipe_path.parts else "claude"
                    )
                    manifest_path = runtime_root / "brains" / "brain-manifest.json"
                    home_path = runtime_root / "brains" / "home"
                    manifest_path.parent.mkdir(parents=True, exist_ok=True)
                    manifest_path.write_text("{}", encoding="utf-8")
                    home_path.mkdir(parents=True, exist_ok=True)
                    print(
                        json.dumps(
                            {
                                "home_id": "brain-home",
                                "home_path": str(home_path),
                                "manifest_path": str(manifest_path),
                                "launch_helper_path": str(home_path / "launch.py"),
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)

                if subcommand == "start-session":
                    runtime_root = Path(arg_value("--runtime-root"))
                    agent_identity = arg_value("--agent-identity")
                    session_manifest = (
                        runtime_root / "sessions" / "cao_rest" / "integration-session.json"
                    )
                    session_manifest.parent.mkdir(parents=True, exist_ok=True)
                    session_manifest.write_text(
                        json.dumps(
                            {
                                "cao": {
                                    "session_name": agent_identity,
                                    "terminal_id": "term-int",
                                }
                            }
                        ),
                        encoding="utf-8",
                    )
                    if agent_identity not in state["tmux_sessions"]:
                        state["tmux_sessions"].append(agent_identity)
                    save_state()
                    print(
                        json.dumps(
                            {
                                "session_manifest": str(session_manifest),
                                "agent_identity": agent_identity,
                                "tool": state.get("last_built_tool", "claude"),
                            }
                        )
                    )
                    raise SystemExit(0)

                if subcommand == "send-prompt":
                    state["turn_count"] = int(state.get("turn_count", 0)) + 1
                    prompt = arg_value("--prompt")
                    save_state()
                    print(json.dumps({"kind": "submitted", "message": "submitted"}))
                    print(
                        json.dumps(
                            {
                                "kind": "done",
                                "message": f"turn {state['turn_count']}: {prompt}",
                            }
                        )
                    )
                    raise SystemExit(0)

                if subcommand == "send-keys":
                    state["control_count"] = int(state.get("control_count", 0)) + 1
                    sequence = arg_value("--sequence")
                    save_state()
                    print(
                        json.dumps(
                            {
                                "status": "ok",
                                "action": "control_input",
                                "detail": f"control {state['control_count']}: {sequence}",
                            }
                        )
                    )
                    raise SystemExit(0)

                if subcommand == "stop-session":
                    agent_identity = arg_value("--agent-identity")
                    if stop_session_mode == "connection-refused":
                        save_state()
                        print(
                            json.dumps(
                                {
                                    "status": "error",
                                    "action": "terminate",
                                    "detail": (
                                        "delete terminal failed: [Errno 111] Connection refused; "
                                        "delete session failed: [Errno 111] Connection refused"
                                    ),
                                }
                            )
                        )
                        raise SystemExit(2)
                    state["tmux_sessions"] = [
                        session for session in state["tmux_sessions"] if session != agent_identity
                    ]
                    save_state()
                    print(
                        json.dumps(
                            {
                                "status": "ok",
                                "action": "terminate",
                                "detail": "Deleted CAO terminal and session",
                            }
                        )
                    )
                    raise SystemExit(0)

            raise SystemExit(f"unexpected module: {module!r}")
            """
        ),
    )


def _build_env(tmp_path: Path, repo_root: Path) -> dict[str, str]:
    fake_state_path = tmp_path / "fake-pixi-state.json"
    fake_command_log_path = tmp_path / "fake-pixi-commands.jsonl"
    loopback_state_path = tmp_path / "loopback-port-state.txt"
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)
    _write_fake_tools(fake_bin_dir)
    loopback_state_path.write_text("0", encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
    env["PYTHONPATH"] = f"{_source_repo_root() / 'src'}:{env.get('PYTHONPATH', '')}"
    env["FAKE_GIT_TOPLEVEL"] = str(repo_root)
    env["FAKE_PIXI_STATE"] = str(fake_state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(fake_command_log_path)
    env["FAKE_CAO_STATUS_MODE"] = "unhealthy"
    env["FAKE_CAO_STOP_PLAN"] = "success"
    env["FAKE_STOP_SESSION_MODE"] = "ok"
    env[TEST_LOOPBACK_PORT_LISTENING_ENV] = f"file:{loopback_state_path}"
    return env


def _command_log(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _run(
    command: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        input=input_text,
        env=env,
        cwd=cwd,
    )


def test_demo_wrapper_lifecycle_uses_per_run_defaults_from_arbitrary_cwd(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    _run([str(demo_pack_dir / "launch_alice.sh"), "-y"], env=env, cwd=outside_cwd)
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "-y", "--prompt", "first turn"],
        env=env,
        cwd=outside_cwd,
    )
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "-y", "--prompt", "second turn"],
        env=env,
        cwd=outside_cwd,
    )
    verify_result = _run(
        [str(demo_pack_dir / "run_demo.sh"), "verify"],
        env=env,
        cwd=outside_cwd,
    )
    stop_result = _run([str(demo_pack_dir / "stop_demo.sh"), "-y"], env=env, cwd=outside_cwd)

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    report = json.loads((workspace_root / "report.json").read_text(encoding="utf-8"))
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))

    assert (
        workspace_root.parent == repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo"
    )
    assert (workspace_root / "wktree" / ".git").exists()
    assert report["status"] == "ok"
    assert report["turn_count"] == 2
    assert state["active"] is False
    assert FIXED_CAO_BASE_URL in verify_result.stdout
    assert json.loads(stop_result.stdout)["state"]["active"] is False

    command_log = _command_log(Path(env["FAKE_PIXI_COMMAND_LOG"]))
    start_session_call = next(
        entry
        for entry in command_log
        if entry["module"] == "houmao.agents.realm_controller"
        and entry["args"][4] == "start-session"
    )
    args = start_session_call["args"]
    assert args[args.index("--cao-base-url") + 1] == FIXED_CAO_BASE_URL
    assert args[args.index("--workdir") + 1] == str(workspace_root / "wktree")
    assert args[args.index("--agent-def-dir") + 1] == str(
        repo_root / "tests" / "fixtures" / "agents"
    )

    send_prompt_calls = [
        entry
        for entry in command_log
        if entry["module"] == "houmao.agents.realm_controller" and entry["args"][4] == "send-prompt"
    ]
    assert len(send_prompt_calls) == 2
    assert all("--agent-def-dir" not in entry["args"] for entry in send_prompt_calls)

    stop_session_call = next(
        entry
        for entry in command_log
        if entry["module"] == "houmao.agents.realm_controller"
        and entry["args"][4] == "stop-session"
    )
    assert "--agent-def-dir" not in stop_session_call["args"]


def test_demo_explicit_codex_recipe_launches_and_verifies_variant(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)

    _run(
        [
            str(demo_pack_dir / "launch_alice.sh"),
            "-y",
            "--brain-recipe",
            "codex/gpu-kernel-coder-default",
        ],
        env=env,
        cwd=repo_root,
    )
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "-y", "--prompt", "first turn"],
        env=env,
        cwd=repo_root,
    )
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "-y", "--prompt", "second turn"],
        env=env,
        cwd=repo_root,
    )
    _run([str(demo_pack_dir / "run_demo.sh"), "verify"], env=env, cwd=repo_root)

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))
    report = json.loads((workspace_root / "report.json").read_text(encoding="utf-8"))

    assert state["agent_identity"] == "AGENTSYS-alice"
    assert state["tool"] == "codex"
    assert state["variant_id"] == "codex-gpu-kernel-coder-default"
    assert state["brain_recipe"] == "codex/gpu-kernel-coder-default"
    assert report["tool"] == "codex"
    assert report["variant_id"] == "codex-gpu-kernel-coder-default"


def test_demo_start_rejects_ambiguous_recipe_basename(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)

    result = _run(
        [
            str(demo_pack_dir / "run_demo.sh"),
            "start",
            "--brain-recipe",
            "gpu-kernel-coder-default",
        ],
        env=env,
        cwd=repo_root,
        check=False,
    )

    assert result.returncode == 2
    assert "Multiple brain recipes matched `gpu-kernel-coder-default`" in result.stderr


def test_demo_send_keys_wrapper_and_cli_record_controls_without_affecting_verify(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    _run([str(demo_pack_dir / "launch_alice.sh"), "-y"], env=env, cwd=outside_cwd)
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "-y", "--prompt", "first turn"],
        env=env,
        cwd=outside_cwd,
    )
    _run(
        [str(demo_pack_dir / "send_keys.sh"), "-y", "<[Escape]>"],
        env=env,
        cwd=outside_cwd,
    )
    _run(
        [
            str(demo_pack_dir / "run_demo.sh"),
            "-y",
            "send-keys",
            "/model<[Enter]>",
            "--as-raw-string",
        ],
        env=env,
        cwd=outside_cwd,
    )
    verify_result = _run(
        [str(demo_pack_dir / "run_demo.sh"), "verify"],
        env=env,
        cwd=outside_cwd,
        check=False,
    )
    assert verify_result.returncode == 2

    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "-y", "--prompt", "second turn"],
        env=env,
        cwd=outside_cwd,
    )
    verify_result = _run(
        [str(demo_pack_dir / "run_demo.sh"), "verify"],
        env=env,
        cwd=outside_cwd,
    )

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))
    report = json.loads((workspace_root / "report.json").read_text(encoding="utf-8"))
    control_one = json.loads(
        (workspace_root / "controls" / "control-001.json").read_text(encoding="utf-8")
    )
    control_two = json.loads(
        (workspace_root / "controls" / "control-002.json").read_text(encoding="utf-8")
    )

    assert state["turn_count"] == 2
    assert state["control_count"] == 2
    assert report["turn_count"] == 2
    assert control_one["key_stream"] == "<[Escape]>"
    assert control_one["as_raw_string"] is False
    assert control_one["result"]["action"] == "control_input"
    assert control_two["key_stream"] == "/model<[Enter]>"
    assert control_two["as_raw_string"] is True
    assert Path(control_one["stdout_path"]).name == "control-001.stdout.json"
    assert Path(control_two["stderr_path"]).name == "control-002.stderr.log"
    assert FIXED_CAO_BASE_URL in verify_result.stdout

    command_log = _command_log(Path(env["FAKE_PIXI_COMMAND_LOG"]))
    send_keys_calls = [
        entry
        for entry in command_log
        if entry["module"] == "houmao.agents.realm_controller" and entry["args"][4] == "send-keys"
    ]
    assert len(send_keys_calls) == 2

    first_args = send_keys_calls[0]["args"]
    second_args = send_keys_calls[1]["args"]
    assert "--agent-def-dir" not in first_args
    assert "--agent-def-dir" not in second_args
    assert first_args[first_args.index("--sequence") + 1] == "<[Escape]>"
    assert "--escape-special-keys" not in first_args
    assert second_args[second_args.index("--sequence") + 1] == "/model<[Enter]>"
    assert "--escape-special-keys" in second_args


def test_demo_wrapper_verified_cao_replacement_cleans_prior_artifacts_without_prompt(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)

    _run([str(demo_pack_dir / "launch_alice.sh"), "-y"], env=env, cwd=repo_root)
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "--prompt", "first turn"],
        env=env,
        cwd=repo_root,
    )
    _run(
        [str(demo_pack_dir / "send_prompt.sh"), "--prompt", "second turn"],
        env=env,
        cwd=repo_root,
    )
    _run(
        [str(demo_pack_dir / "send_keys.sh"), "<[Escape]>"],
        env=env,
        cwd=repo_root,
    )
    _run([str(demo_pack_dir / "run_demo.sh"), "verify"], env=env, cwd=repo_root)

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    first_workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    assert (first_workspace_root / "report.json").exists()
    assert list((first_workspace_root / "turns").glob("turn-*.json"))
    assert list((first_workspace_root / "controls").glob("*"))

    env["FAKE_CAO_STATUS_MODE"] = "verified"
    _run([str(demo_pack_dir / "launch_alice.sh")], env=env, cwd=repo_root)

    second_workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    assert second_workspace_root != first_workspace_root
    assert not (first_workspace_root / "report.json").exists()
    assert list((first_workspace_root / "turns").glob("turn-*.json")) == []
    assert list((first_workspace_root / "controls").glob("*")) == []

    command_log = _command_log(Path(env["FAKE_PIXI_COMMAND_LOG"]))
    assert any(
        entry["module"] == "houmao.cao.tools.cao_server_launcher" and entry["args"][4] == "stop"
        for entry in command_log
    )


def test_demo_wrapper_verified_cao_replacement_retries_older_known_config_after_invalid_stop_output(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)

    _run([str(demo_pack_dir / "launch_alice.sh"), "-y"], env=env, cwd=repo_root)

    env["FAKE_CAO_STATUS_MODE"] = "verified"
    env["FAKE_CAO_STOP_PLAN"] = "malformed,success"
    _run([str(demo_pack_dir / "launch_alice.sh"), "-y"], env=env, cwd=repo_root)

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))
    command_log = _command_log(Path(env["FAKE_PIXI_COMMAND_LOG"]))
    stop_calls = [
        entry
        for entry in command_log
        if entry["module"] == "houmao.cao.tools.cao_server_launcher" and entry["args"][4] == "stop"
    ]

    assert state["active"] is True
    assert len(stop_calls) == 2
    assert (
        stop_calls[0]["args"][stop_calls[0]["args"].index("--config") + 1]
        != stop_calls[1]["args"][stop_calls[1]["args"].index("--config") + 1]
    )


def test_demo_stop_tolerates_dead_remote_session_and_cleans_tmux(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)

    _run([str(demo_pack_dir / "launch_alice.sh"), "-y"], env=env, cwd=repo_root)
    env["FAKE_STOP_SESSION_MODE"] = "connection-refused"

    stop_result = _run(
        [str(demo_pack_dir / "run_demo.sh"), "stop"],
        env=env,
        cwd=repo_root,
    )

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    workspace_root = Path(current_run_root_path.read_text(encoding="utf-8").strip())
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))
    stop_payload = json.loads(stop_result.stdout)
    fake_state = json.loads(Path(env["FAKE_PIXI_STATE"]).read_text(encoding="utf-8"))

    assert state["active"] is False
    assert stop_payload["state"]["active"] is False
    assert stop_payload["stop_result"]["stale_session_tolerated"] is True
    assert fake_state["tmux_sessions"] == []


def test_demo_wrapper_fails_when_existing_service_is_not_verified_cao_server(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_agent_defs(repo_root)
    demo_pack_dir = _copy_demo_pack(repo_root)
    env = _build_env(tmp_path, repo_root)
    env["FAKE_CAO_STATUS_MODE"] = "wrong-service"

    result = _run(
        [str(demo_pack_dir / "launch_alice.sh")],
        env=env,
        cwd=repo_root,
        check=False,
    )

    current_run_root_path = (
        repo_root / "tmp" / "demo" / "cao-interactive-full-pipeline-demo" / "current_run_root.txt"
    )
    assert result.returncode == 2
    assert "did not verify as `cao-server`" in result.stderr
    assert not current_run_root_path.exists()
