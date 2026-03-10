#!/usr/bin/env python3
"""Drive the CAO Claude Esc-interrupt demo with shadow-status polling."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gig_agents.agents.brain_launch_runtime.runtime import resume_runtime_session
from gig_agents.agents.brain_launch_runtime.backends.claude_code_shadow import (
    ClaudeCodeExtractionResult,
    ClaudeCodeShadowParseError,
    ClaudeCodeShadowParser,
    ClaudeCodeShadowStatus,
)
from gig_agents.cao.rest_client import CaoApiError, CaoRestClient


class ProcessingNotObservedError(RuntimeError):
    """Raised when processing state is not observed after first prompt."""


@dataclass(frozen=True)
class ShadowPollResult:
    """One polling snapshot from CAO mode=full output."""

    scrollback: str
    shadow_status: ClaudeCodeShadowStatus


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CAO Claude Esc-interrupt flow and write JSON output"
    )
    parser.add_argument("--agent-def-dir", type=Path, required=True)
    parser.add_argument("--agent-identity", type=Path, required=True)
    parser.add_argument("--first-prompt-file", type=Path, required=True)
    parser.add_argument("--second-prompt-file", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--poll-interval-seconds", type=float, default=0.4)
    parser.add_argument("--ready-timeout-seconds", type=float, default=30.0)
    parser.add_argument("--processing-timeout-seconds", type=float, default=20.0)
    parser.add_argument("--idle-timeout-seconds", type=float, default=25.0)
    parser.add_argument("--completion-timeout-seconds", type=float, default=90.0)
    parser.add_argument("--http-timeout-seconds", type=float, default=15.0)
    return parser


def _read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"prompt file is empty: {path}")
    return text


def _load_session_fields(path: Path) -> tuple[str, str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cao = payload.get("cao") or {}
    api_base_url = str(cao.get("api_base_url", "")).strip()
    session_name = str(cao.get("session_name", "")).strip()
    terminal_id = str(cao.get("terminal_id", "")).strip()
    if not api_base_url:
        raise RuntimeError("session_manifest missing cao.api_base_url")
    if not session_name:
        raise RuntimeError("session_manifest missing cao.session_name")
    if not terminal_id:
        raise RuntimeError("session_manifest missing cao.terminal_id")
    return api_base_url, session_name, terminal_id


def _terminal_log_path(terminal_id: str) -> str:
    return f"~/.aws/cli-agent-orchestrator/logs/terminal/{terminal_id}.log"


def _fetch_full_output(client: CaoRestClient, terminal_id: str) -> str:
    try:
        return client.get_terminal_output(terminal_id, mode="full").output
    except CaoApiError as exc:
        raise RuntimeError(
            f"failed to fetch terminal output (terminal_id={terminal_id}): {exc.detail}"
        ) from exc


def _wait_for_shadow_status(
    *,
    client: CaoRestClient,
    parser: ClaudeCodeShadowParser,
    terminal_id: str,
    baseline_pos: int,
    accepted_statuses: set[str],
    timeout_seconds: float,
    poll_interval_seconds: float,
    phase: str,
) -> ShadowPollResult:
    deadline = time.monotonic() + timeout_seconds
    last_poll: ShadowPollResult | None = None

    while time.monotonic() < deadline:
        scrollback = _fetch_full_output(client, terminal_id)
        shadow_status = parser.classify_shadow_status(
            scrollback,
            baseline_pos=baseline_pos,
        )
        last_poll = ShadowPollResult(scrollback=scrollback, shadow_status=shadow_status)

        if shadow_status.status in accepted_statuses:
            return last_poll
        if shadow_status.status == "waiting_user_answer":
            excerpt = (
                shadow_status.waiting_user_answer_excerpt
                or parser.ansi_stripped_tail_excerpt(scrollback, max_lines=12)
            )
            detail = f"Claude entered waiting_user_answer during {phase}"
            if excerpt:
                detail = f"{detail}\n\nOptions excerpt:\n{excerpt}"
            raise RuntimeError(detail)

        time.sleep(poll_interval_seconds)

    status_text = last_poll.shadow_status.status if last_poll is not None else "unknown"
    detail = (
        f"timed out waiting for {phase} within {timeout_seconds:.1f}s "
        f"(last shadow status={status_text})"
    )
    if last_poll is not None:
        excerpt = parser.ansi_stripped_tail_excerpt(last_poll.scrollback, max_lines=12)
        if excerpt:
            detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
    raise TimeoutError(detail)


def _send_escape_key(*, agent_def_dir: Path, session_manifest_path: Path) -> None:
    controller = resume_runtime_session(
        agent_def_dir=agent_def_dir.resolve(),
        session_manifest_path=session_manifest_path.resolve(),
    )
    result = controller.send_input_ex("<[Escape]>")
    if result.status != "ok":
        raise RuntimeError(f"runtime send-keys failed: {result.detail}")


def _extract_second_answer(
    *,
    parser: ClaudeCodeShadowParser,
    completion_poll: ShadowPollResult,
    second_baseline_pos: int,
) -> ClaudeCodeExtractionResult:
    try:
        return parser.extract_last_answer(
            completion_poll.scrollback,
            baseline_pos=second_baseline_pos,
        )
    except ClaudeCodeShadowParseError as exc:
        excerpt = parser.ansi_stripped_tail_excerpt(
            completion_poll.scrollback, max_lines=12
        )
        detail = f"failed to extract second answer: {exc}"
        if excerpt:
            detail = f"{detail}\n\nTail excerpt:\n{excerpt}"
        raise RuntimeError(detail) from exc


def _run_driver(args: argparse.Namespace) -> dict[str, Any]:
    first_prompt = _read_text(args.first_prompt_file)
    second_prompt = _read_text(args.second_prompt_file)
    api_base_url, session_name, terminal_id = _load_session_fields(args.agent_identity)
    terminal_log_path = _terminal_log_path(terminal_id)

    client = CaoRestClient(
        api_base_url,
        timeout_seconds=float(args.http_timeout_seconds),
    )
    parser = ClaudeCodeShadowParser()

    terminal = client.get_terminal(terminal_id)
    window_name = terminal.name.strip()
    if not window_name:
        raise RuntimeError("GET /terminals/{id} returned empty terminal.name")
    tmux_target = f"{session_name}:{window_name}"

    _wait_for_shadow_status(
        client=client,
        parser=parser,
        terminal_id=terminal_id,
        baseline_pos=0,
        accepted_statuses={"idle", "completed"},
        timeout_seconds=float(args.ready_timeout_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
        phase="initial ready status",
    )

    first_baseline_output = _fetch_full_output(client, terminal_id)
    first_baseline_pos = parser.capture_baseline_pos(first_baseline_output)
    submit_first_result = client.send_terminal_input(terminal_id, first_prompt)
    if not submit_first_result.success:
        raise RuntimeError("CAO rejected first prompt submission")

    try:
        processing_poll = _wait_for_shadow_status(
            client=client,
            parser=parser,
            terminal_id=terminal_id,
            baseline_pos=first_baseline_pos,
            accepted_statuses={"processing"},
            timeout_seconds=float(args.processing_timeout_seconds),
            poll_interval_seconds=float(args.poll_interval_seconds),
            phase="first prompt processing",
        )
    except TimeoutError as exc:
        raise ProcessingNotObservedError(str(exc)) from exc

    escape_baseline_pos = parser.capture_baseline_pos(processing_poll.scrollback)
    _send_escape_key(
        agent_def_dir=args.agent_def_dir,
        session_manifest_path=args.agent_identity,
    )

    idle_poll = _wait_for_shadow_status(
        client=client,
        parser=parser,
        terminal_id=terminal_id,
        baseline_pos=escape_baseline_pos,
        accepted_statuses={"idle"},
        timeout_seconds=float(args.idle_timeout_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
        phase="post-escape idle status",
    )

    second_baseline_output = _fetch_full_output(client, terminal_id)
    second_baseline_pos = parser.capture_baseline_pos(second_baseline_output)
    submit_second_result = client.send_terminal_input(terminal_id, second_prompt)
    if not submit_second_result.success:
        raise RuntimeError("CAO rejected second prompt submission")

    completion_poll = _wait_for_shadow_status(
        client=client,
        parser=parser,
        terminal_id=terminal_id,
        baseline_pos=second_baseline_pos,
        accepted_statuses={"completed"},
        timeout_seconds=float(args.completion_timeout_seconds),
        poll_interval_seconds=float(args.poll_interval_seconds),
        phase="second prompt completion",
    )

    extraction = _extract_second_answer(
        parser=parser,
        completion_poll=completion_poll,
        second_baseline_pos=second_baseline_pos,
    )
    second_answer_text = extraction.answer_text.strip()
    if not second_answer_text:
        raise RuntimeError("second prompt extracted answer is empty")

    return {
        "status": "ok",
        "terminal_id": terminal_id,
        "session_name": session_name,
        "window_name": window_name,
        "tmux_target": tmux_target,
        "terminal_log_path": terminal_log_path,
        "processing_observed": True,
        "idle_after_escape": idle_poll.shadow_status.status == "idle",
        "second_response_text": second_answer_text,
        "second_response_chars": len(second_answer_text),
        "processing_shadow_status": processing_poll.shadow_status.status,
        "idle_shadow_status": idle_poll.shadow_status.status,
        "second_shadow_status": completion_poll.shadow_status.status,
        "shadow_preset_version": extraction.preset_version,
    }


def main() -> int:
    args = _build_parser().parse_args()

    try:
        payload = _run_driver(args)
    except ProcessingNotObservedError as exc:
        print(f"could not observe processing: {exc}", file=sys.stderr)
        return 3
    except (CaoApiError, RuntimeError, TimeoutError) as exc:
        print(f"interrupt driver failed: {exc}", file=sys.stderr)
        return 1

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"driver report: {args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
