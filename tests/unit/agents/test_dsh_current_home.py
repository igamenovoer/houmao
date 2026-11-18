"""Verify current-home consumption preserves external edits and native precedence."""

import json
from pathlib import Path

import pytest

from houmao.agents.dsh_configuration import (
    DshConfigurationError,
    DshEffectiveToolParams,
    load_dsh_home,
    prepare_dsh_home,
)


def _setup(adapter: str = "deepseek") -> DshEffectiveToolParams:
    """Return two deliberately different models with explicit synthetic routing."""

    return DshEffectiveToolParams.from_mapping(
        {
            "provider": {
                "adapter": adapter,
                "protocol": "messages" if adapter == "deepseek" else "openai-completions",
                "route": "deepseek-official" if adapter == "deepseek" else "current-generic",
                "base_url_env": "CURRENT_ENDPOINT",
                "api_key_env": "CURRENT_API_KEY",
            },
            "models": [
                {
                    "id": "first",
                    "context_window": 8192,
                    "max_output_tokens": 128,
                    "reasoning_efforts": False,
                },
                {
                    "id": "second",
                    "context_window": 16384,
                    "max_output_tokens": 256,
                    "reasoning_efforts": {"off": "off", "high": "high"},
                },
            ],
        }
    )


def _environment() -> dict[str, str]:
    """Supply explicit selected references and a conflicting ambient key."""

    return {
        "PATH": "/usr/bin",
        "CURRENT_ENDPOINT": "http://127.0.0.1:1/v1",
        "CURRENT_API_KEY": "synthetic-selected-only",
        "OPENAI_API_KEY": "synthetic-ambient-never-selected",
        "DSH_PERMISSION_MODE": "danger-full-access",
    }


def _snapshot(home: Path) -> dict[str, bytes]:
    """Capture persistent home bytes so reads cannot silently repair configuration."""

    return {str(p.relative_to(home)): p.read_bytes() for p in home.rglob("*") if p.is_file()}


def test_load_preserves_current_material_and_does_not_reapply_setup(tmp_path: Path) -> None:
    """Current home edits survive loading even when launch defaults differ."""

    prepared = prepare_dsh_home(
        tmp_path, _setup(), _environment(), "original launch role", selected_model="first"
    )
    prepared.role_path.write_text("externally edited role")
    patch = json.loads(prepared.patch_path.read_text())
    next(row for row in patch if row.get("id") == "acp")["config"]["model"] = "second"
    next(row for row in patch if row.get("id") == "skill-filesystem")["config"]["watch"] = True
    patch.append({"insert": [{"id": "native-extra", "name": "operator-owned-plugin"}]})
    prepared.patch_path.write_text(json.dumps(patch))
    (tmp_path / "houmao-empty-credentials.yaml").write_text("operator-owned native config\n")
    before = _snapshot(tmp_path)
    loaded = load_dsh_home(tmp_path, _setup(), _environment())
    assert _snapshot(tmp_path) == before
    assert loaded.patch_path == prepared.patch_path
    assert loaded.role_path.read_text() == "externally edited role"
    assert loaded.model == ("deepseek-official", "second")
    assert loaded.reasoning_effort == "off"
    assert loaded.invocation_patch == ()
    assert loaded.environment["CURRENT_API_KEY"] == "synthetic-selected-only"
    assert "OPENAI_API_KEY" not in loaded.environment
    assert "DSH_PERMISSION_MODE" not in loaded.environment


@pytest.mark.parametrize(
    "removed",
    ["houmao-role.txt", "houmao-profile.patch.json", "houmao-empty-credentials.yaml", "sessions"],
)
def test_load_fails_instead_of_repairing_missing_material(tmp_path: Path, removed: str) -> None:
    """An invocation never turns removal into manifest-backed reconstruction."""

    prepare_dsh_home(tmp_path, _setup(), _environment(), "role", selected_model="first")
    path = tmp_path / removed
    if path.is_dir():
        path.rmdir()
    else:
        path.unlink()
    before = _snapshot(tmp_path)
    with pytest.raises(DshConfigurationError):
        load_dsh_home(tmp_path, _setup(), _environment())
    assert not path.exists()
    assert _snapshot(tmp_path) == before


def test_explicit_model_controls_are_detached_invocation_material(tmp_path: Path) -> None:
    """A selected model/effort changes transient controls without rewriting home."""

    prepared = prepare_dsh_home(tmp_path, _setup(), _environment(), "role", selected_model="first")
    patch = json.loads(prepared.patch_path.read_text())
    adapter = next(row for row in patch if row.get("id") == "llm-deepseek")
    adapter["config"]["baseURL"] = "http://127.0.0.1:2/edited"
    prepared.patch_path.write_text(json.dumps(patch))
    before = _snapshot(tmp_path)
    loaded = load_dsh_home(
        tmp_path, _setup(), _environment(), selected_model="second", reasoning_level="high"
    )
    assert _snapshot(tmp_path) == before
    assert loaded.model == ("deepseek-official", "second")
    assert loaded.reasoning_effort == "high"
    overrides = {row["id"]: row["config"] for row in loaded.invocation_patch}
    assert overrides["llm-deepseek"]["baseURL"] == "http://127.0.0.1:2/edited"
    assert overrides["llm-deepseek"]["maxTokens"] == 256
    assert overrides["llm-deepseek"]["defaultContextWindow"] == 16384
    assert overrides["llm-deepseek"]["reasoningEffort"] == "high"
    assert overrides["llm-deepseek"]["thinking"] == "enabled"
    assert overrides["acp"]["model"] == "second"
    default = load_dsh_home(tmp_path, _setup(), _environment())
    assert default.model == ("deepseek-official", "first")
    assert default.reasoning_effort == "off"
    assert default.invocation_patch == ()


def test_current_mcp_declarations_are_used_without_a_launch_snapshot(tmp_path: Path) -> None:
    """The caller supplies the setup it just read, including current ACP MCP values."""

    setup = _setup()
    prepare_dsh_home(tmp_path, setup, _environment(), "role", selected_model="first")
    document = setup.model_dump(mode="json")
    document["mcp_servers"] = [
        {
            "name": "added-after-launch",
            "command": "/usr/bin/true",
            "args": [],
            "env": [{"name": "CUSTOM", "env_ref": "CURRENT_MCP_REF"}],
        },
    ]
    current = DshEffectiveToolParams.from_mapping(document)
    before = _snapshot(tmp_path)
    loaded = load_dsh_home(
        tmp_path, current, _environment(), credential_environment={"CURRENT_MCP_REF": "synthetic"}
    )
    assert loaded.mcp_servers == (
        {
            "name": "added-after-launch",
            "command": "/usr/bin/true",
            "args": [],
            "env": [{"name": "CUSTOM", "value": "synthetic"}],
        },
    )
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize("adapter", ["deepseek", "pi-ai"])
def test_reasoning_only_override_uses_current_materialized_model(
    tmp_path: Path, adapter: str
) -> None:
    """A current native default supplies reasoning-only request model precedence."""

    setup = _setup(adapter)
    prepared = prepare_dsh_home(
        tmp_path, setup, _environment(), "role", selected_model="second", reasoning_level="off"
    )
    before = _snapshot(tmp_path)
    current = load_dsh_home(tmp_path, setup, _environment(), reasoning_level="high")
    assert current.model == (setup.route, "second")
    assert current.reasoning_effort == "high"
    assert all(row["id"] != "acp" for row in current.invocation_patch)
    assert _snapshot(tmp_path) == before
    default = load_dsh_home(tmp_path, setup, _environment())
    assert default.model == (setup.route, "second")
    assert default.reasoning_effort == "off"
    assert default.invocation_patch == ()
    assert prepared.patch_path.is_file()


@pytest.mark.parametrize("adapter", ["deepseek", "pi-ai"])
def test_nonreasoning_override_drops_previous_native_reasoning_default(
    tmp_path: Path, adapter: str
) -> None:
    """A nonreasoning model cannot inherit the previous model's positive effort."""

    setup = _setup(adapter)
    prepare_dsh_home(
        tmp_path, setup, _environment(), "role", selected_model="second", reasoning_level="high"
    )
    before = _snapshot(tmp_path)
    current = load_dsh_home(tmp_path, setup, _environment(), selected_model="first")
    assert current.model == (setup.route, "first")
    configs = {row["id"]: row["config"] for row in current.invocation_patch}
    if adapter == "deepseek":
        assert configs["llm-deepseek"]["thinking"] == "disabled"
        assert configs["llm-deepseek"]["reasoningEffort"] == "off"
    else:
        assert "reasoning" not in configs["llm-pi-ai"]["providers"][setup.route]
    assert _snapshot(tmp_path) == before
