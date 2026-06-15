"""Tests for packaged system-skill Kimi guidance."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEM_SKILLS_ROOT = REPO_ROOT / "src/houmao/agents/assets/system_skills"
AGENT_DEFINITION_ROOT = SYSTEM_SKILLS_ROOT / "houmao-agent-definition"
CREDENTIAL_MGR_ROOT = SYSTEM_SKILLS_ROOT / "houmao-credential-mgr"
TOURING_ROOT = SYSTEM_SKILLS_ROOT / "houmao-touring"


def _read(path: Path) -> str:
    """Read one UTF-8 text file."""

    return path.read_text(encoding="utf-8")


def _markdown_files(root: Path) -> list[Path]:
    """Return markdown files under one root."""

    return sorted(path for path in root.rglob("*.md") if path.is_file())


def _relative_markdown_link_targets(path: Path) -> list[str]:
    """Return relative markdown link targets from one markdown file."""

    text = _read(path)
    targets: list[str] = []
    for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        target = match.group(1).strip()
        if (
            not target
            or target.startswith("#")
            or target.startswith(("http://", "https://", "mailto:"))
        ):
            continue
        target = target.split("#", maxsplit=1)[0].strip()
        if target:
            targets.append(target)
    return targets


def test_credential_manager_documents_kimi_crud_without_login_helper() -> None:
    """Kimi credential guidance covers CRUD paths while excluding login helpers."""

    skill_text = _read(CREDENTIAL_MGR_ROOT / "SKILL.md")
    add_text = _read(CREDENTIAL_MGR_ROOT / "actions/add.md")
    set_text = _read(CREDENTIAL_MGR_ROOT / "actions/set.md")
    login_text = _read(CREDENTIAL_MGR_ROOT / "actions/login.md")
    kimi_reference = _read(CREDENTIAL_MGR_ROOT / "references/kimi-credential-kinds.md")

    assert "supported CRUD tools: `claude`, `codex`, `kimi`, `gemini`" in skill_text
    assert "supported login-helper tools: `claude`, `codex`, `gemini`" in skill_text
    assert "Do not present Kimi as having a maintained credential login helper" in skill_text
    assert "Kimi: `references/kimi-credential-kinds.md`" in add_text
    assert "`tool`: one of `claude`, `codex`, `kimi`, or `gemini`" in add_text
    assert "`tool`: one of `claude`, `codex`, `kimi`, or `gemini`" in set_text
    assert "Kimi credential CRUD is supported" in login_text
    assert "Do not run or invent a Kimi login helper" in login_text
    assert "--code-home" in kimi_reference
    assert "--config-toml" in kimi_reference
    assert "--credential-json" in kimi_reference


def test_agent_definition_kimi_guidance_and_relative_links_resolve() -> None:
    """Agent-definition guidance uses Kimi examples and keeps local links valid."""

    skill_text = _read(AGENT_DEFINITION_ROOT / "SKILL.md")
    specialists_text = _read(AGENT_DEFINITION_ROOT / "subskills/easy/specialists.md")
    profiles_text = _read(AGENT_DEFINITION_ROOT / "subskills/easy/profiles.md")
    launch_text = _read(AGENT_DEFINITION_ROOT / "subskills/easy/launch-instance.md")
    fast_forward_text = _read(AGENT_DEFINITION_ROOT / "subskills/easy/create-agent-fast-forward.md")

    stale_kimi_example = '"name":"general-kimi","tool":"claude"'
    assert stale_kimi_example not in skill_text
    assert stale_kimi_example not in specialists_text
    assert '"name":"general-kimi","tool":"kimi"' in skill_text
    assert '"name":"general-kimi","tool":"kimi"' in specialists_text
    assert "`--tool claude|codex|kimi|gemini`" in specialists_text
    assert "Kimi supports TUI/local-interactive launch" in launch_text
    assert "unattended prompt mode is the supported managed no-question control" in launch_text
    assert "Do not add raw Kimi `--auto` or `--yolo` launch flags" in launch_text
    assert "Kimi-backed profiles are TUI/local-interactive preferred" in profiles_text
    assert "use `--prompt-mode unattended` as the managed no-question control" in profiles_text
    assert "Kimi is TUI/local-interactive capable" in fast_forward_text
    assert "should not be replaced with raw `--auto` or `--yolo` launch flags" in (
        fast_forward_text
    )

    missing_links: list[str] = []
    for markdown_path in _markdown_files(AGENT_DEFINITION_ROOT):
        for target in _relative_markdown_link_targets(markdown_path):
            if not (markdown_path.parent / target).resolve().exists():
                missing_links.append(f"{markdown_path.relative_to(REPO_ROOT)} -> {target}")

    assert missing_links == []


def test_packaged_guidance_includes_kimi_touring_and_avoids_stale_headless_claims() -> None:
    """Adjacent packaged guidance includes Kimi and avoids old Kimi headless-only text."""

    quickstart_text = _read(TOURING_ROOT / "branches/quickstart.md")
    concepts_text = _read(TOURING_ROOT / "references/concepts.md")
    all_packaged_markdown = "\n".join(_read(path) for path in _markdown_files(SYSTEM_SKILLS_ROOT))

    assert "`command -v kimi || command -v kimi-code`" in quickstart_text
    assert "tool adapters for `claude`, `codex`, `kimi`, and `gemini`" in quickstart_text
    assert "`claude`, `codex`, `kimi`, or `gemini`" in concepts_text
    assert "Gemini and Kimi specialists remain headless-only" not in all_packaged_markdown
    assert "Gemini and Kimi stay headless-only" not in all_packaged_markdown
    assert "Kimi specialists remain headless-only" not in all_packaged_markdown
    assert 'general-kimi","tool":"claude' not in all_packaged_markdown
    assert "raw Kimi `--auto` or `--yolo` launch flags" in all_packaged_markdown
