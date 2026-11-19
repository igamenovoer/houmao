"""Launch explicitly prepared clients and retain private, identity-scoped evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from pydantic import TypeAdapter, ValidationError

from houmao.agents.realm_controller.gateway_access_runtime import owner_gateway_client_binding
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayPromptControlRequestV1,
)
from houmao.agents.realm_controller.native_surface import NativeSurfaceV1, TerminalNativeSurfaceV1
from houmao.gateway.client import GatewayClient, GatewayHttpError

from fixturelib.auth import private_write, write_json
from fixturelib.config import FixtureError
from fixturelib.prepare import (
    ManagedCommandError,
    command_environment,
    fixture_tmux_socket_path,
    isolated_environment,
    load_run,
    manager_call,
    manager_root_call,
)

_VERSION_OUTPUT = re.compile(
    r"(?:codex-cli )?(\d{1,4}\.\d{1,4}\.\d{1,4}(?:[-+][\w.-]{1,40})?)(?: \(Claude Code\))?"
)
_NATIVE_SURFACE = TypeAdapter(NativeSurfaceV1)


def run_environment(run: dict[str, Any]) -> dict[str, str]:
    """Load private selected bindings without returning them in public metadata."""

    root = Path(run["run_dir"])
    try:
        selected = json.loads((root / "private-env.json").read_text())
    except (OSError, ValueError) as exc:
        raise FixtureError("Cannot read prepared private environment") from exc
    if not isinstance(selected, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in selected.items()
    ):
        raise FixtureError("Invalid prepared private environment")
    env = isolated_environment(selected, run_dir=root, tmux_socket_path=run.get("tmux_socket_path"))
    if run["configuration"]["mode"] == "tui":
        env[f"HOUMAO_HOOK_OBSERVATION_{run['configuration']['client'].upper()}"] = "1"
    return env


def _tmux_command(run: dict[str, Any], *arguments: str) -> list[str]:
    """Address the explicitly isolated fixture server, never the caller's server."""

    server = run.get("tmux_server")
    executable = run.get("tmux_executable")
    root = Path(run["run_dir"])
    socket_path = fixture_tmux_socket_path(root)
    if (
        server != "houmao-fixture-" + root.name
        or run.get("tmux_socket_path") != socket_path
        or not executable
    ):
        raise FixtureError("Fixture has no verified isolated tmux server")
    return [executable, "-S", socket_path, *arguments]


def public_run(run: dict[str, Any]) -> dict[str, Any]:
    """Select report fields that exclude private native output and env values."""

    fields = (
        "schema_version",
        "status",
        "run_dir",
        "configuration",
        "backend",
        "native_surface",
        "identity",
        "turns",
        "error",
        "cleanup",
        "gateway_cleanup",
        "prerequisites",
        "usage",
        "client_version",
        "native_state",
    )
    return {key: run[key] for key in fields if key in run}


def _save(run: dict[str, Any]) -> None:
    """Persist safe metadata after every launch and cleanup transition."""

    write_json(Path(run["run_dir"]) / "run.json", run)
    write_json(Path(run["run_dir"]) / "report.json", public_run(run))


def _http(base: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call a maintained local API without reflecting response bodies on error."""

    parsed = urlsplit(base)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise FixtureError("Use an HTTP(S) authority URL without embedded credentials")
    request = Request(
        base.rstrip("/") + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
    except (OSError, ValueError, URLError) as exc:
        raise FixtureError(
            "Maintained local API request failed; inspect private run evidence"
        ) from exc
    if not isinstance(result, dict):
        raise FixtureError("Maintained local API returned an unexpected response")
    return result


def manager_gateway(run: dict[str, Any]) -> GatewayClient:
    """Bind requests to the captured gateway and current fixture self signer."""

    identity = run["identity"]
    try:
        with command_environment(run_environment(run)):
            binding, generation = owner_gateway_client_binding(
                Path(identity["manifest_path"]),
                port=identity["gateway_port"],
                private=True,
                prefer_self=True,
            )
        if binding is None:
            raise ValueError("Missing current fixture binding")
        return GatewayClient(binding=binding, target_incarnation=generation, timeout_seconds=20)
    except (KeyError, OSError, RuntimeError, ValueError):
        raise FixtureError("Current fixture gateway authority is unavailable") from None


def _gateway_request(
    run: dict[str, Any], path: str, body: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Call a fixture-owned gateway operation with owner-local proof."""

    client = manager_gateway(run)
    try:
        if path == "/v1/usage":
            return client.get_usage().model_dump(mode="json")
        if path == "/v1/status":
            return client.status().model_dump(mode="json")
        if path == "/v1/control/prompt":
            return client.control_prompt(
                GatewayPromptControlRequestV1.model_validate(body)
            ).model_dump(mode="json")
        if path == "/v1/control/send-keys":
            return client.send_control_input(
                GatewayControlInputRequestV1.model_validate(body)
            ).model_dump(mode="json")
    except (GatewayHttpError, ValueError):
        raise FixtureError("Fixture gateway request failed; inspect private run evidence") from None
    raise FixtureError("Unsupported fixture gateway operation")


def raw_command(run: dict[str, Any], *, prompt: str | None = None) -> list[str]:
    """Build current native argv; Kimi prompt mode deliberately omits --auto."""

    client = run["configuration"]["client"]
    command = [run["executable"]]
    model = run["configuration"].get("model")
    unattended = run["configuration"].get("operator_prompt_mode", "unattended") == "unattended"
    session = run.get("identity", {}).get("provider_session_id")
    if client == "claude":
        if unattended:
            command += ["--dangerously-skip-permissions"]
        if model:
            command += ["--model", model]
        if prompt is not None:
            command += ["-p", "--verbose", "--output-format", "stream-json"]
            if session:
                command += ["--resume", session]
            command += [prompt]
    elif client == "codex":
        if unattended:
            command += ["--dangerously-bypass-approvals-and-sandbox"]
        if model:
            command += ["--model", model]
        if prompt is not None:
            command += ["exec", "--json", "--skip-git-repo-check"]
            if session:
                command += ["resume", session]
            command += [prompt]
    elif client == "kimi":
        if prompt is None:
            if unattended:
                command += ["--auto"]
        else:
            command += ["--output-format", "stream-json"]
            if session:
                command += ["--session", session]
            command += ["-p", prompt]
    elif client == "dsh" and run["configuration"]["mode"] == "headless":
        command += [
            "--profile",
            "headless",
            "--patch",
            str(Path(run["home_path"]) / "houmao-profile.patch.json"),
            "--patch",
            run["raw_dsh_patch"],
            "--json",
        ]
        if session:
            command += ["--session-id", session]
    else:
        raise FixtureError(f"No direct terminal or one-shot fixture command for {client}")
    return command


def _session_id(path: Path, client: str) -> str | None:
    """Read only native identity fields from a completed raw JSONL capture."""

    for line in path.read_text(errors="replace").splitlines():
        try:
            item = json.loads(line)
        except ValueError:
            continue
        if not isinstance(item, dict):
            continue
        value = item.get("session_id")
        if client == "codex" and item.get("type") == "thread.started":
            value = item.get("thread_id")
        if isinstance(value, str) and value:
            return value
    return None


def _raw_dsh_turn_result(path: Path, *, expected_session: str | None) -> tuple[str | None, str]:
    """Read the exact opening identity and terminal reason from DSH's complete lines."""

    session = None
    outcome = None
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.endswith("\n"):
                    return session, "uncertain"
                event = json.loads(line)
                if not isinstance(event, dict) or outcome is not None:
                    return session, "uncertain"
                kind = event.get("type")
                if not isinstance(kind, str):
                    return session, "uncertain"
                if kind == "error":
                    outcome = "failed"
                elif kind == "session" and session is None:
                    value = event.get("sessionId")
                    if (
                        not isinstance(value, str)
                        or not value
                        or (expected_session is not None and value != expected_session)
                    ):
                        return None, "uncertain"
                    session = value
                elif kind == "final" and session is not None and event.get("sessionId") == session:
                    reason = event.get("reason")
                    tag = reason.get("kind") if isinstance(reason, dict) else None
                    if tag == "completed":
                        outcome = "completed"
                    elif tag == "aborted":
                        outcome = "interrupted"
                    elif tag in ("blocked", "error", "max-tokens"):
                        outcome = "failed"
                    else:
                        outcome = "uncertain"
                elif kind in {"session", "final"} or session is None:
                    return session, "uncertain"
    except (OSError, UnicodeError, ValueError):
        return session, "uncertain"
    return session, outcome or "uncertain"


def _raw_turn(run: dict[str, Any], prompt: str, timeout: float) -> None:
    """Capture raw client output privately, terminating only the owned process group."""

    root = Path(run["run_dir"])
    index = len(run.get("turns", [])) + 1
    stdout = root / f"raw-turn-{index}.jsonl"
    stderr = root / f"raw-turn-{index}.stderr"
    client = run["configuration"]["client"]
    dsh = client == "dsh"
    env = run_environment(run)
    if dsh:
        from fixturelib.dsh import raw_dsh_environment

        env = raw_dsh_environment(run, env)
    private_write(stdout, b"")
    private_write(stderr, b"")
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen(
            raw_command(run, prompt=prompt),
            cwd=run["workdir"],
            env=env,
            stdin=subprocess.PIPE if dsh else subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            umask=0o077,
        )
        worker = {"pid": process.pid, "birth": _process_birth(process.pid)}
        run["active_process"] = worker
        _save(run)
        try:
            if dsh:
                process.communicate(input=prompt.encode(), timeout=timeout)
            else:
                process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        code = process.returncode
        run.pop("active_process", None)
    summary: dict[str, int | str] = {"index": index, "returncode": code}
    if dsh:
        run.setdefault("raw_workers", []).append(worker)
        session, outcome = _raw_dsh_turn_result(
            stdout, expected_session=run.get("identity", {}).get("provider_session_id")
        )
        if outcome in {"failed", "uncertain"} and code in {-signal.SIGINT, 130}:
            # The native launcher reserves 130 for SIGINT-triggered exit.
            outcome = "interrupted"
            summary["evidence_source"] = "worker_exit"
        else:
            if outcome == "completed" and code != 0:
                outcome = "uncertain"
            summary["evidence_source"] = "native_stream"
        summary["status"] = outcome
    else:
        session = _session_id(stdout, client)
    run.setdefault("turns", []).append(summary)
    if session:
        run.setdefault("identity", {})["provider_session_id"] = session
    _save(run)
    if code != 0 or (dsh and summary["status"] != "completed"):
        raise FixtureError("Raw client turn failed; inspect private stdout/stderr captures")


def _process_birth(process_id: int) -> str | None:
    """Read Linux process start ticks so delayed interruption cannot hit a reused PID."""

    try:
        return Path(f"/proc/{process_id}/stat").read_text().rpartition(")")[2].split()[19]
    except (OSError, IndexError):
        return None


def _signal_raw_driver(run: dict[str, Any], signum: int) -> bool:
    """Use birth evidence and a process descriptor when available for this driver."""

    active = run.get("active_process", {})
    pid, birth = active.get("pid"), active.get("birth")
    if not isinstance(pid, int) or birth is None:
        return False
    descriptor: int | None = None
    try:
        if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
            descriptor = os.pidfd_open(pid)
        if _process_birth(pid) != birth:
            return False
        if descriptor is None:
            os.kill(pid, signum)
        else:
            signal.pidfd_send_signal(descriptor, signum)
        return True
    except (OSError, AttributeError):
        return False
    finally:
        if descriptor is not None:
            os.close(descriptor)


def interrupt_run(path: Path) -> dict[str, Any]:
    """Interrupt only this run's captured active execution without replaying input."""

    run = load_run(path)
    identity = run.get("identity", {})
    if run["configuration"]["surface"] == "raw":
        if run["configuration"]["mode"] == "web":
            from fixturelib.web import control_raw_web

            control_raw_web(run, "interrupt")
            _save(run)
        elif not _signal_raw_driver(run, signal.SIGINT):
            raise FixtureError("No verified active raw fixture process to interrupt")
    elif run["configuration"]["surface"] == "manager":
        manager_root_call(
            ["agents", "single", "--agent-id", identity["agent_id"], "interrupt"],
            env=run_environment(run),
        )
    else:
        ref = quote(identity["tracked_agent_id"], safe="")
        _http(identity["passive_url"], f"/houmao/agents/{ref}/interrupt", {})
    return {"status": "interrupt_requested", "run_dir": run["run_dir"]}


def _raw_tui(run: dict[str, Any]) -> None:
    """Start one named tmux session with bindings sourced from a private script."""

    name = "fixture-" + Path(run["run_dir"]).name
    command = [sys.executable, str(Path(__file__).with_name("raw_child.py")), run["run_dir"]]
    started = subprocess.run(
        _tmux_command(
            run,
            "new-session",
            "-d",
            "-P",
            "-F",
            "#{pane_id}",
            "-s",
            name,
            "-c",
            run["workdir"],
            shlex.join(command),
        ),
        check=True,
        capture_output=True,
        text=True,
        env=run_environment(run),
    )
    surface = TerminalNativeSurfaceV1(tmux_session_name=name, pane_id=started.stdout.strip())
    run["identity"] = {
        "tmux_session_name": name,
        "native_surface": surface.model_dump(mode="json"),
    }


def _passive_launch(run: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Build private inputs and use the maintained passive headless creation route."""

    from houmao.agents.brain_builder import BuildRequest, build_brain_home

    with command_environment(run_environment(run)):
        build = build_brain_home(
            BuildRequest(
                agent_def_dir=Path(run["assets_root"]),
                tool=run["configuration"]["client"],
                skills=[],
                setup="fixture",
                auth="default",
                runtime_root=Path(run["run_dir"]) / "runtime",
                operator_prompt_mode="unattended",
            )
        )
    result = _http(
        base_url,
        "/houmao/agents/headless/launches",
        {
            "tool": run["configuration"]["client"],
            "working_directory": run["workdir"],
            "agent_def_dir": run["assets_root"],
            "brain_manifest_path": str(build.manifest_path),
            "role_name": run["role"],
            "agent_name": Path(run["run_dir"]).name,
        },
    )
    return {**result, "passive_url": base_url}


def launch_run(
    path: Path, *, prompt: str | None = None, passive_url: str | None = None, timeout: float = 300
) -> dict[str, Any]:
    """Launch one prepared run and persist authoritative identity before follow-up."""

    run = load_run(path)
    if run["status"] != "prepared":
        raise FixtureError("Launch requires an unused prepared run")
    config = run["configuration"]
    if config["surface"] == "passive-server" and not passive_url:
        raise FixtureError("Passive-server launch requires explicit --passive-url")
    if config["surface"] == "raw" and config["mode"] == "headless" and not prompt:
        raise FixtureError("Raw headless launch requires --prompt")
    if not os.access(run["executable"], os.X_OK):
        run["status"] = "not_run"
        run["prerequisites"] = {"missing": ["client_executable"], "live_requested": True}
        _save(run)
        raise FixtureError("Client executable is unavailable; prepare a fresh fixture run")
    if config["surface"] == "manager" or config["mode"] in {"tui", "web"}:
        _tmux_command(run)
        run_environment(run)
    run["status"] = "launching"
    _save(run)
    try:
        version = subprocess.run(
            [run["executable"], "--version"],
            env=run_environment(run),
            capture_output=True,
            text=True,
            timeout=15,
            umask=0o077,
        )
        # Store the version token only. Other executable output stays private.
        line = version.stdout.strip().splitlines()
        match = _VERSION_OUTPUT.fullmatch(line[0]) if version.returncode == 0 and line else None
        run["client_version"] = match.group(1) if match else None
        if config["surface"] == "raw":
            if config["mode"] == "headless":
                _raw_turn(run, prompt or "", timeout)
            elif config["mode"] == "web":
                from fixturelib.web import launch_raw_web

                with command_environment(run_environment(run)):
                    launch_raw_web(run)
            elif config["mode"] == "tui":
                _raw_tui(run)
            else:
                raise FixtureError("This mode requires the managed fixture surface")
        elif config["surface"] == "manager":
            result = manager_call(
                Path(run["project_dir"]),
                [
                    "agents",
                    "launch",
                    "--specialist",
                    "fixture-agent",
                    "--name",
                    Path(run["run_dir"]).name,
                    "--workdir",
                    run["workdir"],
                    "--gateway-background",
                    "--mode",
                    config["mode"],
                ],
                env=run_environment(run),
            )
            run["identity"] = result
            if not result.get("agent_id") or not result.get("manifest_path"):
                raise FixtureError("Managed launch did not return an authoritative identity")
            if (
                result.get("tool") != config["client"]
                or result.get("mode") != config["mode"]
                or result.get("backend") != run["backend"]
            ):
                raise FixtureError("Managed launch returned a different run mode, tool, or backend")
        else:
            run["identity"] = _passive_launch(run, passive_url or "")
            if not run["identity"].get("tracked_agent_id"):
                raise FixtureError("Passive launch did not return an authoritative identity")
        _record_native_surface(run)
        run["status"] = "launched"
        _save(run)
        if prompt and (config["surface"] != "raw" or config["mode"] == "web"):
            return prompt_run(path, prompt=prompt, timeout=timeout)
        return public_run(run)
    except (FixtureError, OSError, subprocess.SubprocessError) as exc:
        if isinstance(exc, ManagedCommandError):
            run["identity"] = exc.payload
        run["status"] = "launch_failed"
        run["error"] = "Launch failed; private run state retained for inspection"
        _save(run)
        _cleanup(run)
        _save(run)
        raise FixtureError(f"Launch failed; inspect {path / 'report.json'}") from exc


def _record_native_surface(run: dict[str, Any]) -> None:
    """Require a verified and public native surface for an interactive mode."""

    identity = run.get("identity", {})
    payload = identity.pop("native_surface", None)
    expected = {"tui": "terminal", "web": "web"}.get(run["configuration"]["mode"])
    run["native_surface"] = None
    if payload is None and expected is None:
        return
    try:
        surface = _NATIVE_SURFACE.validate_python(payload)
    except ValidationError as exc:
        raise FixtureError("Launch did not return a valid native surface for its mode") from exc
    if surface.kind != expected:
        raise FixtureError("Launch returned a native surface for a different mode")
    safe = surface.model_dump(mode="json")
    identity["native_surface"] = safe
    run["native_surface"] = safe


def prompt_run(path: Path, *, prompt: str, timeout: float = 300) -> dict[str, Any]:
    """Continue an owned raw or managed headless session, or send direct TUI input."""

    run = load_run(path)
    if run["status"] != "launched":
        raise FixtureError("Prompt requires a launched run")
    config = run["configuration"]
    identity = run.get("identity", {})
    if config["surface"] == "raw":
        if config["mode"] == "web":
            from fixturelib.web import prompt_raw_web

            try:
                prompt_raw_web(run, prompt, timeout)
            finally:
                _save(run)
        elif config["mode"] == "headless":
            if not identity.get("provider_session_id"):
                raise FixtureError("Raw continuation requires a captured provider session ID")
            _raw_turn(run, prompt, timeout)
        else:
            target = identity["tmux_session_name"]
            subprocess.run(
                _tmux_command(run, "send-keys", "-t", target, "-l", prompt),
                check=True,
                env=run_environment(run),
            )
            time.sleep(0.25)
            subprocess.run(
                _tmux_command(run, "send-keys", "-t", target, "Enter"),
                check=True,
                env=run_environment(run),
            )
    elif config["surface"] == "passive-server":
        ref = quote(identity["tracked_agent_id"], safe="")
        accepted = _http(identity["passive_url"], f"/houmao/agents/{ref}/turns", {"prompt": prompt})
        turn_id = accepted["turn_id"]
        deadline = time.monotonic() + timeout
        while True:
            turn = _http(
                identity["passive_url"], f"/houmao/agents/{ref}/turns/{quote(turn_id, safe='')}"
            )
            if turn["status"] in {"completed", "failed", "interrupted"}:
                break
            if time.monotonic() >= deadline:
                raise FixtureError("Headless turn timed out; stop the captured run explicitly")
            time.sleep(0.25)
        run.setdefault("turns", []).append(
            {"turn_id": turn_id, "status": turn["status"], "returncode": turn.get("returncode")}
        )
        if turn["status"] != "completed":
            _save(run)
            raise FixtureError("Managed headless turn did not complete")
    else:
        if config["mode"] == "tui":
            _gateway_request(
                run, "/v1/control/send-keys", {"sequence": prompt, "escape_special_keys": True}
            )
            time.sleep(0.25)
            _gateway_request(run, "/v1/control/send-keys", {"sequence": "<[Enter]>"})
        else:
            before = _gateway_request(run, "/v1/usage")
            previous = {record["record_id"] for record in before["records"]}
            accepted = _gateway_request(run, "/v1/control/prompt", {"prompt": prompt})
            require_operation_id = (
                config["mode"] in {"service", "web"} or run.get("backend") == "dsh_headless"
            )
            operation_id = accepted.get("operation_id") if require_operation_id else None
            if require_operation_id and (not isinstance(operation_id, str) or not operation_id):
                raise FixtureError("Managed prompt has no exact admitted operation identity")
            deadline = time.monotonic() + timeout
            while True:
                usage = _gateway_request(run, "/v1/usage")
                rows = [
                    record
                    for record in usage["records"]
                    if record["record_id"] not in previous
                    and (operation_id is None or record.get("turn_id") == operation_id)
                ]
                if rows:
                    break
                if time.monotonic() >= deadline:
                    raise FixtureError(
                        "Managed turn timed out; inspect usage and stop the captured run"
                    )
                time.sleep(0.25)
            run["usage"] = usage
            run.setdefault("turns", []).append(
                {"record_id": rows[0]["record_id"], "status": rows[0]["outcome"]}
            )
            if rows[0]["outcome"] != "completed":
                _save(run)
                raise FixtureError("Managed turn did not complete; inspect public usage")
            # The ledger may finalize before the current gateway worker releases
            # execution ownership. Finish observing that same successful turn;
            # this never waits on or retries a subsequent prompt mutation.
            while _gateway_request(run, "/v1/status").get("active_execution") == "running":
                if time.monotonic() >= deadline:
                    raise FixtureError(
                        "Completed usage is available but the current execution has not settled"
                    )
                time.sleep(0.05)
    _save(run)
    return public_run(run)


def _cleanup(run: dict[str, Any]) -> None:
    """Stop only identities captured by this run; preserve its private evidence."""

    identity = run.get("identity", {})
    config = run["configuration"]
    try:
        if config["surface"] == "raw" and config["mode"] == "web":
            if run.get("raw_web_state"):
                from fixturelib.web import control_raw_web

                with command_environment(run_environment(run)):
                    control_raw_web(run, "terminate")
        elif config["surface"] == "raw" and run.get("active_process"):
            active = run["active_process"]
            current_birth = _process_birth(active["pid"])
            if current_birth is not None and current_birth != active["birth"]:
                raise FixtureError(
                    "Raw fixture process identity changed; cleanup refuses the replacement"
                )
            if current_birth is not None:
                if not _signal_raw_driver(run, signal.SIGTERM):
                    raise FixtureError("Cannot safely signal the owned raw fixture process")
                deadline = time.monotonic() + 25
                while (
                    _process_birth(active["pid"]) == active["birth"] and time.monotonic() < deadline
                ):
                    time.sleep(0.1)
                if _process_birth(active["pid"]) == active["birth"]:
                    if not _signal_raw_driver(run, signal.SIGKILL):
                        raise FixtureError("Raw fixture cleanup lost its verified process target")
            run.pop("active_process", None)
        elif config["surface"] == "manager" and identity.get("agent_id"):
            scope = ["agents", "single", "--agent-id", identity["agent_id"]]
            if identity.get("gateway_port"):
                try:
                    manager_root_call([*scope, "gateway", "detach"], env=run_environment(run))
                except FixtureError:
                    run["gateway_cleanup"] = "detach_failed"
            manager_root_call([*scope, "stop"], env=run_environment(run))
        elif config["surface"] == "passive-server" and identity.get("tracked_agent_id"):
            ref = quote(identity["tracked_agent_id"], safe="")
            _http(identity["passive_url"], f"/houmao/agents/{ref}/stop", {})
        elif config["surface"] == "raw" and identity.get("tmux_session_name"):
            subprocess.run(
                _tmux_command(run, "kill-session", "-t", identity["tmux_session_name"]),
                check=True,
                capture_output=True,
                env=run_environment(run),
            )
        run["cleanup"] = "stopped_owned_identity" if identity else "no_owned_identity"
        if run.get("gateway_cleanup") == "detach_failed":
            try:
                connection = socket.create_connection(
                    (identity.get("gateway_host", "127.0.0.1"), identity["gateway_port"]),
                    timeout=0.3,
                )
                connection.close()
                run["cleanup"] = "failed_requires_scoped_follow_up"
            except OSError:
                run["gateway_cleanup"] = "already_unavailable"
    except (FixtureError, OSError, subprocess.SubprocessError):
        run["cleanup"] = "failed_requires_scoped_follow_up"


def stop_run(path: Path) -> dict[str, Any]:
    """Stop captured owned identities and keep metadata inspectable."""

    run = load_run(path)
    if run["status"] == "stopped" or run.get("cleanup") == "stopped_owned_identity":
        run["status"] = "stopped"
        _save(run)
        return public_run(run)
    _cleanup(run)
    if run["cleanup"] == "failed_requires_scoped_follow_up":
        _save(run)
        raise FixtureError("Cleanup failed; use the captured identity for scoped follow-up")
    run["status"] = "stopped"
    _save(run)
    return public_run(run)


def check_run(path: Path, *, live: bool = False) -> dict[str, Any]:
    """Inspect a prepared run offline; contact only its authority when explicitly asked."""

    run = load_run(path)
    root = Path(run["run_dir"])
    missing = []
    if not os.access(run["executable"], os.X_OK):
        missing.append("client_executable")
    if (
        run["configuration"]["mode"] in {"tui", "web"} or run["configuration"]["surface"] != "raw"
    ) and shutil.which("tmux") is None:
        missing.append("tmux")
    if not (root / "private-env.json").is_file():
        missing.append("private_environment")
    run["prerequisites"] = {"missing": missing, "live_requested": live}
    if live:
        identity = run.get("identity", {})
        if run["configuration"]["mode"] == "web" and run["configuration"]["surface"] == "raw":
            from fixturelib.web import observe_raw_web

            run["native_state"] = observe_raw_web(run)
        elif identity.get("passive_url"):
            ref = quote(identity["tracked_agent_id"], safe="")
            run["usage"] = _http(identity["passive_url"], f"/houmao/agents/{ref}/usage")
        elif identity.get("gateway_port"):
            run["usage"] = _gateway_request(run, "/v1/usage")
        elif identity.get("tmux_session_name"):
            subprocess.run(
                _tmux_command(run, "has-session", "-t", identity["tmux_session_name"]),
                check=True,
                capture_output=True,
                env=run_environment(run),
            )
        elif run["configuration"]["surface"] != "raw":
            raise FixtureError("Live check requires a launched authority identity")
    _save(run)
    return public_run(run)
