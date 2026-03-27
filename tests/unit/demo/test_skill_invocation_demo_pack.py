"""Unit tests for the skill-invocation demo-pack helpers."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _helper_module() -> ModuleType:
    """Load the pack-local helper module from disk."""

    helper_path = (
        _repo_root()
        / "scripts"
        / "demo"
        / "skill-invocation-demo-pack"
        / "scripts"
        / "tutorial_pack_helpers.py"
    )
    module_name = "skill_invocation_demo_pack_helpers"
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


HELPERS = _helper_module()
PACK_DIR = _repo_root() / "scripts" / "demo" / "skill-invocation-demo-pack"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    """Write one JSON payload to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_tracked_demo_parameters_parse_and_render_marker_paths() -> None:
    """The tracked parameter file should expose the documented schema."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    layout = HELPERS.build_demo_layout(demo_output_dir=Path("/tmp/skill-demo"))

    assert parameters.backend == "local_interactive"
    assert parameters.project_fixture == "tests/fixtures/dummy-projects/mailbox-demo-python"
    assert (
        parameters.tool_lanes["claude"].blueprint
        == "tests/fixtures/agents/roles/skill-invocation-demo/presets/claude/default.yaml"
    )
    assert (
        parameters.tool_lanes["codex"].blueprint
        == "tests/fixtures/agents/roles/skill-invocation-demo/presets/codex/default.yaml"
    )
    assert parameters.prompt.trigger_phrase == "workspace probe handshake"
    assert HELPERS.render_prompt_path(parameters, layout=layout) == Path(
        "/tmp/skill-demo/inputs/trigger_prompt.md"
    )
    assert HELPERS.render_marker_path(
        parameters,
        project_workdir=Path("/tmp/skill-demo/project"),
    ) == Path("/tmp/skill-demo/project/.houmao-skill-invocation-demo/markers/workspace-probe.json")


def test_ensure_project_workdir_from_fixture_creates_managed_repo(tmp_path: Path) -> None:
    """Dummy-project provisioning should create a managed standalone git repo."""

    parameters = HELPERS.load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    fixture_dir = HELPERS.resolve_repo_relative_path(
        parameters.project_fixture,
        repo_root=_repo_root(),
    )
    project_workdir = tmp_path / "demo-output" / "project"

    result = HELPERS.ensure_project_workdir_from_fixture(
        repo_root=_repo_root(),
        project_fixture=fixture_dir,
        project_workdir=project_workdir,
        allow_reprovision=False,
    )

    metadata_path = project_workdir / ".houmao-demo-project.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert result == project_workdir.resolve()
    assert metadata["managed_by"] == "skill-invocation-demo-pack"
    assert metadata["fixture_dir"] == str(fixture_dir.resolve())
    assert HELPERS.is_standalone_git_repo(project_workdir=project_workdir) is True


def test_start_demo_uses_selected_lane_and_shadow_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Start orchestration should use the selected blueprint and `shadow_only`."""

    calls: list[list[str]] = []

    def fake_preflight_selected_tool(
        *,
        repo_root: Path,
        agent_def_dir: Path,
        parameters: object,
        tool: str,
    ) -> object:
        del repo_root, agent_def_dir, parameters
        return HELPERS.LanePreflight(
            selected_tool=tool,
            blueprint_path=tmp_path / "agent-defs" / "blueprints" / f"{tool}.yaml",
            brain_recipe_path=tmp_path / "agent-defs" / "recipes" / f"{tool}.yaml",
            role_name="skill-invocation-demo",
            tool_adapter_path=tmp_path / "agent-defs" / "tool-adapters" / f"{tool}.yaml",
            launch_executable=f"/usr/bin/{tool}",
            config_profile="default",
            credential_profile="personal-a-default",
            credential_profile_dir=tmp_path / "creds" / tool,
            credential_env_path=tmp_path / "creds" / tool / "env" / "vars.env",
            selected_allowlisted_env_keys=("API_KEY",),
            required_credential_paths=(tmp_path / "creds" / tool / "files" / "required.txt",),
            optional_credential_paths=(),
            usable_auth_json=(tool == "codex"),
        )

    def fake_resolve_cao_context(
        *,
        repo_root: Path,
        demo_output_dir: Path,
        cao_base_url: str,
    ) -> dict[str, object]:
        del repo_root, demo_output_dir, cao_base_url
        return {
            "managed": True,
            "base_url": "http://localhost:9889",
            "profile_store": str(tmp_path / "cao-profile-store"),
            "ownership_verified": True,
            "healthy": True,
            "started_current_run": True,
            "reused_existing_process": False,
            "message": "started",
        }

    def fake_run_realm_controller_json(
        *,
        repo_root: Path,
        args: list[str],
        stdout_path: Path,
        env: dict[str, str] | None = None,
    ) -> dict[str, object]:
        del repo_root, stdout_path, env
        calls.append(list(args))
        command = args[0]
        if command == "build-brain":
            return {
                "manifest_path": str(
                    tmp_path / "demo-output" / "runtime" / "manifests" / "agent.yaml"
                )
            }
        if command == "start-session":
            return {
                "session_manifest": str(
                    tmp_path / "demo-output" / "runtime" / "sessions" / "agent.json"
                ),
                "agent_identity": "AGENTSYS-skill-invocation-demo-codex",
                "backend": "local_interactive",
                "tool": "codex",
                "tmux_session_name": "tmux-skill-demo-codex",
                "job_dir": str(tmp_path / "jobs" / "AGENTSYS-skill-invocation-demo-codex"),
            }
        raise AssertionError(f"unexpected realm-controller command: {args}")

    monkeypatch.setattr(HELPERS, "preflight_selected_tool", fake_preflight_selected_tool)
    monkeypatch.setattr(HELPERS, "_resolve_cao_context", fake_resolve_cao_context)
    monkeypatch.setattr(HELPERS, "_run_realm_controller_json", fake_run_realm_controller_json)

    demo_output_dir = tmp_path / "demo-output"
    state = HELPERS.start_demo(
        repo_root=_repo_root(),
        pack_dir=PACK_DIR,
        demo_output_dir=demo_output_dir,
        parameters_path=PACK_DIR / "inputs" / "demo_parameters.json",
        tool="codex",
        jobs_dir=None,
    )

    build_args, start_args = calls
    project_workdir = demo_output_dir / "project"

    assert state["selected_tool"] == "codex"
    assert state["preflight"]["selected_tool"] == "codex"
    assert (project_workdir / ".houmao-demo-project.json").is_file()
    assert "--preset" in build_args
    assert build_args[build_args.index("--preset") + 1] == str(
        tmp_path / "agent-defs" / "recipes" / "codex.yaml"
    )
    assert start_args[start_args.index("--role") + 1] == "skill-invocation-demo"
    assert start_args[start_args.index("--backend") + 1] == "local_interactive"
    assert start_args[start_args.index("--cao-parsing-mode") + 1] == "shadow_only"
    assert (
        start_args[start_args.index("--agent-identity") + 1]
        == "AGENTSYS-skill-invocation-demo-codex"
    )
    assert start_args[start_args.index("--workdir") + 1] == str(project_workdir)


def test_inspect_and_build_report_capture_watch_coordinates_and_marker_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inspection and report helpers should capture session metadata and probe evidence."""

    demo_output_dir = tmp_path / "demo-output"
    layout = HELPERS.build_demo_layout(demo_output_dir=demo_output_dir)
    parameters_path = PACK_DIR / "inputs" / "demo_parameters.json"
    parameters = HELPERS.load_demo_parameters(parameters_path)
    marker_path = HELPERS.render_marker_path(parameters, project_workdir=layout.project_workdir)
    prompt_path = HELPERS.render_prompt_path(parameters, layout=layout)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(
        (PACK_DIR / "inputs" / "trigger_prompt.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(
        json.dumps(parameters.prompt.expected_marker_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_json(
        layout.prompt_result_path,
        {
            "trigger_phrase": parameters.prompt.trigger_phrase,
            "prompt_path": str(prompt_path),
            "prompt_text": prompt_path.read_text(encoding="utf-8"),
            "event_count": 2,
            "event_kinds": ["submitted", "done"],
            "done_message": str(marker_path.relative_to(layout.project_workdir)),
            "marker_status_after_prompt": {
                "exists": True,
                "valid_json": True,
                "matches_expected": True,
                "observed_payload": parameters.prompt.expected_marker_payload,
            },
        },
    )
    state = {
        "schema_version": 1,
        "demo_id": "skill-invocation-demo-pack",
        "parameters_path": str(parameters_path),
        "demo_output_dir": str(demo_output_dir),
        "project_workdir": str(layout.project_workdir),
        "project_fixture": str(_repo_root() / "tests/fixtures/dummy-projects/mailbox-demo-python"),
        "runtime_root": str(layout.runtime_root),
        "agent_def_dir": str(_repo_root() / "tests/fixtures/agents"),
        "jobs_dir": None,
        "selected_tool": "codex",
        "selected_lane": {
            "blueprint": "tests/fixtures/agents/roles/skill-invocation-demo/presets/codex/default.yaml",
            "agent_identity": "AGENTSYS-skill-invocation-demo-codex",
        },
        "preflight": {
            "selected_tool": "codex",
            "blueprint_path": str(
                _repo_root()
                / "tests/fixtures/agents/roles/skill-invocation-demo/presets/codex/default.yaml"
            ),
            "brain_recipe_path": str(
                _repo_root()
                / "tests/fixtures/agents/roles/skill-invocation-demo/presets/codex/default.yaml"
            ),
            "role_name": "skill-invocation-demo",
            "tool_adapter_path": str(
                _repo_root() / "tests/fixtures/agents/tools/codex/adapter.yaml"
            ),
            "launch_executable": "/usr/bin/codex",
            "config_profile": "default",
            "credential_profile": "personal-a-default",
            "credential_profile_dir": str(
                _repo_root() / "tests/fixtures/agents/tools/codex/auth/personal-a-default"
            ),
            "credential_env_path": str(
                _repo_root()
                / "tests/fixtures/agents/tools/codex/auth/personal-a-default/env/vars.env"
            ),
            "selected_allowlisted_env_keys": ["OPENAI_API_KEY"],
            "required_credential_paths": [],
            "optional_credential_paths": [
                str(
                    _repo_root()
                    / "tests/fixtures/agents/tools/codex/auth/personal-a-default/files/auth.json"
                )
            ],
            "usable_auth_json": True,
        },
        "cao": {
            "managed": True,
            "base_url": "http://localhost:9889",
            "launcher_config_path": str(layout.cao_launcher_config_path),
            "runtime_root": str(layout.cao_runtime_root),
            "home_dir": str(layout.cao_runtime_root / "cao_servers" / "localhost-9889" / "home"),
            "profile_store": str(
                layout.cao_runtime_root
                / "cao_servers"
                / "localhost-9889"
                / "home"
                / ".aws"
                / "cli-agent-orchestrator"
                / "agent-store"
            ),
            "artifact_dir": str(
                layout.cao_runtime_root / "cao_servers" / "localhost-9889" / "launcher"
            ),
            "log_file": str(
                layout.cao_runtime_root
                / "cao_servers"
                / "localhost-9889"
                / "launcher"
                / "cao-server.log"
            ),
            "launcher_result_file": str(
                layout.cao_runtime_root
                / "cao_servers"
                / "localhost-9889"
                / "launcher"
                / "launcher_result.json"
            ),
            "ownership_file": str(
                layout.cao_runtime_root
                / "cao_servers"
                / "localhost-9889"
                / "launcher"
                / "ownership.json"
            ),
            "healthy": True,
            "started_current_run": True,
            "reused_existing_process": False,
            "ownership_verified": True,
            "message": "started",
        },
        "brain_build": {
            "manifest_path": str(layout.runtime_root / "manifests" / "agent.yaml"),
        },
        "session": {
            "session_manifest": str(layout.runtime_root / "sessions" / "agent.json"),
            "agent_identity": "AGENTSYS-skill-invocation-demo-codex",
            "tmux_session_name": "tmux-skill-demo-codex",
            "job_dir": str(
                layout.project_workdir / ".houmao" / "jobs" / "AGENTSYS-skill-invocation-demo-codex"
            ),
        },
        "prompt_path": str(prompt_path),
        "marker_path": str(marker_path),
    }
    _write_json(layout.state_path, state)

    fake_manifest = SimpleNamespace(payload={"schema_version": 3})
    fake_parsed = SimpleNamespace(
        cao=SimpleNamespace(
            session_name="tmux-skill-demo-codex",
            terminal_id="terminal-123",
            tmux_window_name="codex.0",
            parsing_mode="shadow_only",
        )
    )
    monkeypatch.setattr(HELPERS, "load_session_manifest", lambda path: fake_manifest)
    monkeypatch.setattr(
        HELPERS, "parse_session_manifest_payload", lambda payload, source: fake_parsed
    )

    inspection = HELPERS.inspect_demo(parameters_path=parameters_path, state_path=layout.state_path)
    report = HELPERS.build_report(
        output_path=layout.report_path,
        parameters_path=parameters_path,
        state_path=layout.state_path,
    )
    sanitized = HELPERS.sanitize_report(report)

    assert inspection["cao_terminal_id"] == "terminal-123"
    assert inspection["parsing_mode"] == "shadow_only"
    assert inspection["marker_status"]["matches_expected"] is True
    assert report["verification"]["passed"] is True
    assert report["marker"]["observed_payload"] == parameters.prompt.expected_marker_payload
    assert sanitized["selected_tool"] == "<SELECTED_TOOL>"
    assert sanitized["watch"]["cao_terminal_id"] == "<CAO_TERMINAL_ID>"
    assert sanitized["prompt"]["summary"]["event_count"] == "<EVENT_COUNT>"
    assert sanitized == json.loads(
        (PACK_DIR / "expected_report" / "report.json").read_text(encoding="utf-8")
    )
