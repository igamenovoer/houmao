"""Internal managed-agent authority and turn-record storage helpers.

This module defines the server-owned persistence records used by the native
headless managed-agent API. Those records live under the Houmao server state
tree and remain distinct from the delegated TUI registration bridge.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from houmao.server.config import HoumaoServerConfig


class _ManagedAgentStoreModel(BaseModel):
    """Strict base model for managed-agent persistence records."""

    model_config = ConfigDict(extra="forbid", strict=True)


_ModelT = TypeVar("_ModelT", bound=_ManagedAgentStoreModel)


class ManagedHeadlessAuthorityRecord(_ManagedAgentStoreModel):
    """Server-owned native headless authority record."""

    tracked_agent_id: str
    backend: Literal["claude_headless", "codex_headless", "gemini_headless"]
    tool: str
    manifest_path: str
    session_root: str
    tmux_session_name: str
    agent_def_dir: str
    agent_name: str | None = None
    agent_id: str | None = None
    created_at_utc: str
    updated_at_utc: str

    @field_validator(
        "tracked_agent_id",
        "backend",
        "tool",
        "manifest_path",
        "session_root",
        "tmux_session_name",
        "agent_def_dir",
        "agent_name",
        "agent_id",
        "created_at_utc",
        "updated_at_utc",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require non-empty strings when values are present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class ManagedHeadlessActiveTurnRecord(_ManagedAgentStoreModel):
    """Persisted active-turn authority for one native headless agent."""

    tracked_agent_id: str
    turn_id: str
    turn_index: int
    turn_artifact_dir: str
    started_at_utc: str
    tmux_session_name: str
    tmux_window_name: str | None = None
    interrupt_requested_at_utc: str | None = None

    @field_validator(
        "tracked_agent_id",
        "turn_id",
        "turn_artifact_dir",
        "started_at_utc",
        "tmux_session_name",
        "tmux_window_name",
        "interrupt_requested_at_utc",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require non-empty strings when values are present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("turn_index")
    @classmethod
    def _validate_turn_index(cls, value: int) -> int:
        """Require positive turn indices."""

        if value <= 0:
            raise ValueError("turn_index must be > 0")
        return value


class ManagedHeadlessTurnRecord(_ManagedAgentStoreModel):
    """Durable per-turn record for one accepted headless turn."""

    tracked_agent_id: str
    turn_id: str
    turn_index: int
    status: Literal["active", "completed", "failed", "interrupted", "unknown"] = "active"
    started_at_utc: str
    completed_at_utc: str | None = None
    turn_artifact_dir: str
    tmux_session_name: str
    tmux_window_name: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    status_path: str | None = None
    completion_source: str | None = None
    returncode: int | None = None
    error: str | None = None
    interrupt_requested_at_utc: str | None = None
    history_summary: str | None = None
    diagnostics: dict[str, str] = Field(default_factory=dict)

    @field_validator(
        "tracked_agent_id",
        "turn_id",
        "started_at_utc",
        "completed_at_utc",
        "turn_artifact_dir",
        "tmux_session_name",
        "tmux_window_name",
        "stdout_path",
        "stderr_path",
        "status_path",
        "completion_source",
        "error",
        "interrupt_requested_at_utc",
        "history_summary",
    )
    @classmethod
    def _optional_not_blank(cls, value: str | None) -> str | None:
        """Require non-empty strings when values are present."""

        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("turn_index")
    @classmethod
    def _validate_turn_index(cls, value: int) -> int:
        """Require positive turn indices."""

        if value <= 0:
            raise ValueError("turn_index must be > 0")
        return value


class ManagedHeadlessStore:
    """Read and write server-owned native headless authority records."""

    def __init__(self, *, config: HoumaoServerConfig) -> None:
        """Initialize the managed-agent store."""

        self.m_config = config

    @property
    def root(self) -> Path:
        """Return the managed-agent authority root."""

        return self.m_config.managed_agents_root

    def ensure_directories(self) -> None:
        """Ensure the managed-agent authority root exists."""

        self.root.mkdir(parents=True, exist_ok=True)

    def list_authority_records(self) -> list[ManagedHeadlessAuthorityRecord]:
        """Return all valid persisted authority records."""

        records: list[ManagedHeadlessAuthorityRecord] = []
        if not self.root.exists():
            return records
        for authority_path in sorted(self.root.glob("*/authority.json")):
            record = self._read_model(
                authority_path.resolve(),
                ManagedHeadlessAuthorityRecord,
            )
            if record is not None:
                records.append(record)
        return records

    def read_authority(
        self,
        *,
        tracked_agent_id: str,
    ) -> ManagedHeadlessAuthorityRecord | None:
        """Read one persisted headless authority record."""

        return self._read_model(
            self.authority_path(tracked_agent_id=tracked_agent_id),
            ManagedHeadlessAuthorityRecord,
        )

    def write_authority(self, record: ManagedHeadlessAuthorityRecord) -> None:
        """Persist one headless authority record."""

        self._write_model(self.authority_path(tracked_agent_id=record.tracked_agent_id), record)

    def read_active_turn(
        self,
        *,
        tracked_agent_id: str,
    ) -> ManagedHeadlessActiveTurnRecord | None:
        """Read one persisted active-turn authority record."""

        return self._read_model(
            self.active_turn_path(tracked_agent_id=tracked_agent_id),
            ManagedHeadlessActiveTurnRecord,
        )

    def write_active_turn(self, record: ManagedHeadlessActiveTurnRecord) -> None:
        """Persist one active-turn authority record."""

        self._write_model(self.active_turn_path(tracked_agent_id=record.tracked_agent_id), record)

    def clear_active_turn(self, *, tracked_agent_id: str) -> None:
        """Delete one active-turn authority record when present."""

        path = self.active_turn_path(tracked_agent_id=tracked_agent_id)
        if path.exists():
            path.unlink()

    def list_turn_records(self, *, tracked_agent_id: str) -> list[ManagedHeadlessTurnRecord]:
        """Return persisted turn records for one agent."""

        turn_records: list[ManagedHeadlessTurnRecord] = []
        turns_dir = self.turns_dir(tracked_agent_id=tracked_agent_id)
        if not turns_dir.exists():
            return turn_records
        for turn_path in sorted(turns_dir.glob("*.json")):
            record = self._read_model(turn_path.resolve(), ManagedHeadlessTurnRecord)
            if record is not None:
                turn_records.append(record)
        return turn_records

    def read_turn_record(
        self,
        *,
        tracked_agent_id: str,
        turn_id: str,
    ) -> ManagedHeadlessTurnRecord | None:
        """Read one persisted turn record."""

        return self._read_model(
            self.turn_record_path(tracked_agent_id=tracked_agent_id, turn_id=turn_id),
            ManagedHeadlessTurnRecord,
        )

    def write_turn_record(self, record: ManagedHeadlessTurnRecord) -> None:
        """Persist one headless turn record."""

        self._write_model(
            self.turn_record_path(
                tracked_agent_id=record.tracked_agent_id,
                turn_id=record.turn_id,
            ),
            record,
        )

    def delete_agent(self, *, tracked_agent_id: str) -> None:
        """Delete one managed-agent authority subtree."""

        agent_root = self.agent_root(tracked_agent_id=tracked_agent_id)
        if agent_root.exists():
            shutil.rmtree(agent_root)

    def agent_root(self, *, tracked_agent_id: str) -> Path:
        """Return the per-agent authority root."""

        safe_id = _safe_path_component(tracked_agent_id)
        return (self.root / safe_id).resolve()

    def authority_path(self, *, tracked_agent_id: str) -> Path:
        """Return the authority-record path for one agent."""

        return (self.agent_root(tracked_agent_id=tracked_agent_id) / "authority.json").resolve()

    def active_turn_path(self, *, tracked_agent_id: str) -> Path:
        """Return the active-turn authority path for one agent."""

        return (self.agent_root(tracked_agent_id=tracked_agent_id) / "active_turn.json").resolve()

    def turns_dir(self, *, tracked_agent_id: str) -> Path:
        """Return the per-agent turn-record directory."""

        return (self.agent_root(tracked_agent_id=tracked_agent_id) / "turns").resolve()

    def turn_record_path(self, *, tracked_agent_id: str, turn_id: str) -> Path:
        """Return the turn-record path for one server turn id."""

        safe_turn_id = _safe_path_component(turn_id)
        return (self.turns_dir(tracked_agent_id=tracked_agent_id) / f"{safe_turn_id}.json").resolve()

    def _read_model(self, path: Path, model: type[_ModelT]) -> _ModelT | None:
        """Read one optional JSON model from disk."""

        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return model.model_validate(payload)
        except Exception:
            return None

    def _write_model(self, path: Path, model: _ManagedAgentStoreModel) -> None:
        """Write one JSON model to disk atomically enough for server use."""

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(model.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _safe_path_component(value: str) -> str:
    """Return one safe path component or raise for invalid values."""

    stripped = value.strip()
    if not stripped or "/" in stripped or "\\" in stripped or stripped in {".", ".."}:
        raise ValueError(f"Invalid managed-agent path component: {value!r}")
    return stripped
