"""Guard maintained fixture consumers against account defaults and retired storage."""

from __future__ import annotations

import ast
from pathlib import Path
import subprocess


REPO = Path(__file__).resolve().parents[3]


def test_retired_local_credentials_remain_ignored() -> None:
    """Protect old operator state without reading or changing any credential file."""

    path = "tests/fixtures/auth-bundles/claude/operator-synthetic/files/.credentials.json"
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", path],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == path


def test_maintained_launch_inputs_have_no_account_specific_paths() -> None:
    """Seed configs and current guides cannot reintroduce personal fixture defaults."""

    roots = [
        "AGENTS.md",
        "docs",
        "scripts/agents",
        "scripts/demo",
        "scripts/explore",
        "src/houmao/project/assets/starter_agents",
    ]
    result = subprocess.run(
        ["git", "ls-files", "--", *roots], cwd=REPO, text=True, capture_output=True, check=True
    )
    for relative in result.stdout.splitlines():
        path = REPO / relative
        if (
            "/legacy/" in relative
            or not path.is_file()
            or path.suffix not in {".md", ".py", ".sh", ".json", ".toml", ".yaml"}
        ):
            continue
        text = path.read_text()
        assert "tests/fixtures/auth-bundles/" not in text, relative
        assert "yunwu-openai" not in text, relative
        assert "personal-a-default" not in text, relative


def test_packaged_demo_does_not_import_fixture_utility_or_test_code() -> None:
    """Prepared inputs cross a data boundary rather than a production import dependency."""

    root = REPO / "src/houmao/demo/shared_tui_tracking_demo_pack"
    for path in root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            assert not any(
                name.split(".")[0] in {"tests", "scripts", "fixturelib", "fixture"}
                for name in names
            ), path


def test_exploration_launchers_use_the_shared_prepared_run_interface() -> None:
    """Retained shell entrypoints expose current launch/prompt commands safely."""

    folder = REPO / "scripts/explore/interactive-pipeline-test"
    for name in ("interactive_pipeline_cao_claude.sh", "send_prompt.sh"):
        result = subprocess.run(
            ["bash", str(folder / name), "--help"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "--run-dir" in result.stdout
