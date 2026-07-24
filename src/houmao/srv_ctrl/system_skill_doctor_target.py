"""Authoritative managed-agent target resolution for system-skill doctor."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.errors import BrainLaunchRuntimeError
from houmao.agents.realm_controller.loaders import load_brain_manifest
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.registry_models import ManagedAgentRegistryRecordV3
from houmao.agents.realm_controller.registry_storage import (
    load_external_managed_agent_record_by_agent_id,
    load_managed_agent_record_by_agent_id,
    resolve_external_managed_agent_records_by_name,
    resolve_managed_agent_records_by_name,
)
from houmao.agents.system_skill_doctor import SystemSkillDoctorTarget


class SystemSkillDoctorTargetError(RuntimeError):
    """Raised when doctor cannot resolve one authoritative local target."""


def resolve_managed_system_skill_doctor_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    env: Mapping[str, str] | None = None,
) -> SystemSkillDoctorTarget:
    """Resolve one local registry record to its persistent tool home."""

    if (agent_id is None) == (agent_name is None):
        raise SystemSkillDoctorTargetError(
            "Managed-agent doctor targeting requires exactly one of --agent-id or --agent-name."
        )
    record = (
        _resolve_record_by_id(agent_id, env=env)
        if agent_id is not None
        else _resolve_record_by_name(_require_value(agent_name), env=env)
    )
    manifest_path = Path(record.runtime.manifest_path).expanduser().resolve()
    try:
        handle = load_session_manifest(manifest_path)
        session = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    except (OSError, BrainLaunchRuntimeError) as exc:
        raise SystemSkillDoctorTargetError(
            f"Cannot read session-manifest authority for `{record.agent_id}`: {exc}"
        ) from exc
    if session.agent_id is not None and session.agent_id != record.agent_id:
        raise SystemSkillDoctorTargetError(
            f"Session manifest `{manifest_path}` belongs to `{session.agent_id}`, not "
            f"`{record.agent_id}`."
        )
    if session.tool != record.identity.tool:
        raise SystemSkillDoctorTargetError(
            f"Registry tool `{record.identity.tool}` disagrees with session-manifest tool "
            f"`{session.tool}` for `{record.agent_id}`."
        )
    brain_manifest_path = Path(session.brain_manifest_path).expanduser().resolve()
    try:
        brain_manifest = load_brain_manifest(brain_manifest_path)
        home_path = _brain_home_path(brain_manifest, source=str(brain_manifest_path))
    except (OSError, BrainLaunchRuntimeError, SystemSkillDoctorTargetError) as exc:
        raise SystemSkillDoctorTargetError(
            f"Cannot read brain-manifest home authority for `{record.agent_id}`: {exc}"
        ) from exc
    if not home_path.is_dir():
        raise SystemSkillDoctorTargetError(
            f"Persistent home `{home_path}` for managed agent `{record.agent_id}` is missing."
        )
    return SystemSkillDoctorTarget(
        kind="managed-agent",
        tool=record.identity.tool,
        home_path=home_path,
        agent_id=record.agent_id,
        agent_name=record.agent_name,
        lifecycle_state=record.lifecycle.state,
        session_manifest_path=manifest_path,
        brain_manifest_path=brain_manifest_path,
    )


def _resolve_record_by_id(
    agent_id: str,
    *,
    env: Mapping[str, str] | None,
) -> ManagedAgentRegistryRecordV3:
    """Resolve one authoritative id and reject external-only records."""

    try:
        record = load_managed_agent_record_by_agent_id(agent_id, env=env)
    except BrainLaunchRuntimeError as exc:
        raise SystemSkillDoctorTargetError(
            f"Cannot read local managed-agent registry record `{agent_id}`: {exc}"
        ) from exc
    if record is not None:
        return record
    try:
        external = load_external_managed_agent_record_by_agent_id(agent_id, env=env)
    except BrainLaunchRuntimeError as exc:
        raise SystemSkillDoctorTargetError(
            f"Cannot read external-agent registry record `{agent_id}`: {exc}"
        ) from exc
    if external is not None:
        raise SystemSkillDoctorTargetError(
            f"Agent `{agent_id}` is external; doctor only supports locally managed agents."
        )
    raise SystemSkillDoctorTargetError(f"Unknown local managed-agent id `{agent_id}`.")


def _resolve_record_by_name(
    agent_name: str,
    *,
    env: Mapping[str, str] | None,
) -> ManagedAgentRegistryRecordV3:
    """Resolve one unique friendly name and diagnose ambiguity explicitly."""

    try:
        matches = resolve_managed_agent_records_by_name(agent_name, env=env)
    except BrainLaunchRuntimeError as exc:
        raise SystemSkillDoctorTargetError(
            f"Cannot read local managed-agent records named `{agent_name}`: {exc}"
        ) from exc
    if len(matches) > 1:
        ids = ", ".join(record.agent_id for record in matches)
        raise SystemSkillDoctorTargetError(
            f"Managed-agent name `{agent_name}` is ambiguous ({ids}); use --agent-id."
        )
    if len(matches) == 1:
        return matches[0]
    try:
        external_matches = resolve_external_managed_agent_records_by_name(agent_name, env=env)
    except BrainLaunchRuntimeError as exc:
        raise SystemSkillDoctorTargetError(
            f"Cannot read external-agent records named `{agent_name}`: {exc}"
        ) from exc
    if external_matches:
        raise SystemSkillDoctorTargetError(
            f"Agent name `{agent_name}` resolves only to external agents; doctor requires a "
            "locally managed agent."
        )
    raise SystemSkillDoctorTargetError(f"Unknown local managed-agent name `{agent_name}`.")


def _brain_home_path(brain_manifest: Mapping[str, Any], *, source: str) -> Path:
    """Return the persistent home path recorded by one brain manifest."""

    runtime = brain_manifest.get("runtime")
    if not isinstance(runtime, Mapping):
        raise SystemSkillDoctorTargetError(f"{source} is missing runtime metadata.")
    value = runtime.get("home_path")
    if not isinstance(value, str) or not value.strip():
        raise SystemSkillDoctorTargetError(f"{source} stores invalid runtime.home_path.")
    return Path(value).expanduser().resolve()


def _require_value(value: str | None) -> str:
    """Narrow a selector already validated as present."""

    if value is None:
        raise SystemSkillDoctorTargetError("Missing managed-agent selector.")
    return value


__all__ = (
    "SystemSkillDoctorTargetError",
    "resolve_managed_system_skill_doctor_target",
)
