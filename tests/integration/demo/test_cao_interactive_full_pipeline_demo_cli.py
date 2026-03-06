"""Integration coverage for the interactive CAO full-pipeline demo CLI."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import textwrap
from pathlib import Path

from gig_agents.demo.cao_interactive_full_pipeline_demo import FIXED_CAO_BASE_URL


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_demo_cli_lifecycle_runs_against_fake_pixi(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    agent_def_dir = repo_root / "tests" / "fixtures" / "agents"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = tmp_path / "workspace"
    fake_state_path = tmp_path / "fake-pixi-state.json"
    fake_command_log_path = tmp_path / "fake-pixi-commands.jsonl"
    fake_bin_dir = tmp_path / "bin"
    fake_bin_dir.mkdir(parents=True, exist_ok=True)

    _write_executable(
        fake_bin_dir / "tmux",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        fake_bin_dir / "cao-server",
        "#!/usr/bin/env bash\nexit 0\n",
    )
    _write_executable(
        fake_bin_dir / "pixi",
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            from __future__ import annotations

            import json
            import os
            import sys
            from pathlib import Path

            state_path = Path(os.environ["FAKE_PIXI_STATE"])
            log_path = Path(os.environ["FAKE_PIXI_COMMAND_LOG"])
            if state_path.exists():
                state = json.loads(state_path.read_text(encoding="utf-8"))
            else:
                state = {"turn_count": 0}

            args = sys.argv[1:]
            if args[:3] != ["run", "python", "-m"]:
                raise SystemExit(f"unexpected pixi args: {args!r}")

            module = args[3]
            subcommand = args[4]
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        {
                            "module": module,
                            "subcommand": subcommand,
                            "args": args,
                        }
                    )
                    + "\\n"
                )

            def arg_value(flag: str) -> str:
                index = args.index(flag)
                return args[index + 1]

            def save_state() -> None:
                state_path.write_text(json.dumps(state), encoding="utf-8")

            if module == "gig_agents.cao.tools.cao_server_launcher":
                if subcommand == "status":
                    print("{}")
                    save_state()
                    raise SystemExit(1)
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
                    print(json.dumps({"stopped": True}))
                    save_state()
                    raise SystemExit(0)

            if module == "gig_agents.agents.brain_launch_runtime":
                if subcommand == "build-brain":
                    runtime_root = Path(arg_value("--runtime-root"))
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
                    state["agent_identity"] = agent_identity
                    save_state()
                    print(
                        json.dumps(
                            {
                                "session_manifest": str(session_manifest),
                                "agent_identity": agent_identity,
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

                if subcommand == "stop-session":
                    print(
                        json.dumps(
                            {
                                "status": "ok",
                                "action": "terminate",
                                "detail": "Deleted CAO terminal and session",
                            }
                        )
                    )
                    save_state()
                    raise SystemExit(0)

            raise SystemExit(f"unexpected module/subcommand: {module} {subcommand}")
            """
        ),
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin_dir}:{env.get('PATH', '')}"
    env["FAKE_PIXI_STATE"] = str(fake_state_path)
    env["FAKE_PIXI_COMMAND_LOG"] = str(fake_command_log_path)
    env["CAO_BASE_URL"] = "http://example.invalid:9999"

    command_prefix = [
        sys.executable,
        "-m",
        "gig_agents.demo.cao_interactive_full_pipeline_demo",
        "--repo-root",
        str(repo_root),
        "--workspace-root",
        str(workspace_root),
        "--agent-def-dir",
        str(agent_def_dir),
        "--launcher-home-dir",
        str(workspace_root),
        "--workdir",
        str(repo_root),
    ]

    subprocess.run(
        [*command_prefix, "start", "--agent-name", "demo"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    subprocess.run(
        [*command_prefix, "send-turn", "--prompt", "first turn"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    subprocess.run(
        [*command_prefix, "send-turn", "--prompt", "second turn"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    verify_result = subprocess.run(
        [*command_prefix, "verify"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    stop_result = subprocess.run(
        [*command_prefix, "stop"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    report = json.loads((workspace_root / "report.json").read_text(encoding="utf-8"))
    state = json.loads((workspace_root / "state.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    assert report["turn_count"] == 2
    assert report["unique_agent_identity_count"] == 1
    assert state["active"] is False
    assert json.loads(verify_result.stdout)["cao_base_url"] == FIXED_CAO_BASE_URL
    assert json.loads(stop_result.stdout)["state"]["active"] is False

    command_log = [
        json.loads(line)
        for line in fake_command_log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    start_session_call = next(
        entry
        for entry in command_log
        if entry["module"] == "gig_agents.agents.brain_launch_runtime"
        and entry["subcommand"] == "start-session"
    )
    args = start_session_call["args"]
    assert args[args.index("--cao-base-url") + 1] == FIXED_CAO_BASE_URL
