"""Native CAO-compatible control core and local transport for `houmao-server`."""

from __future__ import annotations

import json
import os
import re
import shlex
import threading
import time
import uuid
from pathlib import Path
from urllib import parse

from houmao.cao.models import CaoInboxMessageStatus
from houmao.server.config import HoumaoServerConfig

from .models import (
    CompatibilityInboxMessageRecord,
    CompatibilityRegistrySnapshot,
    CompatibilitySessionRecord,
    CompatibilityTerminalRecord,
)
from .profile_store import CompatibilityProfileInstallError, CompatibilityProfileStore
from .provider_adapters import (
    CompatibilityProviderError,
    normalize_terminal_status,
    require_provider_adapter,
)
from .tmux_controller import CompatibilityTmuxController, CompatibilityTmuxError

_SESSION_PREFIX = "cao-"
_TERMINAL_ID_RE = re.compile(r"^[a-f0-9]{8}$")
_COMPAT_HOME_ENV_BY_PROVIDER: dict[str, str] = {
    "claude_code": "CLAUDE_CONFIG_DIR",
    "codex": "CODEX_HOME",
    "gemini_cli": "GEMINI_HOME",
}
_COMPAT_CREDENTIAL_ENV_BY_PROVIDER: dict[str, tuple[str, ...]] = {
    "claude_code": (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_SMALL_FAST_MODEL",
        "CLAUDE_CODE_SUBAGENT_MODEL",
        "ANTHROPIC_DEFAULT_OPUS_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    ),
    "codex": (
        "OPENAI_API_KEY",
        "OPENAI_BASE_URL",
        "OPENAI_ORG_ID",
    ),
}


class CompatibilityControlError(RuntimeError):
    """Raised when one compatibility control operation fails explicitly."""

    def __init__(self, *, status_code: int, detail: str) -> None:
        """Initialize one explicit control error."""

        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class CompatibilityControlCore:
    """Houmao-owned native authority for the preserved CAO-compatible slice."""

    def __init__(
        self,
        *,
        config: HoumaoServerConfig,
        profile_store: CompatibilityProfileStore | None = None,
        tmux_controller: CompatibilityTmuxController | None = None,
    ) -> None:
        """Initialize the native compatibility control core."""

        self.m_config = config
        self.m_profile_store = profile_store or CompatibilityProfileStore(config=config)
        self.m_tmux = tmux_controller or CompatibilityTmuxController()
        self.m_lock = threading.RLock()
        self.m_sessions: dict[str, CompatibilitySessionRecord] = {}
        self.m_terminals: dict[str, CompatibilityTerminalRecord] = {}
        self.m_inbox_messages: list[CompatibilityInboxMessageRecord] = []
        self.m_next_message_id = 1

    def startup(self) -> None:
        """Load persisted compatibility state and ensure storage roots exist."""

        self.m_profile_store.ensure_directories()
        with self.m_lock:
            snapshot = self._read_registry_snapshot()
            self.m_sessions = {item.session_name: item for item in snapshot.sessions}
            self.m_terminals = {item.terminal_id: item for item in snapshot.terminals}
            self.m_inbox_messages = list(snapshot.inbox_messages)
            self.m_next_message_id = (
                max((item.message_id for item in self.m_inbox_messages), default=0) + 1
            )
            self._reconcile_registry_locked()
            self._persist_registry_locked()

    def shutdown(self) -> None:
        """Persist the current compatibility registry snapshot."""

        self.m_profile_store.ensure_directories()
        with self.m_lock:
            self._persist_registry_locked()

    def install_profile(
        self,
        *,
        agent_source: str,
        provider: str,
        working_directory: Path | None = None,
    ) -> str:
        """Install one compatibility profile into the server-owned store."""

        record = self.m_profile_store.install_profile(
            agent_source=agent_source,
            provider=provider,
            working_directory=working_directory,
        )
        return (
            "Pair-owned install completed through the Houmao-managed compatibility profile "
            f"store for provider `{record.resolved_provider}` as profile `{record.profile_name}`."
        )

    def health_payload(self) -> dict[str, str]:
        """Return the CAO-compatible health payload."""

        return {"status": "ok", "service": "cli-agent-orchestrator"}

    def list_sessions(self) -> list[dict[str, object]]:
        """Return live CAO-compatible session summaries."""

        with self.m_lock:
            self._reconcile_registry_locked()
            sessions = [self._session_payload(record) for record in self.m_sessions.values()]
        return sorted(sessions, key=lambda item: str(item["id"]))

    def create_session(
        self,
        *,
        provider: str,
        agent_profile: str,
        session_name: str | None,
        working_directory: str | None,
    ) -> dict[str, object]:
        """Create one new session with exactly one terminal."""

        resolved_session_name = self._resolve_session_name(session_name=session_name)
        resolved_working_directory = self._resolve_working_directory(working_directory)

        with self.m_lock:
            if resolved_session_name in self.m_sessions or self.m_tmux.session_exists(
                session_name=resolved_session_name
            ):
                raise CompatibilityControlError(
                    status_code=409,
                    detail=f"Session `{resolved_session_name}` already exists.",
                )

        prepared_profile = self._load_prepared_profile(
            profile_name=agent_profile,
            provider=provider,
        )
        adapter = require_provider_adapter(prepared_profile.resolved_provider)
        window_name = self._next_window_name(
            session_name=resolved_session_name,
            agent_profile=agent_profile,
        )
        self.m_tmux.ensure_tmux_available()
        try:
            window = self.m_tmux.create_session_with_window(
                session_name=resolved_session_name,
                window_name=window_name,
                working_directory=resolved_working_directory,
            )
            terminal_record = CompatibilityTerminalRecord(
                terminal_id=self._generate_terminal_id(),
                session_name=resolved_session_name,
                window_name=window.window_name,
                window_id=window.window_id,
                window_index=window.window_index,
                provider=prepared_profile.resolved_provider,
                agent_profile=prepared_profile.profile.name,
                working_directory=str(resolved_working_directory),
            )
            self._initialize_terminal(
                terminal_record=terminal_record,
                working_directory=resolved_working_directory,
                prepared_provider_profile=prepared_profile,
                adapter=adapter,
            )
        except (
            CompatibilityProfileInstallError,
            CompatibilityProviderError,
            CompatibilityTmuxError,
        ):
            self.m_tmux.kill_session(session_name=resolved_session_name)
            raise

        with self.m_lock:
            self.m_sessions[resolved_session_name] = CompatibilitySessionRecord(
                session_name=resolved_session_name,
                terminal_ids=[terminal_record.terminal_id],
            )
            self.m_terminals[terminal_record.terminal_id] = terminal_record
            self._persist_registry_locked()
            return self._terminal_payload(terminal_record)

    def get_session(self, *, session_name: str) -> dict[str, object]:
        """Return one CAO-compatible session detail payload."""

        with self.m_lock:
            record = self._require_session_locked(session_name=session_name)
            terminals = [
                self._terminal_summary_payload(
                    self._require_terminal_locked(terminal_id=terminal_id)
                )
                for terminal_id in record.terminal_ids
                if terminal_id in self.m_terminals
            ]
            return {
                "session": self._session_payload(record),
                "terminals": terminals,
            }

    def delete_session(self, *, session_name: str) -> dict[str, bool]:
        """Delete one compatibility session and all of its terminals."""

        with self.m_lock:
            record = self._require_session_locked(session_name=session_name)
            terminal_ids = list(record.terminal_ids)
        self.m_tmux.kill_session(session_name=session_name)
        with self.m_lock:
            self.m_sessions.pop(session_name, None)
            for terminal_id in terminal_ids:
                self.m_terminals.pop(terminal_id, None)
            self._persist_registry_locked()
        return {"success": True}

    def create_terminal(
        self,
        *,
        session_name: str,
        provider: str,
        agent_profile: str,
        working_directory: str | None,
    ) -> dict[str, object]:
        """Create one additional terminal in an existing session."""

        resolved_working_directory = self._resolve_working_directory(working_directory)
        prepared_profile = self._load_prepared_profile(
            profile_name=agent_profile,
            provider=provider,
        )
        adapter = require_provider_adapter(prepared_profile.resolved_provider)
        with self.m_lock:
            session_record = self._require_session_locked(session_name=session_name)
            window_name = self._next_window_name(
                session_name=session_name,
                agent_profile=agent_profile,
            )

        window = self.m_tmux.create_window(
            session_name=session_name,
            window_name=window_name,
            working_directory=resolved_working_directory,
        )
        terminal_record = CompatibilityTerminalRecord(
            terminal_id=self._generate_terminal_id(),
            session_name=session_name,
            window_name=window.window_name,
            window_id=window.window_id,
            window_index=window.window_index,
            provider=prepared_profile.resolved_provider,
            agent_profile=prepared_profile.profile.name,
            working_directory=str(resolved_working_directory),
        )
        try:
            self._initialize_terminal(
                terminal_record=terminal_record,
                working_directory=resolved_working_directory,
                prepared_provider_profile=prepared_profile,
                adapter=adapter,
            )
        except (CompatibilityProviderError, CompatibilityTmuxError):
            self.m_tmux.kill_window(window_id=window.window_id)
            raise

        with self.m_lock:
            self.m_terminals[terminal_record.terminal_id] = terminal_record
            session_record.terminal_ids.append(terminal_record.terminal_id)
            self.m_sessions[session_name] = session_record
            self._persist_registry_locked()
            return self._terminal_payload(terminal_record)

    def list_session_terminals(self, *, session_name: str) -> list[dict[str, object]]:
        """Return the current terminal payloads for one session."""

        with self.m_lock:
            session_record = self._require_session_locked(session_name=session_name)
            terminals = [
                self._terminal_payload(self._require_terminal_locked(terminal_id=terminal_id))
                for terminal_id in session_record.terminal_ids
                if terminal_id in self.m_terminals
            ]
        return terminals

    def get_terminal(self, *, terminal_id: str) -> dict[str, object]:
        """Return one terminal payload."""

        with self.m_lock:
            record = self._require_terminal_locked(terminal_id=terminal_id)
        return self._terminal_payload(record)

    def get_terminal_working_directory(self, *, terminal_id: str) -> dict[str, str | None]:
        """Return the current working directory for one terminal."""

        with self.m_lock:
            record = self._require_terminal_locked(terminal_id=terminal_id)
        if record.window_id is not None:
            try:
                working_directory = self.m_tmux.get_window_working_directory(
                    window_id=record.window_id
                )
            except CompatibilityTmuxError:
                working_directory = None
            if working_directory is not None:
                return {"working_directory": working_directory}
        return {"working_directory": record.working_directory}

    def send_terminal_input(self, *, terminal_id: str, message: str) -> dict[str, bool]:
        """Deliver one prompt or control payload to a live terminal."""

        if not message.strip():
            raise CompatibilityControlError(
                status_code=422,
                detail="Terminal input `message` must not be empty.",
            )
        with self.m_lock:
            record = self._require_terminal_locked(terminal_id=terminal_id)
        adapter = require_provider_adapter(record.provider)
        if record.window_id is None:
            raise CompatibilityControlError(
                status_code=503,
                detail=f"Terminal `{terminal_id}` is missing a live tmux window binding.",
            )
        self.m_tmux.send_text(
            window_id=record.window_id,
            text=message,
            enter_count=adapter.paste_enter_count,
        )
        with self.m_lock:
            updated = record.model_copy(update={"last_active_utc": _utc_now_iso()})
            self.m_terminals[terminal_id] = updated
            self._persist_registry_locked()
        return {"success": True}

    def get_terminal_output(self, *, terminal_id: str, mode: str) -> dict[str, str]:
        """Return the requested output view for one terminal."""

        with self.m_lock:
            record = self._require_terminal_locked(terminal_id=terminal_id)
        if record.window_id is None:
            raise CompatibilityControlError(
                status_code=503,
                detail=f"Terminal `{terminal_id}` is missing a live tmux window binding.",
            )
        output_text = self.m_tmux.capture_window(window_id=record.window_id)
        adapter = require_provider_adapter(record.provider)
        if mode == "full":
            resolved_output = output_text
        elif mode == "tail":
            resolved_output = "\n".join(output_text.splitlines()[-80:])
        else:
            resolved_output = adapter.extract_last_message(
                output_text=output_text,
                profile_name=record.agent_profile,
            )
        return {"output": resolved_output, "mode": mode}

    def exit_terminal(self, *, terminal_id: str) -> dict[str, bool]:
        """Deliver the provider-specific exit action to one terminal."""

        with self.m_lock:
            record = self._require_terminal_locked(terminal_id=terminal_id)
        if record.window_id is None:
            raise CompatibilityControlError(
                status_code=503,
                detail=f"Terminal `{terminal_id}` is missing a live tmux window binding.",
            )
        adapter = require_provider_adapter(record.provider)
        adapter.exit_terminal(tmux=self.m_tmux, window_id=record.window_id)
        return {"success": True}

    def delete_terminal(self, *, terminal_id: str) -> dict[str, bool]:
        """Delete one terminal and remove it from the session registry."""

        with self.m_lock:
            record = self._require_terminal_locked(terminal_id=terminal_id)
        if record.window_id is not None:
            self.m_tmux.kill_window(window_id=record.window_id)
        with self.m_lock:
            self.m_terminals.pop(terminal_id, None)
            session_record = self.m_sessions.get(record.session_name)
            if session_record is not None:
                session_record.terminal_ids = [
                    candidate
                    for candidate in session_record.terminal_ids
                    if candidate != terminal_id
                ]
                if session_record.terminal_ids:
                    self.m_sessions[record.session_name] = session_record
                else:
                    self.m_sessions.pop(record.session_name, None)
            self._persist_registry_locked()
        return {"success": True}

    def create_inbox_message(
        self,
        *,
        receiver_id: str,
        sender_id: str,
        message: str,
    ) -> dict[str, object]:
        """Enqueue one compatibility-only terminal-scoped inbox message."""

        with self.m_lock:
            self._require_terminal_locked(terminal_id=receiver_id)
            record = CompatibilityInboxMessageRecord(
                message_id=self.m_next_message_id,
                sender_id=sender_id,
                receiver_id=receiver_id,
                message=message,
                status="pending",
            )
            self.m_next_message_id += 1
            self.m_inbox_messages.append(record)
            self._persist_registry_locked()
        return {
            "success": True,
            "message_id": record.message_id,
            "sender_id": record.sender_id,
            "receiver_id": record.receiver_id,
            "created_at": record.created_at,
        }

    def list_inbox_messages(
        self,
        *,
        terminal_id: str,
        limit: int,
        status: str | None,
    ) -> list[dict[str, object]]:
        """Return the compatibility inbox queue for one terminal."""

        with self.m_lock:
            self._require_terminal_locked(terminal_id=terminal_id)
            filtered = [
                item
                for item in self.m_inbox_messages
                if item.receiver_id == terminal_id and (status is None or item.status == status)
            ]
        filtered.sort(key=lambda item: item.message_id, reverse=True)
        return [
            {
                "id": item.message_id,
                "sender_id": item.sender_id,
                "receiver_id": item.receiver_id,
                "message": item.message,
                "status": CaoInboxMessageStatus(item.status).value,
                "created_at": item.created_at,
            }
            for item in filtered[:limit]
        ]

    def _initialize_terminal(
        self,
        *,
        terminal_record: CompatibilityTerminalRecord,
        working_directory: Path,
        prepared_provider_profile: object,
        adapter: object,
    ) -> None:
        """Wait for the shell, start the provider, and wait for readiness."""

        del working_directory
        if terminal_record.window_id is None:
            raise CompatibilityControlError(
                status_code=500,
                detail=f"Terminal `{terminal_record.terminal_id}` is missing a tmux window binding.",
            )
        prepared = prepared_provider_profile
        if not hasattr(prepared, "profile") or not hasattr(prepared, "resolved_provider"):
            raise CompatibilityControlError(
                status_code=500,
                detail="Compatibility provider profile preparation returned an invalid payload.",
            )
        typed_adapter = adapter
        self.m_tmux.wait_for_shell(
            window_id=terminal_record.window_id,
            timeout_seconds=self.m_config.compat_shell_ready_timeout_seconds,
            polling_interval_seconds=self.m_config.compat_shell_ready_poll_interval_seconds,
        )
        if getattr(typed_adapter, "provider_id", "") == "codex":
            self.m_tmux.send_command(window_id=terminal_record.window_id, command="echo ready")
            if self.m_config.compat_codex_warmup_seconds > 0:
                time.sleep(self.m_config.compat_codex_warmup_seconds)

        profile = getattr(prepared, "profile")
        command = typed_adapter.build_command(
            profile=profile,
            profile_name=terminal_record.agent_profile,
            terminal_id=terminal_record.terminal_id,
            working_directory=Path(terminal_record.working_directory),
        )
        launch_exports = [
            f"export HOME={shlex.quote(str(self.m_config.compatibility_home_dir))}",
        ]
        home_selector_env_var = _COMPAT_HOME_ENV_BY_PROVIDER.get(
            getattr(typed_adapter, "provider_id", "")
        )
        if home_selector_env_var is not None:
            launch_exports.append(
                f"export {home_selector_env_var}="
                f"{shlex.quote(str(self.m_config.compatibility_home_dir))}"
            )
        for env_var_name in _COMPAT_CREDENTIAL_ENV_BY_PROVIDER.get(
            getattr(typed_adapter, "provider_id", ""),
            (),
        ):
            env_var_value = os.environ.get(env_var_name)
            if env_var_value is None or not env_var_value.strip():
                continue
            launch_exports.append(f"export {env_var_name}={shlex.quote(env_var_value)}")
        launch_exports.append(f"export CAO_TERMINAL_ID={shlex.quote(terminal_record.terminal_id)}")
        launch_command = "; ".join([*launch_exports, command])
        self.m_tmux.send_command(window_id=terminal_record.window_id, command=launch_command)
        typed_adapter.wait_until_ready(
            tmux=self.m_tmux,
            window_id=terminal_record.window_id,
            profile_name=terminal_record.agent_profile,
            timeout_seconds=self.m_config.compat_provider_ready_timeout_seconds,
            polling_interval_seconds=self.m_config.compat_provider_ready_poll_interval_seconds,
        )

    def _load_prepared_profile(self, *, profile_name: str, provider: str) -> object:
        """Load one prepared profile through the Houmao-managed store."""

        return self.m_profile_store.load_profile(
            profile_name=profile_name, requested_provider=provider
        )

    def _session_payload(self, record: CompatibilitySessionRecord) -> dict[str, object]:
        """Project one internal session record to the CAO-compatible payload."""

        return {
            "id": record.session_name,
            "name": record.session_name,
            "status": self._session_status(record),
        }

    def _session_status(self, record: CompatibilitySessionRecord) -> str:
        """Return the best-effort CAO-compatible session status string."""

        if not self.m_tmux.session_exists(session_name=record.session_name):
            return "missing"
        clients = self.m_tmux.list_clients(session_name=record.session_name)
        return "attached" if clients else "detached"

    def _terminal_payload(self, record: CompatibilityTerminalRecord) -> dict[str, object]:
        """Project one internal terminal record to the CAO-compatible payload."""

        return {
            "id": record.terminal_id,
            "name": record.window_name,
            "provider": record.provider,
            "session_name": record.session_name,
            "agent_profile": record.agent_profile,
            "status": normalize_terminal_status(self._terminal_status(record)).value,
            "last_active": record.last_active_utc,
        }

    def _terminal_summary_payload(self, record: CompatibilityTerminalRecord) -> dict[str, object]:
        """Project one internal terminal record to the session-summary payload."""

        return {
            "id": record.terminal_id,
            "tmux_session": record.session_name,
            "tmux_window": record.window_name,
            "provider": record.provider,
            "agent_profile": record.agent_profile,
            "last_active": record.last_active_utc,
        }

    def _terminal_status(self, record: CompatibilityTerminalRecord) -> str:
        """Return the live CAO-compatible status string for one terminal."""

        if record.window_id is None:
            return "error"
        try:
            output_text = self.m_tmux.capture_window(window_id=record.window_id)
        except CompatibilityTmuxError:
            return "error"
        adapter = require_provider_adapter(record.provider)
        return adapter.get_status(output_text=output_text, profile_name=record.agent_profile)

    def _resolve_session_name(self, *, session_name: str | None) -> str:
        """Normalize or generate one CAO-compatible session name."""

        if session_name is None or not session_name.strip():
            return f"{_SESSION_PREFIX}{uuid.uuid4().hex[:8]}"
        stripped = session_name.strip()
        return stripped if stripped.startswith(_SESSION_PREFIX) else f"{_SESSION_PREFIX}{stripped}"

    @staticmethod
    def _resolve_working_directory(working_directory: str | None) -> Path:
        """Resolve one optional working-directory input."""

        if working_directory is None:
            return Path.cwd().resolve()
        resolved = Path(working_directory).expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise CompatibilityControlError(
                status_code=422,
                detail=f"Working directory `{resolved}` does not exist or is not a directory.",
            )
        return resolved

    def _next_window_name(self, *, session_name: str, agent_profile: str) -> str:
        """Return the next human-readable window name for one session."""

        safe_profile = re.sub(r"[^a-zA-Z0-9_-]+", "-", agent_profile).strip("-") or "agent"
        with self.m_lock:
            session_record = self.m_sessions.get(session_name)
            existing_count = len(session_record.terminal_ids) if session_record is not None else 0
        return f"{safe_profile}-{existing_count + 1}"

    @staticmethod
    def _generate_terminal_id() -> str:
        """Return one CAO-compatible terminal id."""

        return uuid.uuid4().hex[:8]

    def _require_session_locked(self, *, session_name: str) -> CompatibilitySessionRecord:
        """Return one required session record while holding the core lock."""

        record = self.m_sessions.get(session_name)
        if record is None:
            raise CompatibilityControlError(
                status_code=404,
                detail=f"Session `{session_name}` was not found.",
            )
        return record

    def _require_terminal_locked(self, *, terminal_id: str) -> CompatibilityTerminalRecord:
        """Return one required terminal record while holding the core lock."""

        if not _TERMINAL_ID_RE.match(terminal_id):
            raise CompatibilityControlError(
                status_code=404,
                detail=f"Terminal `{terminal_id}` was not found.",
            )
        record = self.m_terminals.get(terminal_id)
        if record is None:
            raise CompatibilityControlError(
                status_code=404,
                detail=f"Terminal `{terminal_id}` was not found.",
            )
        return record

    def _read_registry_snapshot(self) -> CompatibilityRegistrySnapshot:
        """Read the current registry snapshot from disk."""

        if not self.m_config.compatibility_registry_path.is_file():
            return CompatibilityRegistrySnapshot()
        payload = json.loads(self.m_config.compatibility_registry_path.read_text(encoding="utf-8"))
        return CompatibilityRegistrySnapshot.model_validate(payload)

    def _persist_registry_locked(self) -> None:
        """Persist the current registry snapshot while holding the core lock."""

        snapshot = CompatibilityRegistrySnapshot(
            sessions=list(self.m_sessions.values()),
            terminals=list(self.m_terminals.values()),
            inbox_messages=list(self.m_inbox_messages),
        )
        self.m_config.compatibility_registry_path.write_text(
            json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _reconcile_registry_locked(self) -> None:
        """Drop stale session records whose tmux authority no longer exists."""

        live_sessions = {
            session_name
            for session_name in list(self.m_sessions)
            if self.m_tmux.session_exists(session_name=session_name)
        }
        for session_name in list(self.m_sessions):
            if session_name in live_sessions:
                continue
            self.m_sessions.pop(session_name, None)
        valid_terminal_ids = {
            terminal_id
            for terminal_id, record in self.m_terminals.items()
            if record.session_name in self.m_sessions
        }
        self.m_terminals = {
            terminal_id: record
            for terminal_id, record in self.m_terminals.items()
            if terminal_id in valid_terminal_ids
        }
        self.m_inbox_messages = [
            item for item in self.m_inbox_messages if item.receiver_id in self.m_terminals
        ]


class LocalCompatibilityTransport:
    """Server-local request transport that dispatches `/cao/*` into the native core."""

    def __init__(self, *, control_core: CompatibilityControlCore) -> None:
        """Initialize the local compatibility transport."""

        self.m_control_core = control_core

    def request(
        self,
        *,
        base_url: str,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> object:
        """Dispatch one CAO-compatible request into the native control core."""

        del base_url
        raise NotImplementedError(
            "LocalCompatibilityTransport.request() is wired through `dispatch()` by "
            "`houmao.server.service.LocalCompatibilityTransportBridge`."
        )

    def dispatch(
        self,
        *,
        method: str,
        path: str,
        params: dict[str, str] | None = None,
    ) -> tuple[int, object]:
        """Dispatch one request and return `(status_code, payload)`."""

        try:
            return self._dispatch_success(
                method=method.upper(),
                path=path,
                params=params or {},
            )
        except (CompatibilityControlError, CompatibilityProfileInstallError) as exc:
            return exc.status_code, {"detail": exc.detail}
        except (CompatibilityProviderError, CompatibilityTmuxError) as exc:
            return 503, {"detail": str(exc)}

    def _dispatch_success(
        self,
        *,
        method: str,
        path: str,
        params: dict[str, str],
    ) -> tuple[int, object]:
        """Route one successful request to the native core."""

        if method == "GET" and path == "/health":
            return 200, self.m_control_core.health_payload()
        if method == "GET" and path == "/sessions":
            return 200, self.m_control_core.list_sessions()
        if method == "POST" and path == "/sessions":
            return 201, self.m_control_core.create_session(
                provider=_require_param(params, "provider"),
                agent_profile=_require_param(params, "agent_profile"),
                session_name=params.get("session_name"),
                working_directory=params.get("working_directory"),
            )

        match = re.fullmatch(r"/sessions/([^/]+)", path)
        if match is not None:
            session_name = parse.unquote(match.group(1))
            if method == "GET":
                return 200, self.m_control_core.get_session(session_name=session_name)
            if method == "DELETE":
                return 200, self.m_control_core.delete_session(session_name=session_name)

        match = re.fullmatch(r"/sessions/([^/]+)/terminals", path)
        if match is not None:
            session_name = parse.unquote(match.group(1))
            if method == "GET":
                return 200, self.m_control_core.list_session_terminals(session_name=session_name)
            if method == "POST":
                return 201, self.m_control_core.create_terminal(
                    session_name=session_name,
                    provider=_require_param(params, "provider"),
                    agent_profile=_require_param(params, "agent_profile"),
                    working_directory=params.get("working_directory"),
                )

        match = re.fullmatch(r"/terminals/([a-f0-9]{8})", path)
        if match is not None:
            terminal_id = match.group(1)
            if method == "GET":
                return 200, self.m_control_core.get_terminal(terminal_id=terminal_id)
            if method == "DELETE":
                return 200, self.m_control_core.delete_terminal(terminal_id=terminal_id)

        match = re.fullmatch(r"/terminals/([a-f0-9]{8})/working-directory", path)
        if match is not None and method == "GET":
            return 200, self.m_control_core.get_terminal_working_directory(
                terminal_id=match.group(1)
            )

        match = re.fullmatch(r"/terminals/([a-f0-9]{8})/input", path)
        if match is not None and method == "POST":
            return 200, self.m_control_core.send_terminal_input(
                terminal_id=match.group(1),
                message=_require_param(params, "message"),
            )

        match = re.fullmatch(r"/terminals/([a-f0-9]{8})/output", path)
        if match is not None and method == "GET":
            return 200, self.m_control_core.get_terminal_output(
                terminal_id=match.group(1),
                mode=params.get("mode", "last"),
            )

        match = re.fullmatch(r"/terminals/([a-f0-9]{8})/exit", path)
        if match is not None and method == "POST":
            return 200, self.m_control_core.exit_terminal(terminal_id=match.group(1))

        match = re.fullmatch(r"/terminals/([a-f0-9]{8})/inbox/messages", path)
        if match is not None:
            terminal_id = match.group(1)
            if method == "POST":
                return 200, self.m_control_core.create_inbox_message(
                    receiver_id=terminal_id,
                    sender_id=_require_param(params, "sender_id"),
                    message=_require_param(params, "message"),
                )
            if method == "GET":
                limit = int(params.get("limit", "10"))
                return 200, self.m_control_core.list_inbox_messages(
                    terminal_id=terminal_id,
                    limit=limit,
                    status=params.get("status"),
                )

        raise CompatibilityControlError(
            status_code=404,
            detail=f"Unsupported compatibility route: {method} {path}",
        )


def _require_param(params: dict[str, str], key: str) -> str:
    """Return one required query parameter or raise."""

    value = params.get(key)
    if value is None or not value.strip():
        raise CompatibilityControlError(
            status_code=422,
            detail=f"Missing required compatibility parameter `{key}`.",
        )
    return value


def _utc_now_iso() -> str:
    """Return one second-precision UTC timestamp."""

    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
