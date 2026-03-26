"""Headless agent lifecycle service for the passive server.

Manages the full lifecycle of server-launched headless agents: launch,
turn submission, turn status/events/artifacts, interrupt, stop, and
startup rebuild.
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessInteractiveSession,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    kill_tmux_session,
    tmux_session_exists,
)
from houmao.agents.realm_controller.launch_plan import backend_for_tool
from houmao.agents.realm_controller.registry_storage import (
    remove_live_agent_record,
)
from houmao.agents.realm_controller.runtime import (
    RuntimeSessionController,
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
        self.m_store = ManagedHeadlessStore(config=adapter)  # type: ignore[arg-type]
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

        working_dir = Path(request.working_directory).resolve()
        if not working_dir.is_dir():
            return (400, {"detail": f"working_directory not found: {request.working_directory}"})

        agent_def_dir = Path(request.agent_def_dir).resolve()
        if not agent_def_dir.is_dir():
            return (400, {"detail": f"agent_def_dir not found: {request.agent_def_dir}"})

        manifest_path = Path(request.brain_manifest_path).resolve()
        if not manifest_path.is_file():
            return (
                400,
                {"detail": f"brain_manifest_path not found: {request.brain_manifest_path}"},
            )

        backend = backend_for_tool(request.tool)
        if backend not in _HEADLESS_BACKENDS:
            return (
                400,
                {"detail": f"Unsupported backend for headless launch: {backend}"},
            )

        tracked_agent_id = uuid.uuid4().hex[:12]
        now_utc = datetime.now(UTC).isoformat(timespec="seconds")

        mailbox_transport: str | None = None
        mailbox_root: Path | None = None
        mailbox_principal_id: str | None = None
        mailbox_address: str | None = None
        if request.mailbox is not None:
            mailbox_transport = request.mailbox.transport
            mailbox_root = (
                Path(request.mailbox.filesystem_root)
                if request.mailbox.filesystem_root
                else None
            )
            mailbox_principal_id = request.mailbox.principal_id
            mailbox_address = request.mailbox.address

        try:
            controller = start_runtime_session(
                agent_def_dir=agent_def_dir,
                brain_manifest_path=manifest_path,
                role_name=request.role_name,
                backend=backend,
                working_directory=working_dir,
                api_base_url=self.m_config.api_base_url,
                agent_name=request.agent_name,
                agent_id=request.agent_id or tracked_agent_id,
                mailbox_transport=mailbox_transport,
                mailbox_root=mailbox_root,
                mailbox_principal_id=mailbox_principal_id,
                mailbox_address=mailbox_address,
                registry_launch_authority="external",
            )
        except Exception as exc:
            log.error("Failed to start runtime session for headless agent: %s", exc)
            return (500, {"detail": f"Failed to start headless agent: {exc}"})

        session_root = str(controller.job_dir) if controller.job_dir else str(working_dir)

        authority = ManagedHeadlessAuthorityRecord(
            tracked_agent_id=tracked_agent_id,
            backend=backend,  # type: ignore[arg-type]
            tool=request.tool,
            manifest_path=str(manifest_path),
            session_root=session_root,
            tmux_session_name=controller.tmux_session_name or tracked_agent_id,
            agent_def_dir=str(agent_def_dir),
            agent_name=request.agent_name,
            agent_id=request.agent_id or tracked_agent_id,
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
            request.tool,
            backend,
        )

        return PassiveHeadlessLaunchResponse(
            tracked_agent_id=tracked_agent_id,
            agent_name=request.agent_name or tracked_agent_id,
            manifest_path=str(manifest_path),
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

        record = self.m_store.read_turn_record(
            tracked_agent_id=tracked_agent_id, turn_id=turn_id
        )
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
        """Return structured events from the turn's stdout artifact."""

        record = self.m_store.read_turn_record(
            tracked_agent_id=tracked_agent_id, turn_id=turn_id
        )
        if record is None:
            return (404, {"detail": f"Turn not found: {turn_id}"})

        entries: list[HoumaoHeadlessTurnEvent] = []
        if record.stdout_path:
            stdout_path = Path(record.stdout_path)
            if stdout_path.is_file():
                try:
                    text = stdout_path.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines()):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            payload = json.loads(line)
                            entries.append(
                                HoumaoHeadlessTurnEvent(
                                    kind=payload.get("type", "output"),
                                    message=payload.get("message", line),
                                    turn_index=record.turn_index,
                                    timestamp_utc=payload.get(
                                        "timestamp",
                                        record.started_at_utc,
                                    ),
                                    payload=payload,
                                )
                            )
                        except (json.JSONDecodeError, TypeError):
                            entries.append(
                                HoumaoHeadlessTurnEvent(
                                    kind="output",
                                    message=line,
                                    turn_index=record.turn_index,
                                    timestamp_utc=record.started_at_utc,
                                )
                            )
                except OSError:
                    pass

        return PassiveHeadlessTurnEventsResponse(
            tracked_agent_id=tracked_agent_id,
            turn_id=turn_id,
            entries=entries,
        )

    def turn_artifact_text(
        self, tracked_agent_id: str, turn_id: str, name: str
    ) -> str | tuple[int, dict[str, Any]]:
        """Return the text content of a named turn artifact (stdout / stderr)."""

        record = self.m_store.read_turn_record(
            tracked_agent_id=tracked_agent_id, turn_id=turn_id
        )
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

    # -- internal -------------------------------------------------------------

    def _require_handle(self, tracked_agent_id: str) -> _ManagedHeadlessHandle | None:
        """Return the in-memory handle or ``None``."""

        with self.m_lock:
            return self.m_handles.get(tracked_agent_id)

    def _rebuild_handles(self) -> None:
        """Scan persisted authority records and rebuild in-memory handles."""

        records = self.m_store.list_authority_records()
        for authority in records:
            tid = authority.tracked_agent_id
            alive = tmux_session_exists(session_name=authority.tmux_session_name)
            if alive:
                log.info("Rebuilding handle for live agent %s", tid)
                # We don't attempt to resume the RuntimeSessionController here;
                # the agent runs in tmux and can be stopped via tmux kill.
                handle = _ManagedHeadlessHandle(authority=authority, controller=None)
                with self.m_lock:
                    self.m_handles[tid] = handle
            else:
                log.info("Cleaning up dead agent %s (tmux session gone)", tid)
                agent_id = authority.agent_id or tid
                try:
                    remove_live_agent_record(agent_id)
                except Exception:
                    pass
                self.m_store.delete_agent(tracked_agent_id=tid)

    def _run_turn_worker(
        self,
        tracked_agent_id: str,
        turn_id: str,
        prompt: str,
        backend_session: HeadlessInteractiveSession,
    ) -> None:
        """Worker thread: send prompt and finalize turn record."""

        try:
            backend_session.send_prompt(prompt, turn_artifact_dir_name=turn_id)

            record = self.m_store.read_turn_record(
                tracked_agent_id=tracked_agent_id, turn_id=turn_id
            )
            if record is not None:
                completed_at = datetime.now(UTC).isoformat(timespec="seconds")
                updated = record.model_copy(
                    update={
                        "status": "completed",
                        "completed_at_utc": completed_at,
                        "returncode": 0,
                        "completion_source": "send_prompt",
                    }
                )
                self.m_store.write_turn_record(updated)

            self.m_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
            log.info("Turn %s completed for agent %s", turn_id, tracked_agent_id)

        except Exception as exc:
            log.error("Turn %s failed for agent %s: %s", turn_id, tracked_agent_id, exc)
            record = self.m_store.read_turn_record(
                tracked_agent_id=tracked_agent_id, turn_id=turn_id
            )
            if record is not None:
                failed_at = datetime.now(UTC).isoformat(timespec="seconds")
                updated = record.model_copy(
                    update={
                        "status": "failed",
                        "completed_at_utc": failed_at,
                        "error": str(exc),
                    }
                )
                self.m_store.write_turn_record(updated)

            self.m_store.clear_active_turn(tracked_agent_id=tracked_agent_id)
