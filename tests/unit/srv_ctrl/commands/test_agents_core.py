from __future__ import annotations

import click
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.managed_prompt_header import compose_managed_launch_prompt
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxDeclarativeConfig,
    FilesystemMailboxResolvedConfig,
)
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.srv_ctrl.commands.agents.core import launch_managed_agent_locally


def _expected_default_section_metadata(*, header_enabled: bool) -> dict[str, object]:
    """Return expected default managed-header section metadata."""

    return {
        "identity": {
            "tag": "identity",
            "enabled": True,
            "rendered": header_enabled,
            "resolution_source": "default",
            "stored_policy": None,
            "default_enabled": True,
        },
        "houmao-runtime-guidance": {
            "tag": "houmao_runtime_guidance",
            "enabled": True,
            "rendered": header_enabled,
            "resolution_source": "default",
            "stored_policy": None,
            "default_enabled": True,
        },
        "automation-notice": {
            "tag": "automation_notice",
            "enabled": True,
            "rendered": header_enabled,
            "resolution_source": "default",
            "stored_policy": None,
            "default_enabled": True,
        },
        "task-reminder": {
            "tag": "task_reminder",
            "enabled": False,
            "rendered": False,
            "resolution_source": "default",
            "stored_policy": None,
            "default_enabled": False,
        },
        "mail-ack": {
            "tag": "mail_ack",
            "enabled": False,
            "rendered": False,
            "resolution_source": "default",
            "stored_policy": None,
            "default_enabled": False,
        },
    }


def _install_basic_launch_patches(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runtime_root: Path,
    jobs_root: Path,
    mailbox_root: Path,
    overlay_root: Path,
    source_agent_def_dir: Path,
) -> None:
    """Install one minimal direct-launch environment for `launch_managed_agent_locally()`."""

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
        "houmao.srv_ctrl.commands.agents.core.backend_for_tool",
        lambda tool, prefer_local_interactive: "codex",
    )


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
    memory_binding = captured["memory_binding"]
    assert getattr(memory_binding, "kind") == "auto"
    assert (
        getattr(memory_binding, "directory")
        == (overlay_root / "memory" / "agents" / "6ee1c825367e868092eda76cb18a96e0").resolve()
    )
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
        "sections": _expected_default_section_metadata(header_enabled=True),
    }
    assert build_request.houmao_system_prompt_layout["managed_header"] == {
        "enabled": True,
        "sections": _expected_default_section_metadata(header_enabled=True),
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
        "sections": _expected_default_section_metadata(header_enabled=False),
    }
    assert build_request.houmao_system_prompt_layout["managed_header"] == {
        "enabled": False,
        "sections": _expected_default_section_metadata(header_enabled=False),
    }


def test_launch_managed_agent_locally_fails_before_build_without_force_on_live_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()

    for path in (
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: SimpleNamespace(
            identity=SimpleNamespace(backend="codex_headless"),
            runtime=SimpleNamespace(manifest_path=str(tmp_path / "manifest.json")),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: pytest.fail("builder should not run without `--force`"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: pytest.fail("runtime should not start without `--force`"),
    )

    with pytest.raises(click.ClickException, match="Rerun with `--force`"):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            auth=None,
            session_name="worker-a",
            headless=True,
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
        )


def test_launch_managed_agent_locally_keep_stale_reuses_predecessor_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    session_root = runtime_root / "codex_headless" / "session-1"
    session_manifest_path = session_root / "manifest.json"
    job_dir = jobs_root / "job-1"
    home_path = runtime_root / "homes" / "home-123"
    build_manifest_path = (tmp_path / "build-manifest.yaml").resolve()

    for path in (
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
        session_root,
        job_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )

    record = SimpleNamespace(
        identity=SimpleNamespace(backend="codex_headless"),
        runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
    )
    state = {"record_present": True}
    stop_calls: list[object] = []
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: record if state["record_present"] else None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            job_dir=str(job_dir),
            launch_plan=SimpleNamespace(mailbox=None),
            brain_manifest_path=str(tmp_path / "brain.yaml"),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_brain_manifest",
        lambda path: {
            "runtime": {
                "runtime_root": str(runtime_root),
                "home_id": "home-123",
                "home_path": str(home_path),
            }
        },
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: SimpleNamespace(mode="local"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.stop_managed_agent",
        lambda target: (
            stop_calls.append(target),
            state.__setitem__("record_present", False),
            SimpleNamespace(success=True, detail="stopped"),
        )[2],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (
            captured.setdefault("build_request", request),
            SimpleNamespace(manifest_path=build_manifest_path),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (
            captured.setdefault("runtime_kwargs", kwargs),
            SimpleNamespace(
                agent_identity="worker-a",
                agent_id="agent-123",
                tmux_session_name="worker-a",
                manifest_path=build_manifest_path,
            ),
        )[1],
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="worker-a",
        agent_id=None,
        auth=None,
        session_name="worker-a",
        headless=True,
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        force_mode="keep-stale",
    )

    assert len(stop_calls) == 1
    assert captured["build_request"].home_id == "home-123"
    assert captured["build_request"].existing_home_mode == "keep-stale"
    assert captured["runtime_kwargs"]["managed_force_mode"] == "keep-stale"


def test_launch_managed_agent_locally_clean_removes_replaceable_predecessor_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    session_root = runtime_root / "codex_headless" / "session-1"
    session_manifest_path = session_root / "manifest.json"
    job_dir = jobs_root / "job-1"
    home_path = runtime_root / "homes" / "home-123"
    private_mailbox_dir = (tmp_path / "private-mailboxes" / "worker-a").resolve()
    build_manifest_path = (tmp_path / "build-manifest.yaml").resolve()

    for path in (
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
        session_root,
        job_dir,
        private_mailbox_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    (session_manifest_path).write_text("{}\n", encoding="utf-8")
    (session_root / "session.log").write_text("old session\n", encoding="utf-8")
    (job_dir / "status.json").write_text("{}\n", encoding="utf-8")
    (private_mailbox_dir / "message.eml").write_text("old message\n", encoding="utf-8")

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )

    record = SimpleNamespace(
        identity=SimpleNamespace(backend="codex_headless"),
        runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
    )
    state = {"record_present": True}
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: record if state["record_present"] else None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            job_dir=str(job_dir),
            launch_plan=SimpleNamespace(mailbox={}),
            brain_manifest_path=str(tmp_path / "brain.yaml"),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_brain_manifest",
        lambda path: {
            "runtime": {
                "runtime_root": str(runtime_root),
                "home_id": "home-123",
                "home_path": str(home_path),
            }
        },
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: SimpleNamespace(mode="local"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.stop_managed_agent",
        lambda target: (
            state.__setitem__("record_present", False),
            SimpleNamespace(success=True, detail="stopped"),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolved_mailbox_config_from_payload",
        lambda payload, manifest_path=None: FilesystemMailboxResolvedConfig(
            transport="filesystem",
            principal_id="worker-a",
            address="worker-a@agents.localhost",
            filesystem_root=mailbox_root,
            bindings_version="2026-04-08T00:00:00Z",
            mailbox_kind="symlink",
            mailbox_path=private_mailbox_dir,
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (
            captured.setdefault("build_request", request),
            SimpleNamespace(manifest_path=build_manifest_path),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="worker-a",
            agent_id="agent-123",
            tmux_session_name="worker-a",
            manifest_path=build_manifest_path,
        ),
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="worker-a",
        agent_id=None,
        auth=None,
        session_name="worker-a",
        headless=True,
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        force_mode="clean",
    )

    assert captured["build_request"].existing_home_mode == "clean"
    assert not session_root.exists()
    assert not job_dir.exists()
    assert not private_mailbox_dir.exists()


def test_launch_managed_agent_locally_force_does_not_target_unrelated_tmux_collision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    build_manifest_path = (tmp_path / "build-manifest.yaml").resolve()

    for path in (
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.stop_managed_agent",
        lambda target: pytest.fail("unrelated tmux collision should not stop any managed agent"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=build_manifest_path),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (_ for _ in ()).throw(
            click.ClickException("Tmux session `worker-b` already exists.")
        ),
    )

    with pytest.raises(click.ClickException, match="Tmux session `worker-b` already exists."):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-b",
            agent_id=None,
            auth=None,
            session_name="worker-b",
            headless=True,
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
        )


def test_launch_managed_agent_locally_reports_post_takeover_build_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    session_root = runtime_root / "codex_headless" / "session-1"
    session_manifest_path = session_root / "manifest.json"
    job_dir = jobs_root / "job-1"
    home_path = runtime_root / "homes" / "home-123"

    for path in (
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
        session_root,
        job_dir,
    ):
        path.mkdir(parents=True, exist_ok=True)
    session_manifest_path.write_text("{}\n", encoding="utf-8")

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )

    record = SimpleNamespace(
        identity=SimpleNamespace(backend="codex_headless"),
        runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
    )
    state = {"record_present": True}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: record if state["record_present"] else None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            job_dir=str(job_dir),
            launch_plan=SimpleNamespace(mailbox=None),
            brain_manifest_path=str(tmp_path / "brain.yaml"),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_brain_manifest",
        lambda path: {
            "runtime": {
                "runtime_root": str(runtime_root),
                "home_id": "home-123",
                "home_path": str(home_path),
            }
        },
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: SimpleNamespace(mode="local"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.stop_managed_agent",
        lambda target: (
            state.__setitem__("record_present", False),
            SimpleNamespace(success=True, detail="stopped"),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (_ for _ in ()).throw(RuntimeError("builder exploded")),
    )

    with pytest.raises(
        click.ClickException,
        match=r"after predecessor `worker-a` stood down under `--force clean`: builder exploded",
    ):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            auth=None,
            session_name="worker-a",
            headless=True,
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
        )
