from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_managed_memory_docs_describe_free_form_memo_and_resolve() -> None:
    """Guard the managed-memory docs against stale generated-index wording."""

    guide = (REPO_ROOT / "docs/getting-started/managed-memory-dirs.md").read_text(
        encoding="utf-8"
    )
    system_files = (
        REPO_ROOT / "docs/reference/system-files/agents-and-runtime.md"
    ).read_text(encoding="utf-8")

    assert "free-form Markdown" in guide
    assert "memory resolve --path <page>" in guide
    assert "memo-cue" in guide
    assert "houmao-memory-mgr" in guide
    assert "agent-memory" in guide
    assert "Page writes and deletes do not mutate the memo" in system_files
    for text in (guide, system_files):
        assert "memo page index" not in text
        assert "generated page index" not in text
        assert "agents memory reindex" not in text


def test_managed_header_and_system_skill_docs_describe_memory_cue_and_skill() -> None:
    """Guard docs that surface managed memory through prompt and system-skill layers."""

    header = (REPO_ROOT / "docs/reference/run-phase/managed-prompt-header.md").read_text(
        encoding="utf-8"
    )
    system_skills = (REPO_ROOT / "docs/getting-started/system-skills-overview.md").read_text(
        encoding="utf-8"
    )
    cli_reference = (REPO_ROOT / "docs/reference/cli/system-skills.md").read_text(
        encoding="utf-8"
    )

    assert "`memo-cue`" in header
    assert "<memo_cue>" in header
    assert "resolved absolute `houmao-memo.md` path" in header
    assert "`houmao-memory-mgr`" in system_skills
    assert "`agent-memory`" in system_skills
    assert "`houmao-memory-mgr`" in cli_reference
    assert "`agent-memory`" in cli_reference
