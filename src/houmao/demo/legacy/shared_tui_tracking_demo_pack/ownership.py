"""Run-local tmux ownership bookkeeping for the shared tracked-TUI demo pack."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from houmao.agents.realm_controller.backends.tmux_runtime import (
    TmuxCommandError,
    read_tmux_session_environment_value,
    run_tmux,
    set_tmux_session_environment,
    tmux_session_exists,
)
from houmao.terminal_record.service import stop_terminal_record

from .config import ResolvedDemoConfig
from .models import (
    DEMO_SESSION_OWNERSHIP_SCHEMA_VERSION,
    DEMO_SESSION_OWNERSHIP_FILE_NAME,
    DemoOwnedResource,
    DemoOwnedResourceRole,
    DemoSessionOwnership,
    DemoSessionOwnershipStatus,
    DemoWorkflowKind,
    LiveWatchPaths,
    ToolName,
    load_json,
    load_session_ownership,
    save_session_ownership,
    session_ownership_path,
)
from .tooling import kill_tmux_session_if_exists


DEMO_SESSION_ID_ENV_VAR = "HOUMAO_SHARED_TUI_DEMO_ID"
DEMO_SESSION_RUN_ROOT_ENV_VAR = "HOUMAO_SHARED_TUI_DEMO_RUN_ROOT"
DEMO_SESSION_OWNERSHIP_PATH_ENV_VAR = "HOUMAO_SHARED_TUI_DEMO_OWNERSHIP_PATH"
DEMO_SESSION_ROLE_ENV_VAR = "HOUMAO_SHARED_TUI_DEMO_ROLE"
_ROLE_ORDER: tuple[DemoOwnedResourceRole, ...] = ("tool", "dashboard", "recorder")


@dataclass(frozen=True)
class DemoSessionRecoveryPointers:
    """Ownership pointers published into one tmux session environment."""

    run_root: Path
    ownership_path: Path
    role: DemoOwnedResourceRole


@dataclass(frozen=True)
class ResolvedDemoOwnedResources:
    """Resolved ownership state for one demo run."""

    run_root: Path
    ownership_path: Path
    ownership: DemoSessionOwnership | None
    recorder_run_root: Path | None
    owned_resources: tuple[DemoOwnedResource, ...]
    live_resources: tuple[DemoOwnedResource, ...]

    def live_session_name(self, *, role: DemoOwnedResourceRole) -> str | None:
        """Return the live tmux session name for one role when available."""

        for item in self.live_resources:
            if item.role == role:
                return item.session_name
        return None

    def known_session_name(self, *, role: DemoOwnedResourceRole) -> str | None:
        """Return the best-known tmux session name for one role."""

        live_name = self.live_session_name(role=role)
        if live_name is not None:
            return live_name
        for item in self.owned_resources:
            if item.role == role:
                return item.session_name
        return None


def now_utc_iso() -> str:
    """Return a UTC timestamp string."""

    return datetime.now(UTC).isoformat(timespec="seconds")


def initialize_demo_session_ownership(
    *,
    demo_id: str,
    run_root: Path,
    workflow_kind: DemoWorkflowKind,
    tool: ToolName,
) -> DemoSessionOwnership:
    """Create and persist one initial ownership artifact for a demo run."""

    timestamp = now_utc_iso()
    ownership = DemoSessionOwnership(
        schema_version=DEMO_SESSION_OWNERSHIP_SCHEMA_VERSION,
        demo_id=demo_id,
        workflow_kind=workflow_kind,
        run_root=str(run_root.resolve()),
        tool=tool,
        status="starting",
        recorder_run_root=None,
        owned_resources=(),
        started_at_utc=timestamp,
        updated_at_utc=timestamp,
        stopped_at_utc=None,
        last_error=None,
    )
    save_session_ownership(session_ownership_path(run_root=run_root), ownership)
    return ownership


def set_demo_session_ownership_status(
    *,
    run_root: Path,
    status: DemoSessionOwnershipStatus,
    last_error: str | None = None,
) -> DemoSessionOwnership:
    """Update the lifecycle status of one demo-run ownership artifact."""

    timestamp = now_utc_iso()
    return _update_demo_session_ownership(
        run_root=run_root,
        mutate=lambda current: DemoSessionOwnership(
            schema_version=current.schema_version,
            demo_id=current.demo_id,
            workflow_kind=current.workflow_kind,
            run_root=current.run_root,
            tool=current.tool,
            status=status,
            recorder_run_root=current.recorder_run_root,
            owned_resources=current.owned_resources,
            started_at_utc=current.started_at_utc,
            updated_at_utc=timestamp,
            stopped_at_utc=timestamp if status in {"stopped", "failed"} else None,
            last_error=last_error,
        ),
    )


def set_demo_session_recorder_run_root(
    *, run_root: Path, recorder_run_root: Path
) -> DemoSessionOwnership:
    """Persist the recorder run root for one demo run."""

    return _update_demo_session_ownership(
        run_root=run_root,
        mutate=lambda current: DemoSessionOwnership(
            schema_version=current.schema_version,
            demo_id=current.demo_id,
            workflow_kind=current.workflow_kind,
            run_root=current.run_root,
            tool=current.tool,
            status=current.status,
            recorder_run_root=str(recorder_run_root.resolve()),
            owned_resources=current.owned_resources,
            started_at_utc=current.started_at_utc,
            updated_at_utc=now_utc_iso(),
            stopped_at_utc=current.stopped_at_utc,
            last_error=current.last_error,
        ),
    )


def upsert_demo_owned_resource(
    *,
    run_root: Path,
    role: DemoOwnedResourceRole,
    session_name: str | None,
) -> DemoSessionOwnership:
    """Upsert one workflow-owned tmux resource for a demo run."""

    def _mutate(current: DemoSessionOwnership) -> DemoSessionOwnership:
        resources_by_role = {item.role: item for item in current.owned_resources}
        resources_by_role[role] = DemoOwnedResource(role=role, session_name=session_name)
        ordered_resources = tuple(
            resources_by_role[item_role]
            for item_role in _ROLE_ORDER
            if item_role in resources_by_role
        )
        return DemoSessionOwnership(
            schema_version=current.schema_version,
            demo_id=current.demo_id,
            workflow_kind=current.workflow_kind,
            run_root=current.run_root,
            tool=current.tool,
            status=current.status,
            recorder_run_root=current.recorder_run_root,
            owned_resources=ordered_resources,
            started_at_utc=current.started_at_utc,
            updated_at_utc=now_utc_iso(),
            stopped_at_utc=current.stopped_at_utc,
            last_error=current.last_error,
        )

    return _update_demo_session_ownership(run_root=run_root, mutate=_mutate)


def publish_demo_session_recovery_pointers(
    *,
    demo_id: str,
    run_root: Path,
    session_name: str,
    role: DemoOwnedResourceRole,
) -> None:
    """Publish demo-owned recovery pointers into one tmux session environment."""

    ownership_path = session_ownership_path(run_root=run_root)
    set_tmux_session_environment(
        session_name=session_name,
        env_vars={
            DEMO_SESSION_ID_ENV_VAR: demo_id,
            DEMO_SESSION_RUN_ROOT_ENV_VAR: str(run_root.resolve()),
            DEMO_SESSION_OWNERSHIP_PATH_ENV_VAR: str(ownership_path),
            DEMO_SESSION_ROLE_ENV_VAR: role,
        },
    )


def read_demo_session_recovery_pointers(*, session_name: str) -> DemoSessionRecoveryPointers | None:
    """Read demo-owned recovery pointers from one tmux session environment."""

    try:
        demo_id = read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=DEMO_SESSION_ID_ENV_VAR,
        )
        if demo_id is None:
            return None
        run_root_value = read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=DEMO_SESSION_RUN_ROOT_ENV_VAR,
        )
        ownership_path_value = read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=DEMO_SESSION_OWNERSHIP_PATH_ENV_VAR,
        )
        role_value = read_tmux_session_environment_value(
            session_name=session_name,
            variable_name=DEMO_SESSION_ROLE_ENV_VAR,
        )
    except TmuxCommandError:
        return None
    if role_value not in _ROLE_ORDER:
        return None
    run_root = _optional_absolute_path(run_root_value)
    ownership_path = _optional_absolute_path(ownership_path_value)
    if run_root is None and ownership_path is None:
        return None
    if run_root is None and ownership_path is not None:
        run_root = ownership_path.parent
    if ownership_path is None and run_root is not None:
        ownership_path = session_ownership_path(run_root=run_root)
    assert run_root is not None
    assert ownership_path is not None
    return DemoSessionRecoveryPointers(
        run_root=run_root.resolve(),
        ownership_path=ownership_path.resolve(),
        role=cast(DemoOwnedResourceRole, role_value),
    )


def resolve_demo_owned_resources(*, run_root: Path) -> ResolvedDemoOwnedResources:
    """Resolve workflow-owned resources for one demo run."""

    resolved_run_root = run_root.resolve()
    ownership_path = session_ownership_path(run_root=resolved_run_root)
    ownership = load_session_ownership(ownership_path)
    manifest_resources, manifest_recorder_run_root = _load_manifest_owned_resources(
        run_root=resolved_run_root
    )
    owned_by_role: dict[DemoOwnedResourceRole, DemoOwnedResource] = {}
    live_by_role: dict[DemoOwnedResourceRole, DemoOwnedResource] = {}

    if ownership is not None:
        for item in ownership.owned_resources:
            owned_by_role.setdefault(item.role, item)
            if item.session_name is not None and _tmux_session_is_live(item.session_name):
                live_by_role[item.role] = item

    for item in manifest_resources:
        owned_by_role.setdefault(item.role, item)
        if item.session_name is not None and _tmux_session_is_live(item.session_name):
            live_by_role.setdefault(item.role, item)

    for session_name in _list_tmux_session_names():
        pointers = read_demo_session_recovery_pointers(session_name=session_name)
        if pointers is None:
            continue
        if pointers.run_root != resolved_run_root and pointers.ownership_path != ownership_path:
            continue
        recovered = DemoOwnedResource(role=pointers.role, session_name=session_name)
        live_by_role[pointers.role] = recovered
        current = owned_by_role.get(pointers.role)
        if (
            current is None
            or current.session_name is None
            or not _tmux_session_is_live(current.session_name)
        ):
            owned_by_role[pointers.role] = recovered

    recorder_run_root = None
    if ownership is not None and ownership.recorder_run_root is not None:
        recorder_run_root = Path(ownership.recorder_run_root)
    elif manifest_recorder_run_root is not None:
        recorder_run_root = manifest_recorder_run_root

    return ResolvedDemoOwnedResources(
        run_root=resolved_run_root,
        ownership_path=ownership_path,
        ownership=ownership,
        recorder_run_root=recorder_run_root,
        owned_resources=tuple(owned_by_role[role] for role in _ROLE_ORDER if role in owned_by_role),
        live_resources=tuple(live_by_role[role] for role in _ROLE_ORDER if role in live_by_role),
    )


def reap_demo_owned_resources(
    *,
    resolved_resources: ResolvedDemoOwnedResources,
    include_roles: set[DemoOwnedResourceRole] | None = None,
    stop_recorder: bool,
    best_effort: bool,
) -> dict[str, Any]:
    """Reap workflow-owned resources for one resolved demo run."""

    selected_roles = include_roles or set(_ROLE_ORDER)
    cleaned_sessions: list[str] = []
    recorder_stop: dict[str, Any] | None = None
    errors: list[str] = []

    if (
        "recorder" in selected_roles
        and stop_recorder
        and resolved_resources.recorder_run_root is not None
    ):
        try:
            recorder_stop = stop_terminal_record(run_root=resolved_resources.recorder_run_root)
        except Exception as exc:  # noqa: BLE001
            if best_effort:
                errors.append(str(exc))
            else:
                raise

    for role in _ROLE_ORDER:
        if role not in selected_roles:
            continue
        session_name = resolved_resources.known_session_name(role=role)
        if session_name is None:
            continue
        if not _tmux_session_is_live(session_name):
            continue
        try:
            kill_tmux_session_if_exists(session_name=session_name)
        except Exception as exc:  # noqa: BLE001
            if best_effort:
                errors.append(str(exc))
                continue
            raise
        cleaned_sessions.append(session_name)

    return {
        "run_root": str(resolved_resources.run_root),
        "ownership_path": str(resolved_resources.ownership_path),
        "owned_resources": [item.to_payload() for item in resolved_resources.owned_resources],
        "cleaned_sessions": cleaned_sessions,
        "recorder_stop": recorder_stop,
        "errors": errors,
    }


def cleanup_demo_run(
    *,
    demo_config: ResolvedDemoConfig,
    run_root: Path | None,
) -> dict[str, Any]:
    """Forcefully reap workflow-owned resources for one demo run."""

    selected_run_root = resolve_demo_cleanup_run_root(demo_config=demo_config, run_root=run_root)
    ownership = load_session_ownership(session_ownership_path(run_root=selected_run_root))
    if ownership is not None:
        set_demo_session_ownership_status(
            run_root=selected_run_root,
            status="cleanup_pending",
            last_error="forceful_cleanup_requested",
        )
    resolved_resources = resolve_demo_owned_resources(run_root=selected_run_root)
    cleanup_payload = reap_demo_owned_resources(
        resolved_resources=resolved_resources,
        include_roles={"tool", "dashboard", "recorder"},
        stop_recorder=True,
        best_effort=False,
    )
    if ownership is not None:
        set_demo_session_ownership_status(
            run_root=selected_run_root,
            status="stopped",
            last_error="forceful_cleanup_completed",
        )
    cleanup_payload["cleanup_kind"] = "forceful"
    cleanup_payload["finalized_analysis"] = False
    return cleanup_payload


def resolve_demo_cleanup_run_root(
    *,
    demo_config: ResolvedDemoConfig,
    run_root: Path | None,
) -> Path:
    """Resolve the target run root for forceful cleanup."""

    if run_root is not None:
        return run_root.expanduser().resolve()
    candidates: list[Path] = []
    for parent in (demo_config.live_root_path(), demo_config.recorded_root_path()):
        if not parent.exists():
            continue
        candidates.extend(path.parent for path in parent.rglob(DEMO_SESSION_OWNERSHIP_FILE_NAME))
    if not candidates:
        raise RuntimeError("No demo run roots with ownership metadata found")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _update_demo_session_ownership(
    *,
    run_root: Path,
    mutate: Callable[[DemoSessionOwnership], DemoSessionOwnership],
) -> DemoSessionOwnership:
    """Load, transform, and persist one demo-run ownership artifact."""

    path = session_ownership_path(run_root=run_root)
    current = load_session_ownership(path)
    if current is None:
        raise FileNotFoundError(f"Demo session ownership not found: {path}")
    updated = mutate(current)
    save_session_ownership(path, updated)
    return updated


def _optional_absolute_path(value: str | None) -> Path | None:
    """Return one validated absolute path value when present."""

    if value is None:
        return None
    path = Path(value)
    if not path.is_absolute():
        return None
    return path.resolve()


def _tmux_session_is_live(session_name: str) -> bool:
    """Return whether one tmux session is currently live."""

    return tmux_session_exists(session_name=session_name)


def _list_tmux_session_names() -> tuple[str, ...]:
    """Return the current tmux session names."""

    result = run_tmux(["list-sessions", "-F", "#{session_name}"])
    if result.returncode != 0:
        return ()
    return tuple(line.strip() for line in result.stdout.splitlines() if line.strip())


def _load_manifest_owned_resources(
    *,
    run_root: Path,
) -> tuple[tuple[DemoOwnedResource, ...], Path | None]:
    """Return manifest-declared ownership state when final manifests exist."""

    resources: list[DemoOwnedResource] = []
    recorder_run_root: Path | None = None

    live_paths = LiveWatchPaths.from_run_root(run_root=run_root)
    live_manifest_payload = load_json(live_paths.watch_manifest_path)
    if live_manifest_payload is not None:
        tool_session_name = live_manifest_payload.get("tool_session_name")
        dashboard_session_name = live_manifest_payload.get("dashboard_session_name")
        if isinstance(tool_session_name, str):
            resources.append(DemoOwnedResource(role="tool", session_name=tool_session_name))
        if isinstance(dashboard_session_name, str):
            resources.append(
                DemoOwnedResource(role="dashboard", session_name=dashboard_session_name)
            )
        recorder_root_value = live_manifest_payload.get("terminal_record_run_root")
        if isinstance(recorder_root_value, str) and recorder_root_value:
            recorder_run_root = Path(recorder_root_value)
            resources.append(DemoOwnedResource(role="recorder", session_name=None))

    capture_manifest_payload = load_json(run_root / "capture_manifest.json")
    if capture_manifest_payload is not None:
        tool_session_name = capture_manifest_payload.get("tool_session_name")
        if isinstance(tool_session_name, str):
            resources.append(DemoOwnedResource(role="tool", session_name=tool_session_name))
        recording_root_value = capture_manifest_payload.get("recording_root")
        if isinstance(recording_root_value, str) and recording_root_value:
            recorder_run_root = Path(recording_root_value)
            resources.append(DemoOwnedResource(role="recorder", session_name=None))

    deduped: dict[DemoOwnedResourceRole, DemoOwnedResource] = {}
    for item in resources:
        deduped.setdefault(item.role, item)
    return tuple(deduped[role] for role in _ROLE_ORDER if role in deduped), recorder_run_root
