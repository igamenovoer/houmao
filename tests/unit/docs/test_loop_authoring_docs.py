from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_loop_authoring_docs_cover_current_loop_authoring() -> None:
    """Guard loop-authoring docs for the current lite and pro workflows."""

    guide = (REPO_ROOT / "docs/getting-started/loop-authoring.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    system_skills = (REPO_ROOT / "docs/getting-started/system-skills-overview.md").read_text(
        encoding="utf-8"
    )
    cli_reference = (REPO_ROOT / "docs/reference/cli/system-skills.md").read_text(encoding="utf-8")

    assert "Houmao has two protected loop-authoring routes" in guide
    assert "$houmao-admin-entrypoint agent-loop-lite" in guide
    assert "$houmao-agent-entrypoint" in guide
    assert "`houmao-agent-loop-lite`" in guide
    assert "Markdown/direct-SQL loops" in guide
    assert "Lite Default Shape" in guide
    assert "Loop-Template-Type" in guide
    assert "runs/<run-id>/state.sqlite3" in guide
    assert "does not generate `execplan/harness/` or `execplan/docs/`" in guide
    assert "`houmao-agent-loop-pro`" in guide
    assert "Do not choose among retired loop packages for new work" in guide
    assert "Choose `tree-loop`" in guide
    assert "Choose `generic-loop`" in guide
    assert "`execplan-specs-process`: process-first pseudo-code" in guide
    assert "`execplan-harness`: loop-local harness scripts" in guide
    assert "`prepare-agents` and `prepare-workspace` are separate stages" in guide
    assert "schema-typed mail families" in guide
    assert "defaulting to SQLite" in guide
    assert "generated skills in one flat skills directory" in guide
    assert "Generated TOML files should include comments above each section" in guide
    assert "`houmao-mgr internals graph high` remains available" in guide
    assert "`agent-loop-lite` route" in readme
    assert "protected `agent-loop-pro` route" in readme
    assert "`tree-loop` versus `generic-loop` topology choice" in readme
    assert "`agent-loop-lite`" in system_skills
    assert "`agent-loop-pro`" in system_skills
    assert "`tree-loop` and `generic-loop` topology modes" in system_skills
    assert "typed Markdown templates" in system_skills
    assert "`houmao-agent-loop-lite`" in cli_reference
    assert "`houmao-agent-loop-pro`" in cli_reference
    assert "Markdown/direct-SQL generated loop authoring" in cli_reference
    assert "email_initialization" not in guide
