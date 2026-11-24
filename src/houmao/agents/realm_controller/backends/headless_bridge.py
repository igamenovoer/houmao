"""Bridge subprocess for managed headless live rendering and artifact capture."""

from __future__ import annotations

import argparse
from contextlib import suppress
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from typing import Callable, Sequence

from houmao.agents.kimi_configuration import kimi_launch_diagnostic_secrets
from houmao.agents.realm_controller.backends.dispatch_control import (
    _dispatch_origin_birth_token,
    headless_dispatch_permission_allowed,
)
from houmao.agents.realm_controller.backends.dsh_diagnostics import (
    dsh_diagnostic_secrets,
    sanitize_dsh_diagnostic,
)
from houmao.agents.realm_controller.backends.headless_output import (
    append_canonical_headless_event,
    append_stderr_diagnostic_event,
    canonical_headless_event_artifact_path,
    canonical_headless_events_from_provider_output,
    load_canonical_headless_events,
    render_canonical_headless_events,
    resolve_headless_display_detail,
    resolve_headless_display_style,
)
from houmao.agents.realm_controller.backends.headless_output import (
    CanonicalHeadlessEvent,
    CanonicalHeadlessEventParser,
    HeadlessProvider,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    _dsh_unverified_settlement,
    load_headless_process_metadata,
)
from houmao.agents.realm_controller.usage_support import persist_terminal_evidence, write_usage_json


def main(argv: Sequence[str] | None = None) -> int:
    """Run the headless bridge CLI."""

    args = _parse_args(argv=argv)
    command = list(args.command)
    if not command:
        raise ValueError("headless bridge requires a provider command after `--`")

    provider: HeadlessProvider = args.provider
    native_dsh = provider == "dsh" and args.output_format == "dsh-cli"
    secrets = (
        dsh_diagnostic_secrets(args.env, key_name=args.env.get("HOUMAO_DSH_DIAGNOSTIC_KEY_NAME"))
        if native_dsh
        else None
    )
    if provider == "kimi":
        secrets = kimi_launch_diagnostic_secrets(args.env)
    turn_dir = args.turn_dir.resolve()
    turn_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = (turn_dir / "stdout.jsonl").resolve()
    stderr_path = (turn_dir / "stderr.log").resolve()
    status_path = (turn_dir / "exitcode").resolve()
    process_path = (turn_dir / "process.json").resolve()
    canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)
    started_monotonic = time.monotonic()

    for path in (stdout_path, stderr_path, canonical_path):
        if native_dsh or provider == "kimi":
            os.close(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600))
        else:
            path.write_text("", encoding="utf-8")

    if args.dispatch_guard_file is not None and not headless_dispatch_permission_allowed(
        args.dispatch_guard_file
    ):
        _record_launch_failure(
            turn_dir=turn_dir,
            returncode=125,
            message="Immediate dispatch permission expired or was revoked.",
            started_monotonic=started_monotonic,
        )
        return 125

    try:
        if native_dsh:
            _own_detached_descendants()
        environment = (
            {name: os.environ[name] for name in ("TMUX", "TMUX_PANE") if name in os.environ}
            if args.replace_environment
            else os.environ.copy()
        )
        environment.update(args.env)
        process = subprocess.Popen(
            command,
            cwd=str(args.cwd.resolve()),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="surrogateescape" if native_dsh else "strict",
            bufsize=1,
            start_new_session=native_dsh,
        )
    except (OSError, ValueError):
        _record_launch_failure(
            turn_dir=turn_dir,
            returncode=127,
            message="Headless client could not start.",
            started_monotonic=started_monotonic,
        )
        return 127

    group_cleanup_failed = threading.Event()
    reaper = None
    if native_dsh:
        reaper = threading.Thread(
            target=_cleanup_owned_group,
            args=(process.pid, group_cleanup_failed),
            daemon=True,
            name=f"houmao-dsh-reaper-{args.turn_index}",
        )
        reaper.start()

    if args.dispatch_guard_file is not None and not headless_dispatch_permission_allowed(
        args.dispatch_guard_file
    ):
        try:
            if reaper is not None:
                # This bridge still owns the unreaped isolated session leader.
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
                reaper.join(1.0)
                if reaper.is_alive():
                    with suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    reaper.join(1.0)
                process.wait(timeout=1.0)
            elif process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=1.0)
        except (OSError, subprocess.TimeoutExpired):
            pass
        finally:
            if process.stdout is not None:
                process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
        _record_launch_failure(
            turn_dir=turn_dir,
            returncode=125,
            message="Immediate dispatch permission expired or was revoked.",
            started_monotonic=started_monotonic,
        )
        return 125

    process_metadata: dict[str, str | int | bool | None] = {
        "runner_pid": os.getpid(),
        "child_pid": process.pid,
        "launched_at_utc": args.launched_at_utc,
        "runner_birth_token": _dispatch_origin_birth_token(os.getpid()),
        "child_birth_token": _dispatch_origin_birth_token(process.pid),
        "child_isolated_group": native_dsh,
    }
    temporary_process = process_path.with_suffix(".tmp")
    descriptor = os.open(temporary_process, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(process_metadata) + "\n")
    temporary_process.replace(process_path)

    parser = CanonicalHeadlessEventParser(
        provider=provider,
        turn_index=args.turn_index,
        output_format=args.output_format,
        diagnostic_secrets=secrets,
    )
    rendered_chunks: list[str] = []
    renderer_lock = threading.Lock()

    def _sink(chunk: str) -> None:
        """Write one rendered chunk to stdout."""

        with renderer_lock:
            rendered_chunks.append(chunk)
            sys.stdout.write(chunk)
            sys.stdout.flush()

    stderr_thread = threading.Thread(
        target=_consume_stderr,
        kwargs={
            "process": process,
            "stderr_path": stderr_path,
            "canonical_path": canonical_path,
            "provider": provider,
            "turn_index": args.turn_index,
            "parser": parser,
            "style": resolve_headless_display_style(args.style),
            "detail": resolve_headless_display_detail(args.detail),
            "sink": _sink,
            "diagnostic_secrets": secrets,
        },
        daemon=True,
        name=f"houmao-headless-stderr-{args.turn_index}",
    )
    stderr_thread.start()

    streaming = args.output_format in {"stream-json", "dsh-cli"}
    buffered_stdout: list[str] = []
    partial_stream = False
    if process.stdout is not None:
        with stdout_path.open(
            "a", encoding="utf-8", errors="surrogateescape" if native_dsh else "strict"
        ) as stdout_handle:
            for raw_line in process.stdout:
                stdout_handle.write(raw_line)
                stdout_handle.flush()
                if not streaming:
                    buffered_stdout.append(raw_line)
                    continue
                if native_dsh and not raw_line.endswith("\n"):
                    partial_stream = True
                    continue
                stripped = raw_line.strip()
                if not stripped:
                    continue
                events = parser.consume_stream_line(stripped)
                _persist_and_render_events(
                    canonical_path=canonical_path,
                    events=events,
                    style=resolve_headless_display_style(args.style),
                    detail=resolve_headless_display_detail(args.detail),
                    sink=_sink,
                )

    if reaper is not None:
        reaper.join()
    raw_returncode = process.wait()
    returncode = raw_returncode
    stderr_thread.join()
    interrupt_path = turn_dir / "usage-interrupt.json"
    owner_interrupted = interrupt_path.is_file()
    if native_dsh:
        if returncode == 0:
            failure = (
                "DSH native stdout or process cleanup did not settle."
                if partial_stream or group_cleanup_failed.is_set()
                else _dsh_unverified_settlement(
                    turn_dir,
                    parser.session_id,
                    load_canonical_headless_events(canonical_path=canonical_path),
                    load_headless_process_metadata(process_path=process_path),
                )
            )
            if failure is not None:
                with stderr_path.open("a", encoding="utf-8") as stream:
                    stream.write(f"{failure}\n")
                returncode = 1
        owner_interrupted = (
            returncode != 0
            and not group_cleanup_failed.is_set()
            and _confirmed_worker_signal(
                interrupt_path, pid=process.pid, birth_token=process_metadata["child_birth_token"]
            )
        )
        if owner_interrupted:
            returncode = 130
        elif returncode == 130:
            returncode = 1
        if returncode in {0, 130}:
            write_usage_json(
                turn_dir / "dsh-native-closure.json",
                {
                    "version": 1,
                    "attempt_id": turn_dir.name,
                    "native_session_id": parser.session_id,
                    "process_id": process.pid,
                    "process_birth_token": process_metadata["child_birth_token"],
                    "source": "native_journal" if returncode == 0 else "owner_process",
                    "returncode": returncode,
                    "raw_returncode": raw_returncode,
                },
            )

    if not streaming:
        events = canonical_headless_events_from_provider_output(
            provider=provider,
            output_format=args.output_format,
            stdout_text="".join(buffered_stdout),
            turn_index=args.turn_index,
        )
        _persist_and_render_events(
            canonical_path=canonical_path,
            events=events,
            style=resolve_headless_display_style(args.style),
            detail=resolve_headless_display_detail(args.detail),
            sink=_sink,
        )

    if rendered_chunks and not rendered_chunks[-1].endswith("\n"):
        sys.stdout.write("\n")
        sys.stdout.flush()

    persist_terminal_evidence(
        turn_dir,
        returncode=returncode,
        completed_at_utc=datetime.now(UTC).isoformat(),
        wall_time_ms=(time.monotonic() - started_monotonic) * 1000,
        interrupted=owner_interrupted or (provider == "dsh" and returncode == 130),
    )
    _publish_exit_status(status_path, returncode)
    return returncode


def _cleanup_owned_group(pid: int, failed: threading.Event) -> None:
    """Reap the process group and detached children adopted from the worker."""

    try:
        os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
        with suppress(ProcessLookupError):
            os.killpg(pid, signal.SIGKILL)
        # DSH creates detached subprocess groups. Once its child exits, Linux
        # reparents their surviving trees to this dedicated bridge subreaper.
        deadline = time.monotonic() + 2.0
        while children := _adopted_children(pid):
            for child in children:
                with suppress(ChildProcessError, ProcessLookupError):
                    reaped, _ = os.waitpid(child, os.WNOHANG)
                    if not reaped:
                        os.kill(child, signal.SIGKILL)
            if time.monotonic() >= deadline:
                failed.set()
                return
            time.sleep(0.01)
    except (OSError, AttributeError):
        failed.set()


def _own_detached_descendants() -> None:
    """Let this dedicated child bridge adopt detached grandchildren on Linux."""

    if sys.platform != "linux":
        raise OSError("Exact DSH process-tree cleanup requires Linux child subreaping")
    set_child_subreaper = 36  # Linux PR_SET_CHILD_SUBREAPER.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(set_child_subreaper, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _adopted_children(leader: int) -> set[int]:
    """List this bridge's children other than its separately reaped leader."""

    children: set[int] = set()
    for thread in Path("/proc/self/task").iterdir():
        with suppress(FileNotFoundError):
            children.update(int(pid) for pid in (thread / "children").read_text().split())
    return children - {leader}


def _confirmed_worker_signal(path: Path, *, pid: int, birth_token: object) -> bool:
    """Match a delivered interrupt to the worker the bridge already reaped."""

    deadline = time.monotonic() + 0.25
    while isinstance(birth_token, str):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(receipt, dict):
                return False
            if receipt.get("signal_delivered") is True:
                return (
                    receipt.get("process_id") == pid
                    and receipt.get("process_birth_token") == birth_token
                )
        except (OSError, ValueError):
            return False
        # The worker can exit while the signal caller is publishing its receipt.
        if time.monotonic() >= deadline:
            break
        time.sleep(0.01)
    return False


def _record_launch_failure(
    *, turn_dir: Path, returncode: int, message: str, started_monotonic: float
) -> None:
    """Publish safe terminal evidence even when the bridge cannot start its client."""

    (turn_dir / "stderr.log").write_text(message + "\n", encoding="utf-8")
    persist_terminal_evidence(
        turn_dir,
        returncode=returncode,
        completed_at_utc=datetime.now(UTC).isoformat(),
        wall_time_ms=(time.monotonic() - started_monotonic) * 1000,
        interrupted=False,
    )
    _publish_exit_status(turn_dir / "exitcode", returncode)


def _publish_exit_status(path: Path, returncode: int) -> None:
    """Expose one settled status only after its complete record is visible."""

    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(f"{returncode}\n")
    temporary.replace(path)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the headless bridge CLI arguments."""

    parser = argparse.ArgumentParser(prog="houmao-headless-bridge")
    parser.add_argument(
        "--provider",
        required=True,
        choices=("claude", "codex", "kimi", "dsh"),
    )
    parser.add_argument("--output-format", required=True)
    parser.add_argument("--turn-index", required=True, type=int)
    parser.add_argument("--turn-dir", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--style", default="plain")
    parser.add_argument("--detail", default="concise")
    parser.add_argument("--launched-at-utc", required=True)
    parser.add_argument("--env-file", required=True, type=Path)
    parser.add_argument("--replace-environment", action="store_true")
    parser.add_argument("--dispatch-guard-file", type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        loaded_env = json.loads(args.env_file.read_text(encoding="utf-8"))
    finally:
        args.env_file.unlink(missing_ok=True)
    if not isinstance(loaded_env, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in loaded_env.items()
    ):
        raise ValueError("env-file must contain a JSON object of string bindings")
    args.env = loaded_env
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    return args


def _persist_and_render_events(
    *,
    canonical_path: Path,
    events: Sequence[CanonicalHeadlessEvent],
    style: str,
    detail: str,
    sink: Callable[[str], None],
) -> None:
    """Append events to the canonical artifact and render them."""

    if not events:
        return
    for event in events:
        append_canonical_headless_event(canonical_path=canonical_path, event=event)
    render_canonical_headless_events(
        events=events,
        style=resolve_headless_display_style(style),
        detail=resolve_headless_display_detail(detail),
        sink=sink,
    )


def _consume_stderr(
    *,
    process: subprocess.Popen[str],
    stderr_path: Path,
    canonical_path: Path,
    provider: HeadlessProvider,
    turn_index: int,
    parser: CanonicalHeadlessEventParser,
    style: str,
    detail: str,
    sink: Callable[[str], None],
    diagnostic_secrets: tuple[str, ...] | None = None,
) -> None:
    """Mirror stderr to artifacts and canonical diagnostics."""

    if process.stderr is None:
        return
    with stderr_path.open(
        "a",
        encoding="utf-8",
        errors="surrogateescape" if diagnostic_secrets is not None else "strict",
    ) as stderr_handle:
        for raw_line in process.stderr:
            stripped = raw_line.rstrip("\n")
            if diagnostic_secrets is not None:
                stripped = sanitize_dsh_diagnostic(stripped, secret_values=diagnostic_secrets)
            stderr_handle.write(f"{stripped}\n" if provider == "kimi" else raw_line)
            stderr_handle.flush()
            if not stripped:
                continue
            event = append_stderr_diagnostic_event(
                canonical_path=canonical_path,
                provider=provider,
                turn_index=turn_index,
                text=stripped,
                session_id=parser.session_id,
            )
            render_canonical_headless_events(
                events=[event],
                style=resolve_headless_display_style(style),
                detail=resolve_headless_display_detail(detail),
                sink=sink,
            )


if __name__ == "__main__":
    raise SystemExit(main())
