"""Automatic tracking-debug workflow for the Houmao-server shadow-watch demo."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from libtmux import Server
from libtmux.pane import Pane

from houmao.demo.houmao_server_dual_shadow_watch.driver import (
    _default_agent_def_dir,
    _default_profile_path,
    _default_project_fixture,
    _repo_root,
    inspect_demo,
    preflight_demo,
    start_demo,
    stop_demo,
)
from houmao.demo.houmao_server_dual_shadow_watch.models import load_demo_state
from houmao.server.client import HoumaoServerClient
from houmao.server.models import (
    HoumaoLifecycleAuthorityMetadata,
    HoumaoOperatorState,
    HoumaoTerminalStateResponse,
)
from houmao.server.tracking_debug import TRACKING_DEBUG_ROOT_ENV_VAR

DEFAULT_DEBUG_POLL_INTERVAL_SECONDS = 0.2
DEFAULT_DEBUG_STABILITY_THRESHOLD_SECONDS = 0.4
DEFAULT_DEBUG_COMPLETION_STABILITY_SECONDS = 0.4
DEFAULT_DEBUG_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS = 8.0
DEFAULT_READY_TIMEOUT_SECONDS = 45.0
DEFAULT_PATH_TIMEOUT_SECONDS = 20.0
DEFAULT_SERVER_PROMPT = "Reply with the single word SERVER_READY and stop."
DEFAULT_TMUX_PROMPT = "Reply with the single word TMUX_READY and stop."


def main(argv: list[str] | None = None) -> int:
    """Run the automatic tracking-debug workflow."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root is not None
        else _default_output_root(_repo_root())
    )
    payload = run_tracking_debug(
        repo_root=_repo_root(),
        output_root=output_root,
        slot=args.slot,
        poll_interval_seconds=float(args.poll_interval_seconds),
        stability_threshold_seconds=float(args.stability_threshold_seconds),
        completion_stability_seconds=float(args.completion_stability_seconds),
        unknown_to_stalled_timeout_seconds=float(args.unknown_to_stalled_timeout_seconds),
        ready_timeout_seconds=float(args.ready_timeout_seconds),
        path_timeout_seconds=float(args.path_timeout_seconds),
        server_prompt=args.server_prompt,
        tmux_prompt=args.tmux_prompt,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def run_tracking_debug(
    *,
    repo_root: Path,
    output_root: Path,
    slot: str,
    poll_interval_seconds: float,
    stability_threshold_seconds: float,
    completion_stability_seconds: float,
    unknown_to_stalled_timeout_seconds: float,
    ready_timeout_seconds: float,
    path_timeout_seconds: float,
    server_prompt: str,
    tmux_prompt: str,
) -> dict[str, Any]:
    """Run the two-path prompt comparison and persist debug artifacts."""

    resolved_output_root = output_root.expanduser().resolve()
    run_root = resolved_output_root / f"demo-run-{resolved_output_root.name}"
    artifacts_dir = (resolved_output_root / "artifacts").resolve()
    summary_dir = (resolved_output_root / "summary").resolve()
    if resolved_output_root.exists():
        shutil.rmtree(resolved_output_root)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    summary_dir.mkdir(parents=True, exist_ok=True)

    selected_agent_def_dir = _default_agent_def_dir(repo_root)
    selected_project_fixture = _default_project_fixture(repo_root)
    selected_profile_path = _default_profile_path(repo_root)
    _write_json(
        artifacts_dir / "effective-parameters.json",
        {
            "output_root": str(resolved_output_root),
            "run_root": str(run_root),
            "slot": slot,
            "poll_interval_seconds": poll_interval_seconds,
            "stability_threshold_seconds": stability_threshold_seconds,
            "completion_stability_seconds": completion_stability_seconds,
            "unknown_to_stalled_timeout_seconds": unknown_to_stalled_timeout_seconds,
            "ready_timeout_seconds": ready_timeout_seconds,
            "path_timeout_seconds": path_timeout_seconds,
            "server_prompt": server_prompt,
            "tmux_prompt": tmux_prompt,
        },
    )

    preflight_payload = preflight_demo(
        repo_root=repo_root,
        run_root=run_root,
        agent_def_dir=selected_agent_def_dir,
        project_fixture=selected_project_fixture,
        profile_path=selected_profile_path,
        port=None,
        json_output=True,
    )
    _write_json(artifacts_dir / "preflight.json", preflight_payload)

    started = False
    stop_payload: dict[str, Any] | None = None
    path_results: list[dict[str, Any]] = []
    state = None
    client = None
    terminal_id = None
    tmux_session_name = None
    try:
        with _temporary_env(TRACKING_DEBUG_ROOT_ENV_VAR, str(resolved_output_root)):
            start_payload = start_demo(
                repo_root=repo_root,
                run_root=run_root,
                agent_def_dir=selected_agent_def_dir,
                project_fixture=selected_project_fixture,
                profile_path=selected_profile_path,
                port=None,
                poll_interval_seconds=poll_interval_seconds,
                stability_threshold_seconds=stability_threshold_seconds,
                completion_stability_seconds=completion_stability_seconds,
                unknown_to_stalled_timeout_seconds=unknown_to_stalled_timeout_seconds,
                server_start_timeout_seconds=20.0,
                launch_timeout_seconds=45.0,
                stop_timeout_seconds=20.0,
                json_output=True,
            )
        started = True
        _write_json(artifacts_dir / "start.json", start_payload)

        state = load_demo_state(run_root / "control" / "demo_state.json")
        agent_state = state.agents[slot]
        terminal_id = agent_state.terminal_id
        tmux_session_name = agent_state.tmux_session_name
        client = HoumaoServerClient(state.server.api_base_url, timeout_seconds=3.0)

        baseline_state = _wait_for_ready_baseline(
            client=client,
            terminal_id=terminal_id,
            timeout_seconds=ready_timeout_seconds,
        )
        _write_json(
            artifacts_dir / "baseline-inspect.json",
            inspect_demo(repo_root=repo_root, run_root=run_root, json_output=True),
        )
        _write_json(
            artifacts_dir / "baseline-terminal-state.json",
            baseline_state.model_dump(mode="json"),
        )
        (artifacts_dir / "baseline-pane.txt").write_text(
            _capture_pane_text(tmux_session_name),
            encoding="utf-8",
        )

        path_results.append(
            _run_server_input_path(
                repo_root=repo_root,
                run_root=run_root,
                artifacts_dir=artifacts_dir / "server-input",
                client=client,
                terminal_id=terminal_id,
                tmux_session_name=tmux_session_name,
                prompt=server_prompt,
                timeout_seconds=path_timeout_seconds,
            )
        )
        _wait_for_ready_baseline(
            client=client,
            terminal_id=terminal_id,
            timeout_seconds=ready_timeout_seconds,
        )

        path_results.append(
            _run_direct_tmux_path(
                repo_root=repo_root,
                run_root=run_root,
                artifacts_dir=artifacts_dir / "direct-tmux",
                client=client,
                terminal_id=terminal_id,
                tmux_session_name=tmux_session_name,
                prompt=tmux_prompt,
                timeout_seconds=path_timeout_seconds,
            )
        )

        summary_payload = _build_summary(
            output_root=resolved_output_root,
            terminal_id=terminal_id,
            path_results=path_results,
        )
        _write_json(summary_dir / "run-summary.json", summary_payload)
        (summary_dir / "timeline.md").write_text(
            _summary_markdown(summary_payload),
            encoding="utf-8",
        )
    finally:
        if started:
            try:
                stop_payload = stop_demo(repo_root=repo_root, run_root=run_root, json_output=True)
                _write_json(artifacts_dir / "stop.json", stop_payload)
            except Exception as exc:  # pragma: no cover - best-effort cleanup reporting
                _write_json(artifacts_dir / "stop-error.json", {"detail": str(exc)})

    result_payload = {
        "status": "completed",
        "output_root": str(resolved_output_root),
        "run_root": str(run_root),
        "events_dir": str(resolved_output_root / "events"),
        "summary_path": str(summary_dir / "run-summary.json"),
        "timeline_path": str(summary_dir / "timeline.md"),
        "stop_payload_path": str(artifacts_dir / "stop.json") if stop_payload is not None else None,
        "paths": path_results,
    }
    _write_json(resolved_output_root / "result.json", result_payload)
    return result_payload


def _run_server_input_path(
    *,
    repo_root: Path,
    run_root: Path,
    artifacts_dir: Path,
    client: HoumaoServerClient,
    terminal_id: str,
    tmux_session_name: str,
    prompt: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Execute the server-owned input path and capture all path artifacts."""

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    before_state = client.terminal_state(terminal_id)
    before_monotonic = time.monotonic()
    _write_json(
        artifacts_dir / "before-inspect.json",
        inspect_demo(repo_root=repo_root, run_root=run_root, json_output=True),
    )
    _write_json(artifacts_dir / "before-terminal-state.json", before_state.model_dump(mode="json"))
    (artifacts_dir / "before-pane.txt").write_text(
        _capture_pane_text(tmux_session_name),
        encoding="utf-8",
    )

    client.send_terminal_input(terminal_id, prompt)
    timeline = _poll_path_timeline(
        client=client,
        terminal_id=terminal_id,
        baseline_projection_text=_projection_text(before_state),
        timeout_seconds=timeout_seconds,
    )
    after_state = timeline[-1][1]
    after_monotonic = time.monotonic()
    _write_timeline(artifacts_dir / "timeline.ndjson", timeline, before_monotonic=before_monotonic)
    _write_json(
        artifacts_dir / "after-inspect.json",
        inspect_demo(repo_root=repo_root, run_root=run_root, json_output=True),
    )
    _write_json(artifacts_dir / "after-terminal-state.json", after_state.model_dump(mode="json"))
    _write_json(
        artifacts_dir / "history.json",
        client.terminal_history(terminal_id, limit=20).model_dump(mode="json"),
    )
    (artifacts_dir / "after-pane.txt").write_text(
        _capture_pane_text(tmux_session_name),
        encoding="utf-8",
    )
    before_operator_state = _require_operator_state(before_state)
    after_operator_state = _require_operator_state(after_state)
    after_lifecycle_authority = _require_lifecycle_authority(after_state)
    return {
        "path_id": "server-input",
        "prompt": prompt,
        "prompt_source": "server_input_route",
        "window_start_monotonic": before_monotonic,
        "window_end_monotonic": after_monotonic,
        "before_completion_state": before_operator_state.completion_state,
        "after_completion_state": after_operator_state.completion_state,
        "after_operator_status": after_operator_state.status,
        "after_turn_anchor_state": after_lifecycle_authority.turn_anchor_state,
        "after_completion_authority": after_lifecycle_authority.completion_authority,
        "before_projection_sha1": _sha1_text(_projection_text(before_state)),
        "after_projection_sha1": _sha1_text(_projection_text(after_state)),
        "artifacts_dir": str(artifacts_dir),
    }


def _run_direct_tmux_path(
    *,
    repo_root: Path,
    run_root: Path,
    artifacts_dir: Path,
    client: HoumaoServerClient,
    terminal_id: str,
    tmux_session_name: str,
    prompt: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Execute the direct tmux-input path and capture all path artifacts."""

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    before_state = client.terminal_state(terminal_id)
    before_monotonic = time.monotonic()
    _write_json(
        artifacts_dir / "before-inspect.json",
        inspect_demo(repo_root=repo_root, run_root=run_root, json_output=True),
    )
    _write_json(artifacts_dir / "before-terminal-state.json", before_state.model_dump(mode="json"))
    (artifacts_dir / "before-pane.txt").write_text(
        _capture_pane_text(tmux_session_name),
        encoding="utf-8",
    )

    _pane_for_session(tmux_session_name).send_keys(
        prompt, enter=True, suppress_history=False, literal=True
    )
    timeline = _poll_path_timeline(
        client=client,
        terminal_id=terminal_id,
        baseline_projection_text=_projection_text(before_state),
        timeout_seconds=timeout_seconds,
    )
    after_state = timeline[-1][1]
    after_monotonic = time.monotonic()
    _write_timeline(artifacts_dir / "timeline.ndjson", timeline, before_monotonic=before_monotonic)
    _write_json(
        artifacts_dir / "after-inspect.json",
        inspect_demo(repo_root=repo_root, run_root=run_root, json_output=True),
    )
    _write_json(artifacts_dir / "after-terminal-state.json", after_state.model_dump(mode="json"))
    _write_json(
        artifacts_dir / "history.json",
        client.terminal_history(terminal_id, limit=20).model_dump(mode="json"),
    )
    (artifacts_dir / "after-pane.txt").write_text(
        _capture_pane_text(tmux_session_name),
        encoding="utf-8",
    )
    before_operator_state = _require_operator_state(before_state)
    after_operator_state = _require_operator_state(after_state)
    after_lifecycle_authority = _require_lifecycle_authority(after_state)
    return {
        "path_id": "direct-tmux",
        "prompt": prompt,
        "prompt_source": "tmux_send_keys",
        "window_start_monotonic": before_monotonic,
        "window_end_monotonic": after_monotonic,
        "before_completion_state": before_operator_state.completion_state,
        "after_completion_state": after_operator_state.completion_state,
        "after_operator_status": after_operator_state.status,
        "after_turn_anchor_state": after_lifecycle_authority.turn_anchor_state,
        "after_completion_authority": after_lifecycle_authority.completion_authority,
        "before_projection_sha1": _sha1_text(_projection_text(before_state)),
        "after_projection_sha1": _sha1_text(_projection_text(after_state)),
        "artifacts_dir": str(artifacts_dir),
    }


def _wait_for_ready_baseline(
    *,
    client: HoumaoServerClient,
    terminal_id: str,
    timeout_seconds: float,
) -> HoumaoTerminalStateResponse:
    """Wait until one terminal returns to a stable ready baseline."""

    deadline = time.monotonic() + timeout_seconds
    last_state: HoumaoTerminalStateResponse | None = None
    while time.monotonic() < deadline:
        last_state = client.terminal_state(terminal_id)
        operator_state = _require_operator_state(last_state)
        lifecycle_authority = _require_lifecycle_authority(last_state)
        if (
            operator_state.status == "ready"
            and operator_state.completion_state == "inactive"
            and lifecycle_authority.completion_authority == "unanchored_background"
            and lifecycle_authority.turn_anchor_state == "absent"
            and last_state.stability.stable
        ):
            return last_state
        time.sleep(0.2)
    raise RuntimeError(
        "Timed out waiting for a stable ready baseline; last state was "
        f"{last_state.model_dump(mode='json') if last_state is not None else None}"
    )


def _poll_path_timeline(
    *,
    client: HoumaoServerClient,
    terminal_id: str,
    baseline_projection_text: str | None,
    timeout_seconds: float,
) -> list[tuple[float, HoumaoTerminalStateResponse]]:
    """Poll one terminal until the prompt path produces a settled visible outcome."""

    deadline = time.monotonic() + timeout_seconds
    samples: list[tuple[float, HoumaoTerminalStateResponse]] = []
    saw_projection_change = False
    while time.monotonic() < deadline:
        state = client.terminal_state(terminal_id)
        sample_monotonic = time.monotonic()
        samples.append((sample_monotonic, state))
        if _projection_text(state) != baseline_projection_text:
            saw_projection_change = True
        if _require_operator_state(state).completion_state in {
            "candidate_complete",
            "completed",
            "blocked",
            "failed",
            "stalled",
        }:
            break
        if saw_projection_change and state.stability.stable:
            break
        time.sleep(0.2)
    if not samples:
        raise RuntimeError("No timeline samples were captured for the prompt path.")
    return samples


def _require_operator_state(response: HoumaoTerminalStateResponse) -> HoumaoOperatorState:
    """Return one required operator-state payload from a terminal response."""

    if response.operator_state is None:
        raise RuntimeError("Tracking debug expected operator_state in terminal response.")
    return response.operator_state


def _require_lifecycle_authority(
    response: HoumaoTerminalStateResponse,
) -> HoumaoLifecycleAuthorityMetadata:
    """Return one required lifecycle-authority payload from a terminal response."""

    if response.lifecycle_authority is None:
        raise RuntimeError("Tracking debug expected lifecycle_authority in terminal response.")
    return response.lifecycle_authority


def _capture_pane_text(tmux_session_name: str) -> str:
    """Capture the full visible pane text for one tmux session."""

    pane = _pane_for_session(tmux_session_name)
    return "\n".join(
        pane.capture_pane(
            start="-",
            end="-",
            join_wrapped=True,
            preserve_trailing=False,
            trim_trailing=False,
        )
    )


def _pane_for_session(tmux_session_name: str) -> Pane:
    """Resolve the primary pane for one single-pane tmux session."""

    session = Server().sessions.get(default=None, session_name=tmux_session_name)
    if session is None:
        raise RuntimeError(f"tmux session not found: {tmux_session_name}")
    if not session.windows:
        raise RuntimeError(f"tmux session has no windows: {tmux_session_name}")
    if not session.windows[0].panes:
        raise RuntimeError(f"tmux session has no panes: {tmux_session_name}")
    return session.windows[0].panes[0]


def _build_summary(
    *,
    output_root: Path,
    terminal_id: str,
    path_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Correlate trace streams into one explicit path-by-path summary."""

    events_dir = (output_root / "events").resolve()
    all_events = _load_events(events_dir)
    path_summaries: list[dict[str, Any]] = []
    direct_tmux_root_cause: str | None = None
    for path_result in path_results:
        filtered = _filter_events_for_path(
            events=all_events,
            terminal_id=terminal_id,
            window_start_monotonic=float(path_result["window_start_monotonic"]),
            window_end_monotonic=float(path_result["window_end_monotonic"]),
        )
        prompt_submission_recorded = _event_count(
            filtered,
            stream="service-prompt-submission",
            event_type="note_prompt_submission_recorded",
        )
        turn_anchor_events = [
            event
            for event in filtered
            if event["stream"] == "tracker-anchor" and event["event_type"] == "turn_anchor_armed"
        ]
        reduction_states = _ordered_unique(
            [
                str(event["data"].get("completion_state"))
                for event in filtered
                if event["stream"] == "tracker-reduction" and "completion_state" in event["data"]
            ]
        )
        transition_publications = [
            event
            for event in filtered
            if event["stream"] == "tracker-transition"
            and event["event_type"] == "transition_published"
        ]
        path_summary = {
            **path_result,
            "app_input_requests": _event_count(
                filtered,
                stream="app-input",
                event_type="route_input_request",
            ),
            "service_prompt_submission_recorded": prompt_submission_recorded,
            "turn_anchor_armed_count": len(turn_anchor_events),
            "turn_anchor_sources": _ordered_unique(
                [str(event["data"].get("source")) for event in turn_anchor_events]
            ),
            "reduction_progression": reduction_states,
            "transition_publication_count": len(transition_publications),
            "transition_changed_fields": _ordered_unique(
                [
                    field
                    for event in transition_publications
                    for field in event["data"].get("changed_fields", [])
                    if isinstance(field, str)
                ]
            ),
            "path_worked": bool(
                reduction_states
                and any(
                    state in {"in_progress", "candidate_complete", "completed"}
                    for state in reduction_states
                )
                and transition_publications
            ),
        }
        if path_result["path_id"] == "direct-tmux":
            if (
                prompt_submission_recorded == 0
                and "surface_inference" in path_summary["turn_anchor_sources"]
            ):
                direct_tmux_root_cause = (
                    "Direct tmux input bypassed the server /terminals/{id}/input route, so "
                    "no server-owned prompt submission was recorded. Before the fix, that left "
                    "the session on unanchored background reduction and suppressed candidate/"
                    "completed lifecycle transitions."
                )
            elif prompt_submission_recorded == 0 and not turn_anchor_events:
                direct_tmux_root_cause = (
                    "Direct tmux input bypassed the server prompt-submission hook and no fallback "
                    "anchor was armed."
                )
        path_summaries.append(path_summary)

    return {
        "events_dir": str(events_dir),
        "paths": path_summaries,
        "first_failing_stage_in_original_bug": "prompt_submission_signal_missing_for_direct_tmux",
        "root_cause": direct_tmux_root_cause,
    }


def _summary_markdown(summary_payload: dict[str, Any]) -> str:
    """Render one concise markdown summary for the run."""

    lines = [
        "# Tracking Debug Summary",
        "",
        f"- Events: `{summary_payload['events_dir']}`",
        f"- First failing stage in original bug: `{summary_payload['first_failing_stage_in_original_bug']}`",
    ]
    root_cause = summary_payload.get("root_cause")
    if root_cause:
        lines.append(f"- Root cause: {root_cause}")
    lines.append("")
    for path_payload in summary_payload["paths"]:
        lines.extend(
            [
                f"## {path_payload['path_id']}",
                "",
                f"- Prompt source: `{path_payload['prompt_source']}`",
                f"- App input requests: `{path_payload['app_input_requests']}`",
                f"- Service prompt submission recorded: `{path_payload['service_prompt_submission_recorded']}`",
                f"- Turn anchor sources: `{', '.join(path_payload['turn_anchor_sources']) or 'none'}`",
                f"- Reduction progression: `{', '.join(path_payload['reduction_progression']) or 'none'}`",
                f"- Transition publication count: `{path_payload['transition_publication_count']}`",
                f"- Path worked: `{path_payload['path_worked']}`",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def _load_events(events_dir: Path) -> list[dict[str, Any]]:
    """Load every emitted tracking event from one run."""

    payloads: list[dict[str, Any]] = []
    if not events_dir.exists():
        return payloads
    for path in sorted(events_dir.glob("*.ndjson")):
        stream = path.stem
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            payload["stream"] = stream
            payloads.append(payload)
    payloads.sort(key=lambda item: int(item.get("event_id", 0)))
    return payloads


def _filter_events_for_path(
    *,
    events: list[dict[str, Any]],
    terminal_id: str,
    window_start_monotonic: float,
    window_end_monotonic: float,
) -> list[dict[str, Any]]:
    """Return one path-scoped event slice around the prompt window."""

    lower_bound = window_start_monotonic - 0.5
    upper_bound = window_end_monotonic + 0.5
    filtered: list[dict[str, Any]] = []
    for event in events:
        event_terminal = event.get("terminal_id")
        monotonic_ts = event.get("monotonic_ts")
        if event_terminal not in {terminal_id, None}:
            continue
        if not isinstance(monotonic_ts, (float, int)):
            continue
        if lower_bound <= float(monotonic_ts) <= upper_bound:
            filtered.append(event)
    return filtered


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with deterministic formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_timeline(
    path: Path,
    states: list[tuple[float, HoumaoTerminalStateResponse]],
    *,
    before_monotonic: float,
) -> None:
    """Persist one sampled terminal-state timeline as NDJSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for sample_monotonic, state in states:
            payload = state.model_dump(mode="json")
            handle.write(
                json.dumps(
                    {
                        "sampled_at_utc": datetime.now(UTC).isoformat(timespec="milliseconds"),
                        "elapsed_since_prompt_seconds": max(
                            sample_monotonic - before_monotonic, 0.0
                        ),
                        "tracked_state": payload,
                    },
                    sort_keys=True,
                )
                + "\n"
            )


def _projection_text(state: HoumaoTerminalStateResponse) -> str | None:
    """Return one normalized projection text from a tracked state."""

    if state.parsed_surface is None:
        return None
    return state.parsed_surface.normalized_projection_text


def _sha1_text(value: str | None) -> str | None:
    """Return the SHA-1 digest for one optional text."""

    if value is None:
        return None
    import hashlib

    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _event_count(
    events: list[dict[str, Any]],
    *,
    stream: str,
    event_type: str,
) -> int:
    """Count matching events in one filtered window."""

    return sum(
        1 for event in events if event["stream"] == stream and event["event_type"] == event_type
    )


def _ordered_unique(values: list[str]) -> list[str]:
    """Return one ordered unique list without empty entries."""

    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _default_output_root(repo_root: Path) -> Path:
    """Return one default run-scoped output root under `tmp/`."""

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return (repo_root / "tmp" / "houmao-server-tracking-debug" / stamp).resolve()


@contextmanager
def _temporary_env(name: str, value: str) -> Iterator[None]:
    """Temporarily set one environment variable."""

    previous = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the tracking-debug runner."""

    parser = argparse.ArgumentParser(
        description="Automatic tracking-debug workflow for the Houmao shadow-watch demo.",
    )
    parser.add_argument("--output-root")
    parser.add_argument("--slot", default="claude", choices=("claude", "codex"))
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=DEFAULT_DEBUG_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--stability-threshold-seconds",
        type=float,
        default=DEFAULT_DEBUG_STABILITY_THRESHOLD_SECONDS,
    )
    parser.add_argument(
        "--completion-stability-seconds",
        type=float,
        default=DEFAULT_DEBUG_COMPLETION_STABILITY_SECONDS,
    )
    parser.add_argument(
        "--unknown-to-stalled-timeout-seconds",
        type=float,
        default=DEFAULT_DEBUG_UNKNOWN_TO_STALLED_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--ready-timeout-seconds",
        type=float,
        default=DEFAULT_READY_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--path-timeout-seconds",
        type=float,
        default=DEFAULT_PATH_TIMEOUT_SECONDS,
    )
    parser.add_argument("--server-prompt", default=DEFAULT_SERVER_PROMPT)
    parser.add_argument("--tmux-prompt", default=DEFAULT_TMUX_PROMPT)
    return parser
