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
    assert "Page writes and deletes do not mutate the memo" in system_files
    for text in (guide, system_files):
        assert "memo page index" not in text
        assert "generated page index" not in text
        assert "agents memory reindex" not in text
