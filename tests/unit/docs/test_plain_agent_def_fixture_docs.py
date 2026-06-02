from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
PLAIN_AGENT_DEF_ROOT = REPO_ROOT / "tests" / "fixtures" / "plain-agent-def"


def _read(relative_path: str) -> str:
    """Read one plain-agent fixture guidance file."""

    return (PLAIN_AGENT_DEF_ROOT / relative_path).read_text(encoding="utf-8")


def test_plain_agent_def_guidance_uses_scoped_cli_paths() -> None:
    """Guard plain fixture guidance against retired root managed-agent commands."""

    guidance = "\n".join(
        [
            _read("README.md"),
            _read("MIGRATION.md"),
            _read("roles/README.md"),
            _read("skills/README.md"),
        ]
    )

    assert "houmao-mgr project agents launch" in guidance
    assert "houmao-mgr agents single --agent-id <id>" in guidance
    assert "houmao-mgr internals native-agent brain build" in guidance
    for retired_command in (
        "houmao-mgr agents launch",
        "houmao-mgr agents stop",
        "houmao-mgr agents cleanup",
    ):
        assert retired_command not in guidance


def test_plain_agent_def_guidance_uses_fixture_relative_paths() -> None:
    """Guard role/skill guidance against stale compatibility-tree path names."""

    role_and_skill_guidance = "\n".join([_read("roles/README.md"), _read("skills/README.md")])

    assert "roles/" in role_and_skill_guidance
    assert "skills/" in role_and_skill_guidance
    assert "agents/roles/" not in role_and_skill_guidance
    assert "agents/skills/" not in role_and_skill_guidance


def test_server_api_smoke_role_uses_maintained_api_wording() -> None:
    """Guard the smoke role prompt against retired standalone server wording."""

    server_api_smoke_guidance = "\n".join(
        [
            _read("roles/README.md"),
            _read("roles/server-api-smoke/README.md"),
            _read("roles/server-api-smoke/system-prompt.md"),
        ]
    )

    assert "managed-agent API" in server_api_smoke_guidance
    assert "passive-server" in server_api_smoke_guidance
    assert "houmao-server" not in server_api_smoke_guidance.lower()
