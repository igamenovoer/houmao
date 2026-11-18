"""Exercise real tmux-managed ACP execution and immutable native accounting."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from houmao.agents.dsh_configuration import DshEffectiveToolParams, prepare_dsh_home
from houmao.agents.realm_controller.backends.dsh_acp import DshAcpSession
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RoleInjectionPlan,
)
from houmao.agents.realm_controller.usage_support import UsageService


def _launch_plan(root: Path, executable: Path, endpoint: str) -> tuple[LaunchPlan, Path]:
    """Compose synthetic account inputs for the actual managed runtime envelope."""

    home = root / "dsh-home"
    home.mkdir()
    (home / "skills").mkdir()
    setup_path = root / "tool-params.json"
    setup_path.write_text(
        json.dumps(
            {
                "provider": {
                    "adapter": "deepseek",
                    "protocol": "messages",
                    "route": "deepseek-official",
                    "base_url_env": "DSH_SYNTHETIC_ENDPOINT",
                    "api_key_env": "DSH_SYNTHETIC_KEY",
                },
                "models": [
                    {
                        "id": "controlled",
                        "context_window": 8192,
                        "max_output_tokens": 128,
                        "reasoning_efforts": False,
                    }
                ],
            }
        )
    )
    plan = LaunchPlan(
        backend="dsh_acp",
        tool="dsh",
        executable=str(executable),
        args=[],
        working_directory=root,
        home_env_var="DSH_HOME",
        home_path=home,
        env={
            "PATH": os.environ["PATH"],
            "HOME": str(root / "user-home"),
            "DSH_SYNTHETIC_KEY": "synthetic-local-only",
            "DSH_SYNTHETIC_ENDPOINT": endpoint,
        },
        env_var_names=["DSH_SYNTHETIC_KEY", "DSH_SYNTHETIC_ENDPOINT"],
        role_injection=RoleInjectionPlan(
            method="native_system_prompt_section",
            role_name="controlled",
            prompt="Managed literal {{example}} $HOME",
        ),
        metadata={"dsh": {"setup_path": str(setup_path), "model": "controlled"}},
    )
    prepare_dsh_home(
        home,
        DshEffectiveToolParams.from_file(setup_path),
        plan.env,
        plan.role_injection.prompt,
        skill_roots=(home / "skills",),
    )
    manifest = root / "runtime" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "agent_id": "native-integration-agent",
                "tool": "dsh",
                "backend": "dsh_acp",
                "registry_generation_id": "native-integration-generation",
                "runtime": {"session_id": "native-integration-runtime"},
                "backend_state": {},
                "launch_plan": plan.redacted_payload(),
            }
        )
    )
    return plan, manifest


def test_managed_tmux_exact_resume_and_usage_finalization(
    tmp_path: Path,
    dsh_executable: Path,
    controlled_messages_server: tuple[str, list[dict[str, Any]]],
    isolated_tmux: Path,
) -> None:
    """Keep one native conversation across workers and one usage row per submission."""

    endpoint, requests = controlled_messages_server
    plan, manifest = _launch_plan(tmp_path, dsh_executable, endpoint)
    session = DshAcpSession(
        launch_plan=plan, role_name="controlled", session_manifest_path=manifest
    )
    try:
        first = session.send_prompt("first controlled work", turn_artifact_dir_name="first")
        native_id = session.state.session_id
        assert native_id is not None
        assert any(event.kind == "done" for event in first)
        payload = json.loads(manifest.read_text())
        payload["backend_state"] = {"session_id": native_id}
        manifest.write_text(json.dumps(payload))
        second = session.send_prompt(
            "second controlled work",
            turn_artifact_dir_name="second",
            session_selection=HeadlessTurnSessionSelection(mode="exact", session_id=native_id),
        )
        assert session.state.session_id == native_id
        assert any(event.kind == "done" for event in second)
        assert len(requests) == 2
        assert "first controlled work" in json.dumps(requests[1]["messages"])
        service = UsageService.from_manifest(manifest)
        service.reconcile()
        page = service.get_usage()
        assert len(page.records) == 2
        assert {record.turn_id for record in page.records} == {"first", "second"}
        assert all(record.outcome == "completed" for record in page.records)
        assert all(record.token_usage.total_tokens.value == 16 for record in page.records)
        assert len({record.provider_turn_id for record in page.records}) == 2
        for name in ("first", "second"):
            artifact = manifest.parent / "manifest.turn-artifacts" / name
            raw = [
                json.loads(line)
                for line in (artifact / "provider-stdout.jsonl").read_text().splitlines()
            ]
            assert any(frame.get("jsonrpc") == "2.0" for frame in raw)
            assert (artifact / "canonical-events.jsonl").exists()
        service.reconcile()
        assert service.get_usage(after=page.next_cursor).records == []
        reset = session.send_prompt(
            "fresh reset work",
            turn_artifact_dir_name="reset",
            session_selection=HeadlessTurnSessionSelection(mode="new"),
        )
        assert any(event.kind == "done" for event in reset)
        assert session.state.session_id != native_id
        assert len(requests) == 3
        assert "first controlled work" not in json.dumps(requests[2]["messages"])
        assert "second controlled work" not in json.dumps(requests[2]["messages"])
        records = service.get_usage().records
        assert len(records) == 3
        assert {record.turn_id for record in records} == {"first", "second", "reset"}
        assert all(record.token_usage.total_tokens.value == 16 for record in records)
    finally:
        session.configure_stop_force_cleanup(force_cleanup=True)
        session.terminate()
