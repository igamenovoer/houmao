"""Unit tests for the serverless gateway mail wake-up demo pack."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import houmao.demo.gateway_mail_wakeup_demo_pack.driver as demo_driver
from houmao.demo.gateway_mail_wakeup_demo_pack.models import (
    DeliveryState,
    DemoState,
    build_demo_layout,
    default_demo_output_dir,
    load_demo_parameters,
    load_demo_state,
    save_demo_state,
)


PACK_DIR = (
    Path(__file__).resolve().parents[3] / "scripts" / "demo" / "gateway-mail-wakeup-demo-pack"
)


def _repo_root() -> Path:
    """Return the repository root for this test module."""

    return Path(__file__).resolve().parents[3]


def _make_state(paths, *, tool: str = "codex", active: bool = True) -> DemoState:
    """Create one representative persisted demo state."""

    for directory in (
        paths.control_dir,
        paths.logs_dir,
        paths.runtime_root,
        paths.registry_root,
        paths.mailbox_root,
        paths.jobs_root,
        paths.deliveries_dir,
        paths.project_dir,
        paths.outputs_dir,
        paths.evidence_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return DemoState(
        active=active,
        created_at_utc="2026-03-27T18:00:00+00:00",
        stopped_at_utc=None if active else "2026-03-27T18:10:00+00:00",
        repo_root=_repo_root(),
        output_root=paths.output_root,
        selected_tool=tool,
        provider="codex" if tool == "codex" else "claude_code",
        selector="gateway-mail-wakeup-demo",
        run_id="gateway-mail-wakeup-20260327T180000Z-deadbeef",
        agent_def_dir=_repo_root() / "tests" / "fixtures" / "agents",
        project_fixture=_repo_root()
        / "tests"
        / "fixtures"
        / "dummy-projects"
        / "mailbox-demo-python",
        project_workdir=paths.project_dir,
        brain_manifest_path=paths.runtime_root / "manifests" / "brain.yaml",
        brain_home_path=paths.runtime_root / "homes" / tool,
        launch_helper_path=paths.runtime_root / "homes" / tool / "launch.sh",
        session_manifest_path=paths.runtime_root
        / "sessions"
        / "local_interactive"
        / "demo"
        / "manifest.json",
        session_root=paths.runtime_root / "sessions" / "local_interactive" / "demo",
        tracked_agent_id=f"tracked-{tool}",
        agent_name=f"gateway-wakeup-{tool}",
        agent_id=f"agent-{tool}",
        tmux_session_name=f"tmux-{tool}",
        terminal_id=None,
        mailbox_principal_id=f"AGENTSYS-gateway-mailbox-agent-{tool}",
        mailbox_address=f"AGENTSYS-gateway-mailbox-agent-{tool}@agents.localhost",
        gateway_root=paths.runtime_root / "sessions" / "local_interactive" / "demo" / "gateway",
        gateway_host="127.0.0.1",
        gateway_port=43123,
        notifier_interval_seconds=1,
        idle_timeout_seconds=180.0,
        output_timeout_seconds=180.0,
        output_file_path=paths.outputs_dir / "wakeup-time.txt",
        deliveries=[],
    )


def test_tracked_parameters_and_default_output_roots_match_the_documented_contract() -> None:
    """The tracked inputs should expose the documented tool and output defaults."""

    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")

    assert parameters.project_fixture == Path("tests/fixtures/dummy-projects/mailbox-demo-python")
    assert parameters.tools["claude"].selector == "gateway-mail-wakeup-demo"
    assert parameters.tools["claude"].provider == "claude_code"
    assert parameters.tools["codex"].selector == "gateway-mail-wakeup-demo"
    assert parameters.tools["codex"].provider == "codex"
    assert parameters.delivery.subject == "Gateway wake-up demo"
    assert (
        default_demo_output_dir(repo_root=_repo_root(), tool="claude")
        == (
            _repo_root()
            / "scripts"
            / "demo"
            / "gateway-mail-wakeup-demo-pack"
            / "outputs"
            / "claude"
        ).resolve()
    )


def test_resolve_paths_rejects_output_root_outside_demo_pack(tmp_path: Path) -> None:
    """Operator overrides must stay inside the demo pack directory."""

    args = type("Args", (), {"demo_output_dir": str(tmp_path), "parameters": ""})()
    with pytest.raises(demo_driver.DemoPackError, match="output root must remain inside"):
        demo_driver._resolve_paths(args, repo_root=_repo_root(), tool="codex")


def test_start_demo_persists_serverless_state_and_pack_local_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup should use pack-local owned roots and persist serverless session state."""

    parameters = load_demo_parameters(PACK_DIR / "inputs" / "demo_parameters.json")
    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    recorded: dict[str, object] = {}
    override_agent_def_dir = tmp_path / "custom-agents"
    override_agent_def_dir.mkdir()

    monkeypatch.setenv("AGENTSYS_AGENT_DEF_DIR", str(override_agent_def_dir))
    monkeypatch.setattr(
        demo_driver,
        "initialize_mailbox",
        lambda *, repo_root, paths, env, timeout_seconds: {"mailbox_root": str(paths.mailbox_root)},
    )

    def fake_provision_project_workdir(*, project_fixture, project_dir, allow_reprovision):
        del project_fixture, allow_reprovision
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    monkeypatch.setattr(demo_driver, "provision_project_workdir", fake_provision_project_workdir)

    def fake_run_launch_command(
        *,
        cwd,
        stdout_path,
        stderr_path,
        selector,
        provider,
        agent_name,
        session_name,
        env,
        timeout_seconds,
    ):
        del stdout_path, stderr_path, timeout_seconds
        recorded["cwd"] = cwd
        recorded["selector"] = selector
        recorded["provider"] = provider
        recorded["agent_name"] = agent_name
        recorded["session_name"] = session_name
        recorded["env"] = dict(env)
        return {"manifest_path": str(tmp_path / "manifest.json")}

    monkeypatch.setattr(demo_driver, "run_launch_command", fake_run_launch_command)
    monkeypatch.setattr(
        demo_driver,
        "query_agent_show",
        lambda **kwargs: {
            "tracked_agent_id": "tracked-codex",
            "identity": {
                "manifest_path": str(tmp_path / "runtime" / "sessions" / "manifest.json"),
                "agent_name": "gateway-wakeup-codex-beefcafe",
                "agent_id": "agent-codex",
                "tmux_session_name": "hm-gateway-wakeup-codex-beefcafe",
                "terminal_id": None,
            },
        },
    )
    monkeypatch.setattr(
        demo_driver,
        "register_mailbox",
        lambda **kwargs: {"mailbox_root": str(paths.mailbox_root), "activation_state": "active"},
    )
    monkeypatch.setattr(
        demo_driver,
        "attach_gateway",
        lambda **kwargs: {"gateway_host": "127.0.0.1", "gateway_port": 43123},
    )
    monkeypatch.setattr(
        demo_driver,
        "enable_notifier",
        lambda **kwargs: {"enabled": True, "interval_seconds": 1},
    )
    monkeypatch.setattr(
        demo_driver,
        "load_session_details",
        lambda **kwargs: {
            "session_root": tmp_path / "runtime" / "sessions" / "local_interactive" / "demo",
            "brain_manifest_path": tmp_path / "runtime" / "manifests" / "brain.yaml",
            "brain_home_path": tmp_path / "runtime" / "homes" / "codex",
            "launch_helper_path": tmp_path / "runtime" / "homes" / "codex" / "launch.sh",
        },
    )

    def fake_expose_project_mailbox_skills(
        *,
        project_workdir,
        brain_manifest_path,
        brain_home_path,
        launch_helper_path,
    ) -> None:
        del brain_manifest_path, brain_home_path, launch_helper_path
        mailbox_dir = project_workdir / "skills" / "mailbox"
        mailbox_dir.mkdir(parents=True, exist_ok=True)
        (mailbox_dir / "README.md").write_text("Mailbox docs\n", encoding="utf-8")

    monkeypatch.setattr(
        demo_driver, "expose_project_mailbox_skills", fake_expose_project_mailbox_skills
    )
    monkeypatch.setattr(
        demo_driver,
        "_wait_for_session_ready",
        lambda **kwargs: {"status": "ready"},
    )
    monkeypatch.setattr(
        demo_driver,
        "query_agent_state",
        lambda **kwargs: {"availability": "available", "turn": {"phase": "ready"}},
    )

    state = demo_driver._start_demo(
        repo_root=_repo_root(),
        paths=paths,
        parameters=parameters,
        tool="codex",
    )
    loaded = load_demo_state(paths.state_path)

    assert state.selected_tool == "codex"
    assert loaded.selected_tool == "codex"
    assert loaded.provider == "codex"
    assert loaded.selector == "gateway-mail-wakeup-demo"
    assert loaded.agent_def_dir == override_agent_def_dir.resolve()
    assert loaded.output_root == paths.output_root.resolve()
    assert loaded.output_file_path == (paths.outputs_dir / "wakeup-time.txt").resolve()
    env = recorded["env"]
    assert env["AGENTSYS_GLOBAL_RUNTIME_DIR"] == str(paths.runtime_root)
    assert env["AGENTSYS_GLOBAL_REGISTRY_DIR"] == str(paths.registry_root)
    assert env["AGENTSYS_GLOBAL_MAILBOX_DIR"] == str(paths.mailbox_root)
    assert env["AGENTSYS_LOCAL_JOBS_DIR"] == str(paths.jobs_root)
    assert env["AGENTSYS_AGENT_DEF_DIR"] == str(override_agent_def_dir)
    assert recorded["cwd"] == paths.project_dir
    assert recorded["selector"] == "gateway-mail-wakeup-demo"
    assert recorded["provider"] == "codex"
    assert (paths.project_dir / "skills" / "mailbox" / "README.md").is_file()


def test_verify_builds_the_sanitized_report_contract(tmp_path: Path) -> None:
    """Verify should write the expected sanitized report for a successful canonical run."""

    paths = build_demo_layout(demo_output_dir=tmp_path / "outputs")
    delivery = DeliveryState(
        delivery_index=1,
        subject="Gateway wake-up demo",
        message_id="msg-1",
        thread_id="thread-1",
        created_at_utc="2026-03-27T18:00:00+00:00",
        staged_message_path=tmp_path / "staged-1.md",
        payload_path=tmp_path / "payload-1.json",
        delivery_artifact_path=tmp_path / "delivery-1.json",
        unread_observed_at_utc="2026-03-27T18:00:01+00:00",
        read_observed_at_utc="2026-03-27T18:00:02+00:00",
        mailbox_state_source="gateway",
    )
    state = _make_state(paths, tool="codex", active=False).model_copy(
        update={"deliveries": [delivery]}
    )
    save_demo_state(paths.state_path, state)
    expected_path = tmp_path / "expected-report.json"

    def fake_inspect_demo(*, repo_root, paths):
        del repo_root, paths
        return {
            "mailbox": {
                "state_source": "gateway",
                "message_count": 1,
                "unread_count": 0,
                "messages": [],
            },
            "gateway": {
                "status": {"gateway_health": "healthy"},
                "notifier": {"enabled": True},
                "audit_summary": {
                    "has_enqueued": True,
                    "has_poll_error": False,
                },
                "queue_state": {
                    "has_notifier_request": True,
                    "has_completed_notifier_request": True,
                },
            },
            "ownership": {
                "output_root_pack_local": True,
                "mailbox_root_within_output_root": True,
                "output_file_within_output_root": True,
            },
            "output_file": {
                "exists": True,
                "timestamp_like": True,
                "modified_after_delivery": True,
            },
            "project": {
                "managed_project_metadata_present": True,
                "visible_mailbox_skill_surface_present": True,
            },
            "deliveries": [],
        }

    original_inspect = demo_driver._inspect_demo
    demo_driver._inspect_demo = fake_inspect_demo
    try:
        demo_driver._verify_demo(
            repo_root=_repo_root(),
            paths=paths,
            expected_report=str(expected_path),
            snapshot=True,
        )
        demo_driver._verify_demo(
            repo_root=_repo_root(),
            paths=paths,
            expected_report=str(expected_path),
            snapshot=False,
        )
    finally:
        demo_driver._inspect_demo = original_inspect

    sanitized = json.loads(paths.sanitized_report_path.read_text(encoding="utf-8"))
    assert sanitized["config"]["selected_tool"] == "<TOOL>"
    assert sanitized["config"]["provider"] == "<PROVIDER>"
    assert sanitized["counts"]["processed_delivery_count"] == 1
    assert sanitized["gateway_evidence"]["queue_completed_notifier_request"] is True
    assert sanitized["deliveries"][0]["message_id"] == "<MESSAGE_ID>"


def test_pack_local_autotest_assets_exist() -> None:
    """The pack should ship the owned autotest harness and wrapper driver."""

    required_paths = (
        PACK_DIR / ".gitignore",
        PACK_DIR / "autotest" / "run_autotest.sh",
        PACK_DIR / "run_demo.sh",
        PACK_DIR / "scripts" / "demo_driver.py",
    )
    for path in required_paths:
        assert path.is_file(), f"missing expected pack asset: {path}"
