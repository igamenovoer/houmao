"""Stepwise command orchestration for the passive-server parallel validation demo pack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.models import (
    CURRENT_RUN_ROOT_FILENAME,
    DEFAULT_AUTOTEST_OUTPUTS_DIRNAME,
    DEFAULT_DEMO_PACK_DIRNAME,
    DEFAULT_EXPECTED_REPORT_RELATIVE_PATH,
    DEFAULT_OUTPUTS_DIRNAME,
    DEFAULT_RUNS_DIRNAME,
    DemoPackPaths,
    PersistedDemoState,
)
from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.provisioning import (
    ParallelConfig,
    SuiteError,
    build_suite_paths,
    capture_gateway_phase,
    capture_headless_phase,
    capture_inspect_phase,
    capture_stop_phase,
    load_suite_paths,
    provision_shared_interactive,
    resolve_fixture_paths,
    run_preflight,
    start_old_server,
    start_passive_server,
    stop_pair_server,
    validate_config,
    _timestamp_slug,
    _utc_now,
    _write_json,
)
from houmao.demo.legacy.passive_server_parallel_validation_demo_pack.reporting import (
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


def default_expected_report_path(pack_dir: Path) -> Path:
    """Return the tracked default expected-report path."""

    return (pack_dir / DEFAULT_EXPECTED_REPORT_RELATIVE_PATH).resolve()


def preflight_demo(
    *,
    pack_paths: DemoPackPaths,
    demo_output_dir: Path,
    config: ParallelConfig,
) -> dict[str, Any]:
    """Run fail-fast preflight checks without starting either authority."""

    validate_config(config)
    if demo_output_dir.exists() and any(demo_output_dir.iterdir()):
        raise SuiteError(f"Demo output root already exists and is not empty: {demo_output_dir}")
    fixtures = resolve_fixture_paths(pack_paths.pack_dir)
    report, credential_env, missing = run_preflight(config=config, fixtures=fixtures)
    payload = {
        **report,
        "pack_dir": str(pack_paths.pack_dir),
        "demo_output_dir": str(demo_output_dir),
        "credential_env": dict(credential_env),
    }
    if missing:
        raise SuiteError("Parallel validation preflight failed:\n- " + "\n- ".join(missing))
    return payload


def start_demo(
    *,
    pack_paths: DemoPackPaths,
    demo_output_dir: Path,
    config: ParallelConfig,
) -> dict[str, Any]:
    """Start both authorities and provision the shared interactive validation agent."""

    validate_config(config)
    fixtures = resolve_fixture_paths(pack_paths.pack_dir)
    run_slug = _timestamp_slug()
    paths = build_suite_paths(
        pack_dir=fixtures.pack_dir,
        output_root=demo_output_dir,
        run_slug=run_slug,
    )
    preflight_report, credential_env, missing = run_preflight(config=config, fixtures=fixtures)
    _write_json(paths.control_dir / "preflight.json", preflight_report)
    if missing:
        raise SuiteError("Parallel validation preflight failed:\n- " + "\n- ".join(missing))

    old_server_info: dict[str, Any] | None = None
    passive_server_info: dict[str, Any] | None = None
    controller = None
    try:
        old_server_info = start_old_server(
            config=config,
            fixtures=fixtures,
            paths=paths,
            credential_env=credential_env,
        )
        passive_server_info = start_passive_server(
            config=config,
            fixtures=fixtures,
            paths=paths,
            credential_env=credential_env,
        )
        controller, shared_agent = provision_shared_interactive(
            config=config,
            fixtures=fixtures,
            paths=paths,
            credential_env=credential_env,
            run_slug=run_slug,
        )
    except Exception as exc:
        if controller is not None:
            try:
                controller.stop(force_cleanup=True)
            except Exception:
                pass
        if passive_server_info is not None:
            stop_pair_server(server_info=passive_server_info, timeout_seconds=5.0)
        if old_server_info is not None:
            stop_pair_server(server_info=old_server_info, timeout_seconds=5.0)
        raise SuiteError(str(exc)) from exc

    state = PersistedDemoState(
        active=True,
        repo_root=str(pack_paths.repo_root),
        pack_dir=str(pack_paths.pack_dir),
        run_root=str(paths.run_root),
        provider=config.provider,
        tool=shared_agent["tool"],
        agent_profile=shared_agent["agent_profile"],
        agent_def_dir=str(fixtures.agent_def_dir),
        started_at_utc=_utc_now(),
        updated_at_utc=_utc_now(),
        steps={"start": True},
        config={
            "provider": config.provider,
            "health_timeout_seconds": config.health_timeout_seconds,
            "discovery_timeout_seconds": config.discovery_timeout_seconds,
            "request_timeout_seconds": config.request_timeout_seconds,
            "request_poll_interval_seconds": config.request_poll_interval_seconds,
            "history_limit": config.history_limit,
            "compat_shell_ready_timeout_seconds": config.compat_shell_ready_timeout_seconds,
            "compat_provider_ready_timeout_seconds": config.compat_provider_ready_timeout_seconds,
            "compat_codex_warmup_seconds": config.compat_codex_warmup_seconds,
            "ports": {
                "old_server": config.old_server_port,
                "passive_server": config.passive_server_port,
            },
            "roots": {
                "shared_runtime_root": str(paths.shared_runtime_root),
                "registry_root": str(paths.registry_root),
                "jobs_root": str(paths.jobs_root),
            },
        },
        preflight={**preflight_report, "credential_env": dict(credential_env)},
        authorities={
            "old_server": old_server_info,
            "passive_server": passive_server_info,
        },
        shared_agent=shared_agent,
    )
    save_demo_state(paths.state_path, state)
    _write_current_run_root(pack_paths.current_run_root_path, paths.run_root)
    payload = {
        "status": "ok",
        "run_root": str(paths.run_root),
        "shared_agent": shared_agent,
        "authorities": {
            "old_server": {
                "api_base_url": old_server_info["api_base_url"],
                "houmao_service": old_server_info["houmao_service"],
            },
            "passive_server": {
                "api_base_url": passive_server_info["api_base_url"],
                "houmao_service": passive_server_info["houmao_service"],
            },
        },
    }
    _write_json(paths.control_dir / "start.json", payload)
    return payload


def inspect_demo(
    *,
    demo_output_dir: Path,
    history_limit: int,
) -> dict[str, Any]:
    """Compare shared interactive managed views across the two authorities."""

    paths = load_suite_paths(demo_output_dir)
    state = _require_active_state(load_demo_state(paths.state_path), command_name="inspect")
    result = capture_inspect_phase(state=state.to_payload(), paths=paths, history_limit=history_limit)
    state.inspect_result = result
    state.steps["inspect"] = bool(result.get("ok"))
    state.updated_at_utc = _utc_now()
    save_demo_state(paths.state_path, state)
    if not bool(result.get("ok")):
        raise SuiteError("Shared interactive parity comparison failed; inspect phase evidence preserved.")
    return result


def gateway_demo(
    *,
    demo_output_dir: Path,
) -> dict[str, Any]:
    """Attach a gateway locally and exercise the passive-server gateway proxy phase."""

    paths = load_suite_paths(demo_output_dir)
    state = _require_active_state(load_demo_state(paths.state_path), command_name="gateway")
    fixtures = resolve_fixture_paths(Path(state.pack_dir))
    gateway_prompt_text = fixtures.gateway_prompt_path.read_text(encoding="utf-8").strip()
    result = capture_gateway_phase(
        state=state.to_payload(),
        paths=paths,
        gateway_prompt_text=gateway_prompt_text,
        history_limit=int(state.config["history_limit"]),
    )
    state.gateway_result = result
    state.shared_agent["gateway_attached"] = True
    state.steps["gateway"] = bool(result.get("ok"))
    state.updated_at_utc = _utc_now()
    save_demo_state(paths.state_path, state)
    if not bool(result.get("ok")):
        raise SuiteError("Gateway phase did not observe progress on both authorities.")
    return result


def headless_demo(
    *,
    demo_output_dir: Path,
) -> dict[str, Any]:
    """Launch one passive headless agent and verify old-server visibility."""

    paths = load_suite_paths(demo_output_dir)
    state = _require_active_state(load_demo_state(paths.state_path), command_name="headless")
    headless_agent, result = capture_headless_phase(state=state.to_payload(), paths=paths)
    state.headless_agent = headless_agent
    state.headless_result = result
    state.steps["headless"] = bool(result.get("ok"))
    state.updated_at_utc = _utc_now()
    save_demo_state(paths.state_path, state)
    if not bool(result.get("ok")):
        raise SuiteError("Passive headless phase failed; old-server visibility was not confirmed.")
    return {
        **result,
        "headless_agent": headless_agent,
    }


def stop_demo(
    *,
    demo_output_dir: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Stop the shared validation agents and both authorities."""

    paths = load_suite_paths(demo_output_dir)
    state = _require_active_state(load_demo_state(paths.state_path), command_name="stop")
    result = capture_stop_phase(state=state.to_payload(), paths=paths, timeout_seconds=timeout_seconds)
    state.stop_result = result
    state.steps["stop"] = bool(result.get("ok"))
    state.active = False
    state.updated_at_utc = _utc_now()
    save_demo_state(paths.state_path, state)
    if not bool(result.get("ok")):
        raise SuiteError("Stop phase failed; propagation or authority shutdown did not complete cleanly.")
    return result


def verify_demo(
    *,
    demo_output_dir: Path,
    expected_report_path: Path,
    snapshot: bool,
) -> dict[str, Any]:
    """Build, sanitize, and verify the dual-authority report."""

    paths = load_suite_paths(demo_output_dir)
    state = load_demo_state(paths.state_path)
    if state is None:
        raise SuiteError("No demo state was found. Run `start` before `verify`.")

    report = build_report(state_payload=state.to_payload(), report_path=paths.report_path)
    sanitized = sanitize_report(report)
    paths.sanitized_report_path.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if snapshot:
        expected_report_path.parent.mkdir(parents=True, exist_ok=True)
        expected_report_path.write_text(
            json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        verification = {"status": "snapshot-updated"}
    else:
        expected = json.loads(expected_report_path.read_text(encoding="utf-8"))
        verify_sanitized_report(sanitized, expected)
        verification = {"status": "passed"}

    state.last_verify_result = {
        "report_path": str(paths.report_path),
        "sanitized_report_path": str(paths.sanitized_report_path),
        "expected_report_path": str(expected_report_path),
        **verification,
    }
    state.steps["verify"] = verification["status"] in {"passed", "snapshot-updated"}
    state.updated_at_utc = _utc_now()
    save_demo_state(paths.state_path, state)
    return dict(state.last_verify_result)


def auto_demo(
    *,
    pack_paths: DemoPackPaths,
    demo_output_dir: Path,
    config: ParallelConfig,
    expected_report_path: Path,
    snapshot: bool,
) -> dict[str, Any]:
    """Run the full Step 7 workflow end to end."""

    start_payload = start_demo(
        pack_paths=pack_paths,
        demo_output_dir=demo_output_dir,
        config=config,
    )
    inspect_payload = inspect_demo(
        demo_output_dir=demo_output_dir,
        history_limit=config.history_limit,
    )
    gateway_payload = gateway_demo(demo_output_dir=demo_output_dir)
    headless_payload = headless_demo(demo_output_dir=demo_output_dir)
    stop_payload = stop_demo(
        demo_output_dir=demo_output_dir,
        timeout_seconds=10.0,
    )
    verify_payload = verify_demo(
        demo_output_dir=demo_output_dir,
        expected_report_path=expected_report_path,
        snapshot=snapshot,
    )
    return {
        "status": "ok",
        "start": start_payload,
        "inspect": inspect_payload,
        "gateway": gateway_payload,
        "headless": headless_payload,
        "stop": stop_payload,
        "verify": verify_payload,
    }


def _require_active_state(
    state: PersistedDemoState | None, *, command_name: str
) -> PersistedDemoState:
    """Require one active persisted demo state."""

    if state is None:
        raise SuiteError(f"No demo state was found. Run `start` before `{command_name}`.")
    if not state.active:
        raise SuiteError(
            f"The selected demo state is inactive. Run `start` before `{command_name}`."
        )
    return state
