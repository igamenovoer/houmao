"""Stepwise command orchestration for the agent API demo pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from houmao.server.client import HoumaoServerClient

from houmao.demo.houmao_server_agent_api_demo_pack.models import (
    DEFAULT_AUTOTEST_OUTPUTS_DIRNAME,
    CURRENT_RUN_ROOT_FILENAME,
    DEFAULT_DEMO_PACK_DIRNAME,
    DEFAULT_EXPECTED_REPORT_RELATIVE_PATH,
    DEFAULT_INTERRUPT_PROMPT_FILENAME,
    DEFAULT_OUTPUTS_DIRNAME,
    DEFAULT_PROMPT_FILENAME,
    DEFAULT_RUNS_DIRNAME,
    DemoPackPaths,
    PersistedDemoState,
)
from houmao.demo.houmao_server_agent_api_demo_pack.provisioning import (
    DEFAULT_HISTORY_LIMIT,
    ArtifactRecorder,
    LaneRuntime,
    SuiteConfig,
    SuiteError,
    _build_suite_paths,
    _cleanup_lanes,
    _prepare_lane_runtimes,
    _provision_lane,
    _record_route_call,
    _resolve_fixture_paths,
    _resolve_selected_lanes,
    _run_preflight,
    _start_suite_server,
    _stop_suite_server,
    _submit_interrupt_and_verify,
    _submit_prompt_and_verify,
    _timestamp_slug,
    _utc_now,
    _validate_config,
    _verify_lane_routes,
    _verify_shared_routes,
    _write_json,
    load_suite_paths,
)
from houmao.demo.houmao_server_agent_api_demo_pack.reporting import (
    build_report,
    sanitize_report,
    verify_sanitized_report,
)


def resolve_repo_root(repo_root: Path | None = None) -> Path:
    """Resolve the repository root for the demo pack."""

    if repo_root is not None:
        return repo_root.resolve()
    return Path(__file__).resolve().parents[4]


def resolve_pack_paths(
    *,
    repo_root: Path | None = None,
    pack_dir: Path | None = None,
) -> DemoPackPaths:
    """Resolve the pack directory and output-root metadata."""

    resolved_repo_root = resolve_repo_root(repo_root)
    resolved_pack_dir = (
        pack_dir.resolve()
        if pack_dir is not None
        else (resolved_repo_root / "scripts" / "demo" / DEFAULT_DEMO_PACK_DIRNAME).resolve()
    )
    outputs_dir = (resolved_pack_dir / DEFAULT_OUTPUTS_DIRNAME).resolve()
    runs_dir = (outputs_dir / DEFAULT_RUNS_DIRNAME).resolve()
    autotest_outputs_dir = (outputs_dir / DEFAULT_AUTOTEST_OUTPUTS_DIRNAME).resolve()
    return DemoPackPaths(
        repo_root=resolved_repo_root,
        pack_dir=resolved_pack_dir,
        outputs_dir=outputs_dir,
        runs_dir=runs_dir,
        autotest_outputs_dir=autotest_outputs_dir,
        current_run_root_path=(outputs_dir / CURRENT_RUN_ROOT_FILENAME).resolve(),
    )


def resolve_demo_output_dir(
    *,
    command_name: str,
    pack_paths: DemoPackPaths,
    raw_demo_output_dir: Path | None,
) -> Path:
    """Resolve the selected demo output root for one command."""

    if raw_demo_output_dir is not None:
        if raw_demo_output_dir.is_absolute():
            return raw_demo_output_dir.resolve()
        return (pack_paths.repo_root / raw_demo_output_dir).resolve()
    if command_name in {"start", "auto"}:
        return (pack_paths.runs_dir / _timestamp_slug()).resolve()
    current = _read_current_run_root(pack_paths.current_run_root_path)
    if current is not None:
        return current
    latest = _latest_demo_run_root(pack_paths.runs_dir)
    if latest is not None:
        return latest
    raise SuiteError(
        "No current demo run was found. Run `start` or provide `--demo-output-dir` first."
    )


def _read_current_run_root(path: Path) -> Path | None:
    """Load the current run-root pointer when it exists."""

    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    candidate = Path(raw).expanduser()
    return candidate.resolve() if candidate.exists() else None


def _write_current_run_root(path: Path, run_root: Path) -> None:
    """Persist the current run-root pointer."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(run_root.resolve()) + "\n", encoding="utf-8")


def _latest_demo_run_root(runs_dir: Path) -> Path | None:
    """Return the most recent generated run root under the pack outputs directory."""

    if not runs_dir.is_dir():
        return None
    candidates = [path for path in runs_dir.iterdir() if path.is_dir()]
    if not candidates:
        return None
    return sorted(candidates)[-1].resolve()


def load_demo_state(path: Path) -> PersistedDemoState | None:
    """Load the persisted demo state when it exists."""

    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SuiteError(f"Invalid demo state JSON object: {path}")
    return PersistedDemoState.from_payload(payload)


def save_demo_state(path: Path, state: PersistedDemoState) -> None:
    """Persist one demo state payload."""

    _write_json(path, state.to_payload())


def _state_path(run_root: Path) -> Path:
    """Return the persisted demo-state path for one run root."""

    return (run_root.resolve() / "control" / "demo_state.json").resolve()


def _existing_artifact_recorder(root: Path) -> ArtifactRecorder:
    """Create one recorder that appends after existing JSON snapshots."""

    next_index = 1
    if root.is_dir():
        next_index = len(sorted(root.glob("*.json"))) + 1
    return ArtifactRecorder(root=root.resolve(), next_index=next_index)


def _restore_lane_runtimes(
    *,
    state: PersistedDemoState,
) -> list[LaneRuntime]:
    """Rebuild lane runtime objects from persisted state."""

    restored: list[LaneRuntime] = []
    definitions = {
        lane.lane_id: lane for lane in _resolve_selected_lanes(tuple(state.selected_lane_ids))
    }
    for lane_id in state.selected_lane_ids:
        lane_payload = dict(state.lanes.get(lane_id, {}))
        if lane_id not in definitions:
            raise SuiteError(f"Persisted state references unknown lane `{lane_id}`.")
        lane_root = Path(str(lane_payload.get("lane_root"))).resolve()
        workdir = Path(str(lane_payload.get("workdir"))).resolve()
        runtime = LaneRuntime(
            definition=definitions[lane_id],
            lane_root=lane_root,
            workdir=workdir,
            http_recorder=_existing_artifact_recorder((lane_root / "http").resolve()),
        )
        runtime.requested_session_name = lane_payload.get("requested_session_name")
        runtime.requested_agent_name = lane_payload.get("requested_agent_name")
        runtime.requested_agent_id = lane_payload.get("requested_agent_id")
        runtime.session_name = lane_payload.get("session_name")
        runtime.terminal_id = lane_payload.get("terminal_id")
        runtime.tmux_window_name = lane_payload.get("tmux_window_name")
        runtime.tracked_agent_id = lane_payload.get("tracked_agent_id")
        runtime.manifest_path = lane_payload.get("manifest_path")
        runtime.session_root = lane_payload.get("session_root")
        runtime.launch_metadata = lane_payload.get("launch_metadata")
        runtime.route_verification = lane_payload.get("route_verification")
        runtime.prompt_verification = lane_payload.get("prompt_verification")
        runtime.interrupt_verification = lane_payload.get("interrupt_verification")
        runtime.stop_result = lane_payload.get("stop_result")
        restored.append(runtime)
    return restored


def _state_from_runtime(
    *,
    state: PersistedDemoState,
    lane_runtimes: list[LaneRuntime],
) -> PersistedDemoState:
    """Return one updated state with current lane runtime summaries."""

    state.lanes = {lane.definition.lane_id: lane.summary_payload() for lane in lane_runtimes}
    state.updated_at_utc = _utc_now()
    return state


def _require_active_state(state: PersistedDemoState | None, *, command_name: str) -> PersistedDemoState:
    """Require one active persisted demo state."""

    if state is None:
        raise SuiteError(f"No demo state was found. Run `start` before `{command_name}`.")
    if not state.active:
        raise SuiteError(
            f"The selected demo state is inactive. Run `start` before `{command_name}`."
        )
    return state


def _config_payload(config: SuiteConfig, *, pack_dir: Path, demo_output_dir: Path) -> dict[str, Any]:
    """Build one JSON-ready config payload for the run root."""

    return {
        "pack_dir": str(pack_dir.resolve()),
        "output_root": str(demo_output_dir.resolve()),
        "selected_lane_ids": list(config.selected_lane_ids),
        "port": config.port,
        "compat_http_timeout_seconds": config.compat_http_timeout_seconds,
        "compat_create_timeout_seconds": config.compat_create_timeout_seconds,
        "compat_provider_ready_timeout_seconds": config.compat_provider_ready_timeout_seconds,
        "health_timeout_seconds": config.health_timeout_seconds,
        "prompt_timeout_seconds": config.prompt_timeout_seconds,
        "prompt_poll_interval_seconds": config.prompt_poll_interval_seconds,
        "history_limit": config.history_limit,
    }


def _default_prompt_path(pack_dir: Path) -> Path:
    """Return the tracked default prompt fixture path."""

    return (pack_dir / "inputs" / DEFAULT_PROMPT_FILENAME).resolve()


def _default_interrupt_prompt_path(pack_dir: Path) -> Path:
    """Return the tracked default interrupt prompt fixture path."""

    return (pack_dir / "inputs" / DEFAULT_INTERRUPT_PROMPT_FILENAME).resolve()


def _load_prompt_text(
    *,
    pack_dir: Path,
    prompt: str | None,
    prompt_file: Path | None,
    default_path: Path,
) -> str | None:
    """Resolve one prompt text value from inline text, file, or tracked default."""

    if prompt is not None:
        stripped = prompt.strip()
        if not stripped:
            raise SuiteError("Prompt text must not be empty.")
        return stripped
    if prompt_file is not None:
        text = prompt_file.read_text(encoding="utf-8").strip()
        if not text:
            raise SuiteError(f"Prompt file is empty: {prompt_file}")
        return text
    if default_path.is_file():
        text = default_path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def preflight_demo(
    *,
    pack_paths: DemoPackPaths,
    demo_output_dir: Path,
    config: SuiteConfig,
) -> dict[str, Any]:
    """Run fail-fast preflight checks without starting the owned server."""

    _validate_config(config)
    if demo_output_dir.exists() and any(demo_output_dir.iterdir()):
        raise SuiteError(f"Demo output root already exists and is not empty: {demo_output_dir}")
    fixtures = _resolve_fixture_paths(pack_paths.pack_dir)
    selected_lanes = _resolve_selected_lanes(config.selected_lane_ids)
    report, _credential_env, missing = _run_preflight(
        fixtures=fixtures,
        selected_lanes=selected_lanes,
    )
    payload = {
        **report,
        "pack_dir": str(pack_paths.pack_dir),
        "demo_output_dir": str(demo_output_dir.resolve()),
        "output_root_safe": True,
    }
    if missing:
        raise SuiteError("Live-suite preflight failed before server startup:\n- " + "\n- ".join(missing))
    return payload


def start_demo(
    *,
    pack_paths: DemoPackPaths,
    demo_output_dir: Path,
    config: SuiteConfig,
) -> dict[str, Any]:
    """Start the owned server and provision the selected managed-agent lanes."""

    _validate_config(config)
    selected_lanes = _resolve_selected_lanes(config.selected_lane_ids)
    fixtures = _resolve_fixture_paths(pack_paths.pack_dir)
    paths = _build_suite_paths(
        pack_dir=pack_paths.pack_dir,
        output_root=demo_output_dir,
        run_slug=_timestamp_slug(),
    )
    suite_http_recorder = ArtifactRecorder(paths.suite_http_dir)
    preflight_report, credential_env, missing = _run_preflight(
        fixtures=fixtures,
        selected_lanes=selected_lanes,
    )
    _write_json(paths.control_dir / "config.json", _config_payload(config, pack_dir=pack_paths.pack_dir, demo_output_dir=paths.run_root))
    _write_json(paths.control_dir / "preflight.json", preflight_report)

    state = PersistedDemoState(
        active=False,
        repo_root=str(pack_paths.repo_root),
        pack_dir=str(pack_paths.pack_dir),
        run_root=str(paths.run_root),
        selected_lane_ids=[lane.lane_id for lane in selected_lanes],
        started_at_utc=_utc_now(),
        updated_at_utc=_utc_now(),
        steps={
            "start_complete": False,
            "inspect_complete": False,
            "prompt_complete": False,
            "interrupt_complete": False,
            "verify_complete": False,
            "stop_complete": False,
        },
        config=_config_payload(config, pack_dir=pack_paths.pack_dir, demo_output_dir=paths.run_root),
        preflight=preflight_report,
    )
    save_demo_state(_state_path(paths.run_root), state)

    if missing:
        raise SuiteError("Live-suite preflight failed before server startup:\n- " + "\n- ".join(missing))

    lane_runtimes = _prepare_lane_runtimes(
        fixtures=fixtures,
        paths=paths,
        selected_lanes=selected_lanes,
        run_slug=_timestamp_slug(),
    )
    server_info: dict[str, Any] | None = None
    client: HoumaoServerClient | None = None
    try:
        server_info = _start_suite_server(
            config=config,
            fixtures=fixtures,
            paths=paths,
            suite_http_recorder=suite_http_recorder,
            credential_env=credential_env,
        )
        client = HoumaoServerClient(
            str(server_info["api_base_url"]),
            timeout_seconds=config.compat_http_timeout_seconds,
            create_timeout_seconds=config.compat_create_timeout_seconds,
        )
        run_slug = Path(str(paths.run_root)).name
        for lane_runtime in lane_runtimes:
            _provision_lane(
                client=client,
                config=config,
                fixtures=fixtures,
                paths=paths,
                server_info=server_info,
                lane_runtime=lane_runtime,
                run_slug=run_slug,
            )
    except Exception as exc:
        state.failure = str(exc)
        _state_from_runtime(state=state, lane_runtimes=lane_runtimes)
        save_demo_state(_state_path(paths.run_root), state)
        cleanup_results = _cleanup_lanes(client=client, lane_runtimes=lane_runtimes)
        shutdown_result = _stop_suite_server(server_info, timeout_seconds=10.0)
        _write_json(paths.server_dir / "shutdown.json", shutdown_result)
        _write_json(paths.control_dir / "stop_result.json", {"lanes": cleanup_results, "server": shutdown_result})
        raise SuiteError(str(exc)) from exc

    state.active = True
    state.server = dict(server_info)
    state.steps["start_complete"] = True
    _state_from_runtime(state=state, lane_runtimes=lane_runtimes)
    save_demo_state(_state_path(paths.run_root), state)
    _write_current_run_root(pack_paths.current_run_root_path, paths.run_root)
    return state.to_payload()


def inspect_demo(
    *,
    demo_output_dir: Path,
    history_limit: int | None = None,
    with_dialog_tail: int | None = None,
) -> dict[str, Any]:
    """Verify shared and per-lane state routes for the selected run."""

    state_path = _state_path(demo_output_dir)
    state = _require_active_state(load_demo_state(state_path), command_name="inspect")
    paths = load_suite_paths(Path(state.run_root))
    lane_runtimes = _restore_lane_runtimes(state=state)
    config_history_limit = int(state.config.get("history_limit", DEFAULT_HISTORY_LIMIT))
    resolved_history_limit = history_limit if history_limit is not None else config_history_limit
    client = HoumaoServerClient(
        str(state.server["api_base_url"]),
        timeout_seconds=float(state.config.get("compat_http_timeout_seconds", 20.0)),
        create_timeout_seconds=float(state.config.get("compat_create_timeout_seconds", 90.0)),
    )
    shared_routes = _verify_shared_routes(
        client=client,
        suite_http_recorder=_existing_artifact_recorder(paths.suite_http_dir),
        lane_runtimes=lane_runtimes,
        history_limit=resolved_history_limit,
    )
    for lane_runtime in lane_runtimes:
        _verify_lane_routes(
            client=client,
            lane_runtime=lane_runtime,
            history_limit=resolved_history_limit,
        )
        if with_dialog_tail is not None and lane_runtime.definition.transport == "tui":
            if lane_runtime.terminal_id is None:
                continue
            terminal_state = _record_route_call(
                recorder=lane_runtime.http_recorder,
                label="get-terminal-state",
                method="GET",
                path=f"/houmao/terminals/{lane_runtime.terminal_id}/state",
                request_payload=None,
                callback=lambda terminal_id=lane_runtime.terminal_id: client.terminal_state(terminal_id),
            )
            dialog_tail = ""
            parsed_surface = getattr(terminal_state, "parsed_surface", None)
            if parsed_surface is not None:
                tail_value = getattr(parsed_surface, "dialog_tail", "")
                dialog_tail = str(tail_value)[-with_dialog_tail:]
            route_verification = lane_runtime.route_verification or {}
            route_verification["terminal_state"] = terminal_state.model_dump(mode="json")
            route_verification["dialog_tail"] = dialog_tail
            lane_runtime.route_verification = route_verification
            _write_json(
                lane_runtime.lane_root / "route-verification.json",
                lane_runtime.route_verification,
            )
    _write_json(paths.control_dir / "shared_routes.json", shared_routes)
    state.shared_routes = shared_routes
    state.steps["inspect_complete"] = True
    _state_from_runtime(state=state, lane_runtimes=lane_runtimes)
    save_demo_state(state_path, state)
    return {
        "run_root": str(paths.run_root),
        "shared_routes": shared_routes,
        "lanes": {lane.definition.lane_id: lane.route_verification for lane in lane_runtimes},
    }


def prompt_demo(
    *,
    pack_dir: Path,
    demo_output_dir: Path,
    prompt: str | None,
    prompt_file: Path | None,
    lane_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Submit one prompt to the selected active lanes and record state evidence."""

    state_path = _state_path(demo_output_dir)
    state = _require_active_state(load_demo_state(state_path), command_name="prompt")
    lane_runtimes = _restore_lane_runtimes(state=state)
    requested_lane_ids = set(lane_ids) if lane_ids else set(state.selected_lane_ids)
    prompt_text = _load_prompt_text(
        pack_dir=pack_dir,
        prompt=prompt,
        prompt_file=prompt_file,
        default_path=_default_prompt_path(pack_dir),
    )
    config = SuiteConfig(
        selected_lane_ids=tuple(state.selected_lane_ids),
        pack_dir=Path(state.pack_dir),
        output_root=Path(state.run_root),
        port=None,
        compat_http_timeout_seconds=float(state.config.get("compat_http_timeout_seconds", 20.0)),
        compat_create_timeout_seconds=float(state.config.get("compat_create_timeout_seconds", 90.0)),
        compat_provider_ready_timeout_seconds=float(
            state.config.get("compat_provider_ready_timeout_seconds", 90.0)
        ),
        health_timeout_seconds=float(state.config.get("health_timeout_seconds", 30.0)),
        prompt_timeout_seconds=float(state.config.get("prompt_timeout_seconds", 120.0)),
        prompt_poll_interval_seconds=float(
            state.config.get("prompt_poll_interval_seconds", 2.0)
        ),
        history_limit=int(state.config.get("history_limit", DEFAULT_HISTORY_LIMIT)),
    )
    client = HoumaoServerClient(
        str(state.server["api_base_url"]),
        timeout_seconds=config.compat_http_timeout_seconds,
        create_timeout_seconds=config.compat_create_timeout_seconds,
    )
    targeted: list[str] = []
    for lane_runtime in lane_runtimes:
        if lane_runtime.definition.lane_id not in requested_lane_ids:
            continue
        _submit_prompt_and_verify(
            client=client,
            config=config,
            lane_runtime=lane_runtime,
            prompt_text=prompt_text,
        )
        targeted.append(lane_runtime.definition.lane_id)
    state.steps["prompt_complete"] = True
    _state_from_runtime(state=state, lane_runtimes=lane_runtimes)
    save_demo_state(state_path, state)
    return {
        "run_root": str(Path(state.run_root).resolve()),
        "targeted_lanes": targeted,
        "lanes": {lane.definition.lane_id: lane.prompt_verification for lane in lane_runtimes if lane.definition.lane_id in requested_lane_ids},
    }


def interrupt_demo(
    *,
    pack_dir: Path,
    demo_output_dir: Path,
    lane_ids: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Submit one interrupt to the selected active lanes and record follow-up evidence."""

    del pack_dir
    state_path = _state_path(demo_output_dir)
    state = _require_active_state(load_demo_state(state_path), command_name="interrupt")
    lane_runtimes = _restore_lane_runtimes(state=state)
    requested_lane_ids = set(lane_ids) if lane_ids else set(state.selected_lane_ids)
    config = SuiteConfig(
        selected_lane_ids=tuple(state.selected_lane_ids),
        pack_dir=Path(state.pack_dir),
        output_root=Path(state.run_root),
        compat_http_timeout_seconds=float(state.config.get("compat_http_timeout_seconds", 20.0)),
        compat_create_timeout_seconds=float(state.config.get("compat_create_timeout_seconds", 90.0)),
        compat_provider_ready_timeout_seconds=float(
            state.config.get("compat_provider_ready_timeout_seconds", 90.0)
        ),
        health_timeout_seconds=float(state.config.get("health_timeout_seconds", 30.0)),
        prompt_timeout_seconds=float(state.config.get("prompt_timeout_seconds", 120.0)),
        prompt_poll_interval_seconds=float(
            state.config.get("prompt_poll_interval_seconds", 2.0)
        ),
        history_limit=int(state.config.get("history_limit", DEFAULT_HISTORY_LIMIT)),
    )
    client = HoumaoServerClient(
        str(state.server["api_base_url"]),
        timeout_seconds=config.compat_http_timeout_seconds,
        create_timeout_seconds=config.compat_create_timeout_seconds,
    )
    targeted: list[str] = []
    for lane_runtime in lane_runtimes:
        if lane_runtime.definition.lane_id not in requested_lane_ids:
            continue
        _submit_interrupt_and_verify(
            client=client,
            config=config,
            lane_runtime=lane_runtime,
        )
        targeted.append(lane_runtime.definition.lane_id)
    state.steps["interrupt_complete"] = True
    _state_from_runtime(state=state, lane_runtimes=lane_runtimes)
    save_demo_state(state_path, state)
    return {
        "run_root": str(Path(state.run_root).resolve()),
        "targeted_lanes": targeted,
        "lanes": {lane.definition.lane_id: lane.interrupt_verification for lane in lane_runtimes if lane.definition.lane_id in requested_lane_ids},
    }


def verify_demo(
    *,
    demo_output_dir: Path,
    expected_report_path: Path,
    snapshot: bool,
) -> dict[str, Any]:
    """Build, sanitize, and verify the report contract for one run root."""

    state_path = _state_path(demo_output_dir)
    state = load_demo_state(state_path)
    if state is None:
        raise SuiteError("No demo state was found. Run `start` before `verify`.")
    control_dir = load_suite_paths(Path(state.run_root)).control_dir
    report_path = (control_dir / "report.json").resolve()
    sanitized_report_path = (control_dir / "report.sanitized.json").resolve()
    verify_result_path = (control_dir / "verify_result.json").resolve()

    state.steps["verify_complete"] = True
    state.updated_at_utc = _utc_now()
    save_demo_state(state_path, state)
    report = build_report(state_payload=state.to_payload(), report_path=report_path)
    sanitized = sanitize_report(report)
    _write_json(sanitized_report_path, sanitized)

    if snapshot:
        expected_report_path.parent.mkdir(parents=True, exist_ok=True)
        expected_report_path.write_text(
            json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        if not expected_report_path.is_file():
            raise SuiteError(
                "Expected report is missing. Run `verify --snapshot-report` to create it: "
                f"{expected_report_path}"
            )
        expected_payload = json.loads(expected_report_path.read_text(encoding="utf-8"))
        if not isinstance(expected_payload, dict):
            raise SuiteError(f"Expected report must be a JSON object: {expected_report_path}")
        verify_sanitized_report(sanitized, expected_payload)

    result = {
        "ok": True,
        "snapshot_updated": snapshot,
        "expected_report_path": str(expected_report_path.resolve()),
        "report_path": str(report_path),
        "sanitized_report_path": str(sanitized_report_path),
    }
    _write_json(verify_result_path, result)
    state.last_verify_result = result
    state.updated_at_utc = _utc_now()
    save_demo_state(state_path, state)
    return result


def stop_demo(
    *,
    demo_output_dir: Path,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Stop all launched lanes and the owned server for one selected run."""

    state_path = _state_path(demo_output_dir)
    state = load_demo_state(state_path)
    if state is None:
        raise SuiteError("No demo state was found. Nothing to stop.")
    paths = load_suite_paths(Path(state.run_root))
    lane_runtimes = _restore_lane_runtimes(state=state)
    client: HoumaoServerClient | None = None
    if state.active and state.server.get("api_base_url"):
        client = HoumaoServerClient(
            str(state.server["api_base_url"]),
            timeout_seconds=float(state.config.get("compat_http_timeout_seconds", 20.0)),
            create_timeout_seconds=float(state.config.get("compat_create_timeout_seconds", 90.0)),
        )
    cleanup_results = _cleanup_lanes(client=client, lane_runtimes=lane_runtimes)
    shutdown_result = _stop_suite_server(state.server, timeout_seconds=timeout_seconds)
    _write_json(paths.server_dir / "shutdown.json", shutdown_result)
    result = {"lanes": cleanup_results, "server_shutdown": shutdown_result}
    _write_json(paths.control_dir / "stop_result.json", result)
    state.active = False
    state.steps["stop_complete"] = True
    state.last_stop_result = result
    _state_from_runtime(state=state, lane_runtimes=lane_runtimes)
    save_demo_state(state_path, state)
    return result


def auto_demo(
    *,
    pack_paths: DemoPackPaths,
    demo_output_dir: Path,
    config: SuiteConfig,
    expected_report_path: Path,
    snapshot: bool,
) -> dict[str, Any]:
    """Run the canonical unattended `start -> inspect -> prompt -> verify -> stop` flow."""

    start_demo(pack_paths=pack_paths, demo_output_dir=demo_output_dir, config=config)
    try:
        inspect_demo(
            demo_output_dir=demo_output_dir,
            history_limit=config.history_limit,
            with_dialog_tail=None,
        )
        prompt_demo(
            pack_dir=pack_paths.pack_dir,
            demo_output_dir=demo_output_dir,
            prompt=None,
            prompt_file=None,
            lane_ids=tuple(),
        )
        verify_result = verify_demo(
            demo_output_dir=demo_output_dir,
            expected_report_path=expected_report_path,
            snapshot=snapshot,
        )
    except Exception:
        try:
            stop_demo(demo_output_dir=demo_output_dir)
        except Exception:
            pass
        raise
    stop_demo(demo_output_dir=demo_output_dir)
    return verify_result


def default_expected_report_path(pack_dir: Path) -> Path:
    """Return the tracked expected-report path for the pack."""

    return (pack_dir / DEFAULT_EXPECTED_REPORT_RELATIVE_PATH).resolve()
