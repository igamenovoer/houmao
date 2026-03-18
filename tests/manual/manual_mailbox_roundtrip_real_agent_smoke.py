"""Opt-in real-agent smoke entrypoint for the mailbox roundtrip tutorial pack."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


REQUIRED_TOOLS = ("pixi", "tmux", "claude", "codex")


def _repo_root() -> Path:
    """Return the tracked repository root."""

    return Path(__file__).resolve().parents[2]


def _default_demo_output_dir(repo_root: Path) -> Path:
    """Return one timestamped default demo-output dir for manual smoke."""

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return repo_root / "tmp" / "manual" / "mailbox-roundtrip-real-agent-smoke" / stamp


def _pack_run_demo(repo_root: Path) -> Path:
    """Return the tracked pack wrapper path."""

    return repo_root / "scripts" / "demo" / "mailbox-roundtrip-tutorial-pack" / "run_demo.sh"


def _credential_prerequisites(repo_root: Path) -> list[str]:
    """Return missing tracked credential prerequisites for the default smoke path."""

    checks = [
        repo_root
        / "tests"
        / "fixtures"
        / "agents"
        / "brains"
        / "api-creds"
        / "claude"
        / "personal-a-default"
        / "env"
        / "vars.env",
        repo_root
        / "tests"
        / "fixtures"
        / "agents"
        / "brains"
        / "api-creds"
        / "claude"
        / "personal-a-default"
        / "files"
        / "claude_state.template.json",
        repo_root
        / "tests"
        / "fixtures"
        / "agents"
        / "brains"
        / "api-creds"
        / "codex"
        / "personal-a-default"
        / "env"
        / "vars.env",
    ]
    missing: list[str] = []
    for path in checks:
        if not path.exists():
            missing.append(str(path))
    return missing


def _validate_prerequisites(repo_root: Path) -> None:
    """Raise a clear error when manual smoke prerequisites are missing."""

    missing_tools = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
    missing_paths = _credential_prerequisites(repo_root)
    if not missing_tools and not missing_paths:
        return

    lines = ["manual real-agent smoke prerequisites are missing:"]
    if missing_tools:
        lines.append("- tools: " + ", ".join(missing_tools))
    for path in missing_paths:
        lines.append(f"- credential path: {path}")
    raise SystemExit("\n".join(lines))


def _run_step(*, repo_root: Path, demo_output_dir: Path, command: str) -> None:
    """Run one pack command and fail fast on errors."""

    argv = [
        str(_pack_run_demo(repo_root)),
        command,
        "--demo-output-dir",
        str(demo_output_dir),
    ]
    result = subprocess.run(argv, cwd=repo_root, check=False)
    if result.returncode == 0:
        return
    raise RuntimeError(f"`{' '.join(argv)}` failed with exit code {result.returncode}")


def _build_parser() -> argparse.ArgumentParser:
    """Build the manual smoke CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-output-dir", type=Path)
    parser.add_argument(
        "--pause-before-roundtrip",
        action="store_true",
        help="Wait for Enter after printing inspect commands so you can attach in another terminal.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the opt-in real-agent smoke sequence."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    _validate_prerequisites(repo_root)
    demo_output_dir = (
        args.demo_output_dir.resolve()
        if args.demo_output_dir is not None
        else _default_demo_output_dir(repo_root)
    )

    print(f"demo_output_dir: {demo_output_dir}")
    print("starting real-agent smoke with tracked mailbox-demo defaults")

    try:
        _run_step(repo_root=repo_root, demo_output_dir=demo_output_dir, command="start")
        print("inspect commands:")
        print(
            "  "
            + str(_pack_run_demo(repo_root))
            + f" inspect --demo-output-dir {demo_output_dir} --agent sender"
        )
        print(
            "  "
            + str(_pack_run_demo(repo_root))
            + f" inspect --demo-output-dir {demo_output_dir} --agent receiver --json --with-output-text 400"
        )
        if args.pause_before_roundtrip:
            input("Press Enter to continue into roundtrip... ")
        _run_step(repo_root=repo_root, demo_output_dir=demo_output_dir, command="roundtrip")
        _run_step(repo_root=repo_root, demo_output_dir=demo_output_dir, command="verify")
    except Exception as exc:
        try:
            _run_step(repo_root=repo_root, demo_output_dir=demo_output_dir, command="stop")
        except Exception:
            pass
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _run_step(repo_root=repo_root, demo_output_dir=demo_output_dir, command="stop")
    print("manual real-agent smoke completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
