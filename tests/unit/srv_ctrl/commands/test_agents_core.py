from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from houmao.agents.managed_prompt_header import compose_managed_launch_prompt
from houmao.agents.mailbox_runtime_models import FilesystemMailboxDeclarativeConfig
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
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
            role_prompt="You are a precise repo researcher.",
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
    assert captured["gateway_execution_mode_override"] == "tmux_auxiliary_window"
    assert launch_result.controller.agent_identity == "repo-research-1"


def test_launch_managed_agent_locally_forwards_launch_profile_inputs_to_builder(
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
                operator_prompt_mode="unattended",
                launch_env_records={"OPENAI_BASE_URL": "https://profile.example/v1"},
                mailbox=None,
                extra=None,
            ),
            preset_path=source_agent_def_dir / "presets" / "researcher-codex-default.yaml",
            role_name="researcher",
            role_prompt="You are a precise repo researcher.",
            tool="codex",
        ),
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (
            captured.setdefault("build_request", request),
            SimpleNamespace(manifest_path=manifest_path),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.backend_for_tool",
        lambda tool, prefer_local_interactive: "codex",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        ),
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research-1",
        agent_id=None,
        auth="breakglass",
        session_name="HOUMAO-repo-research-1",
        headless=True,
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        declared_mailbox=FilesystemMailboxDeclarativeConfig(
            transport="filesystem",
            principal_id="alice",
            address="alice@agents.localhost",
            filesystem_root="/shared-mail-root",
        ),
        operator_prompt_mode="as_is",
        persistent_env_records={"OPENAI_ORG_ID": "org-alice"},
        prompt_overlay_mode="append",
        prompt_overlay_text="Prefer Alice repository conventions.",
        launch_profile_provenance={
            "name": "alice",
            "lane": "launch_profile",
        },
    )

    build_request = captured["build_request"]
    assert build_request.auth == "breakglass"
    assert build_request.operator_prompt_mode == "as_is"
    assert build_request.mailbox == FilesystemMailboxDeclarativeConfig(
        transport="filesystem",
        principal_id="alice",
        address="alice@agents.localhost",
        filesystem_root="/shared-mail-root",
    )
    assert build_request.persistent_env_records == {
        "OPENAI_BASE_URL": "https://profile.example/v1",
        "OPENAI_ORG_ID": "org-alice",
    }
    assert build_request.role_prompt_override == compose_managed_launch_prompt(
        base_prompt="You are a precise repo researcher.",
        overlay_mode="append",
        overlay_text="Prefer Alice repository conventions.",
        managed_header_enabled=True,
        agent_name="repo-research-1",
        agent_id="6ee1c825367e868092eda76cb18a96e0",
    )
    assert build_request.managed_prompt_header == {
        "version": 1,
        "enabled": True,
        "resolution_source": "default",
        "stored_policy": None,
        "agent_name": "repo-research-1",
        "agent_id": "6ee1c825367e868092eda76cb18a96e0",
    }
    assert build_request.launch_profile_provenance == {
        "name": "alice",
        "lane": "launch_profile",
    }


def test_launch_managed_agent_locally_can_disable_default_managed_header(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    manifest_path = (tmp_path / "manifest.json").resolve()

    for path in (
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
            role_prompt="",
            tool="codex",
        ),
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (
            captured.setdefault("build_request", request),
            SimpleNamespace(manifest_path=manifest_path),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.backend_for_tool",
        lambda tool, prefer_local_interactive: "codex",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="HOUMAO-codex-researcher",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-codex-researcher",
            manifest_path=manifest_path,
        ),
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name=None,
        agent_id=None,
        auth=None,
        session_name="HOUMAO-codex-researcher",
        headless=True,
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        managed_header_override=False,
    )

    build_request = captured["build_request"]
    assert build_request.role_prompt_override == ""
    assert build_request.managed_prompt_header == {
        "version": 1,
        "enabled": False,
        "resolution_source": "launch_override",
        "stored_policy": None,
        "agent_name": "HOUMAO-codex-researcher",
        "agent_id": derive_agent_id_from_name("HOUMAO-codex-researcher"),
    }
