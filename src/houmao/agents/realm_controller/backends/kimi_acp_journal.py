"""Read attributable native Kimi ACP turn evidence from an owned session journal."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, BinaryIO, Literal

from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.hook_observation.kimi_journal import kimi_native_workspace_path


_SESSION_ID = re.compile(r"[A-Za-z0-9_-]{1,128}")
_MAX_STATE_BYTES = 1024 * 1024
_MAX_INTERVAL_BYTES = 16 * 1024 * 1024
_MAX_OUTPUT_CHARS = 128 * 1024
KimiTurnOutcome = Literal["completed", "failed", "interrupted"]


@dataclass(frozen=True)
class KimiTurnClosure:
    """One native main prompt and the first byte after its validated closing row."""

    turn_id: str
    prompt_id: str
    outcome: KimiTurnOutcome
    settled_offset: int
    text: str


@dataclass(frozen=True)
class KimiJournalInterval:
    """A snapshot of complete records before the protected native stdio write."""

    path: Path
    device: int
    inode: int
    offset: int

    @classmethod
    def capture(cls, path: Path) -> KimiJournalInterval:
        """Capture the exact file and reject an open or malformed baseline row."""

        with _open_native_file(path) as stream:
            info = os.fstat(stream.fileno())
            if info.st_size:
                stream.seek(info.st_size - 1)
                if stream.read(1) != b"\n":
                    raise BackendExecutionError("Kimi ACP journal has an incomplete baseline")
        return cls(path, info.st_dev, info.st_ino, info.st_size)

    def closure(self, prompt_digest: str) -> KimiTurnClosure | None:
        """Require one exact user prompt and compatible turn and prompt terminal rows."""

        with _open_native_file(self.path) as stream:
            info = os.fstat(stream.fileno())
            if (info.st_dev, info.st_ino) != (self.device, self.inode) or not (
                self.offset <= info.st_size <= self.offset + _MAX_INTERVAL_BYTES
            ):
                raise BackendExecutionError(
                    "Kimi ACP journal changed outside the admitted interval"
                )
            stream.seek(self.offset)
            return _read_turn(stream, prompt_digest, limit=info.st_size)


def kimi_session_journal(home: Path, workspace: Path, session_id: str) -> Path:
    """Verify native session metadata inside its exact workspace-bound directory."""

    if _SESSION_ID.fullmatch(session_id) is None:
        raise BackendExecutionError("Kimi ACP returned an invalid native session identity")
    root = kimi_native_workspace_path(home, workspace) / session_id
    try:
        with _open_native_file(root / "state.json") as stream:
            contents = stream.read(_MAX_STATE_BYTES + 1)
        if len(contents) > _MAX_STATE_BYTES:
            raise ValueError("Native state is oversized")
        state = json.loads(contents)
        cwd = state.get("cwd") if isinstance(state, dict) else None
        if (
            not isinstance(cwd, str)
            or not Path(cwd).is_absolute()
            or Path(cwd).resolve(strict=True) != workspace.resolve(strict=True)
            or state.get("id") != session_id
        ):
            raise ValueError("Native state does not identify the selected workspace")
    except (OSError, ValueError, RuntimeError):
        raise BackendExecutionError(
            "Kimi ACP session is missing from the selected private workspace"
        ) from None
    return root / "agents" / "main" / "wire.jsonl"


def _open_native_file(path: Path) -> BinaryIO:
    """Open only a regular file in the canonical, owner-controlled native tree."""

    if path.resolve(strict=True) != path:
        raise OSError("Unexpected symbolic link in Kimi native state")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(descriptor, "rb")
    info = os.fstat(stream.fileno())
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        stream.close()
        raise OSError("Kimi native state is not owned or is writable by another account")
    return stream


def _read_turn(stream: BinaryIO, prompt_digest: str, *, limit: int) -> KimiTurnClosure | None:
    """Accumulate output from complete records whose native turn is qualified."""

    turn_id: str | None = None
    prompt_id: str | None = None
    turn_outcome: KimiTurnOutcome | None = None
    prompt_outcome: KimiTurnOutcome | None = None
    text: list[str] = []
    remaining = _MAX_OUTPUT_CHARS
    while stream.tell() < limit:
        raw = stream.readline(limit - stream.tell())
        if not raw.endswith(b"\n"):
            return None
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise BackendExecutionError("Kimi ACP journal contains an invalid native record")
        if row.get("agentId") != "main":
            continue
        kind = row.get("type")
        if kind == "turn.prompt":
            if turn_id is not None or not _matches_input(row, prompt_digest):
                raise BackendExecutionError("Kimi ACP journal contains an unrelated main prompt")
            turn_id = _native_turn_id(row.get("turnId"))
            prompt_id = row.get("promptId")
            if turn_id is None or not isinstance(prompt_id, str) or not prompt_id:
                raise BackendExecutionError(
                    "Kimi ACP journal omitted a native turn or prompt identity"
                )
        elif kind == "turn.ended":
            if (
                turn_id is None
                or turn_outcome is not None
                or _native_turn_id(row.get("turnId")) != turn_id
            ):
                raise BackendExecutionError("Kimi ACP journal has a conflicting main turn closure")
            turn_outcome = _outcome(row.get("reason"))
        elif kind in ("prompt.aborted", "prompt.completed") and prompt_id is not None:
            if row.get("promptId") == prompt_id:
                if prompt_outcome is not None:
                    raise BackendExecutionError("Kimi ACP journal repeated a native prompt closure")
                prompt_outcome = (
                    "interrupted" if kind == "prompt.aborted" else _outcome(row.get("reason"))
                )
        elif kind == "context.append_loop_event" and turn_id is not None and remaining:
            value = _assistant_text(row.get("event"), turn_id)[:remaining]
            if value:
                text.append(value)
                remaining -= len(value)
        if turn_id is not None and prompt_id is not None and turn_outcome and prompt_outcome:
            if turn_outcome != prompt_outcome:
                raise BackendExecutionError("Kimi ACP native terminal records disagree")
            return KimiTurnClosure(turn_id, prompt_id, turn_outcome, stream.tell(), "".join(text))
    return None


def _matches_input(row: dict[str, Any], digest: str) -> bool:
    """Match exactly the one text block written to the privately owned ACP stream."""

    origin, content = row.get("origin"), row.get("input")
    if not isinstance(origin, dict) or origin.get("kind") != "user":
        return False
    if not isinstance(content, list) or len(content) != 1 or not isinstance(content[0], dict):
        return False
    block = content[0]
    text = block.get("text")
    return (
        block.get("type") == "text"
        and isinstance(text, str)
        and hashlib.sha256(text.encode("utf-8")).hexdigest() == digest
    )


def _native_turn_id(value: object) -> str | None:
    """Keep the native zero ordinal and normalize wire string ordinals."""

    if type(value) is int and value >= 0:
        return str(value)
    if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 16:
        return value
    return None


def _outcome(reason: object) -> KimiTurnOutcome:
    """Map Kimi native reasons without folding a failed turn into ACP end_turn."""

    if reason == "completed":
        return "completed"
    if reason == "cancelled":
        return "interrupted"
    if reason in ("failed", "blocked"):
        return "failed"
    raise BackendExecutionError("Kimi ACP journal reported an unsupported terminal reason")


def _assistant_text(event: object, turn_id: str) -> str:
    """Project only attributable assistant text from the native journal."""

    if not isinstance(event, dict) or event.get("type") != "content.part":
        return ""
    if _native_turn_id(event.get("turnId")) != turn_id:
        return ""
    part = event.get("part")
    if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
        return str(part["text"])
    return ""
