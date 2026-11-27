from __future__ import annotations

from contextlib import nullcontext
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
from unittest.mock import Mock

import click
from click.testing import CliRunner
import pytest

from houmao.agents.managed_prompt_header import compose_managed_launch_prompt
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxDeclarativeConfig,
    FilesystemMailboxResolvedConfig,
    MailboxesDeclarativeConfig,
    MailboxesResolvedConfig,
    MailboxSlotConfig,
)
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.backends.kimi_web import KimiWebSession
from houmao.agents.realm_controller.errors import SessionManifestError
from houmao.agents.realm_controller.gateway_models import GatewayTuiTrackingTimingOverridesV1
from houmao.agents.realm_controller.gateway_storage import (
    gateway_paths_from_manifest_path,
    read_gateway_mail_notifier_record,
)
from houmao.agents.realm_controller.manifest import default_manifest_path
from houmao.agents.realm_controller.models import SessionControlResult
from houmao.agents.system_skills import SystemSkillSelectionPolicy
from houmao.execution.context import execution_binding_scope, observed_local_binding
from houmao.owned_paths import (
    HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR,
    HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR,
)
from houmao.project.catalog import ManagedContentRef
from houmao.project.launch_profiles import ResolvedLaunchProfileMemoSeed
from houmao.srv_ctrl.commands.agents.core import (
    _resolve_launch_profile_system_skill_policy_or_click,
    launch_managed_agent_locally,
)
from houmao.srv_ctrl.commands.main import cli


@pytest.mark.parametrize("style", ["plain", "fancy", "json"])
@pytest.mark.parametrize("owner_available", [True, False])
def test_native_open_browser_reports_one_verified_outcome(
    monkeypatch: pytest.MonkeyPatch, style: str, owner_available: bool
) -> None:
    """Format a verified browser outcome after one local action."""

    backend = KimiWebSession()
    calls: list[str] = []

    def require_owner() -> None:
        """Check the current owner before opening a browser."""

        calls.append("owner")
        if not owner_available:
            raise SessionManifestError("Stale browser owner.")

    def open_browser() -> SessionControlResult:
        """Return a control result without invoking a real browser."""

        calls.append("browser")
        return SessionControlResult(
            status="ok", action="open_browser", detail="Opened the browser."
        )

    target = SimpleNamespace(
        mode="local",
        identity=SimpleNamespace(backend="kimi_web"),
        controller=SimpleNamespace(
            backend_session=backend,
            execution_scope=nullcontext,
            require_managed_control_owner=require_owner,
        ),
    )
    monkeypatch.setattr(backend, "open_browser", open_browser)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: target,
    )

    result = CliRunner().invoke(
        cli, [f"--print-{style}", "agents", "single", "--agent-id", "kimi-web", "open-browser"]
    )
    if not owner_available:
        assert result.exit_code != 0
        assert "Stale browser owner." in result.output
        assert calls == ["owner"]
        return

    assert result.exit_code == 0, result.output
    fields = {"status": "ok", "action": "open_browser", "detail": "Opened the browser."}
    if style == "json":
        assert json.loads(result.output) == fields
    else:
        for name, value in fields.items():
            assert name in result.output
            assert value in result.output
    assert "SessionControlResult" not in result.output
    assert "#token=" not in result.output
    assert "open-browser.html" not in result.output
    assert calls == ["owner", "browser"]


@pytest.fixture
def stub_brain_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub preflight for orchestration tests with mocked builders and source assets."""

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.validate_brain_inputs",
        lambda request, **kwargs: None,
    )


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
        "memo-cue": {
            "tag": "memo_cue",
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
    tool: str = "codex",
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
                tool_params={},
                tool=tool,
                skills=(),
                setup="default",
                auth="work",
                launch_overrides=None,
                operator_prompt_mode=None,
                launch_env_records=None,
                mailboxes=None,
                extra=None,
            ),
            preset_path=source_agent_def_dir / "presets" / "researcher-codex-default.yaml",
            role_name="researcher",
            role_prompt="You are a precise repo researcher.",
            tool=tool,
        ),
    )


@pytest.mark.parametrize("explicit_timings", [False, True])
@pytest.mark.parametrize(
    ("tool", "mode", "refusal"),
    [
        ("codex", "tui", None),
        ("codex", "headless", "require a terminal native surface"),
        ("codex", "service", "require a terminal native surface"),
        ("dsh", "web", "require a terminal native surface"),
        ("hermes", "tui", "Hermes TUI uses native readiness"),
    ],
)
def test_manager_launch_checks_only_explicit_timings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    mode: str,
    refusal: str | None,
    explicit_timings: bool,
) -> None:
    """Gate explicit choices at the manager entry point before brain preparation."""

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=tmp_path / "runtime",
        jobs_root=tmp_path / "jobs",
        mailbox_root=tmp_path / "mailbox",
        overlay_root=tmp_path / "overlay",
        source_agent_def_dir=tmp_path,
        tool=tool,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_hermes_executable", lambda **_: tmp_path
    )
    prepare = Mock(side_effect=RuntimeError("reached brain preparation"))
    monkeypatch.setattr("houmao.srv_ctrl.commands.agents.core.validate_brain_inputs", prepare)
    expected = refusal if explicit_timings and refusal is not None else "reached brain preparation"

    with pytest.raises(click.ClickException, match=expected):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name=None,
            agent_id=None,
            auth=None,
            session_name=None,
            mode=mode,
            provider="codex",
            working_directory=tmp_path,
            source_agent_def_dir=tmp_path,
            source_env={},
            headless_display_style="plain",
            headless_display_detail="concise",
            gateway_auto_attach=True,
            gateway_tui_tracking_timing_overrides=(
                GatewayTuiTrackingTimingOverridesV1(watch_poll_interval_seconds=0.25)
                if explicit_timings
                else None
            ),
        )
    assert prepare.call_count == int(expected == "reached brain preparation")


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_merges_launch_profile_skill_overlays(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    manifest_path = (tmp_path / "manifest.json").resolve()
    private_source = (tmp_path / "private" / "notes").resolve()

    for path in (
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
        private_source,
    ):
        path.mkdir(parents=True, exist_ok=True)
    (private_source / "SKILL.md").write_text("# notes\n\nPrivate.\n", encoding="utf-8")
    manifest_path.write_text("{}\n", encoding="utf-8")
    source_system_skill_policy = SystemSkillSelectionPolicy(
        mode="extend",
        pack_ids=("admin",),
    )
    profile_system_skill_policy = SystemSkillSelectionPolicy(
        mode="replace",
        pack_ids=("agent",),
    )
    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            agent_def_dir=source_agent_def_dir,
            preset=SimpleNamespace(
                tool_params={},
                tool="codex",
                skills=("notes",),
                setup="default",
                auth="work",
                launch_overrides=None,
                operator_prompt_mode=None,
                launch_env_records=None,
                launch_system_skill_policy=source_system_skill_policy,
                mailboxes=None,
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
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="repo-research",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research",
            manifest_path=manifest_path,
        ),
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name=None,
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        launch_profile_registered_skill_names=("mailbox", "notes"),
        launch_profile_private_skills=(
            SimpleNamespace(name="notes", source_path=private_source, mode="copy"),
        ),
        launch_profile_system_skill_policy=profile_system_skill_policy,
        launch_profile_provenance={"name": "alice", "lane": "launch_profile"},
    )

    build_request = captured["build_request"]
    assert build_request.skills == ["notes", "mailbox"]
    assert build_request.private_skills[0].name == "notes"
    assert build_request.private_skills[0].source_path == private_source
    assert build_request.source_system_skill_policy == source_system_skill_policy
    assert build_request.launch_profile_system_skill_policy == profile_system_skill_policy
    assert build_request.launch_profile_provenance["skills"] == {
        "registered": ["mailbox", "notes"],
        "private": [
            {
                "name": "notes",
                "resolved_path": str(private_source),
                "mode": "copy",
            }
        ],
        "private_shadowed_names": ["notes"],
    }


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_passes_complete_kimi_prompt_to_builder(
    monkeypatch: pytest.MonkeyPatch,
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
                tool_params={},
                tool="kimi",
                skills=(),
                setup="default",
                auth="oauth",
                launch_overrides=None,
                operator_prompt_mode="unattended",
                launch_env_records=None,
                launch_system_skill_policy=None,
                mailboxes=None,
                extra=None,
            ),
            preset_path=source_agent_def_dir / "presets" / "researcher-kimi-default.yaml",
            role_name="researcher",
            role_prompt="You are a precise repo researcher.",
            tool="kimi",
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
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="repo-research-kimi",
            agent_id="agent-123",
            tmux_session_name="HOUMAO-repo-research-kimi",
            manifest_path=manifest_path,
        ),
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research-kimi",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name="HOUMAO-repo-research-kimi",
        mode="tui",
        provider="kimi",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
    )

    build_request = captured["build_request"]
    assert build_request.role_prompt_override
    assert "You are a precise repo researcher." in build_request.role_prompt_override
    assert not hasattr(build_request, "required_auto_skill_names")


def test_launch_profile_policy_rejects_removed_individual_system_skill_selector() -> None:
    with pytest.raises(click.ClickException, match="obsolete system-skills selector field.*skills"):
        _resolve_launch_profile_system_skill_policy_or_click(
            {
                "mode": "extend",
                "skills": ["houmao-utils-llm-wiki"],
            },
            source="launch dossier `alice` system_skills",
        )


@pytest.mark.usefixtures("stub_brain_preflight")
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
                tool_params={},
                tool="codex",
                skills=(),
                setup="default",
                auth="work",
                launch_overrides=None,
                operator_prompt_mode=None,
                launch_env_records=None,
                mailboxes=None,
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

    captured: dict[str, object] = {}
    timing_overrides = GatewayTuiTrackingTimingOverridesV1(
        watch_poll_interval_seconds=0.25,
        stale_active_recovery_seconds=6.0,
        final_stable_active_recovery_seconds=18.0,
    )

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
        agent_id_mode="name-hash",
        auth=None,
        session_name="HOUMAO-repo-research-1",
        mode="tui",
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        gateway_auto_attach=True,
        gateway_host="127.0.0.1",
        gateway_port=0,
        gateway_tui_tracking_timing_overrides=timing_overrides,
    )

    assert captured["gateway_auto_attach"] is True
    assert captured["gateway_host"] == "127.0.0.1"
    assert captured["gateway_port"] == 0
    assert captured["gateway_execution_mode_override"] == "tmux_auxiliary_window"
    assert captured["gateway_tui_tracking_timing_overrides"] == timing_overrides
    memory_paths = captured["memory_paths"]
    expected_memory_root = (
        overlay_root / "memory" / "agents" / "6ee1c825367e868092eda76cb18a96e0"
    ).resolve()
    assert getattr(memory_paths, "memory_root") == expected_memory_root
    assert getattr(memory_paths, "memo_file") == (expected_memory_root / "houmao-memo.md").resolve()
    assert getattr(memory_paths, "pages_dir") == (expected_memory_root / "pages").resolve()
    assert launch_result.controller.agent_identity == "repo-research-1"


@pytest.mark.usefixtures("stub_brain_preflight")
@pytest.mark.parametrize("selection", ["overlay", "shared", "explicit", "declared", "owner"])
def test_launch_managed_agent_locally_selects_owner_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    selection: str,
) -> None:
    """Record the paths chosen from the owner and the launch project's overlay."""

    project_dir = tmp_path / "project"
    overlay = project_dir / ".houmao"
    working_dir = tmp_path / "workdir"
    shared_runtime = tmp_path / "shared-runtime"
    owner_runtime = tmp_path / "owner-runtime"
    shared_mailbox = tmp_path / "shared-mailbox"
    explicit_mailbox = tmp_path / "explicit-mailbox" if selection == "explicit" else None
    declared_mailboxes = (
        MailboxesDeclarativeConfig(
            offline=FilesystemMailboxDeclarativeConfig(
                transport="filesystem", filesystem_root="declared-mailbox"
            )
        )
        if selection == "declared"
        else None
    )
    if selection == "overlay":
        monkeypatch.delenv(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, raising=False)
        monkeypatch.delenv(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR, raising=False)
    else:
        monkeypatch.setenv(HOUMAO_GLOBAL_RUNTIME_DIR_ENV_VAR, str(shared_runtime))
        monkeypatch.setenv(HOUMAO_GLOBAL_MAILBOX_DIR_ENV_VAR, str(shared_mailbox))
    owner = (
        observed_local_binding(
            working_directory=project_dir,
            runtime_root=owner_runtime,
            registry_root=tmp_path / "owner-registry",
            tmux_socket=None,
        )
        if selection == "owner"
        else None
    )
    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=overlay / "runtime",
        jobs_root=overlay / "jobs",
        mailbox_root=overlay / "mailbox",
        overlay_root=overlay,
        source_agent_def_dir=overlay / "agents",
    )
    build = Mock(return_value=SimpleNamespace(manifest_path=tmp_path / "manifest.json"))
    start = Mock(return_value=SimpleNamespace())
    monkeypatch.setattr("houmao.srv_ctrl.commands.agents.core.build_brain_home", build)
    monkeypatch.setattr("houmao.srv_ctrl.commands.agents.core.start_runtime_session", start)

    with execution_binding_scope(owner):
        result = launch_managed_agent_locally(
            agents="researcher",
            agent_name="root-selection",
            agent_id=None,
            auth=None,
            session_name=None,
            mode="headless",
            provider="codex",
            working_directory=working_dir,
            source_working_directory=project_dir,
            source_agent_def_dir=overlay / "agents",
            headless_display_style="plain",
            headless_display_detail="concise",
            mailbox_root=explicit_mailbox,
            declared_mailboxes=declared_mailboxes,
        )

    expected_runtime = {
        "overlay": overlay / "runtime",
        "owner": owner_runtime,
    }.get(selection, shared_runtime)
    expected_mailbox = {
        "overlay": overlay / "mailbox",
        "explicit": tmp_path / "explicit-mailbox",
        "declared": expected_runtime / "declared-mailbox",
    }.get(selection, shared_mailbox)
    assert build.call_args.args[0].runtime_root == expected_runtime
    assert start.call_args.kwargs["runtime_root"] == result.runtime_root == expected_runtime
    assert start.call_args.kwargs["mailbox_root"] == result.mailbox_root == expected_mailbox
    assert start.call_args.kwargs["project_overlay_dir"] == overlay
    assert start.call_args.kwargs["working_directory"] == working_dir
    assert start.call_args.kwargs["shared_runtime_root"] == (
        None if selection == "overlay" else expected_runtime
    )
    assert start.call_args.kwargs["shared_mailbox_root"] == (
        None if selection == "overlay" else expected_mailbox
    )


@pytest.mark.usefixtures("stub_brain_preflight")
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
                tool_params={},
                tool="codex",
                skills=(),
                setup="default",
                auth="work",
                launch_overrides=None,
                operator_prompt_mode="unattended",
                launch_env_records={"OPENAI_BASE_URL": "https://profile.example/v1"},
                mailboxes=None,
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
        agent_id_mode="name-hash",
        auth="breakglass",
        session_name="HOUMAO-repo-research-1",
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        declared_mailboxes=MailboxesDeclarativeConfig(
            offline=FilesystemMailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="alice",
                address="alice@agents.localhost",
                filesystem_root="/shared-mail-root",
            )
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
    assert build_request.mailboxes == MailboxesDeclarativeConfig(
        offline=FilesystemMailboxDeclarativeConfig(
            transport="filesystem",
            principal_id="alice",
            address="alice@agents.localhost",
            filesystem_root="/shared-mail-root",
        )
    )
    assert build_request.persistent_env_records == {
        "OPENAI_BASE_URL": "https://profile.example/v1",
        "OPENAI_ORG_ID": "org-alice",
    }
    expected_memo_file = (
        overlay_root / "memory" / "agents" / "6ee1c825367e868092eda76cb18a96e0" / "houmao-memo.md"
    ).resolve()
    assert build_request.role_prompt_override == compose_managed_launch_prompt(
        base_prompt="You are a precise repo researcher.",
        overlay_mode="append",
        overlay_text="Prefer Alice repository conventions.",
        managed_header_enabled=True,
        agent_name="repo-research-1",
        agent_id="6ee1c825367e868092eda76cb18a96e0",
        memo_file=str(expected_memo_file),
    )
    assert build_request.managed_prompt_header == {
        "version": 2,
        "enabled": True,
        "resolution_source": "default",
        "stored_policy": None,
        "agent_name": "repo-research-1",
        "agent_id": "6ee1c825367e868092eda76cb18a96e0",
        "id_provenance": "name-hash",
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


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_applies_launch_profile_memo_seed_before_build(
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
    memo_seed_root = (tmp_path / "seed").resolve()

    for path in (
        repo_root,
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
        memo_seed_root,
    ):
        path.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")
    (memo_seed_root / "houmao-memo.md").write_text(
        "Read the launch memo before doing anything else.\n",
        encoding="utf-8",
    )
    (memo_seed_root / "pages" / "checklists").mkdir(parents=True, exist_ok=True)
    (memo_seed_root / "pages" / "checklists" / "launch.md").write_text(
        "Confirm the repo target.\n",
        encoding="utf-8",
    )

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )

    captured: dict[str, object] = {}

    def _fake_build_brain_home(request: object) -> SimpleNamespace:
        captured["build_request"] = request
        agent_id = derive_agent_id_from_name("repo-research-1")
        expected_memory_root = (overlay_root / "memory" / "agents" / agent_id).resolve()
        assert (expected_memory_root / "houmao-memo.md").read_text(encoding="utf-8") == (
            "Read the launch memo before doing anything else.\n"
        )
        assert (expected_memory_root / "pages" / "checklists" / "launch.md").read_text(
            encoding="utf-8"
        ) == "Confirm the repo target.\n"
        return SimpleNamespace(manifest_path=manifest_path)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        _fake_build_brain_home,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id=derive_agent_id_from_name("repo-research-1"),
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        ),
    )

    launch_result = launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research-1",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name="HOUMAO-repo-research-1",
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        launch_profile_memo_seed=ResolvedLaunchProfileMemoSeed(
            source_kind="tree",
            content_ref=ManagedContentRef(
                content_kind="memo_seed",
                storage_kind="tree",
                relative_path="memo-seeds/launch-profiles/alice/seed",
            ),
            source_path=memo_seed_root,
        ),
    )

    build_request = captured["build_request"]
    expected_memo_file = (
        overlay_root
        / "memory"
        / "agents"
        / derive_agent_id_from_name("repo-research-1")
        / "houmao-memo.md"
    ).resolve()
    assert build_request.role_prompt_override == compose_managed_launch_prompt(
        base_prompt="You are a precise repo researcher.",
        overlay_mode=None,
        overlay_text=None,
        managed_header_enabled=True,
        agent_name="repo-research-1",
        agent_id=derive_agent_id_from_name("repo-research-1"),
        memo_file=str(expected_memo_file),
    )
    assert launch_result.memo_seed_application is not None
    assert launch_result.memo_seed_application.to_payload() == {
        "status": "applied",
        "source_kind": "tree",
        "memo_written": True,
        "page_file_count": 1,
        "page_directory_count": 1,
    }


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_seeds_profile_mail_notifier_appendix(
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
    manifest_path = default_manifest_path(
        runtime_root,
        "codex_headless",
        "codex-headless-1",
    ).resolve()

    for path in (
        repo_root,
        runtime_root,
        jobs_root,
        mailbox_root,
        overlay_root,
        working_directory,
        source_agent_def_dir,
        manifest_path.parent,
    ):
        path.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{}\n", encoding="utf-8")

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: SimpleNamespace(manifest_path=manifest_path),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id=derive_agent_id_from_name("repo-research-1"),
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(
                mailboxes=MailboxesResolvedConfig(
                    offline=MailboxSlotConfig(
                        binding=FilesystemMailboxResolvedConfig(
                            transport="filesystem",
                            principal_id="agent-seed",
                            agent_id="agent-seed",
                            binding_id="binding-seed",
                            address="seed@houmao.localhost",
                            filesystem_root=mailbox_root,
                            bindings_version="seed-revision",
                        )
                    ),
                )
            ),
        ),
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research-1",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name="HOUMAO-repo-research-1",
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        launch_profile_mail_notifier_appendix_text=(
            "Prefer urgent legal mail before routine updates."
        ),
    )

    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    record = read_gateway_mail_notifier_record(
        paths.queue_path, scope_key='["agent-seed","offline","binding-seed"]'
    )
    assert record.enabled is False
    assert record.appendix_text == "Prefer urgent legal mail before routine updates."


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_memo_only_seed_preserves_pages(
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
    memo_seed_path = (tmp_path / "seed.md").resolve()

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
    memo_seed_path.write_text("Replacement launch memo.\n", encoding="utf-8")

    agent_id = derive_agent_id_from_name("repo-research-1")
    expected_memory_root = (overlay_root / "memory" / "agents" / agent_id).resolve()
    expected_memory_root.mkdir(parents=True, exist_ok=True)
    (expected_memory_root / "houmao-memo.md").write_text("Existing memo.\n", encoding="utf-8")
    (expected_memory_root / "pages").mkdir(parents=True, exist_ok=True)
    (expected_memory_root / "pages" / "notes.md").write_text(
        "Existing page.\n",
        encoding="utf-8",
    )

    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime_root,
        jobs_root=jobs_root,
        mailbox_root=mailbox_root,
        overlay_root=overlay_root,
        source_agent_def_dir=source_agent_def_dir,
    )

    def _fake_build_brain_home(request: object) -> SimpleNamespace:
        assert (expected_memory_root / "houmao-memo.md").read_text(encoding="utf-8") == (
            "Replacement launch memo.\n"
        )
        assert (expected_memory_root / "pages" / "notes.md").read_text(encoding="utf-8") == (
            "Existing page.\n"
        )
        return SimpleNamespace(manifest_path=manifest_path)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        _fake_build_brain_home,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: SimpleNamespace(
            agent_identity="repo-research-1",
            agent_id=agent_id,
            tmux_session_name="HOUMAO-repo-research-1",
            manifest_path=manifest_path,
        ),
    )

    launch_result = launch_managed_agent_locally(
        agents="researcher",
        agent_name="repo-research-1",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name="HOUMAO-repo-research-1",
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_working_directory=repo_root,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        launch_profile_memo_seed=ResolvedLaunchProfileMemoSeed(
            source_kind="memo",
            content_ref=ManagedContentRef(
                content_kind="memo_seed",
                storage_kind="file",
                relative_path="memo-seeds/launch-profiles/alice/seed",
            ),
            source_path=memo_seed_path,
        ),
    )

    assert launch_result.memo_seed_application is not None
    assert launch_result.memo_seed_application.to_payload() == {
        "status": "applied",
        "source_kind": "memo",
        "memo_written": True,
        "page_file_count": 0,
        "page_directory_count": 0,
    }


@pytest.mark.usefixtures("stub_brain_preflight")
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
                tool_params={},
                tool="codex",
                skills=(),
                setup="default",
                auth="work",
                launch_overrides=None,
                operator_prompt_mode=None,
                launch_env_records=None,
                mailboxes=None,
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
        agent_id_mode="name-hash",
        auth=None,
        session_name="HOUMAO-codex-researcher",
        mode="headless",
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
        "version": 2,
        "enabled": False,
        "resolution_source": "launch_override",
        "stored_policy": None,
        "agent_name": "HOUMAO-codex-researcher",
        "agent_id": derive_agent_id_from_name("HOUMAO-codex-researcher"),
        "id_provenance": "name-hash",
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
            identity=SimpleNamespace(backend="codex_headless", tool="codex"),
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
            agent_id_mode="name-hash",
            auth=None,
            session_name="worker-a",
            mode="headless",
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
        )


@pytest.mark.usefixtures("stub_brain_preflight")
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
        home_path,
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
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
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
            launch_plan=SimpleNamespace(
                mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=None))
            ),
            tmux=None,
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
        agent_id_mode="name-hash",
        auth=None,
        session_name="worker-a",
        mode="headless",
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


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_reuse_home_rebuilds_stopped_predecessor_home(
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
        home_path,
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
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
        runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
        terminal=SimpleNamespace(last_session_name="HOUMAO-worker-a"),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_relaunchable_managed_agent_record_by_agent_id",
        lambda agent_id: record,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.stop_managed_agent",
        lambda target: pytest.fail("stopped preserved-home reuse should not stop a live target"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            job_dir=str(job_dir),
            launch_plan=SimpleNamespace(
                mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=None))
            ),
            tmux=None,
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
        agent_id_mode="name-hash",
        auth=None,
        session_name=None,
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        launch_profile_provenance={
            "relaunch": {
                "chat_session": {
                    "mode": "tool_last_or_new",
                }
            }
        },
        reuse_home=True,
    )

    assert captured["build_request"].home_id == "home-123"
    assert captured["build_request"].existing_home_mode is None
    assert captured["build_request"].reuse_home is True
    assert captured["build_request"].launch_profile_provenance == {
        "relaunch": {
            "chat_session": {
                "mode": "tool_last_or_new",
            }
        }
    }
    assert captured["runtime_kwargs"]["managed_force_mode"] is None
    assert captured["runtime_kwargs"]["tmux_session_name"] is None
    assert captured["runtime_kwargs"]["default_tmux_session_name"] == "HOUMAO-worker-a"
    assert "relaunch_chat_session" not in captured["runtime_kwargs"]


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_reuse_home_explicit_session_name_override_wins(
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
        home_path,
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
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
        runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
        terminal=SimpleNamespace(last_session_name="HOUMAO-worker-a"),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_relaunchable_managed_agent_record_by_agent_id",
        lambda agent_id: record,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            job_dir=str(job_dir),
            launch_plan=SimpleNamespace(
                mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=None))
            ),
            tmux=None,
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
                tmux_session_name="worker-a-debug",
                manifest_path=build_manifest_path,
            ),
        )[1],
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="worker-a",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name="worker-a-debug",
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        reuse_home=True,
    )

    assert captured["build_request"].home_id == "home-123"
    assert captured["runtime_kwargs"]["tmux_session_name"] == "worker-a-debug"
    assert captured["runtime_kwargs"]["default_tmux_session_name"] is None


def test_launch_managed_agent_locally_reuse_home_fails_without_preserved_home(
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
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_relaunchable_managed_agent_record_by_agent_id",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: pytest.fail("builder should not run without a preserved home"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: pytest.fail("runtime should not start without a preserved home"),
    )

    with pytest.raises(
        click.ClickException, match="requires one compatible stopped preserved home"
    ):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name="worker-a",
            mode="headless",
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            reuse_home=True,
        )


def test_launch_managed_agent_locally_reuse_home_rejects_live_owner_even_with_force(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_root = (tmp_path / "runtime").resolve()
    jobs_root = (tmp_path / "jobs").resolve()
    mailbox_root = (tmp_path / "mailbox").resolve()
    overlay_root = (tmp_path / "overlay").resolve()
    working_directory = (tmp_path / "workdir").resolve()
    source_agent_def_dir = (tmp_path / "agents").resolve()
    session_manifest_path = (tmp_path / "manifest.json").resolve()

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
            identity=SimpleNamespace(backend="codex_headless", tool="codex"),
            runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
            terminal=SimpleNamespace(last_session_name="HOUMAO-worker-a"),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.stop_managed_agent",
        lambda target: pytest.fail("reuse-home should not stand down a live owner"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: pytest.fail("builder should not run when reuse-home hits a live owner"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: pytest.fail("runtime should not start when reuse-home hits a live owner"),
    )

    with pytest.raises(
        click.ClickException,
        match=r"Stop the live owner before attempting `--reuse-home` restart\.",
    ):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name=None,
            mode="headless",
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="keep-stale",
            reuse_home=True,
        )


def test_launch_managed_agent_locally_rejects_reuse_home_with_clean_force(
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
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: pytest.fail("builder should not run for `--reuse-home --force clean`"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: pytest.fail("runtime should not start for `--reuse-home --force clean`"),
    )

    with pytest.raises(
        click.ClickException,
        match=r"`--reuse-home` is incompatible with `--force clean`",
    ):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name="worker-a",
            mode="headless",
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
            reuse_home=True,
        )


@pytest.mark.usefixtures("stub_brain_preflight")
def test_launch_managed_agent_locally_reuse_home_projects_current_specialist_inputs(
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
        home_path,
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
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: SimpleNamespace(
            agent_def_dir=source_agent_def_dir,
            preset=SimpleNamespace(
                tool_params={},
                tool="codex",
                skills=("notes", "mailbox"),
                setup="updated-default",
                auth="updated-auth",
                launch_overrides=None,
                operator_prompt_mode="unattended",
                launch_env_records={"PROJECT_CONTEXT": "current"},
                mailboxes=None,
                extra={"theme": "fresh"},
            ),
            preset_path=source_agent_def_dir / "presets" / "researcher-codex-default.yaml",
            role_name="researcher",
            role_prompt="You are the updated researcher.",
            tool="codex",
        ),
    )

    record = SimpleNamespace(
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
        runtime=SimpleNamespace(manifest_path=str(session_manifest_path)),
        terminal=SimpleNamespace(last_session_name="HOUMAO-worker-a"),
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_live_agent_record_by_agent_id",
        lambda agent_id: None,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_relaunchable_managed_agent_record_by_agent_id",
        lambda agent_id: record,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            job_dir=str(job_dir),
            launch_plan=SimpleNamespace(
                mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=None))
            ),
            tmux=None,
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
                tmux_session_name="HOUMAO-worker-a",
                manifest_path=build_manifest_path,
            ),
        )[1],
    )

    launch_managed_agent_locally(
        agents="researcher",
        agent_name="worker-a",
        agent_id=None,
        agent_id_mode="name-hash",
        auth=None,
        session_name=None,
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        reuse_home=True,
    )

    assert captured["build_request"].home_id == "home-123"
    assert captured["build_request"].setup == "updated-default"
    assert captured["build_request"].skills == ("notes", "mailbox")
    assert captured["build_request"].auth == "updated-auth"
    assert captured["build_request"].operator_prompt_mode == "unattended"
    assert captured["build_request"].persistent_env_records == {"PROJECT_CONTEXT": "current"}
    assert captured["build_request"].extra == {"theme": "fresh"}


@pytest.mark.usefixtures("stub_brain_preflight")
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
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
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
            launch_plan=SimpleNamespace(
                mailboxes=SimpleNamespace(offline=SimpleNamespace(binding={}))
            ),
            tmux=None,
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
            agent_id="worker-a",
            binding_id="worker-binding",
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
        agent_id_mode="name-hash",
        auth=None,
        session_name="worker-a",
        mode="headless",
        provider="codex",
        working_directory=working_directory,
        source_agent_def_dir=source_agent_def_dir,
        headless_display_style="plain",
        headless_display_detail="concise",
        force_mode="clean",
    )

    assert captured["build_request"].existing_home_mode == "clean"
    assert not session_root.exists()
    assert job_dir.exists()
    assert not private_mailbox_dir.exists()


@pytest.mark.usefixtures("stub_brain_preflight")
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
            agent_id_mode="name-hash",
            auth=None,
            session_name="worker-b",
            mode="headless",
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
        )


@pytest.mark.usefixtures("stub_brain_preflight")
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
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
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
            launch_plan=SimpleNamespace(
                mailboxes=SimpleNamespace(offline=SimpleNamespace(binding=None))
            ),
            tmux=None,
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
            agent_id_mode="name-hash",
            auth=None,
            session_name="worker-a",
            mode="headless",
            provider="codex",
            working_directory=working_directory,
            source_agent_def_dir=source_agent_def_dir,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
        )


@pytest.mark.parametrize("force_mode", ["keep-stale", "clean"])
@pytest.mark.parametrize(
    ("tool_params", "claude_version", "error"),
    [
        ({"include_partial_messages": True}, "0.1.0", "include_partial_messages.*unsupported"),
        ({"output_format": "stream-json"}, "0.1.0", "output_format.*reserved"),
        ({"session_id": None}, "0.1.0", "session_id.*reserved.*relaunch"),
        ({}, "0.1.0", "No compatible unattended launch strategy"),
        (
            {"permission_mode": "plan"},
            "2.1.296",
            "permission_mode=bypassPermissions.*direct.*as_is",
        ),
    ],
)
def test_invalid_merged_tool_params_leave_force_predecessor_intact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    force_mode: str,
    tool_params: dict[str, object],
    claude_version: str,
    error: str,
) -> None:
    """Reject reserved values and unsupported backend settings before takeover."""

    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime,
        jobs_root=tmp_path / "jobs",
        mailbox_root=tmp_path / "mail",
        overlay_root=tmp_path / "overlay",
        source_agent_def_dir=source,
    )
    from houmao.srv_ctrl.commands.agents import core
    from houmao.agents.launch_policy.models import ToolVersion

    monkeypatch.setattr(
        "houmao.agents.launch_policy.engine.detect_tool_version",
        lambda **kwargs: ToolVersion.parse(claude_version),
    )

    claude = source / "tools" / "claude"
    setup = claude / "setups" / "default"
    setup.mkdir(parents=True)
    auth_env = claude / "auth" / "work" / "env"
    auth_env.mkdir(parents=True)
    (auth_env / "vars.env").touch()
    shutil.copyfile(
        Path(__file__).resolve().parents[3] / "fixtures/plain-agent-def/tools/claude/adapter.yaml",
        claude / "adapter.yaml",
    )
    (setup / "tool-params.yaml").write_text("include_partial_messages: false\n", encoding="utf-8")
    resolve_target = core.resolve_native_launch_target

    def claude_target(**kwargs: object) -> SimpleNamespace:
        target = resolve_target(**kwargs)
        target.tool = target.preset.tool = "claude"
        return target

    monkeypatch.setattr(core, "resolve_native_launch_target", claude_target)
    previous = runtime / "previous"
    previous.mkdir(parents=True)
    (previous / "manifest.json").write_text("predecessor manifest", encoding="utf-8")
    monkeypatch.setattr(
        core,
        "_resolve_managed_predecessor_home_context",
        lambda **kwargs: SimpleNamespace(
            target=object(), home_id="previous", force_mode=force_mode
        ),
    )

    def unexpected_mutation(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid tool parameters reached runtime mutation")

    monkeypatch.setattr(core, "_perform_managed_force_takeover", unexpected_mutation)
    monkeypatch.setattr(core, "build_brain_home", unexpected_mutation)
    with pytest.raises(click.ClickException, match=error):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name=None,
            mode="tui",
            provider="claude_code",
            working_directory=tmp_path,
            source_agent_def_dir=source,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode=force_mode,
            direct_tool_params=tool_params,
        )
    assert (previous / "manifest.json").read_text(encoding="utf-8") == "predecessor manifest"
    assert list(runtime.iterdir()) == [previous]


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ('api_key = "synthetic-private";', r"Kimi TOML configuration.*config\.toml"),
        (
            'default_model = "selected"\n[models.selected]\n'
            'support_efforts = ["quick", 5]\n[providers.api]\napi_key = "synthetic-private"',
            "selected.*support_efforts",
        ),
    ],
)
def test_invalid_kimi_config_leaves_force_predecessor_intact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, content: str, error: str
) -> None:
    """Validate private Kimi TOML before stopping an existing managed agent."""

    from houmao.srv_ctrl.commands.agents import core

    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime,
        jobs_root=tmp_path / "jobs",
        mailbox_root=tmp_path / "mail",
        overlay_root=tmp_path / "overlay",
        source_agent_def_dir=source,
    )
    tool_root = source / "tools/kimi"
    (tool_root / "setups/default").mkdir(parents=True)
    auth = tool_root / "auth/work"
    (auth / "files").mkdir(parents=True)
    (auth / "env").mkdir()
    (auth / "env/vars.env").touch()
    (auth / "files/config.toml").write_text(content, encoding="utf-8")
    shutil.copyfile(
        Path(core.__file__).resolve().parents[3]
        / "project/assets/starter_agents/tools/kimi/adapter.yaml",
        tool_root / "adapter.yaml",
    )
    resolve_target = core.resolve_native_launch_target

    def kimi_target(**kwargs: object) -> SimpleNamespace:
        """Reuse the test launch target with Kimi as the selected tool."""

        target = resolve_target(**kwargs)
        target.tool = target.preset.tool = "kimi"
        return target

    monkeypatch.setattr(core, "resolve_native_launch_target", kimi_target)
    previous = runtime / "previous"
    previous.mkdir(parents=True)
    monkeypatch.setattr(
        core,
        "_resolve_managed_predecessor_home_context",
        lambda **kwargs: SimpleNamespace(target=object(), home_id="previous", force_mode="clean"),
    )
    takeover = Mock()
    builder = Mock()
    monkeypatch.setattr(core, "_perform_managed_force_takeover", takeover)
    monkeypatch.setattr(core, "build_brain_home", builder)

    with pytest.raises(click.ClickException, match=error) as raised:
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name=None,
            mode="tui",
            provider="kimi",
            working_directory=tmp_path,
            source_agent_def_dir=source,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
            direct_model_config=ModelConfig(reasoning=ModelReasoningConfig(level=2)),
        )
    takeover.assert_not_called()
    builder.assert_not_called()
    assert "synthetic-private" not in str(raised.value)
    assert list(runtime.iterdir()) == [previous]


def test_codex_service_below_minimum_leaves_force_predecessor_intact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Native service preflight still runs before forced takeover in as-is mode."""

    from houmao.srv_ctrl.commands.agents import core

    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime,
        jobs_root=tmp_path / "jobs",
        mailbox_root=tmp_path / "mail",
        overlay_root=tmp_path / "overlay",
        source_agent_def_dir=source,
    )
    previous = runtime / "previous"
    previous.mkdir(parents=True)
    (previous / "manifest.json").write_text("predecessor manifest", encoding="utf-8")
    executable = tmp_path / "codex"
    executable.write_text("#!/bin/sh\nprintf 'codex-cli 0.168.0\\n'\n", encoding="utf-8")
    executable.chmod(0o700)
    monkeypatch.setattr(
        core,
        "validate_brain_inputs",
        lambda *args, **kwargs: SimpleNamespace(
            adapter=SimpleNamespace(launch_executable=str(executable))
        ),
    )
    monkeypatch.setattr(
        core,
        "_resolve_managed_predecessor_home_context",
        lambda **kwargs: SimpleNamespace(target=object(), home_id="previous", force_mode="clean"),
    )
    monkeypatch.setattr(
        core,
        "_perform_managed_force_takeover",
        lambda *args, **kwargs: pytest.fail("Below-minimum service reached force takeover"),
    )
    monkeypatch.setattr(
        core,
        "build_brain_home",
        lambda *args, **kwargs: pytest.fail("Below-minimum service reached home construction"),
    )

    with pytest.raises(click.ClickException, match=r"codex_app_server.*>=0\.169\.0.*0\.168\.0"):
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name=None,
            mode="service",
            provider="codex",
            operator_prompt_mode="as_is",
            working_directory=tmp_path,
            source_agent_def_dir=source,
            headless_display_style="plain",
            headless_display_detail="concise",
            force_mode="clean",
        )
    assert (previous / "manifest.json").read_text(encoding="utf-8") == "predecessor manifest"


@pytest.mark.parametrize(
    ("mode", "error"),
    [("service", "Hermes was not found on PATH in execution context"), ("web", "does not support")],
)
def test_hermes_launch_preflight_preserves_existing_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mode: str, error: str
) -> None:
    """Refuse unsupported modes and a missing executable before touching the predecessor."""

    from houmao.srv_ctrl.commands.agents import core

    source = tmp_path / "source"
    runtime = tmp_path / "runtime"
    workdir = tmp_path / "workspace"
    workdir.mkdir()
    _install_basic_launch_patches(
        monkeypatch,
        runtime_root=runtime,
        jobs_root=tmp_path / "jobs",
        mailbox_root=tmp_path / "mail",
        overlay_root=tmp_path / "overlay",
        source_agent_def_dir=source,
    )
    resolve_target = core.resolve_native_launch_target

    def hermes_target(**kwargs: object) -> SimpleNamespace:
        """Select Hermes while relying on the normal launch-mode validation."""

        target = resolve_target(**kwargs)
        target.tool = target.preset.tool = "hermes"
        return target

    monkeypatch.setattr(core, "resolve_native_launch_target", hermes_target)
    predecessor = runtime / "existing"
    predecessor.mkdir(parents=True)
    manifest = predecessor / "manifest.json"
    manifest.write_text("existing manifest", encoding="utf-8")
    probes = [Mock() for _ in range(3)]
    for name, probe in zip(
        ("_resolve_managed_predecessor_home_context", "build_brain_home", "start_runtime_session"),
        probes,
        strict=True,
    ):
        monkeypatch.setattr(core, name, probe)
    with pytest.raises(click.ClickException, match=error) as raised:
        launch_managed_agent_locally(
            agents="researcher",
            agent_name="worker-a",
            agent_id=None,
            agent_id_mode="name-hash",
            auth=None,
            session_name=None,
            mode=mode,
            provider="hermes",
            working_directory=workdir,
            source_agent_def_dir=source,
            source_env={"PATH": str(tmp_path / "missing-path")},
            headless_display_style=None,
            headless_display_detail=None,
            force_mode="clean",
        )
    if mode == "service":
        assert f"in execution context {workdir}" in str(raised.value)
        assert "command -v hermes" in str(raised.value)
    assert manifest.read_text(encoding="utf-8") == "existing manifest"
    assert list(runtime.iterdir()) == [predecessor]
    for probe in probes:
        probe.assert_not_called()
