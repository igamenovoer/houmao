from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest
import yaml

from houmao.agents.auto_skills import (
    AUTO_SKILL_SYSTEM_PROMPT,
    AUTO_SKILL_SYSTEM_PROMPT_REASON,
    prompt_sha256,
)
from houmao.agents.brain_builder import (
    BuildError,
    BuildRequest,
    PrivateSkillProjection,
    _load_tool_adapter,
    build_brain_home,
    load_brain_recipe,
)
from houmao.agents.launch_overrides import LaunchArgsSection, LaunchOverrides
from houmao.agents.mailbox_runtime_models import FilesystemMailboxDeclarativeConfig
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig
from houmao.agents.system_skills import (
    SYSTEM_SKILL_AGENT_ENTRYPOINT,
    SYSTEM_SKILL_ADMIN_ENTRYPOINT,
    SYSTEM_SKILL_ADMIN_WELCOME,
    SYSTEM_SKILL_PACK_ADMIN,
    SYSTEM_SKILL_PACK_AGENT,
    SystemSkillPolicyError,
    SystemSkillSelectionPolicy,
    discover_installed_system_skills,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _agent_shared_root(home_path: Path) -> Path:
    """Return the protected shared-routine root inside the agent entrypoint."""

    return home_path / "skills" / SYSTEM_SKILL_AGENT_ENTRYPOINT / "subskills/houmao-shared-routines"


def _agent_routine_root(home_path: Path, logical_id: str) -> Path:
    """Return one agent-composed protected routine root."""

    return _agent_shared_root(home_path) / "subskills" / logical_id


def _seed_repo(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "tools/codex/adapter.yaml",
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
setup_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
auth_projection:
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

    _write(agent_def_dir / "skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "skills/skill-b/SKILL.md", "# skill-b\n")
    _write(
        agent_def_dir / "tools/codex/setups/default/config.toml",
        'model_reasoning_effort = "medium"\n\n[tui]\nshow_tooltips = false\n',
    )
    _write(
        agent_def_dir / "tools/codex/auth/personal-a/files/auth.json",
        '{"token": "secret"}\n',
    )
    _write(
        agent_def_dir / "tools/codex/auth/personal-a/env/vars.env",
        """
OPENAI_API_KEY=sk-test-123
OPENAI_BASE_URL=https://api.example.test
NOT_ALLOWLISTED=do-not-export
""".strip()
        + "\n",
    )


def _seed_claude_repo(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "tools/claude/adapter.yaml",
        """
schema_version: 1
tool: claude
home_selector:
  env_var: CLAUDE_CONFIG_DIR
launch:
  executable: claude
  args: []
  default_tool_params: {}
  metadata:
    tool_params:
      include_partial_messages:
        type: boolean
        backends:
          claude_headless:
            args_when_true:
              - --include-partial-messages
  env_injection:
    mode: export_from_env_file
setup_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
auth_projection:
  files_dir: files
  file_mappings:
    - source: .credentials.json
      destination: .credentials.json
      mode: copy
      required: false
    - source: .claude.json
      destination: .claude.json
      mode: copy
      required: false
    - source: claude_state.template.json
      destination: claude_state.template.json
      mode: copy
      required: false
  env:
    source: env/vars.env
    allowlist:
      - ANTHROPIC_API_KEY
      - CLAUDE_CODE_OAUTH_TOKEN
      - ANTHROPIC_BASE_URL
""".strip()
        + "\n",
    )
    _write(agent_def_dir / "skills/skill-a/SKILL.md", "# skill-a\n")
    _write(
        agent_def_dir / "tools/claude/setups/default/settings.json",
        '{"skipDangerousModePermissionPrompt": true}\n',
    )
    _write(
        agent_def_dir / "tools/claude/auth/personal-a/files/claude_state.template.json",
        "{}\n",
    )
    _write(
        agent_def_dir / "tools/claude/auth/personal-a/files/.credentials.json",
        '{"claudeAiOauth": {"accessToken": "vendor-access-token"}}\n',
    )
    _write(
        agent_def_dir / "tools/claude/auth/personal-a/files/.claude.json",
        '{"hasCompletedOnboarding": true, "numStartups": 7}\n',
    )
    _write(
        agent_def_dir / "tools/claude/auth/personal-a/env/vars.env",
        "\n".join(
            [
                "ANTHROPIC_API_KEY='sk-test'",
                "CLAUDE_CODE_OAUTH_TOKEN=oauth-token-test",
                'ANTHROPIC_BASE_URL="https://api.example.test"',
            ]
        )
        + "\n",
    )


def _seed_kimi_repo(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "tools/kimi/adapter.yaml",
        """
schema_version: 1
tool: kimi
home_selector:
  env_var: KIMI_CODE_HOME
launch:
  executable: kimi
  args: []
  default_tool_params: {}
  metadata:
    tool_params: {}
  env_injection:
    mode: export_from_env_file
setup_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
auth_projection:
  files_dir: files
  file_mappings:
    - source: config.toml
      destination: config.toml
      mode: copy
      required: false
    - source: credentials/kimi-code.json
      destination: credentials/kimi-code.json
      mode: copy
      required: false
  env:
    source: env/vars.env
    allowlist:
      - KIMI_MODEL_NAME
      - KIMI_MODEL_API_KEY
      - KIMI_MODEL_PROVIDER_TYPE
      - KIMI_MODEL_BASE_URL
      - KIMI_CODE_BASE_URL
      - KIMI_CODE_OAUTH_HOST
      - KIMI_OAUTH_HOST
      - KIMI_DISABLE_TELEMETRY
""".strip()
        + "\n",
    )
    _write(agent_def_dir / "skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "tools/kimi/setups/default/README.md", "Kimi setup\n")
    _write(
        agent_def_dir / "tools/kimi/auth/oauth/files/config.toml",
        'default_model = "kimi-code/default"\n',
    )
    _write(
        agent_def_dir / "tools/kimi/auth/oauth/files/credentials/kimi-code.json",
        '{"access_token": "secret"}\n',
    )
    _write(agent_def_dir / "tools/kimi/auth/oauth/env/vars.env", "\n")
    _write(
        agent_def_dir / "tools/kimi/auth/env-model/env/vars.env",
        "\n".join(
            [
                "KIMI_MODEL_NAME=kimi-code/baseline",
                "KIMI_MODEL_API_KEY=sk-kimi",
                "KIMI_MODEL_BASE_URL=https://kimi.example.test",
                "NOT_ALLOWLISTED=do-not-export",
            ]
        )
        + "\n",
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
    config_payload = tomllib.loads((home / "config.toml").read_text(encoding="utf-8"))
    assert "model" not in config_payload
    assert config_payload["model_reasoning_effort"] == "medium"
    assert config_payload["tui"]["show_tooltips"] is False
    assert (home / "skills/skill-a").is_symlink()
    agent_entrypoint = home / "skills" / SYSTEM_SKILL_AGENT_ENTRYPOINT
    assert (agent_entrypoint / "SKILL.md").is_file()
    for logical_id in (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
        "houmao-memory-mgr",
        "houmao-adv-usage-pattern",
        "houmao-agent-loop-pro",
        "houmao-agent-loop-lite",
        "houmao-agent-instance",
        "houmao-agent-inspect",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
        "houmao-interop-ag-ui",
        "houmao-ext-graphing",
    ):
        assert (_agent_routine_root(home, logical_id) / "SKILL.md").is_file()
    assert not _agent_routine_root(home, "houmao-project-mgr").exists()
    assert not _agent_routine_root(home, "houmao-agent-definition").exists()
    assert not (home / "skills/houmao-agent-email-comms").exists()
    assert not (home / "skills/.system/mailbox").exists()
    assert not (home / "skills/skill-b").exists()
    installed_records = discover_installed_system_skills(tool="codex", home_path=home)
    assert tuple(record.name for record in installed_records) == (SYSTEM_SKILL_AGENT_ENTRYPOINT,)

    # Credential file projection and env contract setup.
    assert (home / "auth.json").is_symlink()
    assert (home / ".env").is_symlink()
    assert (home / "launch.sh").is_file()
    launch_script = (home / "launch.sh").read_text(encoding="utf-8")
    assert "houmao.agents.launch_policy.cli" in launch_script
    assert "--requested-operator-prompt-mode unattended" in launch_script

    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_text)

    assert manifest["inputs"]["skills"] == ["skill-a"]
    assert manifest["launch_policy"]["operator_prompt_mode"] == "unattended"
    assert manifest["runtime"]["home_path"] == str(home)
    assert manifest["credentials"]["env_contract"]["selected_env_vars"] == [
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
    ]
    assert "NOT_ALLOWLISTED" not in manifest_text
    assert "sk-test-123" not in manifest_text


def test_build_brain_home_applies_source_additive_system_skill_policy(
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
            source_system_skill_policy=SystemSkillSelectionPolicy(
                mode="extend",
                pack_ids=(SYSTEM_SKILL_PACK_ADMIN,),
            ),
            home_id="codex-home-source-system-skills",
        )
    )

    installed_records = discover_installed_system_skills(tool="codex", home_path=result.home_path)
    installed_names = tuple(record.name for record in installed_records)
    assert installed_names == (
        SYSTEM_SKILL_ADMIN_WELCOME,
        SYSTEM_SKILL_ADMIN_ENTRYPOINT,
        SYSTEM_SKILL_AGENT_ENTRYPOINT,
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    system_skill_provenance = manifest["runtime"]["launch_contract"]["construction_provenance"][
        "system_skills"
    ]
    assert system_skill_provenance["source_policy"] == {
        "mode": "extend",
        "packs": [SYSTEM_SKILL_PACK_ADMIN],
    }
    assert system_skill_provenance["profile_policy"] == {}
    assert system_skill_provenance["selected_packs"] == [
        SYSTEM_SKILL_PACK_AGENT,
        SYSTEM_SKILL_PACK_ADMIN,
    ]
    assert system_skill_provenance["public_skills"] == [
        SYSTEM_SKILL_AGENT_ENTRYPOINT,
        SYSTEM_SKILL_ADMIN_WELCOME,
        SYSTEM_SKILL_ADMIN_ENTRYPOINT,
    ]


def test_build_brain_home_rejects_removed_llm_wiki_system_skill_policy_before_mutation(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = agent_def_dir / "tmp/agents-runtime"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    with pytest.raises(SystemSkillPolicyError, match="Unknown system-skill pack `unknown`"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=runtime_root,
                tool="codex",
                skills=["skill-a"],
                config_profile="default",
                credential_profile="personal-a",
                source_system_skill_policy=SystemSkillSelectionPolicy(
                    mode="extend",
                    pack_ids=("unknown",),
                ),
                home_id="codex-home-removed-system-skill",
            )
        )

    assert not (runtime_root / "homes/codex-home-removed-system-skill").exists()


def test_build_brain_home_profile_replacement_overrides_source_system_skill_policy(
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
            source_system_skill_policy=SystemSkillSelectionPolicy(
                mode="extend",
                pack_ids=(SYSTEM_SKILL_PACK_ADMIN,),
            ),
            launch_profile_system_skill_policy=SystemSkillSelectionPolicy(
                mode="replace",
                pack_ids=(SYSTEM_SKILL_PACK_AGENT,),
            ),
            home_id="codex-home-profile-system-skills",
        )
    )

    installed_names = tuple(
        record.name
        for record in discover_installed_system_skills(tool="codex", home_path=result.home_path)
    )
    assert installed_names == (SYSTEM_SKILL_AGENT_ENTRYPOINT,)

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    system_skill_provenance = manifest["runtime"]["launch_contract"]["construction_provenance"][
        "system_skills"
    ]
    assert system_skill_provenance["source_policy"] == {
        "mode": "extend",
        "packs": [SYSTEM_SKILL_PACK_ADMIN],
    }
    assert system_skill_provenance["profile_policy"] == {
        "mode": "replace",
        "packs": [SYSTEM_SKILL_PACK_AGENT],
    }
    assert system_skill_provenance["selected_packs"] == [SYSTEM_SKILL_PACK_AGENT]
    assert system_skill_provenance["public_skills"] == [SYSTEM_SKILL_AGENT_ENTRYPOINT]


def test_build_brain_home_disabled_profile_policy_removes_stale_system_skills_on_reuse(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    first_result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="personal-a",
            home_id="codex-home-reused-system-skills",
        )
    )
    assert (first_result.home_path / f"skills/{SYSTEM_SKILL_AGENT_ENTRYPOINT}/SKILL.md").is_file()

    second_result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="personal-a",
            launch_profile_system_skill_policy=SystemSkillSelectionPolicy(mode="none"),
            home_id="codex-home-reused-system-skills",
            reuse_home=True,
        )
    )

    assert discover_installed_system_skills(tool="codex", home_path=second_result.home_path) == ()
    manifest = yaml.safe_load(second_result.manifest_path.read_text(encoding="utf-8"))
    system_skill_provenance = manifest["runtime"]["launch_contract"]["construction_provenance"][
        "system_skills"
    ]
    assert system_skill_provenance["profile_policy"] == {"mode": "none"}
    assert system_skill_provenance["selected_packs"] == []
    assert system_skill_provenance["public_skills"] == []
    assert system_skill_provenance["removed_packs"] == [SYSTEM_SKILL_PACK_AGENT]
    assert (
        f"skills/{SYSTEM_SKILL_AGENT_ENTRYPOINT}"
        in system_skill_provenance["removed_projected_relative_dirs"]
    )


def test_build_brain_home_rejects_registered_system_skill_name_collision(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    _write(agent_def_dir / "skills/houmao-agent-definition/SKILL.md", "# collision\n")

    with pytest.raises(BuildError, match="cannot collide with packaged Houmao system-skill names"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=["houmao-agent-definition"],
                config_profile="default",
                credential_profile="personal-a",
                home_id="codex-home-system-skill-collision",
            )
        )


def test_build_brain_home_rejects_private_system_skill_name_collision(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    private_skill = tmp_path / "private" / "houmao-agent-definition"
    _write(private_skill / "SKILL.md", "# collision\n")

    with pytest.raises(BuildError, match="cannot collide with packaged Houmao system-skill names"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=["skill-a"],
                private_skills=(
                    PrivateSkillProjection(
                        name="houmao-agent-definition",
                        source_path=private_skill,
                        mode="copy",
                    ),
                ),
                config_profile="default",
                credential_profile="personal-a",
                home_id="codex-home-private-system-skill-collision",
            )
        )


@pytest.mark.parametrize("collision_kind", ["registered", "private"])
def test_build_brain_home_rejects_auto_skill_name_collisions(
    tmp_path: Path,
    collision_kind: str,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    private_skills: tuple[PrivateSkillProjection, ...] = ()
    selected_skills = ["skill-a"]
    if collision_kind == "registered":
        _write(agent_def_dir / f"skills/{AUTO_SKILL_SYSTEM_PROMPT}/SKILL.md", "# collision\n")
        selected_skills = [AUTO_SKILL_SYSTEM_PROMPT]
    else:
        private_skill = tmp_path / "private" / AUTO_SKILL_SYSTEM_PROMPT
        _write(private_skill / "SKILL.md", "# collision\n")
        private_skills = (
            PrivateSkillProjection(
                name=AUTO_SKILL_SYSTEM_PROMPT,
                source_path=private_skill,
                mode="copy",
            ),
        )

    with pytest.raises(BuildError, match="reserved Houmao auto-skill names"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=selected_skills,
                private_skills=private_skills,
                config_profile="default",
                credential_profile="personal-a",
                required_auto_skill_names=(AUTO_SKILL_SYSTEM_PROMPT,),
                role_prompt_override="Managed prompt.",
                home_id=f"codex-home-auto-skill-collision-{collision_kind}",
            )
        )


def test_build_brain_home_copies_selected_setup_bundle_verbatim(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    custom_setup = (
        """
model_provider = "yunwu-openai"
model_reasoning_effort = "medium"

[tui]
show_tooltips = false

[model_providers.yunwu-openai]
name = "Yunwu"
base_url = "https://api.example.test/v1"
env_key = "OPENAI_API_KEY"
requires_openai_auth = false
wire_api = "responses"
""".strip()
        + "\n"
    )
    _write(agent_def_dir / "tools/codex/setups/yunwu-openai/config.toml", custom_setup)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a"],
            config_profile="yunwu-openai",
            credential_profile="personal-a",
            home_id="home-selected-setup",
        )
    )

    assert (result.home_path / "config.toml").read_text(encoding="utf-8") == custom_setup
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    codex_overrides = manifest["runtime"]["launch_contract"]["model_selection"][
        "codex_cli_config_overrides"
    ]
    assert not any(arg.startswith("--config=model=") for arg in codex_overrides["args"])
    assert '--config=model_provider="yunwu-openai"' in codex_overrides["args"]
    assert (
        '--config=model_providers.yunwu-openai.base_url="https://api.example.test/v1"'
        in codex_overrides["args"]
    )
    assert "sk-test-123" not in str(codex_overrides)


def test_build_brain_home_persists_persistent_launch_env_records(
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
            persistent_env_records={
                "FEATURE_FLAG_X": "1",
                "OPENAI_MODEL": "gpt-5.4",
            },
            home_id="home-persistent-launch-env",
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert "export FEATURE_FLAG_X=1" in launch_script
    assert "export OPENAI_MODEL=gpt-5.4" in launch_script
    assert manifest["runtime"]["launch_contract"]["env_records"] == {
        "FEATURE_FLAG_X": "1",
        "OPENAI_MODEL": "gpt-5.4",
    }


def test_build_brain_home_rejects_persistent_env_records_owned_by_credentials(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    with pytest.raises(BuildError, match="belongs to credential env"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=["skill-a"],
                config_profile="default",
                credential_profile="personal-a",
                persistent_env_records={"OPENAI_API_KEY": "override"},
                home_id="home-invalid-persistent-launch-env",
            )
        )


def test_build_brain_home_projects_gateway_first_mailbox_system_skills(tmp_path: Path) -> None:
    """Projected mailbox skills should include the workflow and lower-level gateway layers."""

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
            mailbox=FilesystemMailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="HOUMAO-research",
                address="HOUMAO-research@agents.localhost",
                filesystem_root="shared-mail",
            ),
            home_id="home-gateway-first-mailbox",
        )
    )

    processing_root = _agent_routine_root(result.home_path, "houmao-process-emails-via-gateway")
    gateway_root = _agent_routine_root(result.home_path, "houmao-agent-email-comms")
    mailbox_mgr_root = _agent_routine_root(result.home_path, "houmao-mailbox-mgr")
    memory_mgr_root = _agent_routine_root(result.home_path, "houmao-memory-mgr")
    advanced_root = _agent_routine_root(result.home_path, "houmao-adv-usage-pattern")
    processing_skill = (processing_root / "SKILL.md").read_text(encoding="utf-8")
    gateway_skill = (gateway_root / "SKILL.md").read_text(encoding="utf-8")
    mailbox_mgr_skill = (mailbox_mgr_root / "SKILL.md").read_text(encoding="utf-8")
    memory_mgr_skill = (memory_mgr_root / "SKILL.md").read_text(encoding="utf-8")
    advanced_skill = (advanced_root / "SKILL.md").read_text(encoding="utf-8")
    pairwise_edge_loop_pattern = (
        advanced_root / "commands/pairwise-edge-loop-via-gateway-and-mailbox.md"
    )
    relay_loop_pattern = advanced_root / "commands/relay-loop-via-gateway-and-mailbox.md"

    assert "houmao-process-emails-via-gateway" in processing_skill
    assert "metadata-first triage" in processing_skill
    assert "stalled or interrupted" in processing_skill
    assert "It is acceptable to defer unrelated open emails" in processing_skill
    assert "Archive only the successfully processed selected emails" in processing_skill
    assert "wait for the next notification" in processing_skill
    assert "Do not switch to `houmao-mgr agents self mail resolve-live`" in processing_skill
    assert "pixi run houmao-mgr agents self mail resolve-live" not in processing_skill
    assert "houmao-agent-email-comms" in gateway_skill
    assert (
        "houmao-agent-entrypoint->houmao-shared-routines->process-emails-via-gateway"
        in gateway_skill
    )
    assert (
        "current prompt or recent mailbox context already provides the exact current gateway base URL"
        in gateway_skill
    )
    assert "houmao-mgr agents self mail resolve-live" in gateway_skill
    assert "pixi run houmao-mgr agents self mail resolve-live" not in gateway_skill
    assert "self-notification.md" in advanced_skill
    assert "pairwise-edge-loop-via-gateway-and-mailbox.md" in advanced_skill
    assert "relay-loop-via-gateway-and-mailbox.md" in advanced_skill
    assert pairwise_edge_loop_pattern.is_file()
    assert relay_loop_pattern.is_file()
    assert "The trigger word `houmao` is intentional." in gateway_skill
    assert "houmao-mgr mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr project mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr agents single --agent-id <id> mailbox ..." in mailbox_mgr_skill
    assert "`--agent-name <name>`" in mailbox_mgr_skill
    assert "HOUMAO_AGENT_MEMO_FILE" in memory_mgr_skill
    assert "houmao-mgr agents self memory" in memory_mgr_skill
    assert "houmao-mgr agents single --agent-name <name> memory" in memory_mgr_skill
    assert "houmao-mgr agents memory" not in memory_mgr_skill


def test_build_brain_home_projects_claude_mailbox_skills_top_level(
    tmp_path: Path,
) -> None:
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
            mailbox=FilesystemMailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="HOUMAO-research",
                address="HOUMAO-research@agents.localhost",
                filesystem_root="shared-mail",
            ),
            home_id="claude-home-mailbox",
        )
    )

    skills_root = result.home_path / "skills"
    processing_root = _agent_routine_root(result.home_path, "houmao-process-emails-via-gateway")
    gateway_root = _agent_routine_root(result.home_path, "houmao-agent-email-comms")
    mailbox_mgr_root = _agent_routine_root(result.home_path, "houmao-mailbox-mgr")
    filesystem_path = gateway_root / "references/transports/filesystem.md"
    stalwart_path = gateway_root / "references/transports/stalwart.md"
    processing_skill = (processing_root / "SKILL.md").read_text(encoding="utf-8")
    gateway_skill = (gateway_root / "SKILL.md").read_text(encoding="utf-8")
    mailbox_mgr_skill = (mailbox_mgr_root / "SKILL.md").read_text(encoding="utf-8")
    filesystem_skill = filesystem_path.read_text(encoding="utf-8")
    stalwart_skill = stalwart_path.read_text(encoding="utf-8")
    curl_reference = (gateway_root / "references/curl-examples.md").read_text(encoding="utf-8")

    assert (skills_root / f"{SYSTEM_SKILL_AGENT_ENTRYPOINT}/SKILL.md").is_file()
    assert (processing_root / "SKILL.md").is_file()
    assert (gateway_root / "SKILL.md").is_file()
    assert (mailbox_mgr_root / "SKILL.md").is_file()
    assert (_agent_routine_root(result.home_path, "houmao-memory-mgr") / "SKILL.md").is_file()
    assert (
        _agent_routine_root(result.home_path, "houmao-adv-usage-pattern") / "SKILL.md"
    ).is_file()
    assert filesystem_path.is_file()
    assert stalwart_path.is_file()
    assert not (skills_root / "mailbox").exists()
    assert not (agent_def_dir / ".claude").exists()
    assert "houmao-agent-entrypoint->houmao-shared-routines->agent-email-comms" in processing_skill
    assert (
        "installed Houmao skill "
        "`houmao-agent-entrypoint->houmao-shared-routines->agent-email-comms`" in processing_skill
    )
    assert (
        "current prompt or recent mailbox context already provides the exact current gateway base URL"
        in (gateway_skill)
    )
    assert "references/root-selection.md" in mailbox_mgr_skill
    assert "For notifier-driven shared mailbox gateway work" in filesystem_skill
    assert (
        "use `houmao-agent-entrypoint->houmao-shared-routines->process-emails-via-gateway`"
        in filesystem_skill
    )
    assert "$GATEWAY_BASE_URL/v1/mail/status" in curl_reference
    assert "houmao-mgr agents self mail resolve-live | jq -r '.gateway.base_url'" in curl_reference
    assert "pixi run houmao-mgr agents self mail resolve-live" not in curl_reference
    assert '"schema_version":1,"message_refs":["<opaque message_ref>"]' in curl_reference

    assert (
        "houmao-agent-entrypoint->houmao-shared-routines->process-emails-via-gateway"
        in filesystem_skill
    )
    assert "houmao-agent-email-comms" not in filesystem_skill
    assert "gateway: null" in filesystem_skill
    assert "filesystem" in filesystem_skill
    assert "pixi run houmao-mgr agents self mail resolve-live" not in filesystem_skill
    assert (
        "houmao-agent-entrypoint->houmao-shared-routines->process-emails-via-gateway"
        in stalwart_skill
    )
    assert "houmao-agent-email-comms" not in stalwart_skill
    assert "gateway: null" in stalwart_skill
    assert "stalwart" in stalwart_skill
    assert "pixi run houmao-mgr agents self mail resolve-live" not in stalwart_skill


def test_load_brain_recipe_rejects_legacy_recipe_shape(tmp_path: Path) -> None:
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

    with pytest.raises(BuildError, match="Rewrite this file using the current preset fields"):
        load_brain_recipe(recipe_path)


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
            mailbox=FilesystemMailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="HOUMAO-research",
                address="HOUMAO-research@agents.localhost",
                filesystem_root="shared-mail",
            ),
            home_id="home-mailbox-001",
        )
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["mailbox"] == {
        "transport": "filesystem",
        "principal_id": "HOUMAO-research",
        "address": "HOUMAO-research@agents.localhost",
        "filesystem_root": "shared-mail",
    }


def test_build_brain_home_skips_missing_optional_credential_file(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    (agent_def_dir / "tools/codex/auth/personal-a/files/auth.json").unlink()

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

    adapter_path = agent_def_dir / "tools/codex/adapter.yaml"
    adapter_text = adapter_path.read_text(encoding="utf-8").replace(
        "required: false",
        "required: true",
    )
    adapter_path.write_text(adapter_text, encoding="utf-8")
    (agent_def_dir / "tools/codex/auth/personal-a/files/auth.json").unlink()

    with pytest.raises(BuildError, match="Missing auth file"):
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
            operator_prompt_mode="as_is",
        )
    )

    settings_path = result.home_path / "settings.json"
    assert settings_path.is_file()
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    assert payload["skipDangerousModePermissionPrompt"] is True
    assert (result.home_path / "claude_state.template.json").is_file()
    assert (result.home_path / ".credentials.json").is_file()
    assert (result.home_path / ".claude.json").is_file()
    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    assert 'exec claude "$@"' in launch_script
    assert "export ANTHROPIC_API_KEY=sk-test" in launch_script
    assert "export CLAUDE_CODE_OAUTH_TOKEN=oauth-token-test" in launch_script
    assert "export ANTHROPIC_BASE_URL=https://api.example.test" in launch_script
    assert "ENV_FILE=" not in launch_script
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["launch_policy"]["operator_prompt_mode"] == "as_is"


def test_build_brain_home_routes_unattended_launch_helper_through_shared_policy_cli(
    tmp_path: Path,
) -> None:
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
            home_id="claude-home-unattended",
            operator_prompt_mode="unattended",
        )
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")

    assert manifest["launch_policy"]["operator_prompt_mode"] == "unattended"
    assert "houmao.agents.launch_policy.cli" in launch_script
    assert "--requested-operator-prompt-mode unattended" in launch_script
    assert "--backend raw_launch" in launch_script


def test_build_brain_home_projects_kimi_oauth_files_and_skills(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_kimi_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="kimi",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="oauth",
            home_id="kimi-home-oauth",
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert (result.home_path / "skills/skill-a").is_symlink()
    assert (result.home_path / f"skills/{SYSTEM_SKILL_AGENT_ENTRYPOINT}/SKILL.md").is_file()
    assert (_agent_routine_root(result.home_path, "houmao-ext-graphing") / "SKILL.md").is_file()
    config_payload = tomllib.loads((result.home_path / "config.toml").read_text(encoding="utf-8"))
    assert config_payload["default_model"] == "kimi-code/default"
    assert config_payload["extra_skill_dirs"] == [str((result.home_path / "skills").resolve())]
    assert (result.home_path / "credentials/kimi-code.json").read_text(encoding="utf-8") == (
        '{"access_token": "secret"}\n'
    )
    assert "export KIMI_CODE_HOME=" in launch_script
    assert "KIMI_MODEL_API_KEY" not in launch_script
    projected_destinations = [
        Path(item["destination"]).relative_to(result.home_path).as_posix()
        for item in manifest["credentials"]["projected_files"]
    ]
    assert projected_destinations == [
        "config.toml",
        "credentials/kimi-code.json",
    ]
    kimi_extra_skill_dirs = manifest["runtime"]["launch_contract"]["construction_provenance"][
        "kimi_extra_skill_dirs"
    ]
    assert kimi_extra_skill_dirs["projected_skill_root"] == str(
        (result.home_path / "skills").resolve()
    )
    assert kimi_extra_skill_dirs["added"] is True
    assert kimi_extra_skill_dirs["value"] == [str((result.home_path / "skills").resolve())]


@pytest.mark.parametrize(
    ("profile_policy", "expected_public_skill_names"),
    [
        (SystemSkillSelectionPolicy(mode="none"), ()),
        (
            SystemSkillSelectionPolicy(
                mode="replace",
                pack_ids=(SYSTEM_SKILL_PACK_AGENT,),
            ),
            (SYSTEM_SKILL_AGENT_ENTRYPOINT,),
        ),
    ],
)
def test_build_brain_home_projects_required_auto_skill_independent_from_system_skill_policy(
    tmp_path: Path,
    profile_policy: SystemSkillSelectionPolicy,
    expected_public_skill_names: tuple[str, ...],
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_kimi_repo(agent_def_dir)
    prompt_text = "Use this Houmao role prompt as standing instruction."

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="kimi",
            skills=[],
            config_profile="default",
            credential_profile="oauth",
            launch_profile_system_skill_policy=profile_policy,
            required_auto_skill_names=(AUTO_SKILL_SYSTEM_PROMPT,),
            role_prompt_override=prompt_text,
            home_id=f"kimi-home-auto-skill-{profile_policy.mode}",
        )
    )

    managed_skill_root = str((result.home_path / "skills").resolve())
    config_payload = tomllib.loads((result.home_path / "config.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    construction_provenance = manifest["runtime"]["launch_contract"]["construction_provenance"]
    auto_skill_provenance = construction_provenance["auto_skills"]
    system_skill_provenance = construction_provenance["system_skills"]

    assert (result.home_path / f"skills/{AUTO_SKILL_SYSTEM_PROMPT}/SKILL.md").is_file()
    assert config_payload["extra_skill_dirs"] == [managed_skill_root]
    assert construction_provenance["kimi_extra_skill_dirs"] == {
        "path": str(result.home_path / "config.toml"),
        "key_path": ["extra_skill_dirs"],
        "projected_skill_root": managed_skill_root,
        "added": True,
        "value": [managed_skill_root],
    }
    assert auto_skill_provenance["state"] == "projected"
    assert auto_skill_provenance["applied"] is False
    assert auto_skill_provenance["selected_skill_names"] == [AUTO_SKILL_SYSTEM_PROMPT]
    assert auto_skill_provenance["reason"] == AUTO_SKILL_SYSTEM_PROMPT_REASON
    assert auto_skill_provenance["projected_relative_dirs"] == [
        f"skills/{AUTO_SKILL_SYSTEM_PROMPT}"
    ]
    assert auto_skill_provenance["destination_root"] == "skills"
    assert auto_skill_provenance["prompt_reference"] == "brain_manifest.inputs.role_prompt_text"
    assert auto_skill_provenance["prompt_sha256"] == prompt_sha256(prompt_text)
    assert system_skill_provenance["public_skills"] == list(expected_public_skill_names)
    for skill_name in expected_public_skill_names:
        assert (result.home_path / f"skills/{skill_name}/SKILL.md").is_file()
    if not expected_public_skill_names:
        assert not (result.home_path / f"skills/{SYSTEM_SKILL_AGENT_ENTRYPOINT}").exists()


def test_build_brain_home_preserves_kimi_extra_skill_dirs_without_duplicates(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_kimi_repo(agent_def_dir)
    _write(
        agent_def_dir / "tools/kimi/auth/oauth/files/config.toml",
        "\n".join(
            [
                'default_model = "kimi-code/default"',
                'extra_skill_dirs = ["/custom/skills"]',
                "",
                "[ui]",
                'theme = "dark"',
                "",
            ]
        ),
    )

    request = BuildRequest(
        agent_def_dir=agent_def_dir,
        runtime_root=agent_def_dir / "tmp/agents-runtime",
        tool="kimi",
        skills=["skill-a"],
        config_profile="default",
        credential_profile="oauth",
        home_id="kimi-home-extra-skill-dirs",
    )
    first_result = build_brain_home(request)
    second_result = build_brain_home(
        BuildRequest(
            agent_def_dir=request.agent_def_dir,
            runtime_root=request.runtime_root,
            tool=request.tool,
            skills=request.skills,
            config_profile=request.config_profile,
            credential_profile=request.credential_profile,
            home_id=request.home_id,
            reuse_home=True,
        )
    )

    assert second_result.home_path == first_result.home_path
    config_payload = tomllib.loads(
        (second_result.home_path / "config.toml").read_text(encoding="utf-8")
    )
    managed_skill_root = str((second_result.home_path / "skills").resolve())
    assert config_payload["default_model"] == "kimi-code/default"
    assert config_payload["ui"]["theme"] == "dark"
    assert config_payload["extra_skill_dirs"] == ["/custom/skills", managed_skill_root]
    assert config_payload["extra_skill_dirs"].count(managed_skill_root) == 1


def test_build_brain_home_projects_kimi_oauth_model_selection_as_cli_args(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_kimi_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="kimi",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="oauth",
            home_id="kimi-home-oauth-model",
            preset_model_config=ModelConfig(name="kimi-code/kimi-for-coding"),
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    model_selection = manifest["runtime"]["launch_contract"]["model_selection"]

    assert "--launch-arg --model --launch-arg kimi-code/kimi-for-coding" in launch_script
    assert model_selection["provider_cli_args"] == {
        "tool": "kimi",
        "args": ["--model", "kimi-code/kimi-for-coding"],
    }
    assert model_selection["native_projection"]["model"] == {
        "surface": "cli_arg",
        "arg": "--model",
        "value": "kimi-code/kimi-for-coding",
        "cli_args": ["--model", "kimi-code/kimi-for-coding"],
    }


def test_build_brain_home_projects_kimi_env_model_override_through_env(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_kimi_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="kimi",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="env-model",
            home_id="kimi-home-env-model",
            direct_model_config=ModelConfig(name="kimi-code/override"),
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    manifest = yaml.safe_load(manifest_text)
    model_selection = manifest["runtime"]["launch_contract"]["model_selection"]

    assert "export KIMI_MODEL_NAME=kimi-code/override" in launch_script
    assert "export KIMI_MODEL_API_KEY=sk-kimi" in launch_script
    assert "export KIMI_MODEL_BASE_URL=https://kimi.example.test" in launch_script
    assert "NOT_ALLOWLISTED" not in launch_script
    assert "NOT_ALLOWLISTED" not in manifest_text
    assert "sk-kimi" not in manifest_text
    assert model_selection["provider_cli_args"] is None
    assert model_selection["native_projection"]["model"] == {
        "surface": "env",
        "env_var": "KIMI_MODEL_NAME",
        "value": "kimi-code/override",
    }


def test_build_brain_home_supports_launch_overrides(tmp_path: Path) -> None:
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
            home_id="claude-home-interactive",
            launch_overrides=LaunchOverrides(
                args=LaunchArgsSection(mode="replace", values=()),
            ),
            operator_prompt_mode="as_is",
        )
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    assert manifest["schema_version"] == 3
    assert manifest["runtime"]["launch_contract"]["requested_overrides"]["direct"] == {
        "args": {"mode": "replace", "values": []}
    }
    assert 'exec claude "$@"' in launch_script


def test_build_brain_home_persists_recipe_and_direct_launch_override_layers(
    tmp_path: Path,
) -> None:
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
            recipe_path=tmp_path / "recipe.yaml",
            recipe_launch_overrides=LaunchOverrides(
                args=LaunchArgsSection(mode="append", values=("--recipe",)),
                tool_params={"include_partial_messages": True},
            ),
            launch_overrides=LaunchOverrides(
                args=LaunchArgsSection(mode="replace", values=("--direct",)),
            ),
            home_id="claude-home-layered",
        )
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")

    assert manifest["runtime"]["launch_contract"]["adapter_defaults"] == {
        "args": [],
        "tool_params": {},
    }
    assert manifest["runtime"]["launch_contract"]["requested_overrides"]["preset"] == {
        "args": {"mode": "append", "values": ["--recipe"]},
        "tool_params": {"include_partial_messages": True},
    }
    assert manifest["runtime"]["launch_contract"]["requested_overrides"]["direct"] == {
        "args": {"mode": "replace", "values": ["--direct"]}
    }
    assert manifest["runtime"]["launch_contract"]["construction_provenance"]["preset_path"] == str(
        (tmp_path / "recipe.yaml").resolve()
    )
    assert "houmao.agents.launch_policy.cli" in launch_script
    assert "--requested-operator-prompt-mode unattended" in launch_script
    assert "--launch-arg --direct" in launch_script


def test_build_brain_home_persists_launch_profile_provenance_and_role_prompt_override(
    tmp_path: Path,
) -> None:
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
            home_id="claude-home-profiled",
            role_prompt_override="Operate only on Alice-owned repositories.",
            managed_prompt_header={
                "version": 1,
                "enabled": True,
                "resolution_source": "default",
                "stored_policy": None,
                "agent_name": "alice",
                "agent_id": "agent-alice",
            },
            houmao_system_prompt_layout={
                "version": 1,
                "root_tag": "houmao_system_prompt",
                "sections": [{"kind": "managed_header"}],
            },
            launch_profile_provenance={
                "name": "alice",
                "lane": "launch_profile",
                "source_kind": "recipe",
                "source_name": "researcher-claude-default",
            },
        )
    )

    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["inputs"]["role_prompt_text"] == "Operate only on Alice-owned repositories."
    assert manifest["inputs"]["managed_prompt_header"] == {
        "version": 1,
        "enabled": True,
        "resolution_source": "default",
        "stored_policy": None,
        "agent_name": "alice",
        "agent_id": "agent-alice",
    }
    assert manifest["inputs"]["houmao_system_prompt_layout"] == {
        "version": 1,
        "root_tag": "houmao_system_prompt",
        "sections": [{"kind": "managed_header"}],
    }
    assert manifest["runtime"]["launch_contract"]["construction_provenance"]["launch_profile"] == {
        "name": "alice",
        "lane": "launch_profile",
        "source_kind": "recipe",
        "source_name": "researcher-claude-default",
    }


def test_build_brain_home_projects_private_skills_after_registered_skills(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    private_shadow = tmp_path / "private" / "skill-a"
    private_live = tmp_path / "private" / "live-skill"
    _write(private_shadow / "SKILL.md", "# skill-a\n\nPrivate shadow.\n")
    _write(private_live / "SKILL.md", "# live-skill\n\nPrivate live.\n")

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="codex",
            skills=["skill-a", "skill-b"],
            private_skills=(
                PrivateSkillProjection(
                    name="skill-a",
                    source_path=private_shadow,
                    mode="copy",
                ),
                PrivateSkillProjection(
                    name="live-skill",
                    source_path=private_live,
                    mode="symlink",
                ),
            ),
            config_profile="default",
            credential_profile="personal-a",
            home_id="codex-home-private-skills",
        )
    )

    shadow_target = result.home_path / "skills/skill-a"
    live_target = result.home_path / "skills/live-skill"
    assert not shadow_target.is_symlink()
    assert (shadow_target / "SKILL.md").read_text(encoding="utf-8") == (
        "# skill-a\n\nPrivate shadow.\n"
    )
    assert live_target.is_symlink()
    assert live_target.resolve() == private_live
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["runtime"]["launch_contract"]["construction_provenance"][
        "private_skill_projections"
    ] == [
        {
            "name": "skill-a",
            "source_path": str(private_shadow),
            "mode": "copy",
        },
        {
            "name": "live-skill",
            "source_path": str(private_live),
            "mode": "symlink",
        },
    ]


def test_build_brain_home_rejects_missing_private_skill_source(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    with pytest.raises(BuildError, match="Private skill projection source"):
        build_brain_home(
            BuildRequest(
                agent_def_dir=agent_def_dir,
                runtime_root=agent_def_dir / "tmp/agents-runtime",
                tool="codex",
                skills=["skill-a"],
                private_skills=(
                    PrivateSkillProjection(
                        name="missing-private",
                        source_path=tmp_path / "missing-private",
                        mode="copy",
                    ),
                ),
                config_profile="default",
                credential_profile="personal-a",
                home_id="codex-home-missing-private-skill",
            )
        )


def test_build_brain_home_resolves_model_selection_precedence_for_codex(tmp_path: Path) -> None:
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
            home_id="codex-home-model-selection",
            preset_model_config=ModelConfig(
                name="gpt-5.4",
                reasoning=ModelReasoningConfig(level=7),
            ),
            launch_profile_model_config=ModelConfig(
                reasoning=ModelReasoningConfig(level=3),
            ),
            direct_model_config=ModelConfig(
                name="gpt-5.4-nano",
                reasoning=ModelReasoningConfig(level=10),
            ),
        )
    )

    payload = tomllib.loads((result.home_path / "config.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert payload["model"] == "gpt-5.4-nano"
    assert payload["model_reasoning_effort"] == "xhigh"
    assert manifest["runtime"]["launch_contract"]["model_selection"]["codex_cli_config_overrides"][
        "args"
    ] == [
        '--config=model="gpt-5.4-nano"',
        '--config=model_reasoning_effort="xhigh"',
    ]
    assert manifest["runtime"]["launch_contract"]["model_selection"]["resolved"] == {
        "effective": {"name": "gpt-5.4-nano", "reasoning": {"level": 10}},
        "sources": {
            "name": "direct_launch",
            "reasoning_level": "direct_launch",
        },
    }


def test_build_brain_home_projects_codex_reasoning_without_forcing_model(
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
            home_id="codex-home-reasoning-only",
            direct_model_config=ModelConfig(
                reasoning=ModelReasoningConfig(level=2),
            ),
        )
    )

    payload = tomllib.loads((result.home_path / "config.toml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))
    model_selection = manifest["runtime"]["launch_contract"]["model_selection"]

    assert "model" not in payload
    assert payload["model_reasoning_effort"] == "medium"
    assert model_selection["codex_cli_config_overrides"]["args"] == [
        '--config=model_reasoning_effort="medium"',
    ]
    assert model_selection["native_projection"]["reasoning"]["model_name"] is None
    assert model_selection["resolved"] == {
        "effective": {"reasoning": {"level": 2}},
        "sources": {
            "name": None,
            "reasoning_level": "direct_launch",
        },
    }


def test_build_brain_home_projects_claude_model_selection(tmp_path: Path) -> None:
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
            home_id="claude-home-model-selection",
            operator_prompt_mode="as_is",
            preset_model_config=ModelConfig(
                name="claude-sonnet-4-5",
                reasoning=ModelReasoningConfig(level=10),
            ),
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    settings_payload = json.loads((result.home_path / "settings.json").read_text(encoding="utf-8"))
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert "export ANTHROPIC_MODEL=claude-sonnet-4-5" not in launch_script
    assert "--model claude-sonnet-4-5 --effort high" in launch_script
    assert settings_payload["effortLevel"] == "high"
    assert manifest["runtime"]["launch_contract"]["model_selection"]["provider_cli_args"] == {
        "tool": "claude",
        "args": ["--model", "claude-sonnet-4-5", "--effort", "high"],
    }
    assert manifest["runtime"]["launch_contract"]["model_selection"]["native_projection"][
        "model"
    ] == {
        "surface": "cli_arg",
        "arg": "--model",
        "value": "claude-sonnet-4-5",
        "cli_args": ["--model", "claude-sonnet-4-5"],
    }
    assert manifest["runtime"]["launch_contract"]["model_selection"]["native_projection"][
        "reasoning"
    ] == {
        "effective_level": 3,
        "tool": "claude",
        "tool_version": None,
        "requested_level": 10,
        "model_name": "claude-sonnet-4-5",
        "saturated": True,
        "off_requested": False,
        "native_scale": "effortLevel",
        "native_value": "high",
        "native_settings": [
            {
                "native_scale": "effortLevel",
                "native_value": "high",
                "projection_target": {
                    "surface": "json",
                    "path": "settings.json",
                    "key_path": ["effortLevel"],
                },
            }
        ],
        "projection_target": {
            "surface": "json",
            "path": "settings.json",
            "key_path": ["effortLevel"],
        },
        "cli_args": ["--effort", "high"],
    }


def test_claude_tool_adapter_allowlist_and_file_mappings_include_vendor_auth_surfaces() -> None:
    agent_def_dir = Path(__file__).resolve().parents[2] / "fixtures" / "plain-agent-def"
    adapter = _load_tool_adapter(agent_def_dir / "tools" / "claude" / "adapter.yaml")

    allowlist = set(adapter.credential_env_allowlist)
    assert {
        "CLAUDE_CODE_OAUTH_TOKEN",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    }.issubset(allowlist)
    file_mappings = {mapping.source: mapping.destination for mapping in adapter.auth_file_mappings}
    assert file_mappings[".credentials.json"] == ".credentials.json"
    assert file_mappings[".claude.json"] == ".claude.json"
    assert file_mappings["claude_state.template.json"] == "claude_state.template.json"


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
setup_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
auth_projection:
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
        ("missing_config", "Missing setup bundle"),
        ("missing_creds", "Missing auth bundle"),
    ],
)
def test_build_brain_home_validation_errors(tmp_path: Path, mutation: str, message: str) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)

    if mutation == "missing_adapter":
        (agent_def_dir / "tools/codex/adapter.yaml").unlink()
    elif mutation == "unknown_skill":
        requested_skill = "missing-skill"
    else:
        requested_skill = "skill-a"

    if mutation == "missing_config":
        (agent_def_dir / "tools/codex/setups/default").rename(
            agent_def_dir / "tools/codex/setups/default.bak"
        )
    if mutation == "missing_creds":
        (agent_def_dir / "tools/codex/auth/personal-a").rename(
            agent_def_dir / "tools/codex/auth/personal-a.bak"
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
