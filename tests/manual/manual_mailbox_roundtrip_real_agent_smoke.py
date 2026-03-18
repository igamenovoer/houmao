"""Thin wrapper around the pack-local real-agent autotest harness."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    """Return the tracked repository root."""

    return Path(__file__).resolve().parents[2]


def _pack_run_autotest(repo_root: Path) -> Path:
    """Return the pack-local real-agent autotest harness path."""

    return (
        repo_root
        / "scripts"
        / "demo"
        / "mailbox-roundtrip-tutorial-pack"
        / "autotest"
        / "run_autotest.sh"
    )


def _build_parser() -> argparse.ArgumentParser:
    """Build the manual smoke CLI parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=[
            "real-agent-roundtrip",
            "real-agent-preflight",
            "real-agent-mailbox-persistence",
        ],
        default="real-agent-roundtrip",
    )
    parser.add_argument("--demo-output-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the opt-in real-agent smoke sequence."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    argv = [str(_pack_run_autotest(repo_root)), "--case", args.case]
    if args.demo_output_dir is not None:
        argv.extend(["--demo-output-dir", str(args.demo_output_dir.resolve())])
    result = subprocess.run(argv, cwd=repo_root, check=False)
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
