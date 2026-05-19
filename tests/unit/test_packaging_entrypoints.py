from __future__ import annotations

import tomllib
from pathlib import Path


def test_packaged_console_scripts_expose_only_retained_entrypoints() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

    scripts = pyproject["project"]["scripts"]

    assert scripts == {
        "houmao-mgr": "houmao.srv_ctrl.cli:main",
        "houmao-passive-server": "houmao.passive_server.cli:main",
    }
    assert "houmao-server" not in scripts
    assert "houmao-cli" not in scripts
