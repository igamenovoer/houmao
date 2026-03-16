from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from houmao.agents.brain_builder import (
    BuildError,
    BuildRequest,
    _load_tool_adapter,
    build_brain_home,
    load_brain_recipe,
)
from houmao.agents.mailbox_runtime_models import MailboxDeclarativeConfig


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_repo(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "brains/tool-adapters/codex.yaml",
        """
schema_version: 1
tool: codex
home_selector:
  env_var: CODEX_HOME
launch:
  executable: codex
  args: []
  env_injection:
    mode: home_dotenv
    env_file_in_home: .env
config_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
credential_projection:
  files_dir: files
  file_mappings:
    - source: auth.json
      destination: auth.json
      mode: symlink
      required: false
  env:
    source: env/vars.env
    allowlist:
      - OPENAI_API_KEY
      - OPENAI_BASE_URL
""".strip()
        + "\n",
    )

    _write(agent_def_dir / "brains/skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "brains/skills/skill-b/SKILL.md", "# skill-b\n")
    _write(agent_def_dir / "brains/cli-configs/codex/default/config.toml", "model='x'\n")
    _write(
        agent_def_dir / "brains/api-creds/codex/personal-a/files/auth.json",
        '{"token": "secret"}\n',
    )
    _write(
        agent_def_dir / "brains/api-creds/codex/personal-a/env/vars.env",
        """
OPENAI_API_KEY=sk-test-123
OPENAI_BASE_URL=https://api.example.test
NOT_ALLOWLISTED=do-not-export
""".strip()
        + "\n",
    )


def _seed_claude_repo(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "brains/tool-adapters/claude.yaml",
        """
schema_version: 1
tool: claude
home_selector:
  env_var: CLAUDE_CONFIG_DIR
launch:
  executable: claude
  args:
    - -p
  env_injection:
    mode: export_from_env_file
config_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
credential_projection:
  files_dir: files
  file_mappings:
    - source: claude_state.template.json
      destination: claude_state.template.json
      mode: copy
  env:
    source: env/vars.env
    allowlist:
      - ANTHROPIC_API_KEY
      - ANTHROPIC_BASE_URL
""".strip()
        + "\n",
    )
    _write(agent_def_dir / "brains/skills/skill-a/SKILL.md", "# skill-a\n")
    _write(
        agent_def_dir / "brains/cli-configs/claude/default/settings.json",
        '{"skipDangerousModePermissionPrompt": true}\n',
    )
    _write(
        agent_def_dir / "brains/api-creds/claude/personal-a/files/claude_state.template.json",
        "{}\n",
    )
    _write(
        agent_def_dir / "brains/api-creds/claude/personal-a/env/vars.env",
        "ANTHROPIC_API_KEY=sk-test\n",
    )


def test_build_brain_home_projects_selected_components_and_manifest(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="personal-a",
            home_id="home-001",
        )
    )

    home = result.home_path
    assert home == agent_def_dir / "tmp/agents-runtime/homes/home-001"
    assert home.is_dir()
    assert result.manifest_path == agent_def_dir / "tmp/agents-runtime/manifests/home-001.yaml"

    # Fresh home content is built from selected inputs only.
    assert (home / "config.toml").is_file()
    assert (home / "skills/skill-a").is_symlink()
    assert (home / "skills/.system/mailbox/email-via-filesystem/SKILL.md").is_file()
    assert not (home / "skills/skill-b").exists()

    # Credential file projection and env contract setup.
    assert (home / "auth.json").is_symlink()
    assert (home / ".env").is_symlink()
    assert (home / "launch.sh").is_file()
    launch_script = (home / "launch.sh").read_text(encoding="utf-8")
    assert "ensure_codex_home_bootstrap" in launch_script

    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_text)

    assert manifest["inputs"]["skills"] == ["skill-a"]
    assert manifest["runtime"]["home_path"] == str(home)
    assert manifest["credentials"]["env_contract"]["selected_env_vars"] == [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ]
    assert "NOT_ALLOWLISTED" not in manifest_text
    assert "sk-test-123" not in manifest_text


def test_load_brain_recipe_accepts_default_agent_name(tmp_path: Path) -> None:
    recipe_path = tmp_path / "recipe.yaml"
    _write(
        recipe_path,
        """
schema_version: 1
name: gpu-kernel-coder-default
tool: codex
default_agent_name: cao-codex-demo
skills:
  - skill-a
config_profile: default
credential_profile: personal-a
""".strip()
        + "\n",
    )

    recipe = load_brain_recipe(recipe_path)

    assert recipe.default_agent_name == "cao-codex-demo"
    assert recipe.skills == ["skill-a"]


def test_load_brain_recipe_accepts_mailbox_config(tmp_path: Path) -> None:
    recipe_path = tmp_path / "recipe.yaml"
    _write(
        recipe_path,
        """
schema_version: 1
name: gpu-kernel-coder-default
tool: codex
skills:
  - skill-a
config_profile: default
credential_profile: personal-a
mailbox:
  transport: filesystem
  principal_id: AGENTSYS-research
  address: AGENTSYS-research@agents.localhost
  filesystem_root: shared-mail
""".strip()
        + "\n",
    )

    recipe = load_brain_recipe(recipe_path)

    assert recipe.mailbox == MailboxDeclarativeConfig(
        transport="filesystem",
        principal_id="AGENTSYS-research",
        address="AGENTSYS-research@agents.localhost",
        filesystem_root="shared-mail",
    )


def test_load_brain_recipe_allows_missing_default_agent_name(tmp_path: Path) -> None:
    recipe_path = tmp_path / "recipe.yaml"
    _write(
        recipe_path,
        """
schema_version: 1
name: gpu-kernel-coder-default
tool: claude
skills:
  - skill-a
config_profile: default
credential_profile: personal-a
""".strip()
        + "\n",
    )

    recipe = load_brain_recipe(recipe_path)

    assert recipe.default_agent_name is None


def test_build_brain_home_persists_declarative_mailbox_config_in_manifest(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="personal-a",
            mailbox=MailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="AGENTSYS-research",
                address="AGENTSYS-research@agents.localhost",
                filesystem_root="shared-mail",
            ),
            home_id="home-mailbox-001",
        )
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["mailbox"] == {
        "transport": "filesystem",
        "principal_id": "AGENTSYS-research",
        "address": "AGENTSYS-research@agents.localhost",
        "filesystem_root": "shared-mail",
    }


def test_build_brain_home_skips_missing_optional_credential_file(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    (agent_def_dir / "brains/api-creds/codex/personal-a/files/auth.json").unlink()

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="personal-a",
            home_id="home-optional-auth",
        )
    )

    assert not (result.home_path / "auth.json").exists()
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["credentials"]["projected_files"] == []


def test_build_brain_home_still_requires_missing_required_credential_file(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    adapter_path = agent_def_dir / "brains/tool-adapters/codex.yaml"
    adapter_text = adapter_path.read_text(encoding="utf-8").replace(
        "required: false",
        "required: true",
    )
    adapter_path.write_text(adapter_text, encoding="utf-8")
    (agent_def_dir / "brains/api-creds/codex/personal-a/files/auth.json").unlink()

    with pytest.raises(BuildError, match="Missing credential file"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=["skill-a"],
                config_profile="default",
                credential_profile="personal-a",
                home_id="home-required-auth",
            )
        )


def test_build_brain_home_is_fresh_by_default(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    base_request = BuildRequest(
        agent_def_dir=agent_def_dir,
        runtime_root=agent_def_dir / "tmp/agents-runtime",
        tool="codex",
        skills=["skill-a"],
        config_profile="default",
        credential_profile="personal-a",
        home_id="home-001",
    )

    build_brain_home(base_request)

    with pytest.raises(BuildError, match="fresh-by-default"):
        build_brain_home(base_request)

    reused = build_brain_home(
        BuildRequest(
            agent_def_dir=base_request.agent_def_dir,
            runtime_root=base_request.runtime_root,
            tool=base_request.tool,
            skills=base_request.skills,
            config_profile=base_request.config_profile,
            credential_profile=base_request.credential_profile,
            home_id=base_request.home_id,
            reuse_home=True,
        )
    )
    assert reused.home_path.exists()


def test_build_brain_home_projects_claude_settings_and_template(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_claude_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="claude",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="personal-a",
            home_id="claude-home-001",
        )
    )

    settings_path = result.home_path / "settings.json"
    assert settings_path.is_file()
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["skipDangerousModePermissionPrompt"] is True
    assert (result.home_path / "claude_state.template.json").is_file()
    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    assert "ensure_claude_home_bootstrap" in launch_script


def test_claude_tool_adapter_allowlist_includes_model_selection_env_vars() -> None:
    agent_def_dir = Path(__file__).resolve().parents[2] / "fixtures" / "agents"
    adapter = _load_tool_adapter(agent_def_dir / "brains" / "tool-adapters" / "claude.yaml")

    allowlist = set(adapter.credential_env_allowlist)
    assert {
        "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    }.issubset(allowlist)


def test_tool_adapter_file_mappings_default_required_to_true(tmp_path: Path) -> None:
    adapter_path = tmp_path / "codex.yaml"
    _write(
        adapter_path,
        """
schema_version: 1
tool: codex
home_selector:
  env_var: CODEX_HOME
launch:
  executable: codex
  args: []
  env_injection:
    mode: home_dotenv
    env_file_in_home: .env
config_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
credential_projection:
  files_dir: files
  file_mappings:
    - source: auth.json
      destination: auth.json
      mode: symlink
  env:
    source: env/vars.env
    allowlist:
      - OPENAI_API_KEY
""".strip()
        + "\n",
    )

    adapter = _load_tool_adapter(adapter_path)

    assert adapter.credential_file_mappings[0].required is True


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing_adapter", "Missing adapter"),
        ("unknown_skill", "Unknown skill"),
        ("missing_config", "Missing config profile"),
        ("missing_creds", "Missing credential profile"),
    ],
)
def test_build_brain_home_validation_errors(tmp_path: Path, mutation: str, message: str) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    if mutation == "missing_adapter":
        (agent_def_dir / "brains/tool-adapters/codex.yaml").unlink()
    elif mutation == "unknown_skill":
        requested_skill = "missing-skill"
    else:
        requested_skill = "skill-a"

    if mutation == "missing_config":
        (agent_def_dir / "brains/cli-configs/codex/default").rename(
            agent_def_dir / "brains/cli-configs/codex/default.bak"
        )
    if mutation == "missing_creds":
        (agent_def_dir / "brains/api-creds/codex/personal-a").rename(
            agent_def_dir / "brains/api-creds/codex/personal-a.bak"
        )

    with pytest.raises(BuildError, match=message):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=[requested_skill] if mutation == "unknown_skill" else ["skill-a"],
                config_profile="default",
                credential_profile="personal-a",
                home_id="home-001",
            )
        )
