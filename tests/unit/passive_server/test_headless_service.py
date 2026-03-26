"""Focused tests for passive-server managed headless behavior."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.errors import LaunchPlanError, SessionManifestError
from houmao.agents.realm_controller.models import SessionEvent
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.discovery import DiscoveredAgent, _summary_from_record
from houmao.passive_server.headless import HeadlessAgentService
from houmao.passive_server.models import (
    PassiveAgentActionResponse,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnRequest,
)
from houmao.passive_server.service import PassiveServerService
from houmao.server.managed_agents import ManagedHeadlessAuthorityRecord
from houmao.server.models import HoumaoHeadlessLaunchMailboxOptions
from tests.unit.passive_server.test_discovery import _make_record


def _make_service(tmp_path: Path) -> PassiveServerService:
    """Build a passive-server service with an isolated runtime root."""

    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=tmp_path,
    )
    return PassiveServerService(config=config)


def _write_launch_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create minimal on-disk launch inputs for headless tests."""

    workdir = tmp_path / "workspace"
    agent_def_dir = tmp_path / "agent-defs"
    manifest_path = tmp_path / "brain.yaml"
    workdir.mkdir()
    agent_def_dir.mkdir()
    manifest_path.write_text("inputs:\n  tool: claude\n", encoding="utf-8")
    return workdir, agent_def_dir, manifest_path


def _launch_request(
    tmp_path: Path,
    *,
    tool: str = "claude",
    role_name: str | None = "gpu-kernel-coder",
    agent_name: str | None = "AGENTSYS-alpha",
    agent_id: str | None = "published-alpha",
    mailbox: HoumaoHeadlessLaunchMailboxOptions | None = None,
) -> PassiveHeadlessLaunchRequest:
    """Build one launch request with real temporary paths."""

    workdir, agent_def_dir, manifest_path = _write_launch_inputs(tmp_path)
    return PassiveHeadlessLaunchRequest(
        tool=tool,
        working_directory=str(workdir),
        agent_def_dir=str(agent_def_dir),
        brain_manifest_path=str(manifest_path),
        role_name=role_name,
        agent_name=agent_name,
        agent_id=agent_id,
        mailbox=mailbox,
    )


class _FakeHeadlessBackendSession(HeadlessInteractiveSession):
    """Minimal headless backend session for passive-server tests."""

    def __init__(self, send_prompt_callback=None) -> None:
        self.m_send_prompt_callback = send_prompt_callback or (lambda *_args, **_kwargs: [])

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
    ) -> list[SessionEvent]:
        return list(
            self.m_send_prompt_callback(
                prompt,
                turn_artifact_dir_name=turn_artifact_dir_name,
            )
        )

    def interrupt(self) -> SimpleNamespace:
        return SimpleNamespace(detail="ctrl-c")

    def close(self) -> None:
        return None


class _FakeRuntimeController:
    """Simple runtime-controller stand-in for passive-server tests."""

    def __init__(
        self,
        *,
        manifest_path: Path,
        tmux_session_name: str = "AGENTSYS-alpha",
        agent_identity: str = "AGENTSYS-alpha",
        agent_id: str = "published-alpha",
        backend_session: HeadlessInteractiveSession | None = None,
        registry_record: object | None = None,
        registry_launch_authority: str = "external",
        output_format: str = "stream-json",
    ) -> None:
        self.manifest_path = manifest_path
        self.job_dir = manifest_path.parent
        self.tmux_session_name = tmux_session_name
        self.agent_identity = agent_identity
        self.agent_id = agent_id
        self.backend_session = backend_session or _FakeHeadlessBackendSession()
        self.launch_plan = SimpleNamespace(metadata={"headless_output_format": output_format})
        self.registry_launch_authority = registry_launch_authority
        self.m_registry_record = registry_record if registry_record is not None else object()
        self.stop_calls: list[bool] = []

    def build_shared_registry_record(self) -> object:
        return self.m_registry_record

    def stop(self, *, force_cleanup: bool = False) -> SimpleNamespace:
        self.stop_calls.append(force_cleanup)
        return SimpleNamespace(status="ok")


def _seed_managed_handle(
    svc: PassiveServerService,
    *,
    tracked_agent_id: str = "tracked-alpha",
    agent_name: str = "AGENTSYS-alpha",
    agent_id: str = "published-alpha",
    controller: _FakeRuntimeController | None = None,
) -> ManagedHeadlessAuthorityRecord:
    """Seed one managed headless authority plus in-memory handle."""

    authority = ManagedHeadlessAuthorityRecord(
        tracked_agent_id=tracked_agent_id,
        backend="claude_headless",
        tool="claude",
        manifest_path=str(
            svc.m_config.runtime_root / "runtime" / tracked_agent_id / "manifest.json"
        ),
        session_root=str(svc.m_config.runtime_root / "runtime" / tracked_agent_id),
        tmux_session_name=f"{agent_name}-tmux",
        agent_def_dir=str(svc.m_config.runtime_root / "agent-defs"),
        agent_name=agent_name,
        agent_id=agent_id,
        created_at_utc="2026-03-20T09:00:00+00:00",
        updated_at_utc="2026-03-20T09:00:00+00:00",
    )
    svc.m_headless.m_store.write_authority(authority)
    svc.m_headless.m_handles[tracked_agent_id] = SimpleNamespace(
        authority=authority,
        controller=controller
        or _FakeRuntimeController(manifest_path=Path(authority.manifest_path)),
        turn_worker=None,
    )
    return authority


def _populate_discovery(
    svc: PassiveServerService,
    *,
    agent_id: str,
    agent_name: str,
    session_name: str | None = None,
) -> None:
    """Populate the passive discovery index with one discovered agent."""

    record = _make_record(
        agent_id=agent_id,
        agent_name=agent_name,
        session_name=session_name or f"{agent_name}-{agent_id}",
    )
    agent = DiscoveredAgent(record=record, summary=_summary_from_record(record))
    svc.m_discovery.m_index.replace({agent_id: agent})


def _join_turn_worker(headless: HeadlessAgentService, tracked_agent_id: str) -> None:
    """Wait for one background turn worker to finish."""

    handle = headless._require_handle(tracked_agent_id)
    assert handle is not None
    assert handle.turn_worker is not None
    handle.turn_worker.join(timeout=2.0)
    assert not handle.turn_worker.is_alive()


class TestHeadlessLaunch:
    """Launch publication, rollback, and validation behavior."""

    def test_launch_publishes_shared_registry_record(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        request = _launch_request(tmp_path)
        runtime_manifest_path = tmp_path / "runtime" / "tracked-alpha" / "manifest.json"
        runtime_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        controller = _FakeRuntimeController(
            manifest_path=runtime_manifest_path,
            agent_identity="AGENTSYS-alpha",
            agent_id="published-alpha",
            registry_record=SimpleNamespace(agent_id="published-alpha"),
        )
        published: list[object] = []

        monkeypatch.setattr(
            "houmao.passive_server.headless.load_brain_manifest",
            lambda _path: {"inputs": {"tool": "claude"}},
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.load_role_package",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.start_runtime_session",
            lambda **_kwargs: controller,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.publish_live_agent_record",
            lambda record: published.append(record),
        )

        response = svc.m_headless.launch(request)

        assert response.status == "ok"
        assert response.agent_name == "AGENTSYS-alpha"
        assert published == [controller.m_registry_record]
        authority = svc.m_headless.m_store.read_authority(
            tracked_agent_id=response.tracked_agent_id
        )
        assert authority is not None
        assert authority.agent_id == "published-alpha"
        assert (
            svc.m_headless.resolve_managed_tracked_id("published-alpha")
            == response.tracked_agent_id
        )

    def test_launch_rolls_back_when_registry_publish_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        request = _launch_request(tmp_path)
        runtime_manifest_path = tmp_path / "runtime" / "tracked-alpha" / "manifest.json"
        runtime_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        controller = _FakeRuntimeController(manifest_path=runtime_manifest_path)

        monkeypatch.setattr(
            "houmao.passive_server.headless.load_brain_manifest",
            lambda _path: {"inputs": {"tool": "claude"}},
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.load_role_package",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.start_runtime_session",
            lambda **_kwargs: controller,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.publish_live_agent_record",
            MagicMock(side_effect=SessionManifestError("publish failed")),
        )

        response = svc.m_headless.launch(request)

        assert response == (
            503,
            {
                "detail": (
                    "Managed headless launch could not publish shared-registry state: "
                    "publish failed"
                )
            },
        )
        assert controller.stop_calls == [True]
        assert svc.m_headless.m_store.list_authority_records() == []

    def test_launch_rejects_manifest_tool_mismatch_with_422(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        request = _launch_request(tmp_path, tool="claude", role_name=None)

        monkeypatch.setattr(
            "houmao.passive_server.headless.load_brain_manifest",
            lambda _path: {"inputs": {"tool": "codex"}},
        )

        response = svc.m_headless.launch(request)

        assert isinstance(response, tuple)
        assert response[0] == 422
        assert "inputs.tool" in response[1]["detail"]

    def test_launch_rejects_invalid_role_with_422(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        request = _launch_request(tmp_path, role_name="missing-role")

        monkeypatch.setattr(
            "houmao.passive_server.headless.load_brain_manifest",
            lambda _path: {"inputs": {"tool": "claude"}},
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.load_role_package",
            MagicMock(side_effect=LaunchPlanError("Unknown role `missing-role`.")),
        )

        response = svc.m_headless.launch(request)

        assert response == (422, {"detail": "Unknown role `missing-role`."})

    def test_launch_returns_422_for_runtime_validation_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        request = _launch_request(tmp_path)

        monkeypatch.setattr(
            "houmao.passive_server.headless.load_brain_manifest",
            lambda _path: {"inputs": {"tool": "claude"}},
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.load_role_package",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.start_runtime_session",
            MagicMock(side_effect=SessionManifestError("mailbox validation failed")),
        )

        response = svc.m_headless.launch(request)

        assert response == (422, {"detail": "mailbox validation failed"})

    def test_launch_forwards_stalwart_mailbox_options(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        mailbox_root = tmp_path / "mailbox-root"
        request = _launch_request(
            tmp_path,
            mailbox=HoumaoHeadlessLaunchMailboxOptions(
                transport="stalwart",
                filesystem_root=str(mailbox_root),
                principal_id="principal-1",
                address="agent@example.com",
                stalwart_base_url="https://stalwart.example.test",
                stalwart_jmap_url="https://stalwart.example.test/jmap",
                stalwart_management_url="https://stalwart.example.test/manage",
                stalwart_login_identity="agent@example.com",
            ),
        )
        runtime_manifest_path = tmp_path / "runtime" / "tracked-alpha" / "manifest.json"
        runtime_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        controller = _FakeRuntimeController(manifest_path=runtime_manifest_path)
        recorded_start_kwargs: dict[str, object] = {}

        monkeypatch.setattr(
            "houmao.passive_server.headless.load_brain_manifest",
            lambda _path: {"inputs": {"tool": "claude"}},
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.load_role_package",
            lambda *_args, **_kwargs: None,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.start_runtime_session",
            lambda **kwargs: recorded_start_kwargs.update(kwargs) or controller,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.publish_live_agent_record",
            lambda _record: None,
        )

        response = svc.m_headless.launch(request)

        assert response.status == "ok"
        assert recorded_start_kwargs["mailbox_transport"] == "stalwart"
        assert recorded_start_kwargs["mailbox_root"] == mailbox_root.resolve()
        assert recorded_start_kwargs["mailbox_principal_id"] == "principal-1"
        assert recorded_start_kwargs["mailbox_address"] == "agent@example.com"
        assert recorded_start_kwargs["mailbox_stalwart_base_url"] == "https://stalwart.example.test"
        assert (
            recorded_start_kwargs["mailbox_stalwart_jmap_url"]
            == "https://stalwart.example.test/jmap"
        )
        assert (
            recorded_start_kwargs["mailbox_stalwart_management_url"]
            == "https://stalwart.example.test/manage"
        )
        assert recorded_start_kwargs["mailbox_stalwart_login_identity"] == "agent@example.com"


class TestManagedHeadlessRouting:
    """Passive-server routing through authoritative managed headless ids."""

    def test_submit_turn_accepts_custom_published_agent_id(
        self,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        _seed_managed_handle(
            svc,
            tracked_agent_id="tracked-alpha",
            agent_name="AGENTSYS-alpha",
            agent_id="published-custom",
        )
        _populate_discovery(
            svc,
            agent_id="published-custom",
            agent_name="AGENTSYS-alpha",
        )
        svc.m_headless.submit_turn = MagicMock(
            return_value=PassiveHeadlessTurnAcceptedResponse(
                tracked_agent_id="tracked-alpha",
                turn_id="turn-001",
                turn_index=1,
                turn_status="active",
                detail="accepted",
            )
        )

        response = svc.submit_turn(
            "published-custom",
            PassiveHeadlessTurnRequest(prompt="hello"),
        )

        assert response.status == "ok"
        svc.m_headless.submit_turn.assert_called_once_with("tracked-alpha", "hello")

    def test_interrupt_and_stop_accept_tracked_and_published_refs(
        self,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        _seed_managed_handle(
            svc,
            tracked_agent_id="tracked-alpha",
            agent_name="AGENTSYS-alpha",
            agent_id="published-custom",
        )
        _populate_discovery(
            svc,
            agent_id="published-custom",
            agent_name="AGENTSYS-alpha",
        )
        svc.m_headless.interrupt_managed = MagicMock(
            return_value=PassiveAgentActionResponse(
                agent_id="tracked-alpha",
                detail="interrupt sent",
            )
        )
        svc.m_headless.stop_managed = MagicMock(
            return_value=PassiveAgentActionResponse(
                agent_id="tracked-alpha",
                detail="stopped",
            )
        )

        interrupt_response = svc.interrupt_agent("tracked-alpha")
        stop_response = svc.stop_agent("published-custom")

        assert interrupt_response.status == "ok"
        assert stop_response.status == "ok"
        svc.m_headless.interrupt_managed.assert_called_once_with("tracked-alpha")
        svc.m_headless.stop_managed.assert_called_once_with("tracked-alpha")


class TestRestartResume:
    """Rebuild/resume behavior for persisted managed headless authorities."""

    def test_restart_resumes_live_authority_into_operable_controller(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        agent_def_dir = tmp_path / "agent-defs"
        manifest_path = tmp_path / "runtime" / "tracked-alpha" / "manifest.json"
        agent_def_dir.mkdir()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}\n", encoding="utf-8")

        def _send_prompt(
            _prompt: str,
            *,
            turn_artifact_dir_name: str | None = None,
        ) -> list[SessionEvent]:
            assert turn_artifact_dir_name is not None
            turn_dir = (
                svc.m_headless.m_store.agent_root(tracked_agent_id="tracked-alpha")
                / "artifacts"
                / turn_artifact_dir_name
            )
            turn_dir.mkdir(parents=True, exist_ok=True)
            (turn_dir / "stdout.jsonl").write_text(
                '{"type":"assistant","message":"hello after resume"}\n',
                encoding="utf-8",
            )
            (turn_dir / "stderr.log").write_text("", encoding="utf-8")
            (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")
            return [
                SessionEvent(
                    kind="done",
                    message="turn completed",
                    turn_index=1,
                    payload={"completion_source": "tmux_wait_for"},
                )
            ]

        controller = _FakeRuntimeController(
            manifest_path=manifest_path,
            agent_identity="AGENTSYS-alpha",
            agent_id="published-custom",
            backend_session=_FakeHeadlessBackendSession(send_prompt_callback=_send_prompt),
        )

        svc.m_headless.m_store.write_authority(
            ManagedHeadlessAuthorityRecord(
                tracked_agent_id="tracked-alpha",
                backend="claude_headless",
                tool="claude",
                manifest_path=str(manifest_path),
                session_root=str(manifest_path.parent),
                tmux_session_name="AGENTSYS-alpha",
                agent_def_dir=str(agent_def_dir),
                agent_name="AGENTSYS-alpha",
                agent_id="published-custom",
                created_at_utc="2026-03-20T09:00:00+00:00",
                updated_at_utc="2026-03-20T09:00:00+00:00",
            )
        )

        monkeypatch.setattr(
            "houmao.passive_server.headless.tmux_session_exists",
            lambda **_kwargs: True,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.resume_runtime_session",
            lambda **_kwargs: controller,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.publish_live_agent_record",
            lambda _record: None,
        )

        svc.m_headless.start()
        accepted = svc.m_headless.submit_turn("tracked-alpha", "hello after restart")
        _join_turn_worker(svc.m_headless, "tracked-alpha")

        assert accepted.status == "ok"
        assert svc.m_headless.resolve_managed_tracked_id("published-custom") == "tracked-alpha"

    def test_restart_cleans_stale_authority_when_resume_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)
        agent_def_dir = tmp_path / "agent-defs"
        manifest_path = tmp_path / "runtime" / "tracked-alpha" / "manifest.json"
        agent_def_dir.mkdir()
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}\n", encoding="utf-8")
        svc.m_headless.m_store.write_authority(
            ManagedHeadlessAuthorityRecord(
                tracked_agent_id="tracked-alpha",
                backend="claude_headless",
                tool="claude",
                manifest_path=str(manifest_path),
                session_root=str(manifest_path.parent),
                tmux_session_name="AGENTSYS-alpha",
                agent_def_dir=str(agent_def_dir),
                agent_name="AGENTSYS-alpha",
                agent_id="published-custom",
                created_at_utc="2026-03-20T09:00:00+00:00",
                updated_at_utc="2026-03-20T09:00:00+00:00",
            )
        )
        removed: list[str] = []

        monkeypatch.setattr(
            "houmao.passive_server.headless.tmux_session_exists",
            lambda **_kwargs: True,
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.resume_runtime_session",
            MagicMock(side_effect=SessionManifestError("broken runtime state")),
        )
        monkeypatch.setattr(
            "houmao.passive_server.headless.remove_live_agent_record",
            lambda agent_id: removed.append(agent_id),
        )

        svc.m_headless.start()

        assert svc.m_headless._require_handle("tracked-alpha") is None
        assert svc.m_headless.m_store.read_authority(tracked_agent_id="tracked-alpha") is None
        assert removed == ["published-custom"]


class TestTurnFinalization:
    """Turn completion refresh from durable artifacts."""

    def test_completed_turn_persists_artifacts_and_loads_events(
        self,
        tmp_path: Path,
    ) -> None:
        svc = _make_service(tmp_path)

        def _send_prompt(
            _prompt: str,
            *,
            turn_artifact_dir_name: str | None = None,
        ) -> list[SessionEvent]:
            assert turn_artifact_dir_name is not None
            turn_dir = (
                svc.m_headless.m_store.agent_root(tracked_agent_id="tracked-alpha")
                / "artifacts"
                / turn_artifact_dir_name
            )
            turn_dir.mkdir(parents=True, exist_ok=True)
            (turn_dir / "stdout.jsonl").write_text(
                '{"type":"assistant","message":"hello from worker"}\n',
                encoding="utf-8",
            )
            (turn_dir / "stderr.log").write_text("warning line\n", encoding="utf-8")
            (turn_dir / "exitcode").write_text("0\n", encoding="utf-8")
            return [
                SessionEvent(
                    kind="done",
                    message="turn completed",
                    turn_index=1,
                    payload={"completion_source": "tmux_wait_for"},
                )
            ]

        authority = _seed_managed_handle(
            svc,
            tracked_agent_id="tracked-alpha",
            agent_name="AGENTSYS-alpha",
            agent_id="published-alpha",
            controller=_FakeRuntimeController(
                manifest_path=tmp_path / "runtime" / "tracked-alpha" / "manifest.json",
                backend_session=_FakeHeadlessBackendSession(send_prompt_callback=_send_prompt),
            ),
        )

        accepted = svc.m_headless.submit_turn(authority.tracked_agent_id, "hello")
        _join_turn_worker(svc.m_headless, authority.tracked_agent_id)

        status = svc.m_headless.turn_status(authority.tracked_agent_id, accepted.turn_id)
        events = svc.m_headless.turn_events(authority.tracked_agent_id, accepted.turn_id)
        stdout_text = svc.m_headless.turn_artifact_text(
            authority.tracked_agent_id,
            accepted.turn_id,
            "stdout",
        )
        stderr_text = svc.m_headless.turn_artifact_text(
            authority.tracked_agent_id,
            accepted.turn_id,
            "stderr",
        )

        assert status.status == "completed"
        assert status.returncode == 0
        assert status.completion_source == "tmux_wait_for"
        assert status.stdout_path is not None
        assert status.stderr_path is not None
        turn_record = svc.m_headless.m_store.read_turn_record(
            tracked_agent_id=authority.tracked_agent_id,
            turn_id=accepted.turn_id,
        )
        assert turn_record is not None
        assert turn_record.status_path is not None
        assert [entry.kind for entry in events.entries] == ["assistant"]
        assert events.entries[0].message == "hello from worker"
        assert "hello from worker" in stdout_text
        assert stderr_text == "warning line\n"
