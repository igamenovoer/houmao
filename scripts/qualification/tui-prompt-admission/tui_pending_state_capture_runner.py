"""CLI entrypoint for the TUI pending-state capture runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tui_pending_state_capture.models import ProviderName
from tui_pending_state_capture.runner import CaptureRunConfig, TuiPendingStateCaptureRunner


def _repo_root() -> Path:
    """Return the repository root from this script's location."""

    return Path(__file__).resolve().parents[3]


def _lifecycles_dir() -> Path:
    return Path(__file__).resolve().parent / "lifecycles"


def list_lifecycles() -> list[Path]:
    """Return available provider lifecycle manifests."""

    directory = _lifecycles_dir()
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.json") if path.is_file())


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Capture labeled tmux recordings of the prompt-queue lifecycle."
    )
    parser.add_argument(
        "--provider",
        choices=["claude", "codex", "kimi"],
        required=True,
        help="Provider to capture.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        required=True,
        help="Fresh run root under the repository tmp/ directory.",
    )
    parser.add_argument(
        "--lifecycle",
        type=Path,
        default=None,
        help="Override the default lifecycle manifest for the provider.",
    )
    parser.add_argument(
        "--attempt",
        type=int,
        default=None,
        help="Explicit attempt number (auto-incremented if omitted).",
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Skip rendering the labeled review video.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved lifecycle steps and exit without launching a provider.",
    )
    parser.add_argument(
        "--list-lifecycles",
        action="store_true",
        help="List available lifecycle manifests and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list_lifecycles:
        for path in list_lifecycles():
            print(path.name)
        return 0

    provider: ProviderName = args.provider
    config = CaptureRunConfig(
        provider=provider,
        run_root=args.run_root,
        lifecycle_path=args.lifecycle,
        attempt_id=args.attempt,
        skip_video=args.skip_video,
    )
    runner = TuiPendingStateCaptureRunner(repo_root=_repo_root(), config=config)

    if args.dry_run:
        steps = runner.dry_run_steps()
        print(json.dumps({"provider": provider, "steps": steps}, indent=2))
        return 0

    result = runner.run()
    status = "success" if result.success else "tainted"
    print(
        json.dumps(
            {
                "status": status,
                "attempt_dir": str(result.attempt_dir),
                "recording_root": str(result.recording_root),
                "labels_path": str(result.labels_path),
                "frozen_evidence_path": str(result.frozen_evidence_path),
                "video_path": str(result.video_path) if result.video_path else None,
                "taint_reasons": list(result.taint_reasons),
                "transition_times": result.transition_times,
            },
            indent=2,
        )
    )
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
