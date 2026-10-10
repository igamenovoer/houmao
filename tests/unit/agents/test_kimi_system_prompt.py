"""Tests for Kimi Code native managed-home prompt projection."""

from pathlib import Path

import pytest

from houmao.agents.kimi_system_prompt import (
    KIMI_SYSTEM_PROMPT_FILENAME,
    KIMI_V2_ENGINE_ENV_VAR,
    KimiSystemPromptError,
    ensure_kimi_system_prompt,
    force_kimi_v2_engine_env,
    prompt_sha256,
    render_kimi_system_prompt,
    validate_kimi_native_prompt_launch,
    validate_kimi_v2_engine_env,
)


def test_render_kimi_system_prompt_preserves_base_and_complete_prompt() -> None:
    """The renderer keeps Kimi's builtin base prompt before Houmao content."""

    assert render_kimi_system_prompt("first\nsecond\n\n") == ("${base_prompt}\n\nfirst\nsecond\n\n")


def test_render_kimi_system_prompt_allows_bare_dollar_text() -> None:
    """Only Kimi's identifier-placeholder grammar is reserved."""

    assert render_kimi_system_prompt("price: $5; shell: $HOME") == (
        "${base_prompt}\n\nprice: $5; shell: $HOME\n"
    )


@pytest.mark.parametrize("placeholder", ["${name}", "${_name2}", "text ${base_prompt}"])
def test_render_kimi_system_prompt_rejects_all_identifier_placeholders(
    placeholder: str,
) -> None:
    """Kimi-owned template substitution cannot alter Houmao prompt bytes."""

    with pytest.raises(KimiSystemPromptError, match="placeholder"):
        render_kimi_system_prompt(placeholder)


def test_ensure_kimi_system_prompt_projects_repairs_and_removes(tmp_path: Path) -> None:
    """Projection is deterministic, repairs drift, and removes stale empty state."""

    first = ensure_kimi_system_prompt(home_path=tmp_path, effective_prompt="managed role")
    system_path = tmp_path / KIMI_SYSTEM_PROMPT_FILENAME
    assert system_path.read_text(encoding="utf-8") == "${base_prompt}\n\nmanaged role\n"
    assert first.state == "projected"
    assert first.changed is True
    assert first.effective_prompt_sha256 == prompt_sha256("managed role")
    assert first.rendered_template_sha256 == prompt_sha256(system_path.read_text(encoding="utf-8"))
    assert system_path.stat().st_mode & 0o777 == 0o600

    unchanged = ensure_kimi_system_prompt(home_path=tmp_path, effective_prompt="managed role")
    assert unchanged.changed is False

    system_path.chmod(0o644)
    permission_repaired = ensure_kimi_system_prompt(
        home_path=tmp_path, effective_prompt="managed role"
    )
    assert permission_repaired.changed is True
    assert system_path.stat().st_mode & 0o777 == 0o600

    system_path.write_text("drift\n", encoding="utf-8")
    repaired = ensure_kimi_system_prompt(home_path=tmp_path, effective_prompt="managed role")
    assert repaired.changed is True
    assert system_path.read_text(encoding="utf-8") == "${base_prompt}\n\nmanaged role\n"

    removed = ensure_kimi_system_prompt(home_path=tmp_path, effective_prompt="\n")
    assert removed.state == "removed"
    assert removed.changed is True
    assert not system_path.exists()


@pytest.mark.parametrize(
    "args",
    [
        ["--agent", "other"],
        ["--agent=other"],
        ["--agent-file", "custom.md"],
        ["--agent-file=custom.md"],
    ],
)
def test_validate_kimi_native_prompt_launch_rejects_explicit_agent_selectors(
    tmp_path: Path,
    args: list[str],
) -> None:
    """Explicit selectors outrank SYSTEM.md and are rejected."""

    with pytest.raises(KimiSystemPromptError, match="higher-priority launch option"):
        validate_kimi_native_prompt_launch(
            launch_args=args,
            working_directory=tmp_path,
            home_path=tmp_path / "home",
        )


def test_validate_kimi_native_prompt_launch_rejects_project_default_override(
    tmp_path: Path,
) -> None:
    """A project default-agent override cannot silently replace Houmao's prompt."""

    project_root = tmp_path / "project"
    project_root.joinpath(".git").mkdir(parents=True)
    workdir = project_root / "nested"
    workdir.mkdir()
    agent_path = project_root / ".kimi-code" / "agents" / "agent.md"
    agent_path.parent.mkdir(parents=True)
    agent_path.write_text(
        "---\nname: agent\ndescription: override\noverride: true\n---\nreplacement\n",
        encoding="utf-8",
    )

    with pytest.raises(KimiSystemPromptError, match="override: true"):
        validate_kimi_native_prompt_launch(
            launch_args=[],
            working_directory=workdir,
            home_path=tmp_path / "home",
        )


def test_validate_kimi_native_prompt_launch_rejects_configured_extra_override(
    tmp_path: Path,
) -> None:
    """Configured extra agent roots receive the same precedence check."""

    project_root = tmp_path / "project"
    project_root.joinpath(".git").mkdir(parents=True)
    home_path = tmp_path / "home"
    home_path.mkdir()
    home_path.joinpath("config.toml").write_text(
        'extra_agent_dirs = ["extra-agents"]\n', encoding="utf-8"
    )
    agent_path = project_root / "extra-agents" / "default.md"
    agent_path.parent.mkdir(parents=True)
    agent_path.write_text(
        "---\nname: agent\ndescription: override\noverride: true\n---\nreplacement\n",
        encoding="utf-8",
    )

    with pytest.raises(KimiSystemPromptError, match="override: true"):
        validate_kimi_native_prompt_launch(
            launch_args=[],
            working_directory=project_root,
            home_path=home_path,
        )


def test_validate_kimi_native_prompt_launch_matches_duplicate_discovery_order(
    tmp_path: Path,
) -> None:
    """A later duplicate does not replace Kimi's first valid same-name file."""

    project_root = tmp_path / "project"
    project_root.joinpath(".git").mkdir(parents=True)
    agents_root = project_root / ".kimi-code" / "agents"
    agents_root.mkdir(parents=True)
    agents_root.joinpath("a.md").write_text(
        "---\nname: agent\ndescription: first\noverride: false\n---\nfirst\n",
        encoding="utf-8",
    )
    agents_root.joinpath("b.md").write_text(
        "---\nname: agent\ndescription: second\noverride: true\n---\nsecond\n",
        encoding="utf-8",
    )

    validate_kimi_native_prompt_launch(
        launch_args=[],
        working_directory=project_root,
        home_path=tmp_path / "home",
    )


def test_kimi_v2_engine_environment_is_forced_and_later_truthy_values_fail() -> None:
    """Managed launch fixes the v2 value and rejects legacy-engine overrides."""

    env = force_kimi_v2_engine_env({"OTHER": "value", KIMI_V2_ENGINE_ENV_VAR: "true"})
    assert env[KIMI_V2_ENGINE_ENV_VAR] == "0"
    validate_kimi_v2_engine_env(env)

    with pytest.raises(KimiSystemPromptError, match="legacy engine"):
        validate_kimi_v2_engine_env({KIMI_V2_ENGINE_ENV_VAR: "1"})
