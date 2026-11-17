"""Keep native refresh separate from saved-manifest relaunch generation and chat policy."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.mark.parametrize("chat_policy", ["default", "exact"])
def test_edited_launch_profile_refresh_and_separate_relaunch_keep_their_boundaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    chat_policy: str,
) -> None:
    """Refresh preserves native edits while explicit relaunch uses saved generation rules."""

    repo = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    configuration = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    endpoint, requests = controlled_messages_server
    config = configuration.resolve_config(
        case="cloud-api",
        client="dsh",
        surface="manager",
        process_env={
            "HOUMAO_TEST_CLOUD_MODEL": "controlled",
            "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "8192",
            "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS": "128",
            "HOUMAO_TEST_CLOUD_DSH_REASONING": "false",
            "DEEPSEEK_API_KEY": "synthetic-local-only",
            "DEEPSEEK_BASE_URL_ANTHROPIC": endpoint,
        },
    )
    run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=str(dsh_executable))
    root = Path(run["run_dir"])
    environment = launch.run_environment(launch.load_run(root))
    project = Path(run["project_dir"])
    prepare.manager_call(
        project,
        [
            "profile",
            "create",
            "--name",
            "refresh-boundary",
            "--specialist",
            "fixture-agent",
            "--headless",
            "--prompt-overlay-mode",
            "append",
            "--prompt-overlay-text",
            "ORIGINAL_PROFILE_PROMPT",
            "--relaunch-chat-session-mode",
            "new",
        ],
        env=environment,
    )

    def profile_launch(project: Path, args: list[str], *, env: dict[str, str]) -> dict[str, Any]:
        """Use the fixture's actual maintained launch route with its selected named profile."""

        if args[:2] == ["agents", "launch"]:
            args = list(args)
            index = args.index("--specialist")
            args[index : index + 2] = ["--profile", "refresh-boundary"]
        return prepare.manager_call(project, args, env=env)

    monkeypatch.setattr(launch, "manager_call", profile_launch)
    try:
        first = launch.launch_run(root, prompt="original conversation marker", timeout=45)
        identity = first["identity"]
        manifest_path = Path(identity["manifest_path"])
        manifest = json.loads(manifest_path.read_text())
        brain_path = Path(manifest["brain_manifest_path"])
        brain_before = brain_path.read_bytes()
        home = Path(manifest["launch_plan"]["home_selector"]["home_path"])
        native_id = manifest["headless"]["session_id"]
        generation = manifest["registry_generation_id"]
        runtime_id = manifest["runtime"]["session_id"]
        role = home / "houmao-role.txt"
        initial_role = role.read_bytes()
        assert b"ORIGINAL_PROFILE_PROMPT" in initial_role
        role.write_text("EXTERNALLY_EDITED_MATERIALIZED_ROLE")
        patch = home / "houmao-profile.patch.json"
        rows = json.loads(patch.read_text())
        next(row for row in rows if row.get("id") == "skill-filesystem")["config"]["watch"] = True
        patch.write_text(json.dumps(rows))
        prepare.manager_call(
            project,
            [
                "profile",
                "set",
                "--name",
                "refresh-boundary",
                "--prompt-overlay-mode",
                "replace",
                "--prompt-overlay-text",
                "EDITED_PROJECT_PROFILE_MUST_NOT_APPLY",
                "--relaunch-chat-session-mode",
                "exact",
                "--relaunch-chat-session-id",
                native_id,
            ],
            env=environment,
        )
        protected = {path: path.read_bytes() for path in (brain_path, role, patch)}
        binding = home / "houmao-native-session.json"
        binding_before = binding.read_bytes()
        journal = next((home / "sessions").rglob("session.v4.jsonl"))
        journal_before = journal.read_bytes()
        scope = ["agents", "single", "--agent-id", identity["agent_id"]]
        with pytest.raises(prepare.ManagedCommandError) as checked:
            prepare.manager_root_call([*scope, "refresh", "--check"], env=environment)
        assert checked.value.payload["freshness"] == "unknown"
        refreshed = prepare.manager_root_call([*scope, "refresh"], env=environment)
        assert refreshed["outcome"] == "automatic"
        assert {path: path.read_bytes() for path in protected} == protected
        assert binding.read_bytes() == binding_before
        assert journal.read_bytes() == journal_before
        unchanged = json.loads(manifest_path.read_text())
        assert unchanged["registry_generation_id"] == generation
        assert unchanged["headless"]["session_id"] == native_id
        assert len(requests) == 1

        selection = (
            ["--chat-session-mode", "exact", "--chat-session-id", native_id]
            if chat_policy == "exact"
            else []
        )
        relaunched = prepare.manager_root_call([*scope, "relaunch", *selection], env=environment)
        assert relaunched["success"] is True
        assert role.read_bytes() == initial_role
        assert brain_path.read_bytes() == brain_before
        regenerated = json.loads(patch.read_text())
        assert not next(row for row in regenerated if row.get("id") == "skill-filesystem")[
            "config"
        ]["watch"]
        after = json.loads(manifest_path.read_text())
        assert after["agent_id"] == manifest["agent_id"]
        assert after["runtime"]["session_id"] == runtime_id
        assert len(requests) == 1, "Explicit headless relaunch must not create a model turn"
        continued = launch.prompt_run(root, prompt="after separate relaunch", timeout=45)
        final = json.loads(Path(continued["identity"]["manifest_path"]).read_text())
        if chat_policy == "exact":
            assert final["headless"]["session_id"] == native_id
            assert "original conversation marker" in json.dumps(requests[-1]["messages"])
        else:
            assert final["headless"]["session_id"] != native_id
            assert "original conversation marker" not in json.dumps(requests[-1]["messages"])
        assert "EDITED_PROJECT_PROFILE_MUST_NOT_APPLY" not in json.dumps(requests[-1]["system"])
        assert len(requests) == 2
    finally:
        launch.stop_run(root)
