"""Run the minimal role through explicit fixture preparation and scoped lifecycle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "scripts/agents/test-fixtures"))

from fixture import add_case_arguments, selected_configuration  # noqa: E402
from fixturelib.auth import write_json  # noqa: E402
from fixturelib.config import FixtureError  # noqa: E402
from fixturelib.launch import check_run, launch_run, stop_run  # noqa: E402
from fixturelib.prepare import prepare_run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Prepare a unique private project and preserve the shared minimal role."""

    parser = argparse.ArgumentParser(description=__doc__)
    add_case_arguments(parser)
    parser.add_argument("--provider", choices=("claude_code", "codex"), required=True)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output-dir", type=Path, help="External parent for unique private runs")
    args = parser.parse_args(argv)
    args.client = "claude" if args.provider == "claude_code" else "codex"
    args.surface = "manager"
    args.mode = "headless" if args.headless else "tui"
    root: Path | None = None
    try:
        config = selected_configuration(args)
        demo = REPO_ROOT / "scripts/demo/minimal-agent-launch"
        run = prepare_run(
            config,
            run_root=args.output_dir,
            role="minimal-launch",
            prompt_file=demo / "inputs/agents/roles/minimal-launch/system-prompt.md",
        )
        root = Path(run["run_dir"])
        write_json(
            root / "logs/prepare.json", {"status": run["status"], "configuration": config.summary()}
        )
        launched = launch_run(
            root, prompt=(demo / "inputs/prompt.txt").read_text() if args.headless else None
        )
        write_json(root / "logs/launch.json", launched)
        state = check_run(root, live=True)
        write_json(root / "logs/state.json", state)
        summary = {
            "provider": args.provider,
            "tool": args.client,
            "transport": args.mode,
            "role": "minimal-launch",
            "run_dir": str(root),
            "identity": launched.get("identity", {}),
        }
        if args.headless:
            write_json(root / "logs/stop.json", stop_run(root))
        write_json(root / "summary.json", summary)
        print(json.dumps(summary, indent=2))
        return 0
    except (FixtureError, OSError):
        if root is not None:
            stop_run(root)
        print(
            json.dumps(
                {
                    "error": "Minimal launch failed; inspect the private run evidence",
                    "run_dir": str(root) if root else None,
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
