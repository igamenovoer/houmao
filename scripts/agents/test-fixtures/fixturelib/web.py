"""Reuse the owned Web supervisor for raw fixtures and private browser handoff."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.errors import BrainLaunchRuntimeError

from fixturelib.auth import private_write, write_json
from fixturelib.config import FixtureError


def _raw_session(run: dict[str, Any], *, provider_start: bool = False) -> Any:
    """Create or reconstruct exact raw Web authority without a second host implementation."""

    from houmao.agents.dsh_configuration import MATERIALIZED_DSH_TOOL_PARAMS, DshEffectiveToolParams
    from houmao.agents.realm_controller.backends.dsh_web import (
        DshWebSession,
        DshWebSessionState,
    )
    from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan

    from fixturelib.launch import run_environment

    root = Path(run["run_dir"])
    config = run["configuration"]
    role = run["role"]
    home = Path(run["home_path"])
    setup_path = home / MATERIALIZED_DSH_TOOL_PARAMS
    setup = DshEffectiveToolParams.from_file(setup_path)
    plan = LaunchPlan(
        backend="dsh_web",
        tool="dsh",
        executable=run["executable"],
        args=[],
        working_directory=Path(run["workdir"]),
        home_env_var="DSH_HOME",
        home_path=home,
        env=run_environment(run),
        env_var_names=sorted(json.loads((root / "private-env.json").read_text())),
        role_injection=RoleInjectionPlan(
            method="native_system_prompt_section",
            role_name=role,
            prompt=(Path(run["assets_root"]) / "roles" / role / "system-prompt.md").read_text(),
        ),
        native_surface_kind="web",
        metadata={
            "dsh": {
                "setup_path": str(setup_path),
                "model": config["model"],
                "base_url_env": setup.base_url_env,
                "api_key_env": setup.api_key_env,
                "operator_prompt_mode": config.get("operator_prompt_mode", "unattended"),
            },
            "native_surface_kind": "web",
            "env_source_file": str(
                Path(run["assets_root"]) / "tools/dsh/auth/default/env/vars.env"
            ),
        },
    )
    manifest = root / "raw-web/manifest.json"
    if provider_start:
        write_json(
            manifest,
            {
                "schema_version": 1,
                "agent_id": "raw-fixture-" + root.name,
                "backend": "dsh_web",
                "tool": "dsh",
                "registry_generation_id": "raw-generation-" + root.name,
                "runtime": {"session_id": "raw-runtime-" + root.name},
                "working_directory": run["workdir"],
                "launch_plan": plan.redacted_payload(),
                "backend_state": {},
            },
        )
    state_payload = run.get("raw_web_state")
    if not provider_start and not isinstance(state_payload, dict):
        raise FixtureError("Raw Web follow-up requires captured owned host state")
    state = DshWebSessionState.from_payload(state_payload) if state_payload is not None else None
    try:
        return DshWebSession.from_launch_plan(
            launch_plan=plan,
            session_manifest_path=manifest,
            role_name=role,
            state=state,
            agent_def_dir=Path(run["assets_root"]),
            tmux_session_name="fixture-" + root.name,
            provider_start=provider_start,
        )
    except BrainLaunchRuntimeError as exc:
        raise FixtureError("Owned Web authority is unavailable; inspect the private run") from exc


def _capture_state(run: dict[str, Any], session: Any) -> None:
    """Keep credential-bearing references private while publishing native location/identity."""

    run["raw_web_state"] = session.state.to_payload()
    surface = session.state.native_surface
    if surface is None:
        raise FixtureError("Owned Web host did not publish verified native surface metadata")
    run["identity"] = {
        "native_surface": surface.model_dump(mode="json"),
        "provider_session_id": surface.native_session_id,
        "tmux_session_name": session.state.tmux_session_name,
    }


def launch_raw_web(run: dict[str, Any]) -> None:
    """Explicitly start one owned host and release only this control connection."""

    session = _raw_session(run, provider_start=True)
    try:
        _capture_state(run, session)
    finally:
        session.close_control_connection()


def prompt_raw_web(run: dict[str, Any], prompt: str, timeout: float) -> None:
    """Submit once to the captured live session and preserve its native terminal evidence."""

    session = _raw_session(run)
    index = len(run.get("turns", [])) + 1
    try:
        events = list(
            session.send_web_prompt(
                prompt,
                admission_policy="ready_only",
                operator=False,
                timeout_seconds=timeout,
            )
        )
        write_json(
            Path(run["run_dir"]) / "raw-web" / f"turn-{index}.events.json",
            {"events": [asdict(event) for event in events]},
        )
        _capture_state(run, session)
        done = next((event for event in reversed(events) if event.kind == "done"), None)
        outcome = (done.payload or {}).get("outcome") if done is not None else None
        if outcome not in {"completed", "interrupted", "failed"}:
            raise FixtureError("Raw Web turn lacks an explicit native terminal outcome")
        run.setdefault("turns", []).append({"index": index, "status": outcome})
        if outcome != "completed":
            raise FixtureError("Raw Web turn did not complete; inspect private native evidence")
    except BrainLaunchRuntimeError as exc:
        raise FixtureError("Owned Web prompt failed; no input is retried") from exc
    finally:
        session.close_control_connection()


def control_raw_web(run: dict[str, Any], action: str) -> None:
    """Control only the captured live host without starting or selecting a replacement."""

    session = _raw_session(run)
    try:
        if action == "interrupt":
            result = session.interrupt()
        else:
            session.configure_stop_force_cleanup(force_cleanup=True)
            result = session.terminate()
        if result.status != "ok":
            raise FixtureError("Owned Web control failed; inspect the captured run")
        if action == "interrupt":
            _capture_state(run, session)
        else:
            run["raw_web_state"] = session.state.to_payload()
    except BrainLaunchRuntimeError as exc:
        raise FixtureError("Owned Web control failed; inspect captured native evidence") from exc
    finally:
        session.close_control_connection()


def observe_raw_web(run: dict[str, Any]) -> dict[str, Any]:
    """Inspect structured native state without launching or activating anything."""

    session = _raw_session(run)
    try:
        return dict(session.observe_web_state())
    except BrainLaunchRuntimeError as exc:
        raise FixtureError(
            "Owned Web state is unavailable; inspection did not activate it"
        ) from exc
    finally:
        session.close_control_connection()


def browser_connection_file(run: dict[str, Any]) -> Path:
    """Write an explicit private browser handoff, returning its path rather than a token."""

    tool = run["configuration"]["client"]
    if tool not in {"dsh", "kimi"} or run["configuration"]["mode"] != "web":
        raise FixtureError("Browser handoff requires a launched Web fixture")
    if run.get("status") != "launched":
        raise FixtureError("Browser handoff requires a launched owned host")
    root = Path(run["run_dir"])
    if tool == "kimi":
        return _kimi_browser_connection_file(run, root)
    if run["configuration"]["surface"] == "raw":
        state = run["raw_web_state"]
    else:
        manifest = json.loads(Path(run["identity"]["manifest_path"]).read_text())
        state = manifest["backend_state"]
    bootstrap = Path(state["bootstrap_path"])
    if not bootstrap.resolve().is_relative_to(root) or bootstrap.stat().st_mode & 0o077:
        raise FixtureError("Web bootstrap must remain in this external private fixture root")
    connection = json.loads(bootstrap.read_text())
    if connection.get("origin") != state["origin"]:
        raise FixtureError("Private browser connection does not match the captured Web host")
    native_session_id = state["web_identity"]["native_session_id"]
    token = connection.get("launch_token")
    if not isinstance(token, str) or not token or not native_session_id:
        raise FixtureError("Private browser connection lacks verified native authority")
    target = root / "browser-connection.json"
    private_write(
        target,
        json.dumps(
            {
                "origin": state["origin"],
                "launch_token": token,
                "native_session_id": native_session_id,
            }
        ).encode(),
    )
    return target


def _kimi_browser_connection_file(run: dict[str, Any], root: Path) -> Path:
    """Verify the current owned Kimi listener and write credentials only to the fixture."""

    from houmao.agents.realm_controller.backends.kimi_web import KimiWebSession
    from houmao.agents.realm_controller.manifest import (
        load_session_manifest,
        parse_session_manifest_payload,
    )
    from houmao.agents.realm_controller.runtime import resume_runtime_session

    from fixturelib.launch import run_environment
    from fixturelib.prepare import command_environment

    identity = run["identity"]
    manifest = Path(identity["manifest_path"]).resolve()
    if not manifest.is_relative_to(root.resolve()):
        raise FixtureError("Kimi Web manifest is outside the private fixture")
    saved = parse_session_manifest_payload(
        load_session_manifest(manifest).payload, source=str(manifest)
    )
    saved_agent_def = saved.runtime.agent_def_dir
    if saved_agent_def is None or not Path(saved_agent_def).resolve().is_relative_to(
        root.resolve()
    ):
        raise FixtureError("Kimi Web runtime role is outside the private fixture")
    surface = run["native_surface"]
    with command_environment(run_environment(run)):
        controller = resume_runtime_session(
            agent_def_dir=Path(saved_agent_def), session_manifest_path=manifest, read_only=True
        )
        try:
            backend = controller.backend_session
            if not isinstance(backend, KimiWebSession):
                raise FixtureError("Fixture owner no longer uses Kimi Web")
            origin, token = backend.browser_credentials()
            if (
                origin != surface["origin"]
                or backend.state.native_surface.native_session_id != surface["native_session_id"]
            ):
                raise FixtureError("Kimi Web host changed since this fixture launched")
        finally:
            controller.close()
    target = root / "browser-connection.json"
    private_write(
        target,
        json.dumps(
            {
                "origin": origin,
                "launch_token": token,
                "native_session_id": surface["native_session_id"],
            }
        ).encode(),
    )
    return target
