from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest
import yaml

from houmao.agents.brain_builder import (
    BuildError,
    BuildRequest,
    _load_tool_adapter,
    build_brain_home,
    load_brain_recipe,
)
from houmao.agents.launch_overrides import LaunchArgsSection, LaunchOverrides
from houmao.agents.mailbox_runtime_models import FilesystemMailboxDeclarativeConfig
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig
from houmao.agents.system_skills import load_system_skill_install_state


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
    _write(agent_def_dir / "tools/codex/setups/default/config.toml", "model='x'\n")
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


def _seed_gemini_repo(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "tools/gemini/adapter.yaml",
        """
schema_version: 1
tool: gemini
home_selector:
  env_var: GEMINI_CLI_HOME
launch:
  executable: gemini
  args: []
  default_tool_params: {}
  metadata:
    tool_params: {}
  env_injection:
    mode: export_from_env_file
setup_projection:
  destination: .gemini
skills_projection:
  destination: .gemini/skills
  mode: symlink
auth_projection:
  files_dir: files
  file_mappings:
    - source: oauth_creds.json
      destination: .gemini/oauth_creds.json
      mode: symlink
      required: false
  env:
    source: env/vars.env
    allowlist:
      - GEMINI_API_KEY
      - GOOGLE_GEMINI_BASE_URL
      - GOOGLE_GENAI_USE_GCA
""".strip()
        + "\n",
    )
    _write(agent_def_dir / "skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "tools/gemini/setups/default/settings.json", "{}\n")
    _write(agent_def_dir / "tools/gemini/auth/oauth-only/env/vars.env", "\n")
    _write(
        agent_def_dir / "tools/gemini/auth/oauth-only/files/oauth_creds.json",
        '{"refresh_token": "oauth-only"}\n',
    )
    _write(
        agent_def_dir / "tools/gemini/auth/hybrid/env/vars.env",
        "\n".join(
            [
                "GEMINI_API_KEY=gm-test-123",
                "GOOGLE_GEMINI_BASE_URL=https://gemini.example.test",
            ]
        )
        + "\n",
    )
    _write(
        agent_def_dir / "tools/gemini/auth/hybrid/files/oauth_creds.json",
        '{"refresh_token": "hybrid"}\n',
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
    visible_gateway_skill = home / "skills/houmao-agent-email-comms/SKILL.md"
    visible_processing_skill = home / "skills/houmao-process-emails-via-gateway/SKILL.md"
    visible_mailbox_mgr_skill = home / "skills/houmao-mailbox-mgr/SKILL.md"
    assert visible_processing_skill.is_file()
    assert visible_gateway_skill.is_file()
    assert visible_mailbox_mgr_skill.is_file()
    assert (home / "skills/houmao-manage-specialist/SKILL.md").is_file()
    assert (home / "skills/houmao-manage-credentials/SKILL.md").is_file()
    assert (home / "skills/houmao-manage-agent-definition/SKILL.md").is_file()
    assert (home / "skills/houmao-agent-messaging/SKILL.md").is_file()
    assert (home / "skills/houmao-agent-gateway/SKILL.md").is_file()
    assert not (home / "skills/.system/mailbox").exists()
    assert not (home / "skills/skill-b").exists()
    install_state = load_system_skill_install_state(tool="codex", home_path=home)
    assert install_state is not None
    assert tuple(record.name for record in install_state.installed_skills) == (
        "houmao-process-emails-via-gateway",
        "houmao-agent-email-comms",
        "houmao-mailbox-mgr",
        "houmao-manage-specialist",
        "houmao-manage-credentials",
        "houmao-manage-agent-definition",
        "houmao-agent-messaging",
        "houmao-agent-gateway",
    )

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


def test_build_brain_home_copies_selected_setup_bundle_verbatim(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_repo(agent_def_dir)
    custom_setup = (
        """
model = "gpt-5.4"
model_provider = "yunwu-openai"

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

    processing_skill = (
        result.home_path / "skills/houmao-process-emails-via-gateway/SKILL.md"
    ).read_text(encoding="utf-8")
    gateway_skill = (result.home_path / "skills/houmao-agent-email-comms/SKILL.md").read_text(
        encoding="utf-8"
    )
    mailbox_mgr_skill = (result.home_path / "skills/houmao-mailbox-mgr/SKILL.md").read_text(
        encoding="utf-8"
    )

    assert "houmao-process-emails-via-gateway" in processing_skill
    assert "metadata-first triage" in processing_skill
    assert "stalled or interrupted" in processing_skill
    assert "It is acceptable to defer unrelated unread emails" in processing_skill
    assert "Mark only the successfully processed selected emails read." in processing_skill
    assert "wait for the next notification" in processing_skill
    assert "Do not switch to `houmao-mgr agents mail resolve-live`" in processing_skill
    assert "pixi run houmao-mgr agents mail resolve-live" not in processing_skill
    assert "houmao-agent-email-comms" in gateway_skill
    assert "houmao-process-emails-via-gateway" in gateway_skill
    assert (
        "If the current prompt or recent mailbox context already provides the exact current gateway base URL"
        in gateway_skill
    )
    assert "houmao-mgr agents mail resolve-live" in gateway_skill
    assert "pixi run houmao-mgr agents mail resolve-live" not in gateway_skill
    assert "The trigger word `houmao` is intentional." in gateway_skill
    assert "houmao-mgr mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr project mailbox ..." in mailbox_mgr_skill
    assert "houmao-mgr agents mailbox ..." in mailbox_mgr_skill


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
    processing_skill = (skills_root / "houmao-process-emails-via-gateway/SKILL.md").read_text(
        encoding="utf-8"
    )
    gateway_skill = (skills_root / "houmao-agent-email-comms/SKILL.md").read_text(encoding="utf-8")
    mailbox_mgr_skill = (skills_root / "houmao-mailbox-mgr/SKILL.md").read_text(encoding="utf-8")
    filesystem_skill = (
        skills_root / "houmao-agent-email-comms/transports/filesystem.md"
    ).read_text(encoding="utf-8")
    stalwart_skill = (skills_root / "houmao-agent-email-comms/transports/stalwart.md").read_text(
        encoding="utf-8"
    )
    curl_reference = (
        skills_root / "houmao-agent-email-comms/references/curl-examples.md"
    ).read_text(encoding="utf-8")

    assert (skills_root / "houmao-process-emails-via-gateway/SKILL.md").is_file()
    assert (skills_root / "houmao-agent-email-comms/SKILL.md").is_file()
    assert (skills_root / "houmao-mailbox-mgr/SKILL.md").is_file()
    assert (skills_root / "houmao-agent-email-comms/transports/filesystem.md").is_file()
    assert (skills_root / "houmao-agent-email-comms/transports/stalwart.md").is_file()
    assert not (skills_root / "mailbox").exists()
    assert not (agent_def_dir / ".claude").exists()
    assert "houmao-agent-email-comms" in processing_skill
    assert "installed Houmao skill `houmao-agent-email-comms`" in processing_skill
    assert (
        "current prompt or recent mailbox context already provides the exact current gateway base URL"
        in (gateway_skill)
    )
    assert "references/root-selection.md" in mailbox_mgr_skill
    assert "For notifier-driven shared mailbox gateway work" in filesystem_skill
    assert "use `houmao-process-emails-via-gateway`" in filesystem_skill
    assert "$GATEWAY_BASE_URL/v1/mail/status" in curl_reference
    assert "houmao-mgr agents mail resolve-live | jq -r '.gateway.base_url'" in curl_reference
    assert "pixi run houmao-mgr agents mail resolve-live" not in curl_reference
    assert '"schema_version":1,"message_ref":"<opaque message_ref>","read":true' in curl_reference

    assert "houmao-process-emails-via-gateway" in filesystem_skill
    assert "houmao-agent-email-comms" not in filesystem_skill
    assert "gateway: null" in filesystem_skill
    assert "filesystem" in filesystem_skill
    assert "pixi run houmao-mgr agents mail resolve-live" not in filesystem_skill
    assert "houmao-process-emails-via-gateway" in stalwart_skill
    assert "houmao-agent-email-comms" not in stalwart_skill
    assert "gateway: null" in stalwart_skill
    assert "stalwart" in stalwart_skill
    assert "pixi run houmao-mgr agents mail resolve-live" not in stalwart_skill


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


def test_load_brain_recipe_accepts_launch_policy(tmp_path: Path) -> None:
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
launch_policy:
  operator_prompt_mode: unattended
""".strip()
        + "\n",
    )

    recipe = load_brain_recipe(recipe_path)

    assert recipe.operator_prompt_mode == "unattended"


def test_load_brain_recipe_accepts_launch_overrides(tmp_path: Path) -> None:
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
launch_overrides:
  args:
    mode: append
    values:
      - --verbose
  tool_params:
    include_partial_messages: true
""".strip()
        + "\n",
    )

    recipe = load_brain_recipe(recipe_path)

    assert recipe.launch_overrides is not None
    assert recipe.launch_overrides.to_payload() == {
        "args": {"mode": "append", "values": ["--verbose"]},
        "tool_params": {"include_partial_messages": True},
    }


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
  principal_id: HOUMAO-research
  address: HOUMAO-research@agents.localhost
  filesystem_root: shared-mail
""".strip()
        + "\n",
    )

    recipe = load_brain_recipe(recipe_path)

    assert recipe.mailbox == FilesystemMailboxDeclarativeConfig(
        transport="filesystem",
        principal_id="HOUMAO-research",
        address="HOUMAO-research@agents.localhost",
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


def test_build_brain_home_projects_gemini_skills_under_gemini_root_and_injects_oauth_selector(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_gemini_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="gemini",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="oauth-only",
            home_id="gemini-home-oauth",
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert (result.home_path / ".gemini/skills/skill-a").is_symlink()
    assert (result.home_path / ".gemini/skills/houmao-agent-email-comms/SKILL.md").is_file()
    assert (
        result.home_path / ".gemini/skills/houmao-process-emails-via-gateway/SKILL.md"
    ).is_file()
    assert (result.home_path / ".gemini/skills/houmao-agent-gateway/SKILL.md").is_file()
    assert not (result.home_path / ".gemini/skills/mailbox").exists()
    assert (result.home_path / ".gemini/oauth_creds.json").is_symlink()
    assert "export GOOGLE_GENAI_USE_GCA=true" in launch_script
    assert "export GEMINI_API_KEY=" not in launch_script
    assert manifest["runtime"]["launch_contract"]["env_records"] == {"GOOGLE_GENAI_USE_GCA": "true"}


def test_build_brain_home_reuse_removes_legacy_gemini_agents_skill_root(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_gemini_repo(agent_def_dir)

    build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="gemini",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="oauth-only",
            home_id="gemini-home-reuse",
        )
    )

    home_path = agent_def_dir / "tmp/agents-runtime/homes/gemini-home-reuse"
    legacy_skill = home_path / ".agents/skills/skill-a/SKILL.md"
    legacy_note = home_path / ".agents/README.md"
    legacy_skill.parent.mkdir(parents=True, exist_ok=True)
    legacy_skill.write_text("legacy skill\n", encoding="utf-8")
    legacy_note.parent.mkdir(parents=True, exist_ok=True)
    legacy_note.write_text("keep parent if it has other content\n", encoding="utf-8")

    build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="gemini",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="oauth-only",
            home_id="gemini-home-reuse",
            reuse_home=True,
        )
    )

    assert not (home_path / ".agents/skills").exists()
    assert (home_path / ".agents/README.md").is_file()
    assert (home_path / ".gemini/skills/skill-a").is_symlink()


def test_build_brain_home_gemini_preserves_explicit_api_key_and_base_url_with_oauth_file(
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_gemini_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="gemini",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="hybrid",
            home_id="gemini-home-hybrid",
        )
    )

    launch_script = (result.home_path / "launch.sh").read_text(encoding="utf-8")
    manifest = yaml.safe_load(result.manifest_path.read_text(encoding="utf-8"))

    assert "export GEMINI_API_KEY=gm-test-123" in launch_script
    assert "export GOOGLE_GEMINI_BASE_URL=https://gemini.example.test" in launch_script
    assert "GOOGLE_GENAI_USE_GCA=true" not in launch_script
    assert manifest["runtime"]["launch_contract"]["env_records"] == {}


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
    assert manifest["runtime"]["launch_contract"]["construction_provenance"]["launch_profile"] == {
        "name": "alice",
        "lane": "launch_profile",
        "source_kind": "recipe",
        "source_name": "researcher-claude-default",
    }


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
    assert manifest["runtime"]["launch_contract"]["model_selection"]["resolved"] == {
        "effective": {"name": "gpt-5.4-nano", "reasoning": {"level": 10}},
        "sources": {
            "name": "direct_launch",
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

    assert "export ANTHROPIC_MODEL=claude-sonnet-4-5" in launch_script
    assert settings_payload["effortLevel"] == "high"
    assert manifest["runtime"]["launch_contract"]["model_selection"]["native_projection"][
        "reasoning"
    ] == {
        "tool": "claude",
        "tool_version": None,
        "requested_level": 10,
        "model_name": "claude-sonnet-4-5",
        "native_scale": "effortLevel",
        "native_value": "high",
        "clamped": True,
        "projection_target": {
            "surface": "json",
            "path": "settings.json",
            "key_path": ["effortLevel"],
        },
    }


def test_build_brain_home_projects_gemini_model_selection(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "repo"
    agent_def_dir.mkdir(parents=True)
    _seed_gemini_repo(agent_def_dir)

    result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=agent_def_dir / "tmp/agents-runtime",
            tool="gemini",
            skills=["skill-a"],
            config_profile="default",
            credential_profile="oauth-only",
            home_id="gemini-home-model-selection",
            preset_model_config=ModelConfig(
                name="gemini-2.5-flash",
                reasoning=ModelReasoningConfig(level=10),
            ),
        )
    )

    settings_payload = json.loads(
        (result.home_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )

    assert settings_payload["model"]["name"] == "gemini-2.5-flash"
    assert settings_payload["modelConfigs"]["customOverrides"][0] == {
        "match": {"model": "gemini-2.5-flash"},
        "modelConfig": {
            "generateContentConfig": {
                "thinkingConfig": {
                    "thinkingBudget": 16384,
                }
            }
        },
    }


def test_claude_tool_adapter_allowlist_and_file_mappings_include_vendor_auth_surfaces() -> None:
    agent_def_dir = Path(__file__).resolve().parents[2] / "fixtures" / "agents"
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
