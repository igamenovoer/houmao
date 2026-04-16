from __future__ import annotations

from pathlib import Path

import pytest

from houmao.agents.definition_parser import (
    load_agent_catalog,
    parse_agent_preset,
    parse_tool_adapter,
    resolve_agent_preset,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_agent_defs(agent_def_dir: Path) -> None:
    _write(agent_def_dir / "skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "skills/skill-b/SKILL.md", "# skill-b\n")
    _write(agent_def_dir / "roles/gpu-kernel-coder/system-prompt.md", "Prompt\n")
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
  file_mappings: []
  env:
    source: env/vars.env
    allowlist:
      - ANTHROPIC_API_KEY
""".strip()
        + "\n",
    )
    _write(agent_def_dir / "tools/claude/setups/default/settings.json", "{}\n")
    _write(agent_def_dir / "tools/claude/setups/research/settings.json", "{}\n")
    _write(agent_def_dir / "tools/claude/auth/default/env/vars.env", "ANTHROPIC_API_KEY=demo\n")
    _write(agent_def_dir / "tools/claude/auth/kimi-coding/env/vars.env", "ANTHROPIC_API_KEY=demo\n")
    _write(
        agent_def_dir / "presets/gpu-kernel-coder-claude-default.yaml",
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
auth: default
launch:
  prompt_mode: unattended
""".strip()
        + "\n",
    )
    _write(
        agent_def_dir / "presets/gpu-kernel-coder-claude-research.yaml",
        """
role: gpu-kernel-coder
tool: claude
setup: research
skills:
  - skill-a
  - skill-b
auth: kimi-coding
""".strip()
        + "\n",
    )


def test_load_agent_catalog_tracks_setup_and_auth_namespaces(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "agents"
    _seed_agent_defs(agent_def_dir)

    catalog = load_agent_catalog(agent_def_dir)

    assert sorted(catalog.setups["claude"]) == ["default", "research"]
    assert sorted(catalog.auths["claude"]) == ["default", "kimi-coding"]
    assert catalog.tool_adapters["claude"].setup_destination == "."

    default_preset = catalog.presets[
        (agent_def_dir / "presets/gpu-kernel-coder-claude-default.yaml").resolve()
    ]
    assert default_preset.name == "gpu-kernel-coder-claude-default"
    assert default_preset.role_name == "gpu-kernel-coder"
    assert default_preset.tool == "claude"
    assert default_preset.setup == "default"


def test_parse_agent_preset_rejects_unknown_top_level_fields(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills: []
config_profile: default
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="unsupported top-level field"):
        parse_agent_preset(preset_path)


def test_parse_tool_adapter_rejects_legacy_projection_aliases(tmp_path: Path) -> None:
    adapter_path = tmp_path / "tools/claude/adapter.yaml"
    _write(
        adapter_path,
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
    tool_params: {}
  env_injection:
    mode: export_from_env_file
config_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
credential_projection:
  files_dir: files
  file_mappings: []
  env:
    source: env/vars.env
    allowlist: []
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="missing mapping `setup_projection`"):
        parse_tool_adapter(adapter_path)


def test_parse_agent_preset_accepts_gateway_defaults_under_extra(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
extra:
  gateway:
    host: 127.0.0.1
    port: 43123
""".strip()
        + "\n",
    )

    preset = parse_agent_preset(preset_path)

    assert preset.extra["gateway"] == {"host": "127.0.0.1", "port": 43123}
    assert preset.gateway_defaults is not None
    assert preset.gateway_defaults.host == "127.0.0.1"
    assert preset.gateway_defaults.port == 43123


def test_parse_agent_preset_accepts_as_is_prompt_mode(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
launch:
  prompt_mode: as_is
""".strip()
        + "\n",
    )

    preset = parse_agent_preset(preset_path)

    assert preset.operator_prompt_mode == "as_is"


def test_parse_agent_preset_accepts_launch_env_records(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
launch:
  prompt_mode: unattended
  env_records:
    FEATURE_FLAG_X: "1"
    OPENAI_MODEL: gpt-5.4
""".strip()
        + "\n",
    )

    preset = parse_agent_preset(preset_path)

    assert preset.operator_prompt_mode == "unattended"
    assert preset.launch_env_records == {
        "FEATURE_FLAG_X": "1",
        "OPENAI_MODEL": "gpt-5.4",
    }


def test_parse_agent_preset_accepts_unified_model_config(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
launch:
  prompt_mode: unattended
  model:
    name: claude-sonnet-4-5
    reasoning:
      level: 7
""".strip()
        + "\n",
    )

    preset = parse_agent_preset(preset_path)

    assert preset.launch_model_config is not None
    assert preset.launch_model_config.name == "claude-sonnet-4-5"
    assert preset.launch_model_config.reasoning is not None
    assert preset.launch_model_config.reasoning.level == 7


def test_parse_agent_preset_accepts_large_reasoning_level(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
launch:
  model:
    reasoning:
      level: 11
""".strip()
        + "\n",
    )

    preset = parse_agent_preset(preset_path)

    assert preset.launch_model_config is not None
    assert preset.launch_model_config.reasoning is not None
    assert preset.launch_model_config.reasoning.level == 11


def test_parse_agent_preset_rejects_negative_reasoning_level(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
launch:
  model:
    reasoning:
      level: -1
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="non-negative integer"):
        parse_agent_preset(preset_path)


def test_parse_agent_preset_rejects_invalid_gateway_defaults_under_extra(tmp_path: Path) -> None:
    preset_path = tmp_path / "presets/gpu-kernel-coder-claude-default.yaml"
    _write(
        preset_path,
        """
role: gpu-kernel-coder
tool: claude
setup: default
skills:
  - skill-a
extra:
  gateway:
    host: 127.0.0.1
    token: nope
""".strip()
        + "\n",
    )

    with pytest.raises(ValueError, match="invalid extra.gateway"):
        parse_agent_preset(preset_path)


def test_resolve_agent_preset_uses_default_setup_for_bare_role(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "agents"
    _seed_agent_defs(agent_def_dir)
    catalog = load_agent_catalog(agent_def_dir)

    preset = resolve_agent_preset(catalog=catalog, selector="gpu-kernel-coder", tool="claude")

    assert preset.path == (agent_def_dir / "presets/gpu-kernel-coder-claude-default.yaml").resolve()
    assert preset.auth == "default"


def test_resolve_agent_preset_accepts_explicit_preset_path_selector(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "agents"
    _seed_agent_defs(agent_def_dir)
    catalog = load_agent_catalog(agent_def_dir)

    preset = resolve_agent_preset(
        catalog=catalog,
        selector="presets/gpu-kernel-coder-claude-research.yaml",
        tool="claude",
    )

    assert preset.setup == "research"
    assert preset.auth == "kimi-coding"
    assert preset.skills == ["skill-a", "skill-b"]


def test_resolve_agent_preset_rejects_role_setup_shorthand(tmp_path: Path) -> None:
    agent_def_dir = tmp_path / "agents"
    _seed_agent_defs(agent_def_dir)
    catalog = load_agent_catalog(agent_def_dir)

    with pytest.raises(FileNotFoundError, match="Could not resolve preset path"):
        resolve_agent_preset(
            catalog=catalog,
            selector="gpu-kernel-coder/research",
            tool="claude",
        )
