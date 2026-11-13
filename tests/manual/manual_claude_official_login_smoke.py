"""Exercise explicitly imported Claude vendor login through a private managed run.

Discover and import native state first with scripts/agents/test-fixtures/fixture.py.
This smoke never imports ambient login or copies a personal home automatically.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts/agents/test-fixtures"))

from fixturelib.auth import bundle_path, external_root  # noqa: E402
from fixturelib.config import FixtureError, ResolvedConfig  # noqa: E402
from fixturelib.launch import launch_run, stop_run  # noqa: E402
from fixturelib.prepare import prepare_run  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    """Launch a fresh native-login session and always stop its captured identity."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-bundle", required=True)
    parser.add_argument("--auth-root", type=Path)
    parser.add_argument("--run-root", type=Path)
    args = parser.parse_args(argv)
    run_dir: Path | None = None
    try:
        config = ResolvedConfig(
            client="claude",
            mode="headless",
            surface="manager",
            auth_method="native-login",
            native_bundle=bundle_path(
                external_root("auth", override=args.auth_root), "claude", args.auth_bundle
            ),
        )
        run = prepare_run(config, run_root=args.run_root)
        run_dir = Path(run["run_dir"])
        result = launch_run(run_dir, prompt="Reply exactly NATIVE_LOGIN_OK. Do not use tools.")
        print(json.dumps(result, indent=2))
        return 0
    except (FixtureError, OSError):
        print(
            json.dumps(
                {
                    "error": "Native-login smoke failed; inspect private run evidence",
                    "run_dir": str(run_dir) if run_dir else None,
                }
            ),
            file=sys.stderr,
        )
        return 2
    finally:
        if run_dir is not None:
            stop_run(run_dir)


if __name__ == "__main__":
    raise SystemExit(main())
