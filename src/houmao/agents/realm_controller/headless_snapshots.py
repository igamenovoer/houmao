"""Read one-shot runtime evidence from the owned headless turn artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path

from pydantic import ValidationError

from houmao.agents.realm_controller.backends.headless_output import (
    HeadlessProvider,
    resolve_headless_provider,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessProcessMetadata,
    load_headless_process_metadata,
    load_headless_turn_events,
    read_headless_turn_return_code,
)
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.realm_controller.managed_control import ManagedControlObservationV1
from houmao.agents.realm_controller.models import BackendKind
from houmao.agents.realm_controller.usage_models import UsageTurnSnapshot
from houmao.agents.realm_controller.usage_support import headless_artifact_process_alive


@dataclass(frozen=True)
class HeadlessTurnSnapshot:
    """One owned headless turn derived from runtime artifacts."""

    turn_id: str
    turn_index: int
    status: str
    started_at_utc: str
    completed_at_utc: str | None
    completion_source: str | None
    stdout_path: Path | None
    stderr_path: Path | None
    status_path: Path | None
    returncode: int | None
    history_summary: str | None
    error: str | None
    process_alive: bool = False


def headless_turn_artifacts_root(manifest_path: Path) -> Path:
    """Return the owned headless turn directory for a manifest."""

    root = manifest_path.parent.resolve() / f"{manifest_path.stem}.turn-artifacts"
    if root.is_symlink():
        raise BackendExecutionError("Headless turn artifact root must be runtime-owned.")
    return root


def list_headless_turns(
    *, manifest_path: Path, tool: str, backend: BackendKind
) -> list[HeadlessTurnSnapshot]:
    """Return owned snapshots newest-first, independent of the request ID format."""

    root = headless_turn_artifacts_root(manifest_path)
    if not root.is_dir():
        return []
    provider = resolve_headless_provider(tool=tool, backend=backend)
    snapshots = [
        read_headless_turn(candidate, provider=provider, dsh_cli=backend == "dsh_headless")
        for candidate in root.iterdir()
        if candidate.is_dir() and not candidate.is_symlink()
    ]
    return sorted(
        snapshots,
        key=lambda turn: (turn.started_at_utc, turn.turn_index, turn.turn_id),
        reverse=True,
    )


def latest_headless_turn(
    *, manifest_path: Path, tool: str, backend: BackendKind
) -> HeadlessTurnSnapshot | None:
    """Return the latest owned snapshot, if the runtime has attempted a turn."""

    return next(
        iter(list_headless_turns(manifest_path=manifest_path, tool=tool, backend=backend)), None
    )


def headless_control_observation(
    turn: HeadlessTurnSnapshot | None,
    *,
    owner_available: bool | None,
    native_session_id: str | None = None,
) -> ManagedControlObservationV1:
    """Project owned process or exit evidence without inferring a missing outcome."""

    observed_at = datetime.now(UTC).isoformat(timespec="seconds")
    if turn is None:
        return ManagedControlObservationV1(
            source="headless_artifacts",
            freshness="current" if owner_available is not None else "unknown",
            observed_at_utc=observed_at,
            owner_available=owner_available,
            can_accept_prompt_now=owner_available,
            native_session_id=native_session_id,
        )
    if turn.status == "active" and turn.process_alive:
        return ManagedControlObservationV1(
            source="headless_artifacts",
            freshness="current",
            observed_at_utc=observed_at,
            owner_available=owner_available,
            connection_ready=True,
            can_accept_prompt_now=False,
            native_session_id=native_session_id,
            active_request_id=turn.turn_id,
            active_turn_id=turn.turn_id,
        )
    if turn.returncode is None:
        return ManagedControlObservationV1(
            source="headless_artifacts",
            freshness="unknown",
            observed_at_utc=observed_at,
            owner_available=owner_available,
            can_accept_prompt_now=False,
            native_session_id=native_session_id,
            last_request_id=turn.turn_id,
            last_outcome="uncertain",
        )
    return ManagedControlObservationV1(
        source="headless_artifacts",
        freshness="current",
        observed_at_utc=observed_at,
        owner_available=owner_available,
        can_accept_prompt_now=owner_available,
        native_session_id=native_session_id,
        last_request_id=turn.turn_id,
        last_turn_id=turn.turn_id,
        last_outcome=(
            "completed"
            if turn.returncode == 0
            else "interrupted"
            if turn.status == "interrupted"
            else "failed"
        ),
    )


def read_dsh_cli_terminal_source(turn_dir: Path, *, returncode: int) -> str | None:
    """Read completed or interrupted proof for the exact DSH worker."""

    sources = {0: "native_journal", 130: "owner_process"}
    source = sources.get(returncode)
    if source is None:
        return None
    try:
        evidence = json.loads((turn_dir / "dsh-native-closure.json").read_text(encoding="utf-8"))
        process = load_headless_process_metadata(process_path=turn_dir / "process.json")
    except (OSError, ValueError):
        return None
    if (
        not isinstance(evidence, dict)
        or evidence.get("version") != 1
        or evidence.get("attempt_id") != turn_dir.name
        or evidence.get("returncode") != returncode
        or evidence.get("source") != source
        or process.child_pid is None
        or process.child_birth_token is None
        or evidence.get("process_id") != process.child_pid
        or evidence.get("process_birth_token") != process.child_birth_token
        or (returncode == 0 and not evidence.get("native_session_id"))
    ):
        return None
    return source


def read_headless_turn(
    turn_dir: Path, *, provider: HeadlessProvider, dsh_cli: bool = False
) -> HeadlessTurnSnapshot:
    """Read one local snapshot without modifying process or usage authority."""

    if turn_dir.is_symlink() or any(child.is_symlink() for child in turn_dir.iterdir()):
        raise BackendExecutionError("Headless turn artifacts must be runtime-owned files.")
    stdout_path = turn_dir / "stdout.jsonl"
    stderr_path = turn_dir / "stderr.log"
    status_path = turn_dir / "exitcode"
    process_metadata = _read_process_metadata(turn_dir / "process.json")
    turn_start = _read_turn_start(turn_dir / "usage-start.json")
    started_at_utc = (
        (process_metadata.launched_at_utc if process_metadata is not None else None)
        or (turn_start.started_at_utc if turn_start is not None else None)
        or _isoformat_from_mtime(turn_dir)
    )
    returncode = None
    completed_at_utc = None
    status = "active"
    error = None
    terminal_source = None
    if status_path.is_file():
        try:
            returncode = read_headless_turn_return_code(status_path=status_path)
        except (OSError, BackendExecutionError) as exc:
            error = str(exc)
            status = "failed"
        else:
            status = "completed" if returncode == 0 else "failed"
            completed_at_utc = _isoformat_from_mtime(status_path)
            if dsh_cli:
                terminal_source = read_dsh_cli_terminal_source(turn_dir, returncode=returncode)
                if returncode == 130 and terminal_source is not None:
                    status = "interrupted"
                elif returncode in {0, 130} and terminal_source is None:
                    status = "unknown"
                    returncode = None
                    completed_at_utc = None
                    error = "The DSH worker exited without a matching native closure record."
                elif returncode != 0:
                    error = read_dsh_cli_safe_error(turn_dir)
            elif returncode != 0 and stderr_path.is_file():
                error = stderr_path.read_text(encoding="utf-8").strip() or None
    turn_index = turn_start.turn_index if turn_start is not None else None
    if turn_index is None:
        turn_index = _turn_index_from_name(turn_dir.name)
    return HeadlessTurnSnapshot(
        turn_id=turn_dir.name,
        turn_index=turn_index,
        status=status,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        completion_source=terminal_source
        or _completion_source(turn_dir, provider=provider, turn_index=turn_index),
        stdout_path=stdout_path if stdout_path.is_file() else None,
        stderr_path=stderr_path if stderr_path.is_file() else None,
        status_path=status_path if status_path.is_file() else None,
        returncode=returncode,
        history_summary=f"{turn_dir.name} {status}",
        error=error,
        process_alive=status == "active" and headless_artifact_process_alive(turn_dir),
    )


def read_dsh_cli_safe_error(turn_dir: Path) -> str:
    """Extract a bounded redacted error from bridge-written canonical events."""

    fallback = "The DSH worker failed. Private stdout and stderr retain the diagnostic evidence."
    if not (turn_dir / "canonical-events.jsonl").is_file():
        return fallback
    try:
        events = load_headless_turn_events(
            turn_dir=turn_dir, provider="dsh", output_format="dsh-cli", turn_index=0
        )
    except (OSError, ValueError, BackendExecutionError):
        return fallback
    for event in reversed(events):
        data = event.payload or {}
        if data.get("provider_event_type") in {"stderr", "error"} and event.message.strip():
            return event.message.strip()[:640]
    for event in reversed(events):
        data = event.payload or {}
        if data.get("provider_event_type") != "final":
            continue
        native = data.get("data")
        if not isinstance(native, dict):
            continue
        detail = native.get("error")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()[:640]
        reason = native.get("stop_reason")
        if isinstance(reason, str) and reason:
            return f"DSH native outcome: {reason}."
    return fallback


def _read_process_metadata(path: Path) -> HeadlessProcessMetadata | None:
    """Read optional process evidence during current or recovering execution."""

    try:
        return load_headless_process_metadata(process_path=path)
    except (OSError, ValueError):
        return None


def _read_turn_start(path: Path) -> UsageTurnSnapshot | None:
    """Read the actual turn index carried by owner-assigned request IDs."""

    try:
        return UsageTurnSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def _turn_index_from_name(turn_id: str) -> int:
    """Read the index from an older runtime artifact named turn-NNNN."""

    if turn_id.startswith("turn-"):
        suffix = turn_id.removeprefix("turn-")
        if suffix.isascii() and suffix.isdecimal():
            return int(suffix)
    return 0


def _completion_source(
    turn_dir: Path, *, provider: HeadlessProvider, turn_index: int
) -> str | None:
    """Return completion attribution only when supplied by provider events."""

    try:
        events = load_headless_turn_events(
            turn_dir=turn_dir, provider=provider, output_format="stream-json", turn_index=turn_index
        )
    except (OSError, ValueError, BackendExecutionError):
        return None
    for event in reversed(events):
        value = event.payload.get("completion_source") if event.payload is not None else None
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _isoformat_from_mtime(path: Path) -> str:
    """Return a timezone-aware filesystem timestamp."""

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds")
