from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from houmao.srv_ctrl.commands.agents.core import launch_managed_agent_locally


def test_launch_managed_agent_locally_forwards_gateway_args_to_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    repo_root = (tmp_path / "repo").resolve()
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    manifest_path = (tmp_path / "manifest.json").resolve()

    for path in (
        repo_root,
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.ensure_project_aware_local_roots",
        lambda **kwargs: SimpleNamespace(
            runtime_root=runtime_root,
            jobs_root=jobs_root,
            mailbox_root=mailbox_root,
            overlay_root=overlay_root,
            overlay_root_source="discovered",
            overlay_discovery_mode="ancestor",
            created_overlay=False,
            project_overlay=None,
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            agent_def_dir=source_agent_def_dir,
            preset=SimpleNamespace(
                tool="codex",
                skills=(),
                setup="default",
                auth="work",
                launch_overrides=None,
                operator_prompt_mode=None,
                launch_env_records=None,
                mailbox=None,
                extra=None,
            ),
            preset_path=source_agent_def_dir / "presets" / "researcher-codex-default.yaml",
            role_name="researcher",
            tool="codex",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=manifest_path),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.backend_for_tool",
        lambda tool, prefer_local_interactive: "codex",
    )

    captured: dict[str, object] = {}

    def _fake_start_runtime_session(**kwargs: object) -> SimpleNamespace:
        captured.update(kwargs)
        return SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        _fake_start_runtime_session,
    )

    launch_result = launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research-1",
        agent_id=None,
        auth=None,
        session_name="HOUMAO-repo-research-1",
        headless=True,
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        gateway_auto_attach=True,
        gateway_host="127.0.0.1",
        gateway_port=0,
    )

    assert captured["gateway_auto_attach"] is True
    assert captured["gateway_host"] == "127.0.0.1"
    assert captured["gateway_port"] == 0
    assert launch_result.controller.agent_identity == "repo-research-1"
