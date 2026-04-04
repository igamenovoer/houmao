"""Rendering and small utility helpers for the interactive CAO demo."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from pydantic import ValidationError

from houmao.demo.legacy.cao_interactive_demo.models import (
    ControlActionSummary,
    DemoWorkflowError,
    _ModelT,
)


def _render_human_inspect_output(*, payload: dict[str, object]) -> str:
    """Render a human-readable inspect surface from the machine payload."""

    lines = [
        "Interactive CAO Demo Inspect",
        "",
        "Session Summary",
        f"session_status: {payload['session_status']}",
        f"tool: {payload['tool']}",
        f"variant_id: {payload['variant_id']}",
        f"brain_recipe: {payload['brain_recipe']}",
        f"tool_state: {payload['tool_state']}",
        f"agent_identity: {payload['agent_identity']}",
        f"session_name: {payload['session_name']}",
        f"terminal_id: {payload['terminal_id']}",
        f"last_updated: {payload['updated_at']}",
        "",
        "Commands",
        f"tmux_attach: {payload['tmux_attach_command']}",
        f"terminal_log_tail: {payload['terminal_log_tail_command']}",
        "",
        "Artifacts",
        f"session_manifest: {payload['session_manifest']}",
        f"terminal_log_path: {payload['terminal_log_path']}",
        f"workspace_dir: {payload['workspace_dir']}",
        f"runtime_root: {payload['runtime_root']}",
    ]

    output_text_tail_chars = payload.get("output_text_tail_chars_requested")
    if isinstance(output_text_tail_chars, int):
        lines.extend(
            [
                "",
                f"Best-Effort Output Text Tail (last {output_text_tail_chars} chars)",
            ]
        )
        note = payload.get("output_text_tail_note")
        if isinstance(note, str) and note.strip():
            lines.append(note)
        else:
            output_text_tail = payload.get("output_text_tail")
            if isinstance(output_text_tail, str) and output_text_tail:
                lines.extend(_indented_lines(output_text_tail))
            else:
                lines.append("  <empty>")

    return "\n".join(lines)


def _render_start_output(*, payload: dict[str, object]) -> str:
    """Render a human-readable startup success surface."""

    state = _require_mapping(payload.get("state"), context="start payload missing state")
    agent_identity = _require_non_empty_string(
        state.get("agent_identity"),
        context="start payload missing state.agent_identity",
    )
    tool = _require_non_empty_string(
        state.get("tool"),
        context="start payload missing state.tool",
    )
    variant_id = _require_non_empty_string(
        state.get("variant_id"),
        context="start payload missing state.variant_id",
    )
    brain_recipe = _require_non_empty_string(
        state.get("brain_recipe"),
        context="start payload missing state.brain_recipe",
    )
    tmux_target = _require_non_empty_string(
        state.get("tmux_target"),
        context="start payload missing state.tmux_target",
    )
    terminal_id = _require_non_empty_string(
        state.get("terminal_id"),
        context="start payload missing state.terminal_id",
    )
    terminal_log_path = _require_non_empty_string(
        state.get("terminal_log_path"),
        context="start payload missing state.terminal_log_path",
    )
    session_manifest = _require_non_empty_string(
        state.get("session_manifest"),
        context="start payload missing state.session_manifest",
    )
    workspace_dir = _require_non_empty_string(
        state.get("workspace_dir"),
        context="start payload missing state.workspace_dir",
    )
    runtime_root = _require_non_empty_string(
        state.get("runtime_root"),
        context="start payload missing state.runtime_root",
    )
    brain_manifest = _require_non_empty_string(
        state.get("brain_manifest"),
        context="start payload missing state.brain_manifest",
    )
    launcher_config_path = _require_non_empty_string(
        state.get("launcher_config_path"),
        context="start payload missing state.launcher_config_path",
    )
    cao_base_url = _require_non_empty_string(
        state.get("cao_base_url"),
        context="start payload missing state.cao_base_url",
    )
    updated_at = _require_non_empty_string(
        state.get("updated_at"),
        context="start payload missing state.updated_at",
    )

    lines = [
        "Interactive CAO Demo Started",
        "",
        "Session Summary",
        "session_status: active",
        f"tool: {tool}",
        f"variant_id: {variant_id}",
        f"brain_recipe: {brain_recipe}",
        f"agent_identity: {agent_identity}",
        f"terminal_id: {terminal_id}",
        f"cao_base_url: {cao_base_url}",
        f"last_updated: {updated_at}",
        "",
        "Commands",
        f"tmux_attach: tmux attach -t {tmux_target}",
        f"terminal_log_tail: tail -f {terminal_log_path}",
        "",
        "Artifacts",
        f"session_manifest: {session_manifest}",
        f"brain_manifest: {brain_manifest}",
        f"workspace_dir: {workspace_dir}",
        f"runtime_root: {runtime_root}",
        f"launcher_config_path: {launcher_config_path}",
    ]

    replaced_previous_agent_identity = payload.get("replaced_previous_agent_identity")
    warnings = payload.get("warnings")
    notes: list[str] = []
    if (
        isinstance(replaced_previous_agent_identity, str)
        and replaced_previous_agent_identity.strip()
    ):
        notes.append(f"replaced_previous_agent_identity: {replaced_previous_agent_identity}")
    if isinstance(warnings, list):
        for warning in warnings:
            if isinstance(warning, str) and warning.strip():
                notes.append(f"warning: {warning}")
    if notes:
        lines.extend(["", "Notes", *notes])

    return "\n".join(lines)


def _indented_lines(text: str) -> list[str]:
    """Indent multi-line text for human-readable inspect output."""

    lines = text.splitlines()
    if not lines:
        return ["  <empty>"]
    return [f"  {line}" for line in lines]


def _parse_events(*, stdout: str) -> list[dict[str, object]]:
    """Parse JSONL runtime events from `send-prompt` stdout."""

    events: list[dict[str, object]] = []
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _extract_turn_response_text(events: list[dict[str, object]]) -> tuple[str, str]:
    """Extract one human-facing turn summary plus its source label.

    For shadow-mode turns this prefers an explicit shadow-aware best-effort path
    over the final ``done.message``.
    """

    for event in reversed(events):
        if event.get("kind") != "done":
            continue

        payload = event.get("payload")
        if isinstance(payload, dict):
            dialog_projection = payload.get("dialog_projection")
            if isinstance(dialog_projection, dict):
                dialog_text = dialog_projection.get("dialog_text")
                if isinstance(dialog_text, str):
                    lines = [line.strip() for line in dialog_text.splitlines() if line.strip()]
                    if lines:
                        return (lines[-1], "dialog_projection_last_line_best_effort")

        done_message = str(event.get("message", "")).strip()
        if done_message:
            return (done_message, "done_message")

    return ("", "unavailable")


def _parse_control_action_summary(text: str, *, context: str) -> ControlActionSummary:
    """Parse runtime control-input stdout into a validated control result summary."""

    payload = _parse_json_output(text, context=context)
    return _validate_model(ControlActionSummary, payload, source=context)


def _load_json_file(path: Path, *, context: str) -> dict[str, object]:
    """Load a JSON file and require a top-level object payload."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DemoWorkflowError(f"{context} file not found: `{path}`.") from exc
    except json.JSONDecodeError as exc:
        raise DemoWorkflowError(f"Invalid JSON in {context} `{path}`.") from exc
    return _require_mapping(payload, context=f"{context} `{path}` must contain a JSON object")


def _write_json_file(path: Path, payload: dict[str, object]) -> None:
    """Persist a JSON object payload with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_json_output(text: str, *, context: str) -> dict[str, object]:
    """Parse CLI stdout as a JSON object payload."""

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DemoWorkflowError(f"Invalid JSON in {context}.") from exc
    return _require_mapping(payload, context=f"{context} must be a JSON object")


def _require_mapping(value: object, *, context: str) -> dict[str, object]:
    """Require that a value is a JSON-like object mapping."""

    if not isinstance(value, dict):
        raise DemoWorkflowError(context)
    return value


def _require_non_empty_string(value: object, *, context: str) -> str:
    """Require that a value is a non-empty string."""

    if not isinstance(value, str) or not value.strip():
        raise DemoWorkflowError(context)
    return value.strip()


def _validate_model(model: type[_ModelT], payload: object, *, source: str) -> _ModelT:
    """Validate a strict model payload with an actionable source label."""

    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise DemoWorkflowError(f"Invalid payload for `{source}`: {exc}") from exc


def _require_tool(executable: str) -> None:
    """Require that a command-line executable is available on PATH."""

    if shutil.which(executable) is None:
        raise DemoWorkflowError(f"`{executable}` is required on PATH for this demo.")


def _join_command(command: Sequence[str]) -> str:
    """Render a subprocess command for diagnostic messages."""

    return " ".join(command)


def _emit_startup_progress(message: str) -> None:
    """Print one operator-facing startup progress line on stderr."""

    print(f"[interactive-demo:start] {message}", file=sys.stderr, flush=True)


def _format_elapsed_seconds(elapsed_seconds: float) -> str:
    """Render elapsed time for startup progress heartbeats."""

    if elapsed_seconds < 10.0:
        return f"{elapsed_seconds:.1f}s"
    return f"{elapsed_seconds:.0f}s"


def _positive_int(raw_value: str) -> int:
    """Parse a strictly positive integer CLI flag value."""

    try:
        parsed = int(raw_value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _print_json(payload: dict[str, object]) -> None:
    """Print a JSON payload to stdout."""

    print(json.dumps(payload, indent=2, sort_keys=True))


def _utc_now() -> str:
    """Return the current UTC timestamp in stable ISO-8601 format."""

    return datetime.now(UTC).isoformat(timespec="seconds")
