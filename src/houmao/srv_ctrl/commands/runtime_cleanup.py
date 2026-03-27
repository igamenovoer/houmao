"""Runtime and managed-session cleanup helpers for `houmao-mgr`."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from houmao.agents.realm_controller.backends.tmux_runtime import tmux_session_exists
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import LaunchPlanError, SessionManifestError
from houmao.agents.realm_controller.gateway_storage import gateway_paths_from_session_root
from houmao.agents.realm_controller.loaders import load_brain_manifest
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
    runtime_owned_session_root_from_manifest_path,
)
from houmao.owned_paths import resolve_runtime_root

from .cleanup_support import CleanupAction, build_cleanup_payload, remove_path
from .managed_agents import _resolve_local_managed_agent_record


class CleanupResolutionError(RuntimeError):
    """Raised when a cleanup target cannot be resolved safely."""


@dataclass(frozen=True)
class ResolvedManagedSessionCleanupTarget:
    """Resolved local managed-session cleanup authority."""

    manifest_path: Path
    session_root: Path
    payload: SessionManifestPayloadV4
    resolution: dict[str, object]


@dataclass(frozen=True)
class RuntimeSessionEnvelope:
    """One runtime-owned session envelope discovered under the runtime root."""

    session_root: Path
    manifest_path: Path
    payload: SessionManifestPayloadV4 | None
    parse_error: str | None
    tmux_session_name: str | None
    live: bool


def resolve_managed_session_cleanup_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
) -> ResolvedManagedSessionCleanupTarget:
    """Resolve one managed-session cleanup authority from selectors or paths."""

    from .agents.gateway import _resolve_current_session_manifest, _try_current_tmux_session_name

    selected_authorities = [
        label
        for label, value in (
            ("agent_id", agent_id),
            ("agent_name", agent_name),
            ("manifest_path", manifest_path),
            ("session_root", session_root),
        )
        if value is not None
    ]
    if len(selected_authorities) > 1:
        joined = ", ".join(f"`{name}`" for name in selected_authorities)
        raise CleanupResolutionError(f"Use exactly one cleanup authority, got {joined}.")

    if manifest_path is not None:
        return _load_explicit_manifest_target(
            manifest_path=manifest_path,
            authority="manifest_path",
        )
    if session_root is not None:
        return _load_explicit_manifest_target(
            manifest_path=(session_root.resolve() / "manifest.json"),
            authority="session_root",
            authority_value=str(session_root.resolve()),
        )
    if agent_id is not None or agent_name is not None:
        record = _resolve_local_managed_agent_record(
            agent_id=agent_id,
            agent_name=agent_name,
        )
        if record is None:
            if agent_id is not None:
                selector = f"`--agent-id {agent_id}`"
            else:
                selector = f"`--agent-name {agent_name}`"
            raise CleanupResolutionError(
                "Local cleanup target resolution found no fresh shared-registry record for "
                f"{selector}. Use `--manifest-path` or `--session-root` for stopped sessions."
            )
        return _load_explicit_manifest_target(
            manifest_path=Path(record.runtime.manifest_path),
            authority="agent_id" if agent_id is not None else "agent_name",
            authority_value=record.agent_id if agent_id is not None else record.agent_name,
        )

    session_name = _try_current_tmux_session_name()
    if session_name is None:
        raise CleanupResolutionError(
            "Exactly one of `--agent-id`, `--agent-name`, `--manifest-path`, or "
            "`--session-root` is required unless the command runs inside the target tmux session."
        )
    resolution = _resolve_current_session_manifest(session_name=session_name)
    return _load_explicit_manifest_target(
        manifest_path=resolution.manifest_path,
        authority="current_session",
        authority_value=session_name,
    )


def cleanup_managed_session(
    *,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
    include_job_dir: bool,
    dry_run: bool,
) -> dict[str, object]:
    """Clean one resolved stopped managed-session envelope."""

    target = resolve_managed_session_cleanup_target(
        agent_id=agent_id,
        agent_name=agent_name,
        manifest_path=manifest_path,
        session_root=session_root,
    )
    live = _payload_is_live(target.payload)
    session_name = _payload_tmux_session_name(target.payload)

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    session_action = CleanupAction(
        artifact_kind="session_root",
        path=target.session_root,
        proposed_action="remove",
        reason="managed session no longer appears live on the local host",
        details=_session_identity_details(target.payload),
    )

    job_dir = _payload_job_dir(target.payload)
    job_dir_action = (
        CleanupAction(
            artifact_kind="job_dir",
            path=job_dir,
            proposed_action="remove",
            reason="job_dir was persisted in the stopped session manifest",
            details=_session_identity_details(target.payload),
        )
        if include_job_dir
        and job_dir is not None
        and not _path_is_within(job_dir, target.session_root)
        else None
    )

    if live:
        blocked_actions.append(
            CleanupAction(
                artifact_kind="session_root",
                path=target.session_root,
                proposed_action="remove",
                reason="managed session is still live on the local host",
                details={"tmux_session_name": session_name},
            )
        )
        if job_dir_action is not None:
            blocked_actions.append(
                CleanupAction(
                    artifact_kind="job_dir",
                    path=job_dir_action.path,
                    proposed_action="remove",
                    reason="managed session is still live on the local host",
                    details={"tmux_session_name": session_name},
                )
            )
    else:
        _apply_cleanup_action(
            action=session_action,
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )
        if include_job_dir:
            if job_dir_action is not None and job_dir_action.path.exists():
                _apply_cleanup_action(
                    action=job_dir_action,
                    dry_run=dry_run,
                    planned_actions=planned_actions,
                    applied_actions=applied_actions,
                    blocked_actions=blocked_actions,
                )
            elif job_dir is not None:
                preserved_actions.append(
                    CleanupAction(
                        artifact_kind="job_dir",
                        path=job_dir,
                        proposed_action="preserve",
                        reason="job_dir does not exist",
                    )
                )

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "managed_session_cleanup",
            "manifest_path": str(target.manifest_path),
            "session_root": str(target.session_root),
            "include_job_dir": include_job_dir,
        },
        resolution=target.resolution,
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
        extra_summary={"live_session": live},
    )


def cleanup_managed_session_logs(
    *,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
    dry_run: bool,
) -> dict[str, object]:
    """Clean log-style artifacts for one resolved managed-session envelope."""

    target = resolve_managed_session_cleanup_target(
        agent_id=agent_id,
        agent_name=agent_name,
        manifest_path=manifest_path,
        session_root=session_root,
    )
    live = _payload_is_live(target.payload)
    planned_actions, applied_actions, blocked_actions, preserved_actions = _cleanup_session_logs(
        session_root=target.session_root,
        live=live,
        dry_run=dry_run,
        older_than_seconds=None,
        session_details=_session_identity_details(target.payload),
    )

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "managed_session_logs_cleanup",
            "manifest_path": str(target.manifest_path),
            "session_root": str(target.session_root),
        },
        resolution=target.resolution,
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
        extra_summary={"live_session": live},
    )


def cleanup_managed_session_mailbox(
    *,
    agent_id: str | None,
    agent_name: str | None,
    manifest_path: Path | None,
    session_root: Path | None,
    dry_run: bool,
) -> dict[str, object]:
    """Clean session-local mailbox secret material for one managed session."""

    target = resolve_managed_session_cleanup_target(
        agent_id=agent_id,
        agent_name=agent_name,
        manifest_path=manifest_path,
        session_root=session_root,
    )
    live = _payload_is_live(target.payload)
    session_details = _session_identity_details(target.payload)
    mailbox_secret_dir = (target.session_root / "mailbox-secrets").resolve()

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    mailbox = target.payload.launch_plan.mailbox
    if mailbox is None or getattr(mailbox, "transport", None) != "stalwart":
        preserved_actions.append(
            CleanupAction(
                artifact_kind="session_mailbox_secrets",
                path=mailbox_secret_dir,
                proposed_action="preserve",
                reason="resolved session does not use session-local Stalwart secret material",
                details=session_details,
            )
        )
    elif live:
        blocked_actions.append(
            CleanupAction(
                artifact_kind="session_mailbox_secrets",
                path=mailbox_secret_dir,
                proposed_action="remove",
                reason="managed session is still live on the local host",
                details=session_details,
            )
        )
    elif mailbox_secret_dir.exists():
        _apply_cleanup_action(
            action=CleanupAction(
                artifact_kind="session_mailbox_secrets",
                path=mailbox_secret_dir,
                proposed_action="remove",
                reason="session-local mailbox secret material belongs to a stopped session",
                details=session_details,
            ),
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )
    else:
        preserved_actions.append(
            CleanupAction(
                artifact_kind="session_mailbox_secrets",
                path=mailbox_secret_dir,
                proposed_action="preserve",
                reason="session-local mailbox secret directory is absent",
                details=session_details,
            )
        )

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "managed_session_mailbox_cleanup",
            "manifest_path": str(target.manifest_path),
            "session_root": str(target.session_root),
        },
        resolution=target.resolution,
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
        extra_summary={"live_session": live},
    )


def cleanup_runtime_sessions(
    *,
    runtime_root: Path | None,
    older_than_seconds: int,
    include_job_dir: bool,
    dry_run: bool,
    now: datetime | None = None,
) -> dict[str, object]:
    """Clean stopped or malformed runtime session envelopes under one runtime root."""

    resolved_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    current_time = _coerce_now(now)
    envelopes = discover_runtime_session_envelopes(resolved_runtime_root)

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    for envelope in envelopes:
        removable, reason = _session_envelope_removable(
            envelope=envelope,
            older_than_seconds=older_than_seconds,
            now=current_time,
        )
        session_details = _session_envelope_details(envelope)
        session_action = CleanupAction(
            artifact_kind="session_root",
            path=envelope.session_root,
            proposed_action="remove",
            reason=reason,
            details=session_details,
        )
        if removable:
            _apply_cleanup_action(
                action=session_action,
                dry_run=dry_run,
                planned_actions=planned_actions,
                applied_actions=applied_actions,
                blocked_actions=blocked_actions,
            )
            job_dir = _payload_job_dir(envelope.payload) if envelope.payload is not None else None
            if (
                include_job_dir
                and job_dir is not None
                and job_dir.exists()
                and not _path_is_within(job_dir, envelope.session_root)
            ):
                _apply_cleanup_action(
                    action=CleanupAction(
                        artifact_kind="job_dir",
                        path=job_dir,
                        proposed_action="remove",
                        reason="job_dir belongs to a removable runtime session envelope",
                        details=session_details,
                    ),
                    dry_run=dry_run,
                    planned_actions=planned_actions,
                    applied_actions=applied_actions,
                    blocked_actions=blocked_actions,
                )
            continue

        artifact_kind = "session_root" if not envelope.live else "live_session_root"
        preserved_actions.append(
            CleanupAction(
                artifact_kind=artifact_kind,
                path=envelope.session_root,
                proposed_action="preserve",
                reason=reason,
                details=session_details,
            )
        )

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "runtime_sessions_cleanup",
            "runtime_root": str(resolved_runtime_root),
            "older_than_seconds": older_than_seconds,
            "include_job_dir": include_job_dir,
        },
        resolution={"authority": "runtime_root"},
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
    )


def cleanup_runtime_builds(
    *,
    runtime_root: Path | None,
    older_than_seconds: int,
    dry_run: bool,
    now: datetime | None = None,
) -> dict[str, object]:
    """Clean unreferenced or broken build manifest-home pairs."""

    resolved_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    current_time = _coerce_now(now)
    preserved_brain_manifests = _preserved_session_brain_manifest_paths(
        runtime_root=resolved_runtime_root,
        older_than_seconds=older_than_seconds,
        now=current_time,
    )
    manifests_dir = (resolved_runtime_root / "manifests").resolve()
    homes_dir = (resolved_runtime_root / "homes").resolve()

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    seen_home_paths: set[Path] = set()
    for manifest_path in sorted(_iter_files(manifests_dir)):
        matching_home = (homes_dir / manifest_path.stem).resolve()
        if matching_home.exists():
            seen_home_paths.add(matching_home)

        if not _all_paths_older_than(
            [manifest_path, matching_home if matching_home.exists() else None],
            older_than_seconds=older_than_seconds,
            now=current_time,
        ):
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_build_manifest",
                    path=manifest_path,
                    proposed_action="preserve",
                    reason="build artifact is newer than `--older-than-seconds`",
                )
            )
            if matching_home.exists():
                preserved_actions.append(
                    CleanupAction(
                        artifact_kind="runtime_home",
                        path=matching_home,
                        proposed_action="preserve",
                        reason="build artifact is newer than `--older-than-seconds`",
                    )
                )
            continue

        try:
            manifest_payload = load_brain_manifest(manifest_path)
        except (LaunchPlanError, SessionManifestError) as exc:
            _plan_or_apply_paths(
                candidates=[
                    CleanupAction(
                        artifact_kind="runtime_build_manifest",
                        path=manifest_path,
                        proposed_action="remove",
                        reason=f"build manifest is invalid: {exc}",
                    ),
                    *(
                        [
                            CleanupAction(
                                artifact_kind="runtime_home",
                                path=matching_home,
                                proposed_action="remove",
                                reason="home has only an invalid same-id build manifest",
                            )
                        ]
                        if matching_home.exists()
                        else []
                    ),
                ],
                dry_run=dry_run,
                planned_actions=planned_actions,
                applied_actions=applied_actions,
                blocked_actions=blocked_actions,
            )
            continue

        runtime_section = manifest_payload.get("runtime")
        home_path_value = (
            runtime_section.get("home_path") if isinstance(runtime_section, dict) else None
        )
        if not isinstance(home_path_value, str) or not home_path_value.strip():
            _plan_or_apply_paths(
                candidates=[
                    CleanupAction(
                        artifact_kind="runtime_build_manifest",
                        path=manifest_path,
                        proposed_action="remove",
                        reason="build manifest is missing `runtime.home_path`",
                    )
                ],
                dry_run=dry_run,
                planned_actions=planned_actions,
                applied_actions=applied_actions,
                blocked_actions=blocked_actions,
            )
            continue

        resolved_home_path = Path(home_path_value).resolve()
        if resolved_home_path.exists():
            seen_home_paths.add(resolved_home_path)

        if manifest_path.resolve() in preserved_brain_manifests:
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_build_manifest",
                    path=manifest_path,
                    proposed_action="preserve",
                    reason="build manifest is still referenced by a preserved session manifest",
                )
            )
            if resolved_home_path.exists():
                preserved_actions.append(
                    CleanupAction(
                        artifact_kind="runtime_home",
                        path=resolved_home_path,
                        proposed_action="preserve",
                        reason="runtime home is still referenced by a preserved session manifest",
                    )
                )
            continue

        candidates = [
            CleanupAction(
                artifact_kind="runtime_build_manifest",
                path=manifest_path,
                proposed_action="remove",
                reason="build manifest is no longer referenced by any preserved session manifest",
            )
        ]
        if resolved_home_path.exists():
            candidates.append(
                CleanupAction(
                    artifact_kind="runtime_home",
                    path=resolved_home_path,
                    proposed_action="remove",
                    reason="runtime home belongs to an unreferenced build manifest",
                )
            )
        _plan_or_apply_paths(
            candidates=candidates,
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )

    for home_path in sorted(_iter_directories(homes_dir)):
        resolved_home_path = home_path.resolve()
        if resolved_home_path in seen_home_paths:
            continue
        if not _path_is_old_enough(
            resolved_home_path,
            older_than_seconds=older_than_seconds,
            now=current_time,
        ):
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_home",
                    path=resolved_home_path,
                    proposed_action="preserve",
                    reason="runtime home is newer than `--older-than-seconds`",
                )
            )
            continue
        _apply_cleanup_action(
            action=CleanupAction(
                artifact_kind="runtime_home",
                path=resolved_home_path,
                proposed_action="remove",
                reason="runtime home has no matching build manifest",
            ),
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "runtime_builds_cleanup",
            "runtime_root": str(resolved_runtime_root),
            "older_than_seconds": older_than_seconds,
        },
        resolution={"authority": "runtime_root"},
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
    )


def cleanup_runtime_logs(
    *,
    runtime_root: Path | None,
    older_than_seconds: int,
    dry_run: bool,
) -> dict[str, object]:
    """Clean log-style runtime artifacts while preserving durable gateway state."""

    resolved_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    envelopes = discover_runtime_session_envelopes(resolved_runtime_root)

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    for envelope in envelopes:
        session_planned, session_applied, session_blocked, session_preserved = (
            _cleanup_session_logs(
                session_root=envelope.session_root,
                live=envelope.live,
                dry_run=dry_run,
                older_than_seconds=older_than_seconds,
                session_details=_session_envelope_details(envelope),
            )
        )
        planned_actions.extend(session_planned)
        applied_actions.extend(session_applied)
        blocked_actions.extend(session_blocked)
        preserved_actions.extend(session_preserved)

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "runtime_logs_cleanup",
            "runtime_root": str(resolved_runtime_root),
            "older_than_seconds": older_than_seconds,
        },
        resolution={"authority": "runtime_root"},
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
    )


def cleanup_runtime_mailbox_credentials(
    *,
    runtime_root: Path | None,
    older_than_seconds: int,
    dry_run: bool,
    now: datetime | None = None,
) -> dict[str, object]:
    """Clean unreferenced runtime-owned Stalwart credential files."""

    resolved_runtime_root = resolve_runtime_root(explicit_root=runtime_root)
    current_time = _coerce_now(now)
    referenced_credential_refs = _preserved_session_credential_refs(
        runtime_root=resolved_runtime_root,
        older_than_seconds=older_than_seconds,
        now=current_time,
    )
    credentials_root = (resolved_runtime_root / "mailbox-credentials" / "stalwart").resolve()

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    for candidate in sorted(_iter_files(credentials_root)):
        credential_ref = candidate.stem
        if credential_ref in referenced_credential_refs:
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_mailbox_credential",
                    path=candidate,
                    proposed_action="preserve",
                    reason="credential_ref is still referenced by a preserved session manifest",
                    details={"credential_ref": credential_ref},
                )
            )
            continue
        if not _path_is_old_enough(
            candidate,
            older_than_seconds=older_than_seconds,
            now=current_time,
        ):
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_mailbox_credential",
                    path=candidate,
                    proposed_action="preserve",
                    reason="credential file is newer than `--older-than-seconds`",
                    details={"credential_ref": credential_ref},
                )
            )
            continue
        _apply_cleanup_action(
            action=CleanupAction(
                artifact_kind="runtime_mailbox_credential",
                path=candidate,
                proposed_action="remove",
                reason="credential_ref is no longer referenced by any preserved session manifest",
                details={"credential_ref": credential_ref},
            ),
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )

    return build_cleanup_payload(
        dry_run=dry_run,
        scope={
            "kind": "runtime_mailbox_credentials_cleanup",
            "runtime_root": str(resolved_runtime_root),
            "older_than_seconds": older_than_seconds,
        },
        resolution={"authority": "runtime_root"},
        planned_actions=planned_actions,
        applied_actions=applied_actions,
        blocked_actions=blocked_actions,
        preserved_actions=preserved_actions,
    )


def discover_runtime_session_envelopes(runtime_root: Path) -> tuple[RuntimeSessionEnvelope, ...]:
    """Discover runtime-owned session envelopes under one runtime root."""

    sessions_root = (runtime_root / "sessions").resolve()
    if not sessions_root.exists():
        return ()

    envelopes: list[RuntimeSessionEnvelope] = []
    for backend_dir in sorted(_iter_directories(sessions_root)):
        for session_dir in sorted(_iter_directories(backend_dir)):
            manifest_path = (session_dir / "manifest.json").resolve()
            payload: SessionManifestPayloadV4 | None
            parse_error: str | None
            tmux_session_name: str | None
            live: bool
            if manifest_path.is_file():
                try:
                    handle = load_session_manifest(manifest_path)
                    parsed_payload = parse_session_manifest_payload(
                        handle.payload, source=str(handle.path)
                    )
                except SessionManifestError as exc:
                    payload = None
                    parse_error = str(exc)
                    tmux_session_name = None
                    live = False
                else:
                    payload = parsed_payload
                    parse_error = None
                    tmux_session_name = _payload_tmux_session_name(parsed_payload)
                    live = _payload_is_live(parsed_payload)
            else:
                payload = None
                parse_error = f"session manifest is missing: {manifest_path}"
                tmux_session_name = None
                live = False
            envelopes.append(
                RuntimeSessionEnvelope(
                    session_root=session_dir.resolve(),
                    manifest_path=manifest_path,
                    payload=payload,
                    parse_error=parse_error,
                    tmux_session_name=tmux_session_name,
                    live=live,
                )
            )
    return tuple(envelopes)


def _load_explicit_manifest_target(
    *,
    manifest_path: Path,
    authority: str,
    authority_value: str | None = None,
) -> ResolvedManagedSessionCleanupTarget:
    """Load and validate one explicit manifest-backed cleanup target."""

    resolved_manifest_path = manifest_path.resolve()
    handle = load_session_manifest(resolved_manifest_path)
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    session_root = runtime_owned_session_root_from_manifest_path(handle.path)
    if session_root is None:
        raise CleanupResolutionError(
            "Cleanup target must use the runtime-owned `<session-root>/manifest.json` layout, "
            f"got `{handle.path}`."
        )
    return ResolvedManagedSessionCleanupTarget(
        manifest_path=handle.path.resolve(),
        session_root=session_root.resolve(),
        payload=payload,
        resolution={
            "authority": authority,
            "value": authority_value if authority_value is not None else str(handle.path.resolve()),
        },
    )


def _cleanup_session_logs(
    *,
    session_root: Path,
    live: bool,
    dry_run: bool,
    older_than_seconds: int | None,
    session_details: dict[str, object],
) -> tuple[list[CleanupAction], list[CleanupAction], list[CleanupAction], list[CleanupAction]]:
    """Return log cleanup action lists for one session root."""

    planned_actions: list[CleanupAction] = []
    applied_actions: list[CleanupAction] = []
    blocked_actions: list[CleanupAction] = []
    preserved_actions: list[CleanupAction] = []

    paths = gateway_paths_from_session_root(session_root=session_root)
    durable_paths = (
        paths.gateway_manifest_path,
        paths.attach_path,
        paths.protocol_version_path,
        paths.desired_config_path,
        paths.state_path,
        paths.queue_path,
        paths.events_path,
    )
    for durable_path in durable_paths:
        if durable_path.exists():
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="durable_gateway_state",
                    path=durable_path,
                    proposed_action="preserve",
                    reason="durable gateway state is intentionally outside log cleanup scope",
                    details=session_details,
                )
            )

    if live:
        for candidate in sorted(_iter_files(paths.logs_dir)):
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_log_file",
                    path=candidate,
                    proposed_action="preserve",
                    reason="session is still live; log cleanup only targets stopped envelopes",
                    details=session_details,
                )
            )
        for candidate in (paths.current_instance_path, paths.pid_path):
            if candidate.exists():
                blocked_actions.append(
                    CleanupAction(
                        artifact_kind="runtime_run_artifact",
                        path=candidate,
                        proposed_action="remove",
                        reason="session is still live; ephemeral run markers remain in use",
                        details=session_details,
                    )
                )
        return planned_actions, applied_actions, blocked_actions, preserved_actions

    for candidate in sorted(_iter_files(paths.logs_dir)):
        if older_than_seconds is not None and not _path_is_old_enough(
            candidate,
            older_than_seconds=older_than_seconds,
            now=None,
        ):
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_log_file",
                    path=candidate,
                    proposed_action="preserve",
                    reason="log artifact is newer than `--older-than-seconds`",
                    details=session_details,
                )
            )
            continue
        _apply_cleanup_action(
            action=CleanupAction(
                artifact_kind="runtime_log_file",
                path=candidate,
                proposed_action="remove",
                reason="gateway log output is disposable cleanup-sensitive runtime state",
                details=session_details,
            ),
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )

    for candidate in (paths.current_instance_path, paths.pid_path):
        if not candidate.exists():
            continue
        if older_than_seconds is not None and not _path_is_old_enough(
            candidate,
            older_than_seconds=older_than_seconds,
            now=None,
        ):
            preserved_actions.append(
                CleanupAction(
                    artifact_kind="runtime_run_artifact",
                    path=candidate,
                    proposed_action="preserve",
                    reason="run artifact is newer than `--older-than-seconds`",
                    details=session_details,
                )
            )
            continue
        _apply_cleanup_action(
            action=CleanupAction(
                artifact_kind="runtime_run_artifact",
                path=candidate,
                proposed_action="remove",
                reason="ephemeral gateway run marker belongs to a stopped session",
                details=session_details,
            ),
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )

    return planned_actions, applied_actions, blocked_actions, preserved_actions


def _plan_or_apply_paths(
    *,
    candidates: Sequence[CleanupAction],
    dry_run: bool,
    planned_actions: list[CleanupAction],
    applied_actions: list[CleanupAction],
    blocked_actions: list[CleanupAction],
) -> None:
    """Apply or plan several cleanup actions in order."""

    for candidate in candidates:
        _apply_cleanup_action(
            action=candidate,
            dry_run=dry_run,
            planned_actions=planned_actions,
            applied_actions=applied_actions,
            blocked_actions=blocked_actions,
        )


def _apply_cleanup_action(
    *,
    action: CleanupAction,
    dry_run: bool,
    planned_actions: list[CleanupAction],
    applied_actions: list[CleanupAction],
    blocked_actions: list[CleanupAction],
) -> None:
    """Plan or apply one cleanup action and record the outcome."""

    if not action.path.exists() and not action.path.is_symlink():
        return
    if dry_run:
        planned_actions.append(action)
        return
    try:
        remove_path(action.path)
    except OSError as exc:
        blocked_actions.append(
            CleanupAction(
                artifact_kind=action.artifact_kind,
                path=action.path,
                proposed_action=action.proposed_action,
                reason=f"{action.reason}; removal failed: {exc}",
                details=action.details,
            )
        )
    else:
        applied_actions.append(action)


def _coerce_now(now: datetime | None) -> datetime:
    """Return one timezone-aware UTC timestamp."""

    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _payload_tmux_session_name(payload: SessionManifestPayloadV4) -> str | None:
    """Return the resolved tmux session name from one manifest payload."""

    if payload.tmux is not None and payload.tmux.session_name:
        return payload.tmux.session_name
    return payload.tmux_session_name


def _payload_is_live(payload: SessionManifestPayloadV4) -> bool:
    """Return whether one manifest still appears live on the local host."""

    session_name = _payload_tmux_session_name(payload)
    if session_name is None or not session_name.strip():
        return False
    return tmux_session_exists(session_name=session_name)


def _payload_job_dir(payload: SessionManifestPayloadV4) -> Path | None:
    """Return the optional manifest-persisted job directory."""

    if payload.runtime.job_dir is not None:
        return Path(payload.runtime.job_dir).resolve()
    if payload.job_dir is not None:
        return Path(payload.job_dir).resolve()
    return None


def _path_is_old_enough(
    path: Path,
    *,
    older_than_seconds: int,
    now: datetime | None,
) -> bool:
    """Return whether one path is older than the requested threshold."""

    if older_than_seconds <= 0:
        return True
    current_time = _coerce_now(now)
    modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    return (current_time - modified_at).total_seconds() >= older_than_seconds


def _all_paths_older_than(
    paths: Sequence[Path | None],
    *,
    older_than_seconds: int,
    now: datetime,
) -> bool:
    """Return whether every existing path is old enough for cleanup."""

    return all(
        _path_is_old_enough(path, older_than_seconds=older_than_seconds, now=now)
        for path in paths
        if path is not None and path.exists()
    )


def _session_envelope_removable(
    *,
    envelope: RuntimeSessionEnvelope,
    older_than_seconds: int,
    now: datetime,
) -> tuple[bool, str]:
    """Classify whether one runtime session envelope is removable."""

    if envelope.live:
        return False, "managed session is still live on the local host"
    if not _path_is_old_enough(
        envelope.session_root,
        older_than_seconds=older_than_seconds,
        now=now,
    ):
        return False, "session envelope is newer than `--older-than-seconds`"
    if envelope.parse_error is not None:
        return True, envelope.parse_error
    return True, "managed session no longer appears live on the local host"


def _preserved_session_brain_manifest_paths(
    *,
    runtime_root: Path,
    older_than_seconds: int,
    now: datetime,
) -> set[Path]:
    """Return brain manifest paths referenced by preserved session envelopes."""

    preserved: set[Path] = set()
    for envelope in discover_runtime_session_envelopes(runtime_root):
        removable, _ = _session_envelope_removable(
            envelope=envelope,
            older_than_seconds=older_than_seconds,
            now=now,
        )
        if removable or envelope.payload is None:
            continue
        preserved.add(Path(envelope.payload.brain_manifest_path).resolve())
    return preserved


def _preserved_session_credential_refs(
    *,
    runtime_root: Path,
    older_than_seconds: int,
    now: datetime,
) -> set[str]:
    """Return credential refs still referenced by preserved session envelopes."""

    refs: set[str] = set()
    for envelope in discover_runtime_session_envelopes(runtime_root):
        removable, _ = _session_envelope_removable(
            envelope=envelope,
            older_than_seconds=older_than_seconds,
            now=now,
        )
        if removable or envelope.payload is None:
            continue
        mailbox = envelope.payload.launch_plan.mailbox
        credential_ref = getattr(mailbox, "credential_ref", None)
        if isinstance(credential_ref, str) and credential_ref.strip():
            refs.add(credential_ref)
    return refs


def _session_identity_details(payload: SessionManifestPayloadV4) -> dict[str, object]:
    """Return compact identity details for one parsed session manifest."""

    details: dict[str, object] = {}
    if payload.agent_id is not None:
        details["agent_id"] = payload.agent_id
    if payload.agent_name is not None:
        details["agent_name"] = payload.agent_name
    session_name = _payload_tmux_session_name(payload)
    if session_name is not None:
        details["tmux_session_name"] = session_name
    return details


def _session_envelope_details(envelope: RuntimeSessionEnvelope) -> dict[str, object]:
    """Return compact details for one discovered runtime session envelope."""

    details: dict[str, object] = {
        "session_root": str(envelope.session_root),
        "manifest_path": str(envelope.manifest_path),
    }
    if envelope.tmux_session_name is not None:
        details["tmux_session_name"] = envelope.tmux_session_name
    if envelope.payload is not None:
        if envelope.payload.agent_id is not None:
            details["agent_id"] = envelope.payload.agent_id
        if envelope.payload.agent_name is not None:
            details["agent_name"] = envelope.payload.agent_name
    if envelope.parse_error is not None:
        details["parse_error"] = envelope.parse_error
    return details


def _iter_directories(root: Path) -> Iterable[Path]:
    """Yield direct child directories when the parent exists."""

    if not root.exists():
        return ()
    return (candidate for candidate in root.iterdir() if candidate.is_dir())


def _iter_files(root: Path) -> Iterable[Path]:
    """Yield every file or symlink under one root."""

    if not root.exists():
        return ()
    return (
        candidate for candidate in root.rglob("*") if candidate.is_file() or candidate.is_symlink()
    )


def _path_is_within(path: Path, parent: Path) -> bool:
    """Return whether one path is inside another resolved directory."""

    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True
