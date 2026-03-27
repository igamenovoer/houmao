from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.models import (
    HeadlessResumeSelection,
    JoinedLaunchEnvBinding,
    SessionControlResult,
)
from houmao.agents.realm_controller.registry_storage import JOINED_REGISTRY_SENTINEL_LEASE_TTL
from houmao.agents.realm_controller.runtime import resume_runtime_session
from houmao.agents.realm_controller import runtime as runtime_module
from houmao.srv_ctrl.commands import runtime_artifacts as runtime_artifacts_module


def test_materialize_joined_tui_unavailable_publishes_sentinel_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    published: dict[str, object] = {}
    published_env: dict[str, str] = {}

    monkeypatch.setattr(
        runtime_artifacts_module,
        "ensure_gateway_capability",
        lambda publication: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "set_tmux_session_environment",
        lambda *, session_name, env_vars: published_env.update(env_vars),
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "publish_live_agent_record",
        lambda record: published.setdefault("record", record) or record,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "read_tmux_session_environment_value",
        lambda *, session_name, variable_name: None,
    )

    result = runtime_artifacts_module.materialize_joined_launch(
        runtime_root=tmp_path,
        agent_name="coder",
        agent_id=None,
        provider="codex",
        headless=False,
        tmux_session_name="join-sess",
        tmux_window_name="manual",
        working_directory=tmp_path,
        launch_args=(),
        launch_env=(),
        resume_selection=None,
    )

    payload = parse_session_manifest_payload(
        load_session_manifest(result.manifest_path).payload,
        source=str(result.manifest_path),
    )
    assert payload.agent_launch_authority is not None
    assert payload.agent_launch_authority.session_origin == "joined_tmux"
    assert payload.agent_launch_authority.posture_kind == "unavailable"
    assert payload.tmux is not None
    assert payload.tmux.primary_window_name == "manual"
    record = published["record"]
    assert record is not None
    published_at = datetime.fromisoformat(record.published_at)
    lease_expires_at = datetime.fromisoformat(record.lease_expires_at)
    assert lease_expires_at - published_at == JOINED_REGISTRY_SENTINEL_LEASE_TTL
    assert published_env["AGENTSYS_MANIFEST_PATH"] == str(result.manifest_path)
    assert published_env["AGENTSYS_AGENT_ID"] == result.agent_id


@pytest.mark.parametrize(
    ("resume_selection", "expected_kind", "expected_value"),
    [
        (HeadlessResumeSelection(kind="exact", value="thread_123"), "exact", "thread_123"),
        (HeadlessResumeSelection(kind="last"), "last", None),
        (HeadlessResumeSelection(kind="none"), "none", None),
    ],
)
def test_materialize_joined_headless_persists_resume_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resume_selection: HeadlessResumeSelection,
    expected_kind: str,
    expected_value: str | None,
) -> None:
    monkeypatch.setattr(
        runtime_artifacts_module,
        "ensure_gateway_capability",
        lambda publication: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "set_tmux_session_environment",
        lambda *, session_name, env_vars: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "publish_live_agent_record",
        lambda record: record,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "read_tmux_session_environment_value",
        lambda *, session_name, variable_name: (
            str((tmp_path / "codex-home").resolve()) if variable_name == "CODEX_HOME" else None
        ),
    )

    result = runtime_artifacts_module.materialize_joined_launch(
        runtime_root=tmp_path,
        agent_name="reviewer",
        agent_id=None,
        provider="codex",
        headless=True,
        tmux_session_name="join-sess",
        tmux_window_name="shell",
        working_directory=tmp_path,
        launch_args=("exec", "--json"),
        launch_env=(),
        resume_selection=resume_selection,
    )

    payload = parse_session_manifest_payload(
        load_session_manifest(result.manifest_path).payload,
        source=str(result.manifest_path),
    )
    assert payload.headless is not None
    assert payload.headless.resume_selection_kind == expected_kind
    assert payload.headless.resume_selection_value == expected_value
    assert payload.agent_launch_authority is not None
    assert payload.agent_launch_authority.posture_kind == "headless_launch_options"
    assert payload.agent_launch_authority.launch_args == ["exec", "--json"]


@pytest.mark.parametrize(
    ("launch_args", "launch_env", "expected_success"),
    [
        ((), (), False),
        (
            ("--model", "gpt-5"),
            (JoinedLaunchEnvBinding(mode="literal", name="CODEX_HOME", value="/tmp/codex-home"),),
            True,
        ),
    ],
)
def test_joined_tui_relaunch_respects_unavailable_vs_launchable_posture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launch_args: tuple[str, ...],
    launch_env: tuple[JoinedLaunchEnvBinding, ...],
    expected_success: bool,
) -> None:
    monkeypatch.setattr(
        runtime_artifacts_module,
        "ensure_gateway_capability",
        lambda publication: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "set_tmux_session_environment",
        lambda *, session_name, env_vars: None,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "publish_live_agent_record",
        lambda record: record,
    )
    monkeypatch.setattr(
        runtime_artifacts_module,
        "read_tmux_session_environment_value",
        lambda *, session_name, variable_name: (
            "/tmp/codex-home" if variable_name == "CODEX_HOME" else None
        ),
    )

    result = runtime_artifacts_module.materialize_joined_launch(
        runtime_root=tmp_path,
        agent_name="coder",
        agent_id=None,
        provider="codex",
        headless=False,
        tmux_session_name="join-sess",
        tmux_window_name="manual",
        working_directory=tmp_path,
        launch_args=launch_args,
        launch_env=launch_env,
        resume_selection=None,
    )

    class _FakeBackendSession:
        def __init__(self) -> None:
            self.updated_launch_plans: list[object] = []

        def update_launch_plan(self, launch_plan: object) -> None:
            self.updated_launch_plans.append(launch_plan)

    fake_backend = _FakeBackendSession()
    monkeypatch.setattr(
        runtime_module.RuntimeSessionController,
        "ensure_gateway_capability",
        lambda self, **kwargs: None,
    )
    monkeypatch.setattr(
        runtime_module,
        "_create_backend_session",
        lambda **kwargs: fake_backend,
    )
    monkeypatch.setattr(
        runtime_module, "_refresh_pair_launch_registration", lambda controller: None
    )
    monkeypatch.setattr(runtime_module, "publish_live_agent_record", lambda record: record)
    monkeypatch.setattr(
        runtime_module, "resolve_live_agent_record_by_agent_id", lambda agent_id: None
    )
    monkeypatch.setattr(
        runtime_module,
        "_relaunch_backend_session",
        lambda controller: SessionControlResult(  # type: ignore[arg-type]
            status="ok",
            action="relaunch",
            detail="relaunched",
        ),
    )

    controller = resume_runtime_session(
        agent_def_dir=(result.session_root / "agent_def").resolve(),
        session_manifest_path=result.manifest_path,
    )
    relaunch_result = controller.relaunch()

    assert (relaunch_result.status == "ok") is expected_success
    if expected_success:
        assert relaunch_result.detail == "relaunched"
        assert fake_backend.updated_launch_plans
    else:
        assert "relaunch is unavailable" in relaunch_result.detail
