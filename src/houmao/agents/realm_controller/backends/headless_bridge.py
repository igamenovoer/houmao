"""Bridge subprocess for managed headless live rendering and artifact capture."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import Callable, Sequence

from houmao.agents.realm_controller.backends.headless_output import (
    append_canonical_headless_event,
    append_stderr_diagnostic_event,
    canonical_headless_event_artifact_path,
    canonical_headless_events_from_provider_output,
    render_canonical_headless_events,
    resolve_headless_display_detail,
    resolve_headless_display_style,
)
from houmao.agents.realm_controller.backends.headless_output import (
    CanonicalHeadlessEvent,
    CanonicalHeadlessEventParser,
    HeadlessProvider,
)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the headless bridge CLI."""

    args = _parse_args(argv=argv)
    command = list(args.command)
    if not command:
        raise ValueError("headless bridge requires a provider command after `--`")

    provider: HeadlessProvider = args.provider
    turn_dir = args.turn_dir.resolve()
    turn_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = (turn_dir / "stdout.jsonl").resolve()
    stderr_path = (turn_dir / "stderr.log").resolve()
    status_path = (turn_dir / "exitcode").resolve()
    process_path = (turn_dir / "process.json").resolve()
    canonical_path = canonical_headless_event_artifact_path(turn_dir=turn_dir)

    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    canonical_path.write_text("", encoding="utf-8")

    process = subprocess.Popen(
        command,
        cwd=str(args.cwd.resolve()),
        env={**os.environ, **args.env},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    process_path.write_text(
        (
            "{"
            f'"runner_pid":{os.getpid()},'
            f'"child_pid":{process.pid},'
            f'"launched_at_utc":"{args.launched_at_utc}"'
            "}\n"
        ),
        encoding="utf-8",
    )

    parser = CanonicalHeadlessEventParser(provider=provider, turn_index=args.turn_index)
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
        },
        daemon=True,
        name=f"houmao-headless-stderr-{args.turn_index}",
    )
    stderr_thread.start()

    buffered_stdout: list[str] = []
    if process.stdout is not None:
        with stdout_path.open("a", encoding="utf-8") as stdout_handle:
            for raw_line in process.stdout:
                stdout_handle.write(raw_line)
                stdout_handle.flush()
                buffered_stdout.append(raw_line)
                if args.output_format != "stream-json":
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

    returncode = process.wait()
    stderr_thread.join()

    if args.output_format != "stream-json":
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

    status_path.write_text(f"{returncode}\n", encoding="utf-8")
    return returncode


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the headless bridge CLI arguments."""

    parser = argparse.ArgumentParser(prog="houmao-headless-bridge")
    parser.add_argument("--provider", required=True, choices=("claude", "codex", "gemini"))
    parser.add_argument("--output-format", required=True)
    parser.add_argument("--turn-index", required=True, type=int)
    parser.add_argument("--turn-dir", required=True, type=Path)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--style", default="plain")
    parser.add_argument("--detail", default="concise")
    parser.add_argument("--launched-at-utc", required=True)
    parser.add_argument("--env-json", default="{}")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(list(argv) if argv is not None else None)
    env_payload = args.env_json
    if not isinstance(env_payload, str):
        raise ValueError("env-json must be a JSON object string")

    loaded_env = json.loads(env_payload)
    if not isinstance(loaded_env, dict):
        raise ValueError("env-json must decode to a JSON object")
    args.env = {str(key): str(value) for key, value in loaded_env.items()}
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
) -> None:
    """Mirror stderr to artifacts and canonical diagnostics."""

    if process.stderr is None:
        return
    with stderr_path.open("a", encoding="utf-8") as stderr_handle:
        for raw_line in process.stderr:
            stderr_handle.write(raw_line)
            stderr_handle.flush()
            stripped = raw_line.rstrip("\n")
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
