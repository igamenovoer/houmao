"""Verify Kimi main-turn termination against its private native wire journal."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re

from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.hook_observation.models import HookPosture


_JOURNAL_TAIL_BYTES = 1 << 20
_SESSION_ID = re.compile(r"[A-Za-z0-9_-]+")
_NATIVE_TERMINAL_REASONS = frozenset({"completed", "failed", "cancelled"})


def kimi_native_workspace_path(home: Path, working_directory: Path) -> Path:
    """Locate one workspace's Kimi sessions using Kimi's encodeWorkDirKey."""

    normalized = str(working_directory.resolve()).replace("\\", "/").rstrip("/")
    base = normalized.rsplit("/", 1)[-1].lower()
    slug = re.sub(r"[^a-z0-9._-]+", "-", base).strip("-")[:40].strip("-")
    if slug in {"", ".", ".."}:
        slug = "workspace"
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:12]
    return home.resolve() / "sessions" / f"wd_{slug}_{digest}"


class KimiTurnJournal:
    """Read terminal evidence only from the managed Kimi home and workspace."""

    def __init__(self, *, home: Path, working_directory: Path) -> None:
        """Bind the current owned workspace's native session directory."""

        self.m_workspace: Path = kimi_native_workspace_path(home, working_directory)
        self.m_last_scan: tuple[Path, str, float, int, int, int, int] | None = None
        self.m_last_scan_ended: bool = False

    @classmethod
    def from_session_root(cls, session_root: Path) -> KimiTurnJournal | None:
        """Read the private Kimi home from a current runtime-owned TUI manifest."""

        path = session_root / "manifest.json"
        try:
            handle = load_session_manifest(path)
            manifest = parse_session_manifest_payload(handle.payload, source=str(handle.path))
            home = manifest.launch_plan.home_selector
            if (
                manifest.tool != "kimi"
                or manifest.mode != "tui"
                or manifest.runtime.session_id != session_root.name
                or home.env_var != "KIMI_CODE_HOME"
            ):
                return None
            return cls(
                home=Path(home.home_path), working_directory=Path(manifest.working_directory)
            )
        except (OSError, RuntimeError):
            return None

    def ended(self, posture: HookPosture) -> bool:
        """Check for the exact open main turn's durable terminal record."""

        session_id = posture.session_id
        turn_id = posture.turn_id
        if (
            session_id is None
            or _SESSION_ID.fullmatch(session_id) is None
            or turn_id is None
            or not turn_id.isascii()
            or not turn_id.isdecimal()
            or len(posture.armed_prompts) != 1
            or posture.maintenance_active
        ):
            return False
        source = self.m_workspace / session_id / "agents" / "main" / "wire.jsonl"
        try:
            if source != source.resolve(strict=True) or not source.is_file():
                return False
            armed_at = datetime.fromisoformat(posture.armed_prompts[0].armed_at_utc)
            if armed_at.tzinfo is None:
                return False
            cutoff_ms = armed_at.timestamp() * 1000
            with source.open("rb") as journal:
                info = os.fstat(journal.fileno())
                scan = (
                    source,
                    turn_id,
                    cutoff_ms,
                    info.st_dev,
                    info.st_ino,
                    info.st_size,
                    info.st_mtime_ns,
                )
                if scan == self.m_last_scan:
                    return self.m_last_scan_ended
                offset = max(0, info.st_size - _JOURNAL_TAIL_BYTES)
                journal.seek(offset)
                tail = journal.read(_JOURNAL_TAIL_BYTES)
                self.m_last_scan = scan
                self.m_last_scan_ended = False
        except (OSError, RuntimeError, ValueError):
            return False
        if not tail.endswith(b"\n"):
            # The pending row might open a replacement turn on the same session.
            return False
        lines = tail.split(b"\n")
        for row in reversed(lines[1 if offset else 0 : -1]):
            try:
                record = json.loads(row)
            except (ValueError, UnicodeError):
                return False
            if not isinstance(record, dict) or record.get("agentId") != "main":
                continue
            record_type = record.get("type")
            if record_type in ("turn.prompt", "turn.ended"):
                record_turn = record.get("turnId")
            elif record_type == "context.append_loop_event":
                event = record.get("event")
                record_turn = event.get("turnId") if isinstance(event, dict) else None
            else:
                continue
            if isinstance(record_turn, bool) or not isinstance(record_turn, (int, str)):
                continue
            if str(record_turn) != turn_id:
                return False
            if record_type == "turn.ended":
                recorded_at = record.get("time")
                reason = record.get("reason")
                self.m_last_scan_ended = (
                    type(recorded_at) is int
                    and recorded_at >= cutoff_ms
                    and isinstance(reason, str)
                    and reason in _NATIVE_TERMINAL_REASONS
                )
                return self.m_last_scan_ended
        return False
