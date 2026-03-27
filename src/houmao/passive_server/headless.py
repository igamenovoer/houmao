"""Headless agent lifecycle service for the passive server.

Manages the full lifecycle of server-launched headless agents: launch,
turn submission, turn status/events/artifacts, interrupt, stop, and
startup rebuild.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    load_headless_turn_events,
    read_headless_turn_return_code,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    kill_tmux_session,
    tmux_session_exists,
)
from houmao.agents.realm_controller.errors import LaunchPlanError, SessionManifestError
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.registry_storage import (
    publish_live_agent_record,
    remove_live_agent_record,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
    resume_runtime_session,
    start_runtime_session,
)
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import (
    PassiveAgentActionResponse,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnEventsResponse,
    PassiveHeadlessTurnStatusResponse,
)
from houmao.server.managed_agents import (
    ManagedHeadlessActiveTurnRecord,
    ManagedHeadlessAuthorityRecord,
    ManagedHeadlessStore,
    ManagedHeadlessTurnRecord,
)
from houmao.server.models import HoumaoHeadlessTurnEvent

log = logging.getLogger(__name__)

_HEADLESS_BACKENDS = frozenset({"claude_headless", "codex_headless", "gemini_headless"})


class _StoreConfigAdapter:
    """Minimal adapter so ``ManagedHeadlessStore`` can use passive-server config."""

    def __init__(self, managed_agents_root: Path) -> None:
        self.managed_agents_root = managed_agents_root


class _ManagedHeadlessHandle:
    """In-memory handle for one live server-managed headless agent."""

    def __init__(
        self,
        *,
        authority: ManagedHeadlessAuthorityRecord,
        controller: RuntimeSessionController | None,
    ) -> None:
        self.authority = authority
        self.controller = controller
        self.turn_worker: threading.Thread | None = None


@dataclass(frozen=True)
class PassiveManagedHeadlessControlState:
    """Live compatibility posture for one passive-server-managed headless agent."""

    authority: ManagedHeadlessAuthorityRecord
    controller: RuntimeSessionController | None
    runtime_resumable: bool
    tmux_session_live: bool
    can_accept_prompt_now: bool
    interruptible: bool
    active_turn: ManagedHeadlessActiveTurnRecord | None
    latest_turn: ManagedHeadlessTurnRecord | None


class HeadlessAgentService:
    """Manages server-launched headless agent lifecycle.

    Responsibilities:
    - Launch headless agents via ``start_runtime_session()``
    - Manage turn submission, status, events, and artifacts
    - Rebuild in-memory handles on startup
    - Stop / interrupt individual agents
    """

    def __init__(self, config: PassiveServerConfig) -> None:
        self.m_config = config
        adapter = _StoreConfigAdapter(config.managed_agents_root)
        self.m_store = ManagedHeadlessStore(config=adapter)
        self.m_handles: dict[str, _ManagedHeadlessHandle] = {}
        self.m_lock = threading.Lock()

    # -- lifecycle ------------------------------------------------------------

    def start(self) -> None:
        """Ensure directories exist and rebuild handles for surviving agents."""

        self.m_store.ensure_directories()
        self._rebuild_handles()

    def stop(self) -> None:
        """Best-effort cleanup (handles stay; no forced termination)."""

    # -- launch ---------------------------------------------------------------

    def launch(
        self, request: PassiveHeadlessLaunchRequest
    ) -> PassiveHeadlessLaunchResponse | tuple[int, dict[str, Any]]:
        """Launch a new headless agent and return its tracked identity."""

        resolved_tool = request.tool.strip()
        working_dir = Path(request.working_directory).expanduser().resolve()
        if not working_dir.is_dir():
            return (
                422,
                {
                    "detail": "Native headless launch requires an existing working_directory directory."
                },
            )

        agent_def_dir = Path(request.agent_def_dir).expanduser().resolve()
        if not agent_def_dir.is_dir():
            return (
                422,
                {"detail": "Native headless launch requires an existing agent_def_dir directory."},
            )

        manifest_path = Path(request.brain_manifest_path).expanduser().resolve()
        if not manifest_path.is_file():
            return (
                422,
                {"detail": "Native headless launch requires an existing brain_manifest_path file."},
            )

        resolved_role_name = None
        if request.role_name is not None and request.role_name.strip():
            resolved_role_name = request.role_name.strip()

        try:
            manifest = load_brain_manifest(manifest_path)
            if resolved_role_name is not None:
                load_role_package(agent_def_dir, resolved_role_name)
        except (LaunchPlanError, SessionManifestError) as exc:
            return (422, {"detail": str(exc)})

        manifest_tool = str(manifest.get("inputs", {}).get("tool", "")).strip()
        if manifest_tool != resolved_tool:
            return (
                422,
                {
                    "detail": (
                        "Native headless launch requires tool to match "
                        f"brain_manifest_path inputs.tool; got request={resolved_tool!r} "
                        f"manifest={manifest_tool!r}."
                    )
                },
            )

        try:
            resolved_backend = backend_for_tool(resolved_tool)
        except LaunchPlanError as exc:
            return (422, {"detail": str(exc)})
        if resolved_backend not in _HEADLESS_BACKENDS:
            return (
                422,
                {
                    "detail": (
                        f"Native headless launch for tool `{resolved_tool}` did not resolve to "
                        "a supported headless backend."
                    )
                },
            )
        backend = cast(
            Literal["claude_headless", "codex_headless", "gemini_headless"],
            resolved_backend,
        )

        mailbox_transport: str | None = None
        mailbox_root: Path | None = None
        mailbox_principal_id: str | None = None
        mailbox_address: str | None = None
        mailbox_stalwart_base_url: str | None = None
        mailbox_stalwart_jmap_url: str | None = None
        mailbox_stalwart_management_url: str | None = None
        mailbox_stalwart_login_identity: str | None = None
        if request.mailbox is not None:
            mailbox_transport = request.mailbox.transport
            mailbox_root = (
                Path(request.mailbox.filesystem_root).expanduser().resolve()
                if request.mailbox.filesystem_root
                else None
            )
            mailbox_principal_id = request.mailbox.principal_id
            mailbox_address = request.mailbox.address
            mailbox_stalwart_base_url = request.mailbox.stalwart_base_url
            mailbox_stalwart_jmap_url = request.mailbox.stalwart_jmap_url
            mailbox_stalwart_management_url = request.mailbox.stalwart_management_url
            mailbox_stalwart_login_identity = request.mailbox.stalwart_login_identity

        tracked_agent_id = uuid.uuid4().hex[:12]
        now_utc = datetime.now(UTC).isoformat(timespec="seconds")

        try:
            controller = start_runtime_session(
                agent_def_dir=agent_def_dir,
                brain_manifest_path=manifest_path,
                role_name=resolved_role_name,
                backend=backend,
                working_directory=working_dir,
                api_base_url=self.m_config.api_base_url,
                agent_name=request.agent_name,
                agent_id=request.agent_id or tracked_agent_id,
                mailbox_transport=mailbox_transport,
                mailbox_root=mailbox_root,
                mailbox_principal_id=mailbox_principal_id,
                mailbox_address=mailbox_address,
                mailbox_stalwart_base_url=mailbox_stalwart_base_url,
                mailbox_stalwart_jmap_url=mailbox_stalwart_jmap_url,
                mailbox_stalwart_management_url=mailbox_stalwart_management_url,
                mailbox_stalwart_login_identity=mailbox_stalwart_login_identity,
                registry_launch_authority="external",
            )
        except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
            return (422, {"detail": str(exc)})
        except Exception as exc:
            log.error("Failed to start runtime session for headless agent: %s", exc)
            return (500, {"detail": f"Failed to start headless agent: {exc}"})

        try:
            self._publish_controller_registry_record(controller)
        except (OSError, SessionManifestError) as exc:
            try:
                controller.stop(force_cleanup=True)
            except Exception:
                log.warning(
                    "Failed to rollback managed headless launch after shared-registry publish failure",
                    exc_info=True,
                )
            return (
                503,
                {
                    "detail": (
                        f"Managed headless launch could not publish shared-registry state: {exc}"
                    )
                },
            )

        controller_manifest_path = controller.manifest_path.resolve()
        session_root = str(controller_manifest_path.parent)

        authority = ManagedHeadlessAuthorityRecord(
            tracked_agent_id=tracked_agent_id,
            backend=backend,
            tool=resolved_tool,
            manifest_path=str(controller_manifest_path),
            session_root=session_root,
            tmux_session_name=controller.tmux_session_name or tracked_agent_id,
            agent_def_dir=str(agent_def_dir),
            agent_name=controller.agent_identity,
            agent_id=controller.agent_id,
            created_at_utc=now_utc,
            updated_at_utc=now_utc,
        )
        self.m_store.write_authority(authority)

        handle = _ManagedHeadlessHandle(authority=authority, controller=controller)
        with self.m_lock:
            self.m_handles[tracked_agent_id] = handle

        log.info(
            "Launched headless agent %s (tool=%s, backend=%s)",
            tracked_agent_id,
            resolved_tool,
            backend,
        )

        return PassiveHeadlessLaunchResponse(
            tracked_agent_id=tracked_agent_id,
            agent_name=controller.agent_identity or tracked_agent_id,
            manifest_path=str(controller_manifest_path),
            session_root=session_root,
            detail=f"Headless agent launched: {tracked_agent_id}",
        )

    # -- turns ----------------------------------------------------------------

    def submit_turn(
        self, tracked_agent_id: str, prompt: str
    ) -> PassiveHeadlessTurnAcceptedResponse | tuple[int, dict[str, Any]]:
        """Submit a turn to a managed headless agent."""

        handle = self._require_handle(tracked_agent_id)
        if handle is None:
            return (404, {"detail": f"Managed headless agent not found: {tracked_agent_id}"})

        if handle.controller is None:
            return (
                503,
                {"detail": f"No live controller for agent {tracked_agent_id} (rebuild pending)"},
            )

        backend_session = handle.controller.backend_session
        if not isinstance(backend_session, HeadlessInteractiveSession):
            return (500, {"detail": "Agent backend does not support headless turns"})

        existing_active = self.m_store.read_active_turn(tracked_agent_id=tracked_agent_id)
        if existing_active is not None:
            return (
                409,
                {
                    "detail": (
                        f"Agent {tracked_agent_id} already has an active turn: "
                        f"{existing_active.turn_id}"
                    )
                },
            )

        existing_turns = self.m_store.list_turn_records(tracked_agent_id=tracked_agent_id)
        turn_index = len(existing_turns) + 1
        turn_id = uuid.uuid4().hex[:12]
        now_utc = datetime.now(UTC).isoformat(timespec="seconds")

        turn_artifact_dir = str(
            self.m_store.agent_root(tracked_agent_id=tracked_agent_id) / "artifacts" / turn_id
        )
        Path(turn_artifact_dir).mkdir(parents=True, exist_ok=True)

        active_turn = ManagedHeadlessActiveTurnRecord(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=turn_index,
            turn_artifact_dir=turn_artifact_dir,
            started_at_utc=now_utc,
            tmux_session_name=handle.authority.tmux_session_name,
        )
        self.m_store.write_active_turn(active_turn)

        turn_record = ManagedHeadlessTurnRecord(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=turn_index,
            status="active",
            started_at_utc=now_utc,
            turn_artifact_dir=turn_artifact_dir,
            tmux_session_name=handle.authority.tmux_session_name,
        )
        self.m_store.write_turn_record(turn_record)

        worker = threading.Thread(
            target=self._run_turn_worker,
            args=(tracked_agent_id, turn_id, prompt, backend_session),
            name=f"houmao-headless-turn-{tracked_agent_id}-{turn_id}",
            daemon=True,
        )
        with self.m_lock:
            handle.turn_worker = worker
        worker.start()

        return PassiveHeadlessTurnAcceptedResponse(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=turn_index,
            turn_status="active",
            detail=f"Turn {turn_id} submitted (index={turn_index})",
        )

    def turn_status(
        self, tracked_agent_id: str, turn_id: str
    ) -> PassiveHeadlessTurnStatusResponse | tuple[int, dict[str, Any]]:
        """Return the status of one turn."""

        record = self.m_store.read_turn_record(tracked_agent_id=tracked_agent_id, turn_id=turn_id)
        if record is None:
            return (404, {"detail": f"Turn not found: {turn_id}"})

        return PassiveHeadlessTurnStatusResponse(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            turn_index=record.turn_index,
            status=record.status,
            started_at_utc=record.started_at_utc,
            completed_at_utc=record.completed_at_utc,
            returncode=record.returncode,
            completion_source=record.completion_source,
            stdout_path=record.stdout_path,
            stderr_path=record.stderr_path,
            error=record.error,
        )

    def turn_events(
        self, tracked_agent_id: str, turn_id: str
    ) -> PassiveHeadlessTurnEventsResponse | tuple[int, dict[str, Any]]:
        """Return structured events from the turn's finalized stdout artifact."""

        record = self.m_store.read_turn_record(tracked_agent_id=tracked_agent_id, turn_id=turn_id)
        if record is None:
            return (404, {"detail": f"Turn not found: {turn_id}"})

        entries: list[HoumaoHeadlessTurnEvent] = []
        if record.stdout_path:
            stdout_path = Path(record.stdout_path)
            if stdout_path.is_file():
                try:
                    events = load_headless_turn_events(
                        stdout_path=stdout_path,
                        output_format=self._headless_output_format(
                            tracked_agent_id=tracked_agent_id
                        ),
                        turn_index=record.turn_index,
                    )
                    for event in events:
                        entries.append(
                            HoumaoHeadlessTurnEvent(
                                kind=event.kind,
                                message=event.message,
                                turn_index=event.turn_index,
                                timestamp_utc=event.timestamp_utc,
                                payload=event.payload,
                            )
                        )
                except (OSError, RuntimeError, ValueError):
                    log.warning(
                        "Failed to load persisted headless turn events for %s/%s",
                        tracked_agent_id,
                        turn_id,
                    )

        return PassiveHeadlessTurnEventsResponse(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            entries=entries,
        )

    def turn_artifact_text(
        self, tracked_agent_id: str, turn_id: str, name: str
    ) -> str | tuple[int, dict[str, Any]]:
        """Return the text content of a named turn artifact (stdout / stderr)."""

        record = self.m_store.read_turn_record(tracked_agent_id=tracked_agent_id, turn_id=turn_id)
        if record is None:
            return (404, {"detail": f"Turn not found: {turn_id}"})

        if name == "stdout":
            path_str = record.stdout_path
        elif name == "stderr":
            path_str = record.stderr_path
        else:
            return (404, {"detail": f"Unknown artifact: {name}"})

        if not path_str:
            return (404, {"detail": f"Artifact '{name}' not available for turn {turn_id}"})

        artifact_path = Path(path_str)
        if not artifact_path.is_file():
            return (404, {"detail": f"Artifact file not found: {path_str}"})

        return artifact_path.read_text(encoding="utf-8", errors="replace")

    # -- interrupt / stop -----------------------------------------------------

    def interrupt_managed(
        self, tracked_agent_id: str
    ) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Send interrupt to a managed headless agent."""

        handle = self._require_handle(tracked_agent_id)
        if handle is None:
            return (404, {"detail": f"Managed headless agent not found: {tracked_agent_id}"})

        if handle.controller is None:
            return (
                503,
                {"detail": f"No live controller for agent {tracked_agent_id}"},
            )

        backend_session = handle.controller.backend_session
        if not isinstance(backend_session, HeadlessInteractiveSession):
            return (500, {"detail": "Agent backend does not support interrupt"})

        try:
            result = backend_session.interrupt()
            detail = f"Interrupt sent: {result.detail}" if result.detail else "Interrupt sent"
        except Exception as exc:
            detail = f"Interrupt attempted with error: {exc}"

        return PassiveAgentActionResponse(
            agent_id=tracked_agent_id,
            detail=detail,
        )

    def stop_managed(
        self, tracked_agent_id: str
    ) -> PassiveAgentActionResponse | tuple[int, dict[str, Any]]:
        """Stop and clean up a managed headless agent."""

        handle = self._require_handle(tracked_agent_id)
        if handle is None:
            return (404, {"detail": f"Managed headless agent not found: {tracked_agent_id}"})

        authority = handle.authority

        # Join any active turn worker
        if handle.turn_worker is not None and handle.turn_worker.is_alive():
            handle.turn_worker.join(timeout=5.0)

        # Stop the runtime controller
        if handle.controller is not None:
            try:
                handle.controller.backend_session.close()
            except Exception as exc:
                log.warning("Error closing backend session for %s: %s", tracked_agent_id, exc)

        # Kill tmux session
        try:
            kill_tmux_session(session_name=authority.tmux_session_name)
        except Exception as exc:
            log.warning("Error killing tmux session for %s: %s", tracked_agent_id, exc)

        # Clear shared registry
        agent_id = authority.agent_id or tracked_agent_id
        try:
            remove_live_agent_record(agent_id)
        except Exception as exc:
            log.warning("Error clearing registry for %s: %s", tracked_agent_id, exc)

        # Delete persisted authority + turns
        self.m_store.delete_agent(tracked_agent_id=tracked_agent_id)

        # Remove from in-memory map
        with self.m_lock:
            self.m_handles.pop(tracked_agent_id, None)

        log.info("Stopped managed headless agent %s", tracked_agent_id)

        return PassiveAgentActionResponse(
            agent_id=tracked_agent_id,
            detail=f"Agent {tracked_agent_id} stopped and cleaned up",
        )

    # -- queries --------------------------------------------------------------

    def is_managed(self, tracked_agent_id: str) -> bool:
        """Return whether a tracked agent id is owned by this service."""

        with self.m_lock:
            return tracked_agent_id in self.m_handles

    def resolve_managed_matches(self, agent_ref: str) -> tuple[str, ...]:
        """Return managed tracked ids matching one tracked/published/name reference."""

        candidate = agent_ref.strip()
        if not candidate:
            return ()

        matches: list[str] = []
        with self.m_lock:
            handles = list(self.m_handles.items())
        for tracked_agent_id, handle in handles:
            authority = handle.authority
            aliases = {tracked_agent_id}
            if authority.agent_name is not None:
                aliases.add(authority.agent_name)
            if authority.agent_id is not None:
                aliases.add(authority.agent_id)
            if candidate in aliases:
                matches.append(tracked_agent_id)
        return tuple(sorted(set(matches)))

    def resolve_managed_tracked_id(self, agent_ref: str) -> str | None:
        """Resolve one managed tracked id when the reference is unambiguous."""

        matches = self.resolve_managed_matches(agent_ref)
        if len(matches) != 1:
            return None
        return matches[0]

    def get_managed_control_state(
        self,
        tracked_agent_id: str,
    ) -> PassiveManagedHeadlessControlState | None:
        """Return live control posture for one passive-server-managed headless agent."""

        handle = self._require_handle(tracked_agent_id)
        authority = handle.authority if handle is not None else self.m_store.read_authority(
            tracked_agent_id=tracked_agent_id
        )
        if authority is None:
            return None
        active_turn = self.m_store.read_active_turn(tracked_agent_id=tracked_agent_id)
        latest_turn = self._latest_turn_record(tracked_agent_id=tracked_agent_id)
        runtime_resumable = handle is not None and handle.controller is not None
        tmux_session_live = tmux_session_exists(session_name=authority.tmux_session_name)
        return PassiveManagedHeadlessControlState(
            authority=authority,
            controller=handle.controller if handle is not None else None,
            runtime_resumable=runtime_resumable,
            tmux_session_live=tmux_session_live,
            can_accept_prompt_now=runtime_resumable and tmux_session_live and active_turn is None,
            interruptible=active_turn is not None,
            active_turn=active_turn,
            latest_turn=latest_turn,
        )

    # -- internal -------------------------------------------------------------

    def _require_handle(self, tracked_agent_id: str) -> _ManagedHeadlessHandle | None:
        """Return the in-memory handle or ``None``."""

        with self.m_lock:
            return self.m_handles.get(tracked_agent_id)

    def _latest_turn_record(self, *, tracked_agent_id: str) -> ManagedHeadlessTurnRecord | None:
        """Return the latest persisted turn record when present."""

        turn_records = self.m_store.list_turn_records(tracked_agent_id=tracked_agent_id)
        if not turn_records:
            return None
        turn_records.sort(
            key=lambda record: (
                record.completed_at_utc or "",
                record.started_at_utc,
                record.turn_id,
            ),
            reverse=True,
        )
        return turn_records[0]

    def _rebuild_handles(self) -> None:
        """Scan persisted authority records and rebuild live resumable handles."""

        rebuilt: dict[str, _ManagedHeadlessHandle] = {}
        for authority in self.m_store.list_authority_records():
            tracked_agent_id = authority.tracked_agent_id
            if not tmux_session_exists(session_name=authority.tmux_session_name):
                log.info(
                    "Cleaning up stale managed headless agent %s (tmux session gone)",
                    tracked_agent_id,
                )
                self._delete_authority(authority)
                continue

            manifest_path = Path(authority.manifest_path).expanduser().resolve()
            agent_def_dir = Path(authority.agent_def_dir).expanduser().resolve()
            if not manifest_path.is_file() or not agent_def_dir.is_dir():
                log.warning(
                    "Cleaning up stale managed headless agent %s (manifest or agent_def_dir missing)",
                    tracked_agent_id,
                )
                self._delete_authority(authority)
                continue

            try:
                controller = resume_runtime_session(
                    agent_def_dir=agent_def_dir,
                    session_manifest_path=manifest_path,
                )
            except (LaunchPlanError, SessionManifestError, RuntimeError) as exc:
                log.warning(
                    "Cleaning up unrecoverable managed headless agent %s after resume failure: %s",
                    tracked_agent_id,
                    exc,
                )
                self._delete_authority(authority)
                continue

            if controller.registry_launch_authority != "runtime":
                try:
                    self._publish_controller_registry_record(controller)
                except (OSError, SessionManifestError) as exc:
                    log.warning(
                        "Shared-registry refresh failed while rebuilding managed headless %s: %s",
                        tracked_agent_id,
                        exc,
                    )

            rebuilt_authority = authority.model_copy(
                update={
                    "manifest_path": str(controller.manifest_path.resolve()),
                    "session_root": str(controller.manifest_path.resolve().parent),
                    "tmux_session_name": controller.tmux_session_name
                    or authority.tmux_session_name,
                    "agent_name": controller.agent_identity or authority.agent_name,
                    "agent_id": controller.agent_id or authority.agent_id,
                    "updated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                }
            )
            self.m_store.write_authority(rebuilt_authority)
            rebuilt[tracked_agent_id] = _ManagedHeadlessHandle(
                authority=rebuilt_authority,
                controller=controller,
            )

        with self.m_lock:
            self.m_handles = rebuilt

    def _run_turn_worker(
        self,
        tracked_agent_id: str,
        turn_id: str,
        prompt: str,
        backend_session: HeadlessInteractiveSession,
    ) -> None:
        """Worker thread: send prompt and finalize turn record."""

        try:
            events = backend_session.send_prompt(prompt, turn_artifact_dir_name=turn_id)
            self._refresh_turn_record(
                tracked_agent_id=tracked_agent_id,
                turn_id=turn_id,
                completion_events=events,
                error_detail=None,
            )
            log.info("Turn %s completed for agent %s", turn_id, tracked_agent_id)
        except Exception as exc:
            log.error("Turn %s failed for agent %s: %s", turn_id, tracked_agent_id, exc)
            self._refresh_turn_record(
                tracked_agent_id=tracked_agent_id,
                turn_id=turn_id,
                completion_events=None,
                error_detail=str(exc),
            )

    def _headless_output_format(self, *, tracked_agent_id: str) -> str:
        """Return the configured headless output format for one managed agent."""

        handle = self._require_handle(tracked_agent_id)
        if handle is None or handle.controller is None:
            return "stream-json"
        output_format = handle.controller.launch_plan.metadata.get("headless_output_format")
        if isinstance(output_format, str) and output_format.strip():
            return output_format
        return "stream-json"

    def _refresh_turn_record(
        self,
        *,
        tracked_agent_id: str,
        turn_id: str,
        completion_events: list[SessionEvent] | None,
        error_detail: str | None,
    ) -> ManagedHeadlessTurnRecord | None:
        """Refresh one completed turn record from durable artifacts and final events."""

        record = self.m_store.read_turn_record(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
        )
        active_turn = self.m_store.read_active_turn(tracked_agent_id=tracked_agent_id)
        if record is None:
            if active_turn is not None and active_turn.turn_id == turn_id:
                self.m_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
            return None
        if active_turn is not None and active_turn.turn_id != turn_id:
            active_turn = None

        turn_dir = Path(record.turn_artifact_dir)
        stdout_path = turn_dir / "stdout.jsonl"
        stderr_path = turn_dir / "stderr.log"
        status_path = turn_dir / "exitcode"
        interrupt_requested_at_utc = (
            active_turn.interrupt_requested_at_utc if active_turn is not None else None
        ) or record.interrupt_requested_at_utc

        completion_source = (
            self._completion_source_from_events(completion_events) or record.completion_source
        )
        returncode = record.returncode
        final_status: Literal["active", "completed", "failed", "interrupted"]

        if status_path.exists():
            try:
                returncode = read_headless_turn_return_code(status_path=status_path)
            except Exception as exc:
                final_status = "failed"
                if error_detail is None:
                    error_detail = str(exc)
            else:
                if returncode == 0:
                    final_status = "completed"
                elif interrupt_requested_at_utc is not None:
                    final_status = "interrupted"
                else:
                    final_status = "failed"
                if completion_source is None and stdout_path.exists():
                    try:
                        completion_source = self._completion_source_from_events(
                            load_headless_turn_events(
                                stdout_path=stdout_path,
                                output_format=self._headless_output_format(
                                    tracked_agent_id=tracked_agent_id
                                ),
                                turn_index=record.turn_index,
                            )
                        )
                    except Exception:
                        log.warning(
                            "Failed to parse completion source from persisted stdout for %s/%s",
                            tracked_agent_id,
                            turn_id,
                        )
        elif interrupt_requested_at_utc is not None:
            final_status = "interrupted"
        else:
            final_status = "failed"
            if error_detail is None:
                error_detail = "Headless execution ended without a durable completion marker."

        updated_record = record.model_copy(
            update={
                "status": final_status,
                "completed_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                "stdout_path": str(stdout_path) if stdout_path.exists() else None,
                "stderr_path": str(stderr_path) if stderr_path.exists() else None,
                "status_path": str(status_path) if status_path.exists() else None,
                "completion_source": completion_source,
                "returncode": returncode,
                "error": error_detail,
                "interrupt_requested_at_utc": interrupt_requested_at_utc,
            }
        )
        self.m_store.write_turn_record(updated_record)
        self.m_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
        return updated_record

    def _completion_source_from_events(
        self,
        events: list[SessionEvent] | None,
    ) -> str | None:
        """Extract one completion-source hint from the final runtime events."""

        if not events:
            return None
        for event in reversed(events):
            payload = event.payload
            if not isinstance(payload, dict):
                continue
            value = payload.get("completion_source")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _publish_controller_registry_record(self, controller: RuntimeSessionController) -> None:
        """Publish the current runtime controller state into the shared registry."""

        record = controller.build_shared_registry_record()
        if record is None:
            raise SessionManifestError(
                "Managed runtime controller could not build a shared-registry record."
            )
        publish_live_agent_record(record)

    def _delete_authority(self, authority: ManagedHeadlessAuthorityRecord) -> None:
        """Remove one stale managed authority from registry and local storage."""

        agent_id = authority.agent_id or authority.tracked_agent_id
        try:
            remove_live_agent_record(agent_id)
        except Exception as exc:
            log.warning("Error clearing shared registry for stale agent %s: %s", agent_id, exc)
        self.m_store.delete_agent(tracked_agent_id=authority.tracked_agent_id)
