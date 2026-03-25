"""Manual entrypoint for the houmao-server managed-agent API live suite."""

from __future__ import annotations

from pathlib import Path
import sys


def _ensure_manual_package_path() -> None:
    """Ensure the sibling manual package directory is importable."""

    manual_root = Path(__file__).resolve().parent
    if str(manual_root) not in sys.path:
        sys.path.insert(0, str(manual_root))


_ensure_manual_package_path()

from houmao_server_agent_api_live_suite.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
