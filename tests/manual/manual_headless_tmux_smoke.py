from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def _run_json_command(*, args: list[str], cwd: Path) -> dict[str, object]:
    process = subprocess.run(
        args,
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit={process.returncode}): {' '.join(args)}\n"
            f"stdout:\n{process.stdout}\n"
            f"stderr:\n{process.stderr}"
        )
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Command did not emit JSON: {' '.join(args)}\nstdout:\n{process.stdout}"
        ) from exc


def _run_backend_smoke(
    *,
    agent_def_dir: Path,
    backend: str,
    manifest_path: Path,
    role_name: str,
) -> None:
    runtime_cmd = [
        "pixi",
        "run",
        "python",
        "-m",
        "houmao.agents.realm_controller",
    ]

    start_payload = _run_json_command(
        args=[
            *runtime_cmd,
            "start-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--brain-manifest",
            str(manifest_path),
            "--role",
            role_name,
            "--backend",
            backend,
        ],
        cwd=agent_def_dir,
    )
    session_manifest = str(start_payload["session_manifest"])

    for prompt in ("smoke turn 1", "smoke turn 2"):
        process = subprocess.run(
            [
                *runtime_cmd,
                "send-prompt",
                "--agent-def-dir",
                str(agent_def_dir),
                "--agent-identity",
                session_manifest,
                "--prompt",
                prompt,
            ],
            cwd=str(agent_def_dir),
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            raise RuntimeError(
                f"send-prompt failed for backend={backend}, prompt={prompt!r}\n"
                f"stdout:\n{process.stdout}\n"
                f"stderr:\n{process.stderr}"
            )

    _run_json_command(
        args=[
            *runtime_cmd,
            "stop-session",
            "--agent-def-dir",
            str(agent_def_dir),
            "--agent-identity",
            session_manifest,
            "--force-cleanup",
        ],
        cwd=agent_def_dir,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manual tmux-backed headless smoke test (Codex/Claude/Gemini)."
    )
    parser.add_argument(
        "--agent-def-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "fixtures" / "agents",
        help="Agent definition directory (defaults to tests/fixtures/agents).",
    )
    parser.add_argument(
        "--role",
        default="gpu-kernel-coder",
        help="Role name passed to start-session.",
    )
    parser.add_argument(
        "--codex-manifest",
        type=Path,
        default=None,
        help="Brain manifest path for Codex headless smoke.",
    )
    parser.add_argument(
        "--claude-manifest",
        type=Path,
        default=None,
        help="Brain manifest path for Claude headless smoke.",
    )
    parser.add_argument(
        "--gemini-manifest",
        type=Path,
        default=None,
        help="Brain manifest path for Gemini headless smoke.",
    )
    args = parser.parse_args()

    if shutil.which("tmux") is None:
        raise RuntimeError("tmux not found on PATH")

    agent_def_dir = args.agent_def_dir.resolve()
    executed: list[str] = []

    for backend, manifest in [
        ("codex_headless", args.codex_manifest),
        ("claude_headless", args.claude_manifest),
        ("gemini_headless", args.gemini_manifest),
    ]:
        if manifest is None:
            continue
        _run_backend_smoke(
            agent_def_dir=agent_def_dir,
            backend=backend,
            manifest_path=manifest.resolve(),
            role_name=str(args.role),
        )
        executed.append(backend)

    if not executed:
        raise RuntimeError(
            "No backends executed. Provide at least one of --codex-manifest, "
            "--claude-manifest, --gemini-manifest."
        )

    print("manual-headless-tmux-smoke=PASS")
    print(f"executed_backends={','.join(executed)}")


if __name__ == "__main__":
    main()
