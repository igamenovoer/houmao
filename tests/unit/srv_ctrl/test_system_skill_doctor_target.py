"""Managed-agent target resolution coverage for system-skill doctor."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller.errors import SessionManifestError
import houmao.srv_ctrl.system_skill_doctor_target as target_module
from houmao.srv_ctrl.system_skill_doctor_target import (
    SystemSkillDoctorTargetError,
    resolve_managed_system_skill_doctor_target,
)


def _record(
    *,
    agent_id: str = "agent-id",
    agent_name: str = "HOUMAO-worker",
    tool: str = "codex",
    state: str = "stopped",
    manifest_path: Path,
) -> SimpleNamespace:
    """Return the registry fields used by target resolution."""

    return SimpleNamespace(
        agent_id=agent_id,
        agent_name=agent_name,
        identity=SimpleNamespace(tool=tool),
        lifecycle=SimpleNamespace(state=state),
        runtime=SimpleNamespace(manifest_path=str(manifest_path)),
    )


def _configure_authority(
    monkeypatch: pytest.MonkeyPatch,
    *,
    record: SimpleNamespace,
    home: Path,
) -> None:
    """Provide matching session and brain authority around one record."""

    brain_manifest_path = home.parent / "brain-manifest.yaml"
    monkeypatch.setattr(
        target_module,
        "load_session_manifest",
        lambda path: SimpleNamespace(path=path, payload={"schema_version": 4}),
    )
    monkeypatch.setattr(
        target_module,
        "parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            agent_id=record.agent_id,
            tool=record.identity.tool,
            brain_manifest_path=str(brain_manifest_path),
        ),
    )
    monkeypatch.setattr(
        target_module,
        "load_brain_manifest",
        lambda path: {"runtime": {"home_path": str(home)}},
    )


def test_target_resolves_stopped_agent_by_authoritative_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    record = _record(manifest_path=tmp_path / "manifest.json")
    monkeypatch.setattr(
        target_module, "load_managed_agent_record_by_agent_id", lambda *a, **k: record
    )
    _configure_authority(monkeypatch, record=record, home=home)

    target = resolve_managed_system_skill_doctor_target(
        agent_id=record.agent_id,
        agent_name=None,
    )

    assert target.kind == "managed-agent"
    assert target.agent_id == record.agent_id
    assert target.lifecycle_state == "stopped"
    assert target.tool == "codex"
    assert target.home_path == home.resolve()


def test_target_resolves_unique_friendly_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    record = _record(manifest_path=tmp_path / "manifest.json")
    monkeypatch.setattr(
        target_module,
        "resolve_managed_agent_records_by_name",
        lambda *a, **k: (record,),
    )
    _configure_authority(monkeypatch, record=record, home=home)

    target = resolve_managed_system_skill_doctor_target(
        agent_id=None,
        agent_name=record.agent_name,
    )

    assert target.agent_id == record.agent_id
    assert target.agent_name == record.agent_name


def test_target_rejects_ambiguous_friendly_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = (
        _record(agent_id="agent-one", manifest_path=tmp_path / "one.json"),
        _record(agent_id="agent-two", manifest_path=tmp_path / "two.json"),
    )
    monkeypatch.setattr(
        target_module,
        "resolve_managed_agent_records_by_name",
        lambda *a, **k: records,
    )

    with pytest.raises(SystemSkillDoctorTargetError, match="ambiguous.*--agent-id"):
        resolve_managed_system_skill_doctor_target(
            agent_id=None,
            agent_name="HOUMAO-worker",
        )


def test_target_rejects_external_agent_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        target_module,
        "load_managed_agent_record_by_agent_id",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        target_module,
        "load_external_managed_agent_record_by_agent_id",
        lambda *a, **k: object(),
    )

    with pytest.raises(SystemSkillDoctorTargetError, match="external"):
        resolve_managed_system_skill_doctor_target(agent_id="external-id", agent_name=None)


def test_target_rejects_stale_session_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = _record(manifest_path=tmp_path / "missing.json")
    monkeypatch.setattr(
        target_module, "load_managed_agent_record_by_agent_id", lambda *a, **k: record
    )

    def _fail(path: Path) -> object:
        raise SessionManifestError(f"Session manifest not found: {path}")

    monkeypatch.setattr(target_module, "load_session_manifest", _fail)

    with pytest.raises(SystemSkillDoctorTargetError, match="session-manifest authority"):
        resolve_managed_system_skill_doctor_target(agent_id=record.agent_id, agent_name=None)


def test_target_rejects_missing_persistent_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "missing-home"
    record = _record(manifest_path=tmp_path / "manifest.json")
    monkeypatch.setattr(
        target_module, "load_managed_agent_record_by_agent_id", lambda *a, **k: record
    )
    _configure_authority(monkeypatch, record=record, home=home)

    with pytest.raises(SystemSkillDoctorTargetError, match="Persistent home.*missing"):
        resolve_managed_system_skill_doctor_target(agent_id=record.agent_id, agent_name=None)
