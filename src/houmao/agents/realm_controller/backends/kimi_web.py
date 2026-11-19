"""Own and control a managed stock Kimi Web host alongside its browser."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from html import escape
import json
import os
from pathlib import Path
import shlex
import sys
import time
from typing import Any, cast
from uuid import uuid4
import webbrowser

from houmao.agents.model_selection import ModelConfig
from houmao.agents.realm_controller.backends.dispatch_control import HeadlessDispatchControl
from houmao.agents.realm_controller.backends.dsh_acp_driver import _write_private_json
from houmao.agents.realm_controller.backends.dsh_web import DshWebSession
from houmao.agents.realm_controller.backends.dsh_web_client import DshWebError
from houmao.agents.realm_controller.backends.kimi_acp_journal import (
    _native_turn_id,
    kimi_session_journal,
)
from houmao.agents.realm_controller.backends.kimi_web_client import (
    KimiWebClient,
    KimiWebJournalWindow,
    native_id,
    observed_at,
    owned_listener,
)
from houmao.agents.realm_controller.backends.service_runtime import write_service_record
from houmao.agents.realm_controller.backends.tmux_runtime import (
    create_tmux_session,
    generate_tmux_session_name,
    has_tmux_session,
    kill_tmux_session,
    prepare_headless_agent_window,
    run_tmux,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.gateway_models import GatewayWebExecutionIdentityV1
from houmao.agents.realm_controller.models import (
    HeadlessTurnSessionSelection,
    LaunchPlan,
    RelaunchChatSessionSelection,
    SessionControlResult,
    SessionEvent,
)
from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1
from houmao.agents.realm_controller.usage_support import UsageService

_NATIVE_ARGS = ["web", "--no-open", "--host", "127.0.0.1", "--port", "0"]
_TMUX_OPTION = "@houmao_kimi_web_owner"
_TERMINAL_REASONS = {
    "completed": "completed",
    "failed": "failed",
    "blocked": "failed",
    "cancelled": "interrupted",
}
_OBSERVATION_EVENTS = {
    "turn.prompt": "turn/started",
    "turn.ended": "turn/ended",
    "prompt.completed": "inbox/settled",
    "prompt.aborted": "inbox/settled",
}


@dataclass
class KimiWebSessionState:
    """Persist only owner identities, privately held authority paths, and a clean origin."""

    origin: str
    web_identity: dict[str, Any]
    bootstrap_path: str
    cookie_path: str
    control_path: str
    supervisor_pid: int
    supervisor_birth_token: str
    tmux_session_name: str
    evidence_path: str
    working_directory: str
    native_pid: int
    native_birth_token: str
    turn_index: int = 0
    role_name: str = ""
    tmux_window_id: str | None = None
    tmux_pane_id: str | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> KimiWebSessionState:
        """Validate reconstructed Web identity without touching its native host."""

        names = {field.name for field in fields(cls)}
        state = cls(**{name: value for name, value in payload.items() if name in names})
        GatewayWebExecutionIdentityV1.model_validate(state.web_identity)
        native_id(state.web_identity["native_session_id"])
        state.native_surface
        if (
            type(state.supervisor_pid) is not int
            or state.supervisor_pid <= 0
            or not isinstance(state.supervisor_birth_token, str)
            or not state.supervisor_birth_token
            or type(state.native_pid) is not int
            or state.native_pid <= 0
            or not isinstance(state.native_birth_token, str)
            or not state.native_birth_token
            or not all(
                Path(value).is_absolute()
                for value in (
                    state.bootstrap_path,
                    state.cookie_path,
                    state.control_path,
                    state.evidence_path,
                    state.working_directory,
                )
            )
        ):
            raise BackendExecutionError("Kimi Web ownership state is invalid")
        return state

    def to_payload(self) -> dict[str, Any]:
        """Return owner evidence without any bearer value."""

        return {**asdict(self), "browser_url": self.browser_url}

    @property
    def browser_url(self) -> str:
        """Expose only the owner-local browser origin."""

        return self.origin

    @property
    def native_surface(self) -> WebNativeSurfaceV1:
        """Describe the native browser separately from the supervisor pane."""

        return WebNativeSurfaceV1(
            origin=self.origin, native_session_id=self.web_identity["native_session_id"]
        )


class KimiWebSession:
    """Connect browser-independent managed control to an exact owned Kimi session."""

    backend = "kimi_web"

    def __init__(self) -> None:
        """Construct an unbound adapter before starting or restoring native ownership."""

        self.m_plan: LaunchPlan | None = None
        self.m_manifest_path: Path | None = None
        self.m_state: KimiWebSessionState | None = None
        self.m_dispatch_control: HeadlessDispatchControl | None = None
        self.m_force_cleanup: bool = False
        self.m_binding_changed: Callable[[], None] | None = None

    @classmethod
    def from_launch_plan(
        cls,
        *,
        launch_plan: LaunchPlan,
        session_manifest_path: Path,
        role_name: str,
        state: KimiWebSessionState | None = None,
        agent_def_dir: Path | None = None,
        tmux_session_name: str | None = None,
        provider_start: bool = False,
    ) -> KimiWebSession:
        """Reconstruct an existing binding or explicitly start one owned host."""

        del agent_def_dir
        instance = cls()
        instance.m_plan = launch_plan
        instance.m_manifest_path = session_manifest_path.resolve()
        instance.m_state = state
        if provider_start:
            instance._start(role_name=role_name, tmux_session_name=tmux_session_name)
        elif (
            state is None
            or Path(state.working_directory) != launch_plan.working_directory.resolve()
        ):
            raise BackendExecutionError("Kimi Web requires its exact persisted workspace")
        elif Path(state.cookie_path) != launch_plan.home_path.resolve() / "server.token":
            raise BackendExecutionError("Kimi Web credential escaped its private home")
        return instance

    @property
    def state(self) -> KimiWebSessionState:
        """Return the exact current native and supervisor binding."""

        if self.m_state is None:
            raise BackendExecutionError("Kimi Web ownership is unavailable")
        return self.m_state

    @property
    def plan(self) -> LaunchPlan:
        """Return the resolved Kimi launch plan."""

        if self.m_plan is None:
            raise BackendExecutionError("Kimi Web launch configuration is unavailable")
        return self.m_plan

    @property
    def manifest_path(self) -> Path:
        """Return the owner manifest coordinating runtime request identity."""

        if self.m_manifest_path is None:
            raise BackendExecutionError("Kimi Web runtime manifest is unavailable")
        return self.m_manifest_path

    @property
    def session_route(self) -> str:
        """Address the exact native session without following any user redirect."""

        return f"/sessions/{native_id(self.state.web_identity['native_session_id'])}"

    def _client(self) -> KimiWebClient:
        """Connect to the captured process without retaining a browser cookie."""

        state = self.state
        return KimiWebClient(
            state.origin, state.native_pid, state.native_birth_token, Path(state.cookie_path)
        )

    def set_binding_changed_callback(self, callback: Callable[[], None]) -> None:
        """Set the runtime publisher for explicit Web binding changes."""

        self.m_binding_changed = callback

    def configure_request_dispatch(self, control: HeadlessDispatchControl | None) -> None:
        """Install the revocable permission for one exact managed request."""

        self.m_dispatch_control = control

    def configure_stop_force_cleanup(self, *, force_cleanup: bool) -> None:
        """Allow cleanup of the verified tmux owner when explicitly requested."""

        self.m_force_cleanup = force_cleanup

    def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
        """Update managed metadata without redirecting an existing owner."""

        if (
            launch_plan.backend != self.backend
            or launch_plan.home_path.resolve() != self.plan.home_path.resolve()
            or launch_plan.working_directory.resolve() != self.plan.working_directory.resolve()
        ):
            raise BackendExecutionError("Kimi Web requires its original private home and workspace")
        self.m_plan = launch_plan

    def _start(
        self, *, role_name: str, tmux_session_name: str | None, resume_id: str | None = None
    ) -> None:
        """Start the selected native binary under a private captured supervisor."""

        plan = self.plan
        options = plan.metadata.get("kimi_web")
        selection = plan.metadata.get("managed_web_identity")
        if (
            list(plan.args) != _NATIVE_ARGS
            or not isinstance(options, dict)
            or options.get("detected_version") != "2.6.0"
            or not isinstance(selection, dict)
            or not all(
                isinstance(selection.get(k), str) and selection[k]
                for k in ("agent_id", "runtime_session_id", "generation")
            )
        ):
            raise BackendExecutionError(
                "Kimi Web requires a qualified launch and managed owner identity"
            )
        home = plan.home_path.resolve()
        workspace = plan.working_directory.resolve()
        if resume_id is not None:
            kimi_session_journal(home, workspace, resume_id)
        root = home / "houmao-web" / uuid4().hex
        root.mkdir(parents=True, mode=0o700)
        control = root / "control.json"
        bootstrap = root / "bootstrap.json"
        _write_private_json(control, cast(dict[str, Any], selection))
        invocation = root / "supervisor-input.json"
        environment = {
            **{
                key: os.environ[key]
                for key in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "TERM")
                if key in os.environ
            },
            **plan.env,
            "KIMI_CODE_HOME": str(home),
        }
        _write_private_json(
            invocation,
            {
                "root": str(root),
                "working_directory": str(workspace),
                "environment": environment,
                "command": [plan.executable, *_NATIVE_ARGS],
                "name": "Kimi Web",
            },
        )
        name = tmux_session_name or generate_tmux_session_name(tool="kimi", role_name=role_name)
        previous = self.m_state
        created = has_tmux_session(session_name=name).returncode == 1
        if not created and (previous is None or not self._owns_tmux(name, previous.control_path)):
            raise BackendExecutionError("Kimi Web refuses to adopt another tmux session")
        try:
            if created:
                create_tmux_session(session_name=name, working_directory=workspace)
            if run_tmux(["set-option", "-t", name, _TMUX_OPTION, str(control)]).returncode:
                raise BackendExecutionError("Kimi Web cannot mark its owned tmux session")
            surface = prepare_headless_agent_window(session_name=name, fresh_session=created)
            command = shlex.join(
                [
                    sys.executable,
                    "-m",
                    "houmao.agents.realm_controller.backends.dsh_web_supervisor",
                    "--input",
                    str(invocation),
                ]
            )
            if run_tmux(["respawn-pane", "-k", "-t", surface.pane_id, command]).returncode:
                raise BackendExecutionError("Kimi Web supervisor could not start")
            process, client, meta = self._wait_for_host(home, root)
            if resume_id is None:
                descriptor = client.request(
                    "POST", "/sessions", {"metadata": {"cwd": str(workspace)}}
                )
            else:
                descriptor = client.request("GET", f"/sessions/{native_id(resume_id)}")
            session_id = native_id(descriptor.get("id"))
            self._verify_session(
                descriptor, session_id=resume_id or session_id, workspace=workspace
            )
            journal = kimi_session_journal(home, workspace, session_id)
            identity = {
                "protocol_version": 1,
                **{key: selection[key] for key in ("agent_id", "runtime_session_id", "generation")},
                "host_incarnation": native_id(meta.get("server_id")),
                "native_session_id": session_id,
                "agent_incarnation": uuid4().hex,
            }
            _write_private_json(bootstrap, {"identity": identity, "origin": client.origin})
            self.m_state = KimiWebSessionState(
                origin=client.origin,
                web_identity=identity,
                bootstrap_path=str(bootstrap),
                cookie_path=str(client.token_file),
                control_path=str(control),
                supervisor_pid=process["supervisor_pid"],
                supervisor_birth_token=process["supervisor_birth_token"],
                tmux_session_name=name,
                evidence_path=str(journal),
                working_directory=str(workspace),
                native_pid=client.pid,
                native_birth_token=client.birth,
                role_name=role_name,
                tmux_window_id=surface.window_id,
                tmux_pane_id=surface.pane_id,
            )
        except BaseException:
            DshWebSession._stop_supervisor_file(root / "supervisor.json")
            if created and self._owns_tmux(name, str(control)):
                kill_tmux_session(session_name=name)
            raise
        finally:
            invocation.unlink(missing_ok=True)

    @staticmethod
    def _wait_for_host(
        home: Path, root: Path
    ) -> tuple[dict[str, Any], KimiWebClient, dict[str, Any]]:
        """Pair Kimi's native instance registry with the exact captured listener."""

        until = time.monotonic() + 30
        while time.monotonic() < until and not (root / "exit.json").exists():
            try:
                process = json.loads((root / "supervisor.json").read_text())
                pid, birth = process["native_pid"], process["native_birth_token"]
                for path in (home / "server" / "instances").glob("*.json"):
                    instance = json.loads(path.read_text())
                    port = instance.get("port")
                    if (
                        instance.get("pid") == pid
                        and instance.get("host") == "127.0.0.1"
                        and type(port) is int
                        and 0 < port <= 65535
                        and owned_listener(pid, birth, port)
                    ):
                        client = KimiWebClient(
                            f"http://127.0.0.1:{port}", pid, birth, home / "server.token"
                        )
                        try:
                            client.request("GET", "/meta", authenticated=False)
                        except DshWebError as exc:
                            if exc.code != "authentication_failed":
                                raise
                        else:
                            raise BackendExecutionError(
                                "Kimi Web listener permits unauthenticated access"
                            )
                        meta = client.request("GET", "/meta")
                        if meta.get("dangerous_bypass_auth") is not False:
                            raise BackendExecutionError(
                                "Kimi Web must enforce native authentication"
                            )
                        return process, client, meta
            except (OSError, ValueError, KeyError, DshWebError):
                pass
            time.sleep(0.08)
        raise BackendExecutionError(
            "Kimi Web supervisor did not publish a verified authenticated listener"
        )

    @staticmethod
    def _verify_session(payload: Mapping[str, Any], *, session_id: str, workspace: Path) -> None:
        """Reject another workspace or a session selected by native fallback."""

        metadata = payload.get("metadata")
        cwd = metadata.get("cwd") if isinstance(metadata, dict) else None
        if (
            payload.get("id") != session_id
            or not isinstance(cwd, str)
            or Path(cwd).resolve() != workspace
            or payload.get("archived") is not False
        ):
            raise DshWebError("identity_mismatch", "Kimi Web session or workspace changed")

    def _require_current(self) -> None:
        """Fence mutations by exact persisted owner and host generation."""

        try:
            binding = json.loads(self.manifest_path.read_text())
            if (
                binding["backend"] == self.backend
                and binding["registry_generation_id"] == self.state.web_identity["generation"]
                and binding["backend_state"]["web_identity"] == self.state.web_identity
            ):
                return
        except (OSError, ValueError, KeyError, TypeError):
            pass
        raise DshWebError("stale_identity", "Kimi Web runtime ownership changed")

    def _session(self, client: KimiWebClient) -> dict[str, Any]:
        """Read native indexed session state without starting a cold agent."""

        payload = client.request("GET", self.session_route)
        self._verify_session(
            payload,
            session_id=self.state.web_identity["native_session_id"],
            workspace=Path(self.state.working_directory),
        )
        return payload

    def _journal(self, *, start: int | None = None) -> KimiWebJournalWindow:
        """Read only the verified exact workspace session journal."""

        path = kimi_session_journal(
            Path(self.state.cookie_path).parent,
            Path(self.state.working_directory),
            self.state.web_identity["native_session_id"],
        )
        if path != Path(self.state.evidence_path):
            raise DshWebError("stale_identity", "Kimi Web journal binding changed")
        return KimiWebJournalWindow.read(path, start=start)

    def browser_credentials(self) -> tuple[str, str]:
        """Provide a native browser credential solely within the verified owner context."""

        self._require_current()
        client = self._client()
        if (
            client.request("GET", "/meta").get("server_id")
            != self.state.web_identity["host_incarnation"]
        ):
            raise DshWebError("stale_identity", "Kimi Web host incarnation changed")
        return client.origin, client.credential()

    def open_browser(self) -> SessionControlResult:
        """Open a verified owner-local browser origin through its explicit management command."""

        try:
            origin, token = self.browser_credentials()
            location = escape(f"{origin}/#token={token}", quote=True)
            path = Path(self.state.bootstrap_path).parent / "open-browser.html"
            descriptor = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(
                    f'<!doctype html><meta http-equiv="refresh" content="0;url={location}">'
                )
            opened = webbrowser.open(path.as_uri())
            if not opened:
                path.unlink(missing_ok=True)
        except (OSError, RuntimeError, webbrowser.Error):
            opened = False
        return SessionControlResult(
            "ok" if opened else "error",
            "open_browser",
            "Opened the native Kimi Web browser location."
            if opened
            else "Cannot open the native browser in this execution context.",
        )

    def close_control_connection(self) -> None:
        """Release connection state independently of browser and host ownership."""

    def close(self) -> None:
        """Close adapter control while preserving the owned native host."""

        self.close_control_connection()

    @staticmethod
    def _owns_tmux(name: str, control: str) -> bool:
        """Confirm the exact owned tmux session before acting on any pane."""

        result = run_tmux(["show-options", "-v", "-t", name, _TMUX_OPTION])
        return result.returncode == 0 and result.stdout.strip() == control

    def terminate(self) -> SessionControlResult:
        """Stop only the captured supervisor and native descendants."""

        state = self.state
        try:
            (Path(state.bootstrap_path).parent / "open-browser.html").unlink(missing_ok=True)
            supervisor_file = Path(state.bootstrap_path).parent / "supervisor.json"
            captured = json.loads(supervisor_file.read_text())
            if not isinstance(captured, dict) or any(
                captured.get(field) != getattr(state, field)
                for field in (
                    "supervisor_pid",
                    "supervisor_birth_token",
                    "native_pid",
                    "native_birth_token",
                )
            ):
                raise BackendExecutionError("Kimi Web supervisor identity changed")
            DshWebSession._stop_supervisor_file(supervisor_file)
            if (
                self.m_force_cleanup
                and has_tmux_session(session_name=state.tmux_session_name).returncode == 0
            ):
                if not self._owns_tmux(state.tmux_session_name, state.control_path):
                    raise BackendExecutionError("Kimi Web supervisor ownership changed")
                kill_tmux_session(session_name=state.tmux_session_name)
            return SessionControlResult("ok", "terminate", "Stopped the owned Kimi Web host.")
        except (OSError, ValueError, RuntimeError):
            return SessionControlResult(
                "error", "terminate", "Kimi Web owner cleanup could not be verified."
            )

    def relaunch(
        self, *, chat_session: RelaunchChatSessionSelection | None = None
    ) -> SessionControlResult:
        """Replace the owner and explicitly create or bind the exact requested native session."""

        selected = chat_session or RelaunchChatSessionSelection(mode="new")
        previous = self.state
        exact = previous.web_identity["native_session_id"]
        if selected.mode not in {"new", "exact"} or (
            selected.mode == "exact" and selected.session_id != exact
        ):
            return SessionControlResult(
                "error", "relaunch", "Kimi Web requires new or the exact saved session."
            )
        stopped = self.terminate()
        if stopped.status != "ok":
            return SessionControlResult("error", "relaunch", stopped.detail)
        try:
            self._start(
                role_name=previous.role_name,
                tmux_session_name=previous.tmux_session_name,
                resume_id=exact if selected.mode == "exact" else None,
            )
        except (OSError, ValueError, RuntimeError):
            return SessionControlResult(
                "error", "relaunch", "Kimi Web relaunch could not be verified."
            )
        return SessionControlResult("ok", "relaunch", "Relaunched the owned Kimi Web host.")

    def observe_web_state(self) -> dict[str, Any]:
        """Project current busy state without invoking the native prompt-list route."""

        self._require_current()
        client = self._client()
        session = self._session(client)
        window = self._journal()
        events = self._history_entries(window)
        sequence = events[-1]["sequence"] if events else 0
        active: dict[str, Any] | None = None
        last: dict[str, Any] | None = None
        for item in events:
            if item["event"] == "turn/started":
                active = {"turn": item["turn"], "start_sequence": item["sequence"]}
            elif item["event"] == "turn/ended":
                last = {
                    "turn": item["turn"],
                    "end_sequence": item["sequence"],
                    "result": item["result"],
                }
                if active is not None and active["turn"] == item["turn"]:
                    active = None
        wait = session.get("pending_interaction")
        if wait == "none":
            waits: list[str] = []
        elif wait in ("approval", "question"):
            waits = [wait]
        else:
            waits = ["other"]
        ready = (
            session.get("busy") is False
            and session.get("main_turn_active") is False
            and active is None
            and not waits
        )
        return {
            "protocol_version": 1,
            "identity": self.state.web_identity,
            "available": True,
            "native_agent_live": True if session.get("busy") is True else None,
            "observed_at_utc": datetime.now(UTC).isoformat(),
            "sequence": sequence,
            "cursor": window.end,
            "active_turn": active if session.get("main_turn_active") is True else None,
            "last_turn": last,
            "pending_inbox": [],
            "interaction_waits": waits,
            "admission": {"ready_only": ready, "if_no_pending": False, "always": False},
            "model": None,
        }

    def observe_web_history(self, *, after_sequence: int = -1, limit: int = 100) -> dict[str, Any]:
        """Read covered sparse journal offsets without retargeting the conversation."""

        self._require_current()
        window = self._journal()
        all_events = self._history_entries(window)
        sequence = all_events[-1]["sequence"] if all_events else 0
        covered = (
            after_sequence in {-1, sequence}
            or (after_sequence == 0 and window.start == 0)
            or any(item["sequence"] == after_sequence for item in all_events)
        )
        events = [item for item in all_events if item["sequence"] > after_sequence]
        return {
            "identity": self.state.web_identity,
            "sequence": sequence,
            "previous_sequence": after_sequence,
            "entries": events[:limit] if covered else [],
            "has_more": covered and len(events) > limit,
            "truncated": not covered,
        }

    def _history_entries(self, window: KimiWebJournalWindow) -> list[dict[str, Any]]:
        """Expose native record identities and outcomes without prompt content."""

        entries: list[dict[str, Any]] = []
        for _, end, row in window.records:
            kind = row.get("type")
            if not isinstance(kind, str) or kind not in _OBSERVATION_EVENTS:
                continue
            turn = row.get("turnId")
            if kind.startswith("turn.") and (type(turn) is not int or turn < 0):
                continue
            item: dict[str, Any] = {
                "native_sequence": end,
                "sequence": end,
                "event": _OBSERVATION_EVENTS[kind],
                "observed_at_utc": observed_at(row),
                "identity": self.state.web_identity,
            }
            if type(turn) is int:
                item["turn"] = turn
            if isinstance(row.get("promptId"), str):
                item["message_id"] = native_id(row["promptId"])
            if kind == "turn.ended":
                reason = row.get("reason")
                item["result"] = (
                    _TERMINAL_REASONS.get(reason, "unknown")
                    if isinstance(reason, str)
                    else "unknown"
                )
            entries.append(item)
        return entries

    def plugin_execution_identity(self) -> tuple[str, ...]:
        """Capture the same verified Kimi host and conversation for ordinary dispatch."""

        self.observe_web_state()
        identity = self.state.web_identity
        return tuple(
            identity[key]
            for key in ("generation", "host_incarnation", "agent_incarnation", "native_session_id")
        )

    def send_prompt(
        self,
        prompt: str,
        *,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
    ) -> list[SessionEvent]:
        """Send one ordinary prompt through the exact native session's HTTP route."""

        return self.send_web_prompt(
            prompt,
            turn_artifact_dir_name=turn_artifact_dir_name,
            session_selection=session_selection,
            execution_model=execution_model,
        )

    def send_web_prompt(
        self,
        prompt: str,
        *,
        admission_policy: str = "ready_only",
        operator: bool = True,
        turn_artifact_dir_name: str | None = None,
        session_selection: HeadlessTurnSessionSelection | None = None,
        execution_model: ModelConfig | None = None,
        deadline_epoch_ms: int | None = None,
        timeout_seconds: float = 300,
    ) -> list[SessionEvent]:
        """Check readiness, send one native request, and wait for its exact journal closure."""

        del operator
        if not prompt.strip() or timeout_seconds <= 0:
            raise DshWebError("invalid_request", "Kimi Web requires input and a positive timeout")
        if admission_policy != "ready_only":
            raise DshWebError(
                "invalid_policy", "Kimi Web supports only ordinary ready_only delivery"
            )
        session = self.state.web_identity["native_session_id"]
        if session_selection is not None and (
            session_selection.mode != "exact" or session_selection.session_id != session
        ):
            raise DshWebError("invalid_request", "Kimi Web addresses only its bound native session")
        if execution_model is not None and not execution_model.is_empty():
            raise DshWebError(
                "invalid_request", "Kimi Web prompt delivery preserves native model settings"
            )
        control = self.m_dispatch_control
        if control is not None:
            control.require_allowed()
        self._require_current()
        operation = turn_artifact_dir_name or f"web-{uuid4().hex}"
        path = self._turn_dir(operation)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        identity = dict(self.state.web_identity)
        prompt_id = f"houmao_{uuid4().hex}"
        baseline = self._journal()
        attempt = {
            "version": 1,
            "operation_id": operation,
            "identity": identity,
            "message_id": prompt_id,
            "journal_baseline_offset": baseline.end,
            "journal_device": baseline.device,
            "journal_inode": baseline.inode,
        }
        try:
            _write_private_json(path / "web-attempt.json", attempt)
        except FileExistsError:
            raise DshWebError(
                "invalid_request", "This Kimi Web operation already has a native attempt"
            ) from None
        service = UsageService.from_manifest(self.manifest_path)
        service.begin_headless_turn(
            turn_id=operation,
            turn_dir=path,
            turn_index=self.state.turn_index + 1,
            new_session=False,
        )
        _write_private_json(
            path / "process.json",
            {
                "child_pid": self.state.native_pid,
                "child_birth_token": self.state.native_birth_token,
            },
        )

        client = self._client()

        def before_send() -> None:
            """Recheck the exact managed permission immediately before socket transmission."""

            self._require_current()
            if control is not None:
                try:
                    control.require_allowed()
                except BackendExecutionError:
                    raise DshWebError(
                        "cancelled", "Kimi Web dispatch permission ended before send"
                    ) from None
            self._check_ready(client)
            self._require_current()
            if deadline_epoch_ms is not None and time.time() * 1000 >= deadline_epoch_ms:
                raise DshWebError("expired", "Kimi Web dispatch permission expired before send")
            if control is not None:
                if control.m_cancelled.is_set() or time.monotonic() >= control.m_deadline:
                    raise DshWebError("cancelled", "Kimi Web dispatch permission ended before send")
                control.m_input_started.set()

        reply = client.request(
            "POST",
            f"{self.session_route}/prompts",
            {"content": [{"type": "text", "text": prompt}], "prompt_id": prompt_id},
            before_send=before_send,
        )
        status = reply.get("status")
        if reply.get("prompt_id") != prompt_id or status not in ("running", "queued", "blocked"):
            raise DshWebError(
                "outcome_uncertain", "Kimi Web did not identify the submitted native prompt"
            )
        receipt = {
            "operation_id": operation,
            "identity": identity,
            "status": status,
            "native_status": status,
            "message_id": prompt_id,
        }
        write_service_record(path / "web-receipt.json", receipt)
        if control is not None:
            control.confirm_durable_handoff()
        events = [
            SessionEvent(
                kind="status",
                message=f"Kimi Web prompt {status}",
                turn_index=self.state.turn_index,
                payload={"phase": "native_admission", "native_prompt_id": prompt_id, **receipt},
            )
        ]
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            self._require_current()
            terminal = self._settle(operation, attempt)
            if terminal is not None:
                self.state.turn_index += 1
                if terminal["assistant_text"]:
                    events.append(
                        SessionEvent(
                            kind="assistant",
                            message=terminal["assistant_text"],
                            turn_index=self.state.turn_index,
                            payload={"text": terminal["assistant_text"], "operation_id": operation},
                        )
                    )
                events.append(
                    SessionEvent(
                        kind="done",
                        message=f"Kimi Web turn {terminal['outcome']}",
                        turn_index=self.state.turn_index,
                        payload={
                            "outcome": terminal["outcome"],
                            "operation_id": operation,
                            "identity": identity,
                            "native_input_id": prompt_id,
                            "native_turn_ids": terminal["receipt"]["turns"],
                            "native_status": status,
                        },
                    )
                )
                return events
            time.sleep(0.1)
        raise DshWebError(
            "outcome_uncertain", "Kimi Web terminal evidence is pending for the exact request"
        )

    def _check_ready(self, client: KimiWebClient) -> None:
        """Require exact idle activity and an empty native queue before sending."""

        session = self._session(client)
        if (
            session.get("busy") is not False
            or session.get("main_turn_active") is not False
            or session.get("pending_interaction") != "none"
        ):
            raise DshWebError("not_ready", "Kimi Web is busy or waiting for an interaction")
        # This read may initialize a cold agent. It belongs to explicit dispatch only.
        prompts = client.request("GET", f"{self.session_route}/prompts")
        if "active" not in prompts or prompts["active"] is not None or prompts.get("queued") != []:
            raise DshWebError("not_ready", "Kimi Web already has active or pending input")

    def cancel_request_dispatch(self, control: HeadlessDispatchControl) -> None:
        """Revoke future input without mistaking a crossed HTTP send for a refusal."""

        control.cancel()

    def _turn_dir(self, operation: str) -> Path:
        """Resolve a single operation artifact directory under the managed owner."""

        if not operation or operation in {".", ".."} or Path(operation).name != operation:
            raise DshWebError("invalid_request", "Invalid Kimi Web request identity")
        manifest = self.manifest_path
        return manifest.parent / f"{manifest.stem}.turn-artifacts" / operation

    def recover_web_prompt_result(self, request_id: str) -> None:
        """Settle a previously sent prompt from exact native journal evidence without replay."""

        self._require_current()
        path = self._turn_dir(request_id)
        try:
            attempt = json.loads((path / "web-attempt.json").read_text())
        except FileNotFoundError:
            return
        if (
            attempt.get("identity") == self.state.web_identity
            and attempt.get("operation_id") == request_id
        ):
            self._settle(request_id, attempt)

    def _settle(self, operation: str, attempt: Mapping[str, Any]) -> dict[str, Any] | None:
        """Publish exact native turn outcome and attributed text for one managed prompt."""

        path = self._turn_dir(operation)
        result_file = path / "web-result.json"
        try:
            previous = json.loads(result_file.read_text())
        except FileNotFoundError:
            pass
        else:
            if (
                previous.get("operation_id") == operation
                and previous.get("identity") == self.state.web_identity
            ):
                return cast(dict[str, Any], previous)
            raise DshWebError("identity_mismatch", "Kimi Web terminal evidence changed identity")
        prompt_id = native_id(attempt["message_id"])
        window = self._journal(start=attempt["journal_baseline_offset"])
        if attempt["journal_inode"] and (window.device, window.inode) != (
            attempt["journal_device"],
            attempt["journal_inode"],
        ):
            raise DshWebError(
                "outcome_uncertain", "Kimi Web journal identity changed after dispatch"
            )
        closure = _exact_closure(window, prompt_id)
        if closure is None:
            return None
        try:
            receipt = json.loads((path / "web-receipt.json").read_text())
        except FileNotFoundError:
            receipt = {
                "operation_id": operation,
                "identity": self.state.web_identity,
                "message_id": prompt_id,
                "native_status": "unknown",
            }
        if (
            receipt.get("operation_id") != operation
            or receipt.get("identity") != self.state.web_identity
            or receipt.get("message_id") != prompt_id
        ):
            raise DshWebError("identity_mismatch", "Kimi Web admission evidence changed identity")
        receipt.update(status="terminal", turns=[closure.turn] if closure.turn is not None else [])
        result = {
            "operation_id": operation,
            "identity": self.state.web_identity,
            "outcome": closure.outcome,
            "receipt": receipt,
            "assistant_text": closure.assistant_text,
        }
        if closure.turn is not None and closure.baseline is not None:
            identity = self.state.web_identity
            write_service_record(
                path / "kimi-native-turn.json",
                {
                    "version": 1,
                    "agent_id": identity["agent_id"],
                    "runtime_session_id": identity["runtime_session_id"],
                    "generation_id": identity["generation"],
                    "service_incarnation": identity["host_incarnation"],
                    "request_id": operation,
                    "native_session_id": identity["native_session_id"],
                    "native_turn_id": str(closure.turn),
                    "native_prompt_id": prompt_id,
                    "terminal": closure.outcome,
                    "settled_at_utc": closure.settled_at,
                    "process_id": self.state.native_pid,
                    "process_birth_token": self.state.native_birth_token,
                    "journal_path": self.state.evidence_path,
                    "journal_device": window.device,
                    "journal_inode": window.inode,
                    "journal_baseline_offset": closure.baseline,
                    "journal_settled_offset": closure.end,
                },
            )
        write_service_record(result_file, result)
        return result

    def interrupt(self) -> SessionControlResult:
        """Capture and interrupt the active native prompt without retargeting a later turn."""

        try:
            state = self.observe_web_state()
            active = state["active_turn"]
            if active is None:
                return SessionControlResult(
                    "ok", "interrupt", "No verified active Kimi Web prompt."
                )
            return self.interrupt_web_turn(
                self.state.web_identity,
                turn_start_seq=active["start_sequence"],
            )
        except (OSError, ValueError, RuntimeError):
            return SessionControlResult(
                "error", "interrupt", "Kimi Web interruption is unavailable."
            )

    def interrupt_web_turn(
        self,
        identity: Mapping[str, Any],
        *,
        turn_start_seq: int,
        operation_id: str | None = None,
    ) -> SessionControlResult:
        """Abort only the prompt ID from the captured turn start in this incarnation."""

        try:
            self._require_current()
            if identity != self.state.web_identity:
                raise DshWebError("stale_identity", "Kimi Web host incarnation changed")
            current = self.observe_web_state().get("active_turn")
            if current is None or current["start_sequence"] != turn_start_seq:
                raise DshWebError("stale_identity", "Captured Kimi Web turn already changed")
            target = next(
                native_id(row["promptId"])
                for _, end, row in self._journal().records
                if end == turn_start_seq and row.get("type") == "turn.prompt"
            )
            if operation_id is not None:
                attempt = json.loads(
                    (self._turn_dir(operation_id) / "web-attempt.json").read_text()
                )
                if attempt.get("identity") != identity or attempt.get("message_id") != target:
                    raise DshWebError(
                        "stale_identity", "Captured Kimi Web prompt belongs to another request"
                    )
            receipt = self._client().request(
                "POST",
                f"{self.session_route}/prompts/{target}:abort",
                {},
                before_send=self._require_current,
            )
            if receipt.get("aborted") is not True:
                raise DshWebError("outcome_uncertain", "Kimi Web did not confirm the abort")
            return SessionControlResult(
                "ok", "interrupt", "Kimi Web accepted abort for the captured prompt."
            )
        except (OSError, ValueError, RuntimeError, KeyError, StopIteration):
            return SessionControlResult(
                "error", "interrupt", "Kimi Web refused the captured interruption."
            )


@dataclass(frozen=True)
class _Closure:
    """One exact native request's completed interval."""

    turn: int | None
    baseline: int | None
    end: int
    settled_at: str
    outcome: str
    assistant_text: str


def _exact_closure(window: KimiWebJournalWindow, prompt_id: str) -> _Closure | None:
    """Pair matching native prompt and turn terminal records without borrowing browser output."""

    turn: int | None = None
    baseline: int | None = None
    reason: str | None = None
    chunks: list[str] = []
    remaining = 32 * 1024
    for start, end, row in window.records:
        kind = row.get("type")
        if kind == "turn.prompt" and row.get("promptId") == prompt_id:
            if turn is not None or type(row.get("turnId")) is not int or row["turnId"] < 0:
                raise DshWebError(
                    "outcome_uncertain", "Kimi Web prompt has conflicting native turn identity"
                )
            turn = row["turnId"]
            baseline = start
        elif kind == "turn.ended" and turn is not None and row.get("turnId") == turn:
            value = row.get("reason")
            reason = _TERMINAL_REASONS.get(value) if isinstance(value, str) else None
        elif kind in ("prompt.completed", "prompt.aborted") and row.get("promptId") == prompt_id:
            value = row.get("reason")
            outcome = (
                "interrupted"
                if kind == "prompt.aborted"
                else (_TERMINAL_REASONS.get(value) if isinstance(value, str) else None)
            )
            if (
                outcome is None
                or (turn is not None and outcome != reason)
                or (turn is None and outcome == "completed")
            ):
                raise DshWebError("outcome_uncertain", "Kimi Web terminal evidence disagrees")
            return _Closure(turn, baseline, end, observed_at(row), outcome, "".join(chunks))
        elif kind == "context.append_loop_event" and turn is not None and remaining:
            event = row.get("event")
            if (
                not isinstance(event, dict)
                or _native_turn_id(event.get("turnId")) != str(turn)
                or event.get("type") != "content.part"
            ):
                continue
            part = event.get("part")
            if (
                isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            ):
                encoded = part["text"].encode()[:remaining]
                chunks.append(encoded.decode(errors="ignore"))
                remaining -= len(encoded)
    return None


def recover_kimi_web_prompt_result(manifest_path: Path, generation: str, request_id: str) -> None:
    """Recover one exact local journal result without calling Kimi or reserving ownership."""

    try:
        manifest = json.loads(manifest_path.read_text())
        if manifest["backend"] != "kimi_web" or manifest["registry_generation_id"] != generation:
            return
        state = KimiWebSessionState.from_payload(manifest["backend_state"])
        home = Path(manifest["launch_plan"]["home_selector"]["home_path"]).resolve()
        if (
            Path(state.cookie_path) != home / "server.token"
            or state.web_identity["generation"] != generation
            or state.working_directory != manifest["working_directory"]
        ):
            return
        adapter = KimiWebSession()
        adapter.m_manifest_path = manifest_path.resolve()
        adapter.m_state = state
        adapter.recover_web_prompt_result(request_id)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError):
        return
