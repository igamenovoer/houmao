"""Tests for packaged system-skill Kimi guidance."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEM_SKILLS_ROOT = REPO_ROOT / "src/houmao/agents/assets/system_skills"
SHARED_ROUTINES_ROOT = SYSTEM_SKILLS_ROOT / "public/houmao-shared-routines"
AGENT_DEFINITION_ROOT = SHARED_ROUTINES_ROOT / "subskills/houmao-agent-definition"
CREDENTIAL_MGR_ROOT = SHARED_ROUTINES_ROOT / "subskills/houmao-credential-mgr"
WELCOME_ROOT = SYSTEM_SKILLS_ROOT / "public/houmao-admin-welcome"


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


def test_credential_manager_documents_kimi_login_handling_without_login_helper() -> None:
    """Kimi credential guidance covers CRUD and login handling without login helpers."""

    skill_text = _read(CREDENTIAL_MGR_ROOT / "SKILL-MAIN.md")
    add_text = _read(CREDENTIAL_MGR_ROOT / "commands/add.md")
    set_text = _read(CREDENTIAL_MGR_ROOT / "commands/set.md")
    login_text = _read(CREDENTIAL_MGR_ROOT / "commands/login.md")
    kimi_login_text = _read(CREDENTIAL_MGR_ROOT / "references/kimi-code-login-handling.md")
    kimi_reference = _read(CREDENTIAL_MGR_ROOT / "references/kimi-credential-kinds.md")

    assert "supported CRUD tools: `claude`, `codex`, `kimi`" in skill_text
    assert "supported login-helper tools: `claude`, `codex`" in skill_text
    assert "DO NOT present Kimi as having a maintained credential login helper" in skill_text
    assert "references/kimi-code-login-handling.md" in skill_text
    assert "Kimi: `references/kimi-credential-kinds.md`" in add_text
    assert "`tool`: one of `claude`, `codex`, or `kimi`" in add_text
    assert "`tool`: one of `claude`, `codex`, or `kimi`" in set_text
    assert "Kimi credential CRUD is supported" in login_text
    assert "../references/kimi-code-login-handling.md" in login_text
    assert "Do not run or invent a maintained Kimi login helper" in login_text
    assert "command -v kimi || command -v kimi-code" in kimi_login_text
    assert "KIMI_CODE_HOME" in kimi_login_text
    assert "tmux new-session -d -s" in kimi_login_text
    assert 'proxy_env_args+=(-e "${name}=${!name}")' in kimi_login_text
    assert "kimi login" in kimi_login_text
    assert "credentials/kimi-code.json" in kimi_login_text
    assert "--code-home" in kimi_login_text
    assert "KIMI_CODE_OAUTH_HOST" in kimi_login_text
    assert "KIMI_OAUTH_HOST" in kimi_login_text
    assert "KIMI_CODE_BASE_URL" in kimi_login_text
    assert "kimi-code-env-<hash>.json" in kimi_login_text
    assert "--code-home" in kimi_reference
    assert "--config-toml" in kimi_reference
    assert "--credential-json" in kimi_reference
    assert "Fresh Default Kimi Code OAuth Login" in kimi_reference
    assert "kimi-code-login-handling.md" in kimi_reference
    assert "Kimi Platform API key" in kimi_reference
    assert "kimi-code-env-<hash>.json" in kimi_reference


def test_agent_definition_kimi_guidance_and_relative_links_resolve() -> None:
    """Agent-definition guidance uses Kimi examples and keeps local links valid."""

    skill_text = _read(AGENT_DEFINITION_ROOT / "SKILL-MAIN.md")
    specialists_text = _read(AGENT_DEFINITION_ROOT / "commands/easy/specialists.md")
    profiles_text = _read(AGENT_DEFINITION_ROOT / "commands/easy/profiles.md")
    launch_text = _read(AGENT_DEFINITION_ROOT / "commands/easy/launch-instance.md")
    fast_forward_text = _read(AGENT_DEFINITION_ROOT / "commands/easy/create-agent-fast-forward.md")

    stale_kimi_example = '"name":"general-kimi","tool":"claude"'
    assert stale_kimi_example not in skill_text
    assert stale_kimi_example not in specialists_text
    assert '"name":"general-kimi","tool":"kimi"' in skill_text
    assert '"name":"general-kimi","tool":"kimi"' in specialists_text
    assert "`--tool claude|codex|kimi`" in specialists_text
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


def test_packaged_guidance_includes_kimi_welcome_and_avoids_stale_headless_claims() -> None:
    """Adjacent packaged guidance includes Kimi and avoids old Kimi headless-only text."""

    guided_paths_text = _read(WELCOME_ROOT / "references/guided-paths.md")
    concepts_text = _read(WELCOME_ROOT / "references/concepts.md")
    current_roots = (SYSTEM_SKILLS_ROOT / "public",)
    all_packaged_markdown = "\n".join(
        _read(path) for root in current_roots for path in _markdown_files(root)
    )

    assert "`command -v kimi || command -v kimi-code`" in guided_paths_text
    assert "tool adapters for `claude`, `codex`, and `kimi`" in guided_paths_text
    assert "`claude`, `codex`, or `kimi`" in concepts_text
    assert "Kimi specialists remain headless-only" not in all_packaged_markdown
    assert 'general-kimi","tool":"claude' not in all_packaged_markdown
    assert "raw Kimi `--auto` or `--yolo` launch flags" in all_packaged_markdown
    assert not (SYSTEM_SKILLS_ROOT / "protected").exists()
