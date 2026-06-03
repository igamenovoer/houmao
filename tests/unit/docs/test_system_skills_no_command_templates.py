from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SYSTEM_SKILLS_ROOT = REPO_ROOT / "src/houmao/agents/assets/system_skills"
TEXT_FILE_SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml"}


def _system_skill_text_files() -> list[Path]:
    """Return packaged system-skill files that may contain user-facing guidance."""

    return [
        path
        for path in sorted(SYSTEM_SKILLS_ROOT.rglob("*"))
        if path.is_file() and path.suffix in TEXT_FILE_SUFFIXES
    ]


def test_system_skills_do_not_reference_retired_command_templates() -> None:
    """Packaged skills use direct commands or config drafts, not command templates."""

    retired_terms = (
        "internals command-templates",
        "command template",
        "command-templates",
        "command-template",
        "command templates",
        "template blockers",
        "template id",
        "template ids",
    )

    offenders: list[str] = []
    for path in _system_skill_text_files():
        text = path.read_text(encoding="utf-8")
        for term in retired_terms:
            if term in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {term}")

    assert offenders == []


def test_system_skills_do_not_reference_retired_houmao_mgr_cli_shapes() -> None:
    """Packaged skills spell current scoped houmao-mgr command shapes."""

    retired_cli_shapes = (
        "houmao-mgr agents join",
        "<chosen houmao-mgr launcher> agents join",
        "houmao-mgr agents memory",
        "mail move --message-ref <message_ref> --box",
        "--box <box>",
    )

    offenders: list[str] = []
    for path in _system_skill_text_files():
        text = path.read_text(encoding="utf-8")
        for cli_shape in retired_cli_shapes:
            if cli_shape in text:
                offenders.append(f"{path.relative_to(REPO_ROOT)}: {cli_shape}")

    assert offenders == []
