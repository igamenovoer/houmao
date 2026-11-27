"""Launch explicitly prepared clients and retain private, identity-scoped evidence."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, suppress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any
from urllib.error import URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

import click
import httpx
from pydantic import TypeAdapter, ValidationError

from houmao.agents.hermes_configuration import resolve_hermes_executable
from houmao.agents.launch_env import owner_launch_baseline, owner_tmux_launch_environment
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.errors import BackendExecutionError, SessionManifestError
from houmao.agents.realm_controller.gateway_access_runtime import owner_gateway_client_binding
from houmao.agents.realm_controller.gateway_models import (
    GatewayControlInputRequestV1,
    GatewayPromptControlRequestV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.native_surface import NativeSurfaceV1, TerminalNativeSurfaceV1
from houmao.agents.realm_controller.registry_storage import load_managed_agent_record_by_agent_id
from houmao.agents.realm_controller.runtime import require_active_managed_control_manifest
from houmao.execution.tmux import TmuxCommandError, TmuxServer, tmux_server_scope
from houmao.execution.tmux_selection import TmuxServerSelector, resolve_tmux_server
from houmao.gateway.client import GatewayClient, GatewayHttpError
from houmao.owned_paths import HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR, resolve_registry_root

from fixturelib.auth import private_write, validate_native_bundle, write_json
from fixturelib.config import FixtureError, ResolvedConfig
from fixturelib.hermes_owner import (
    observe_profile,
    owner_environment,
    qualify_owner,
    selected_owner_root,
)
from fixturelib.prepare import (
    ManagedCommandError,
    command_environment,
    fixture_tmux_socket_path,
    isolated_environment,
    load_run,
    manager_call,
    manager_root_call,
    manager_selected_call,
)

if TYPE_CHECKING:
    from houmao.srv_ctrl.commands.managed_agents import ManagedAgentTarget, VerifiedRegistryManifest

_VERSION_OUTPUT = re.compile(
    r"(?:codex-cli )?(\d{1,4}\.\d{1,4}\.\d{1,4}(?:[-+][\w.-]{1,40})?)(?: \(Claude Code\))?"
)
_NATIVE_SURFACE = TypeAdapter(NativeSurfaceV1)
_RAW_TMUX_OWNER = "HOUMAO_FIXTURE_RUN_ID"


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
    legacy_socket = run.get("tmux_socket_path") if "tmux_server_mode" not in run else None
    hermes = run["configuration"]["client"] == "hermes"
    env = isolated_environment(
        selected,
        run_dir=root,
        tmux_socket_path=legacy_socket,
        process_env=owner_launch_baseline(os.environ) if hermes else None,
    )
    if owner := run.get("hermes_owner_root"):
        env.update(owner_environment(selected_owner_root(Path(owner))))
    if run["configuration"]["mode"] == "tui":
        env[f"HOUMAO_HOOK_OBSERVATION_{run['configuration']['client'].upper()}"] = "1"
    return env


def _fixture_tmux(run: dict[str, Any], *, allow_start: bool = False) -> TmuxServer:
    """Bind raw fixture actions to the saved socket, including legacy isolated runs."""

    if "tmux_server_mode" in run:
        socket_path = run.get("tmux_socket_path")
        if not isinstance(socket_path, str):
            raise FixtureError("Fixture has no captured tmux socket")
        return TmuxServer(socket_path, allow_start=allow_start)
    server = run.get("tmux_server")
    executable = run.get("tmux_executable")
    root = Path(run["run_dir"])
    socket_path = fixture_tmux_socket_path(root)
    shim = root / "bin/tmux"
    if (
        server != "houmao-fixture-" + root.name
        or run.get("tmux_socket_path") != socket_path
        or not executable
        or not shim.is_file()
    ):
        raise FixtureError("Fixture has no verified isolated tmux server")
    return TmuxServer(socket_path, executable=str(shim), allow_start=allow_start)


def _select_raw_tmux(run: dict[str, Any]) -> bool:
    """Resolve and save a raw fixture's socket before starting its owned session."""

    mode = run.get("tmux_server_mode")
    if mode is None:
        _fixture_tmux(run)
        return True
    environment = run_environment(run)
    try:
        selected = resolve_tmux_server(
            TmuxServerSelector(server=mode),
            registry_root=resolve_registry_root(env=environment),
            environment=environment,
        )
    except (OSError, ValueError, TmuxCommandError) as exc:
        raise FixtureError("Cannot select the requested fixture tmux server") from exc
    run["tmux_socket_path"] = selected.socket_path
    _save(run)
    return selected.allow_start


@contextmanager
def _raw_web_environment(run: dict[str, Any], *, allow_start: bool = False) -> Iterator[None]:
    """Bind the raw Web supervisor and each follow-up to the saved server."""

    with (
        command_environment(run_environment(run)),
        tmux_server_scope(_fixture_tmux(run).socket_path, allow_start=allow_start),
    ):
        yield


def public_run(run: dict[str, Any]) -> dict[str, Any]:
    """Select report fields that exclude private native output and env values."""

    fields = (
        "schema_version",
        "status",
        "run_dir",
        "configuration",
        "pool_key",
        "pool_slot",
        "backend",
        "tmux_server_mode",
        "tmux_socket_path",
        "native_surface",
        "identity",
        "turns",
        "error",
        "cleanup",
        "gateway_cleanup",
        "manager_exit_code",
        "diagnostic_path",
        "cleanup_diagnostic_path",
        "prerequisites",
        "usage",
        "client_version",
        "native_state",
        "hermes_owner_root",
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


def manager_gateway(run: dict[str, Any], *, generation_id: str | None = None) -> GatewayClient:
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
        if binding is None or (generation_id is not None and generation != generation_id):
            raise ValueError("Missing or changed fixture gateway binding")
        return GatewayClient(binding=binding, target_incarnation=generation, timeout_seconds=20)
    except (KeyError, OSError, RuntimeError, ValueError):
        raise FixtureError("Current fixture gateway authority is unavailable") from None


def _gateway_request(
    run: dict[str, Any],
    path: str,
    body: dict[str, Any] | None = None,
    *,
    generation_id: str | None = None,
) -> dict[str, Any]:
    """Call a fixture-owned gateway operation with owner-local proof."""

    client = manager_gateway(run, generation_id=generation_id)
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
    elif client == "hermes":
        mode = run["configuration"]["mode"]
        if mode == "headless":
            command += ["chat", "--oneshot", "--query-file", "-", "--format", "stream-json"]
        elif mode == "service":
            command += ["acp"]
        else:
            command += ["--tui"]
        if session and mode in {"headless", "tui"}:
            command += ["--resume", session]
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
    hermes = client == "hermes"
    env = run_environment(run)
    command = raw_command(run, prompt=prompt)
    if dsh:
        from fixturelib.dsh import load_raw_dsh_home

        home = load_raw_dsh_home(run, env)
        env = home.environment
        if home.permission_preset is not None:
            command.extend(["--permission-mode", home.permission_preset])
    if hermes:
        from fixturelib.hermes import raw_hermes_daemon

        daemon = raw_hermes_daemon(run, env)
        daemon.ensure()
        previous = run.get("identity", {}).get("provider_session_id")
        if previous:
            daemon.resolve_session(previous)
    private_write(stdout, b"")
    private_write(stderr, b"")
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen(
            command,
            cwd=run["workdir"],
            env=env,
            stdin=subprocess.PIPE if dsh or hermes else subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            umask=0o077,
        )
        worker = {"pid": process.pid, "birth": _process_birth(process.pid)}
        run["active_process"] = worker
        _save(run)
        try:
            if dsh or hermes:
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
    elif hermes:
        from fixturelib.hermes import raw_hermes_result

        run.setdefault("raw_workers", []).append(worker)
        session = raw_hermes_result(stdout, run.get("identity", {}).get("provider_session_id"))
        summary["status"] = "completed" if code == 0 and session else "uncertain"
        summary["evidence_source"] = "native_stream"
    else:
        session = _session_id(stdout, client)
    run.setdefault("turns", []).append(summary)
    if session:
        run.setdefault("identity", {})["provider_session_id"] = session
    _save(run)
    if code != 0 or ((dsh or hermes) and summary["status"] != "completed"):
        raise FixtureError("Raw client turn failed; inspect private stdout/stderr captures")


def _process_birth(process_id: int) -> str | None:
    """Read Linux process start ticks so delayed interruption cannot hit a reused PID."""

    try:
        fields = Path(f"/proc/{process_id}/stat").read_text().rpartition(")")[2].split()
        return fields[19] if fields[0] != "Z" else None
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

            with _raw_web_environment(run):
                control_raw_web(run, "interrupt")
            _save(run)
        elif (
            run["configuration"]["client"] == "hermes" and run["configuration"]["mode"] == "service"
        ):
            raise FixtureError("Raw Hermes ACP fixtures expose prompt and stop controls")
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


def _raw_tui(run: dict[str, Any], *, allow_start: bool, timeout: float) -> None:
    """Start one named tmux session with bindings sourced from a private script."""

    hermes = run["configuration"]["client"] == "hermes"
    if hermes:
        from fixturelib.hermes import raw_hermes_daemon

        raw_hermes_daemon(run, run_environment(run)).ensure()
    name = "fixture-" + Path(run["run_dir"]).name
    command = [sys.executable, str(Path(__file__).with_name("raw_child.py")), run["run_dir"]]
    owner_options = []
    if "tmux_server_mode" in run:
        owner = uuid4().hex
        run["raw_tmux_owner"] = owner
        _save(run)
        owner_options = ["-e", f"{_RAW_TMUX_OWNER}={owner}"]
    server = _fixture_tmux(run, allow_start=allow_start)
    started = server.start(
        [
            "new-session",
            "-d",
            "-E",
            "-P",
            "-F",
            "#{pane_id}",
            "-s",
            name,
            "-c",
            run["workdir"],
            *owner_options,
            shlex.join(command),
        ],
        environment=owner_tmux_launch_environment(run_environment(run)),
    )
    started.require_success()
    surface = TerminalNativeSurfaceV1(tmux_session_name=name, pane_id=started.stdout.strip())
    run["identity"] = {
        "tmux_session_name": name,
        "native_surface": surface.model_dump(mode="json"),
    }
    session_id = _owned_raw_tui_session(run, server)
    if session_id is None:
        raise FixtureError("Raw fixture session disappeared during launch")
    run["identity"]["tmux_session_id"] = session_id
    if hermes:
        _wait_for_raw_hermes_tui(server, started.stdout.strip(), timeout)


def _wait_for_raw_hermes_tui(server: TmuxServer, pane_id: str, timeout: float) -> None:
    """Wait for the fresh stock Ink pane to display its ready status line."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        capture = server.capture_exact(["capture-pane", "-p", "-t", pane_id])
        if capture.returncode != 0:
            raise FixtureError("Raw Hermes TUI pane disappeared during launch")
        if re.search(r"^\s*[─—] ready\s*│", capture.stdout, re.MULTILINE):
            return
        time.sleep(0.2)
    raise FixtureError("Raw Hermes TUI did not display a ready session")


def _raw_hermes_acp(run: dict[str, Any], timeout: float) -> None:
    """Start one stock ACP process under this fixture's persistent IO worker."""

    from fixturelib.hermes import ACP_READY, raw_hermes_daemon

    root = Path(run["run_dir"])
    environment = run_environment(run)
    raw_hermes_daemon(run, environment).ensure()
    log = root / "raw-acp-worker.log"
    private_write(log, b"")
    with log.open("ab") as output:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("hermes.py")), str(root)],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=output,
            start_new_session=True,
            umask=0o077,
        )
    run["active_process"] = {"pid": process.pid, "birth": _process_birth(process.pid)}
    _save(run)
    deadline = time.monotonic() + min(timeout, 65)
    while time.monotonic() < deadline and process.poll() is None:
        marker = root / ACP_READY
        if marker.is_file():
            run["identity"] = json.loads(marker.read_text(encoding="utf-8"))
            return
        time.sleep(0.05)
    raise FixtureError("Raw Hermes ACP startup failed; inspect private ACP artifacts")


def _owned_raw_tui_session(run: dict[str, Any], server: TmuxServer) -> str | None:
    """Return the exact live session ID after validating this fixture's ownership."""

    name = "fixture-" + Path(run["run_dir"]).name
    identity = run.get("identity", {})
    recorded_name = identity.get("tmux_session_name", name)
    if recorded_name != name:
        raise FixtureError("Raw fixture session name differs from its recorded owner")
    if name not in server.list_sessions(allow_missing_server=True):
        return None
    panes = server.observe_session(name)
    if panes is None:
        return None
    session_id = panes[0].session_id
    if session_id is None or identity.get("tmux_session_id", session_id) != session_id:
        raise FixtureError("Raw fixture session identity changed")
    if "tmux_server_mode" in run:
        owner = run.get("raw_tmux_owner")
        actual = server.checked_command(
            ["show-environment", "-t", session_id, _RAW_TMUX_OWNER], no_start=True
        )
        if not isinstance(owner, str) or actual.stdout.strip() != f"{_RAW_TMUX_OWNER}={owner}":
            raise FixtureError("Raw fixture session ownership changed")
    else:
        pane_id = identity.get("native_surface", {}).get("pane_id")
        if not any(pane.pane_id == pane_id for pane in panes):
            raise FixtureError("Legacy fixture pane identity changed")
    return session_id


def _captured_manifest_path(run: dict[str, Any]) -> Path:
    """Select only the canonical manifest recorded in the private fixture run."""

    identity = run.get("identity")
    raw_path = identity.get("manifest_path") if isinstance(identity, dict) else None
    if not isinstance(raw_path, str) or not raw_path:
        raise FixtureError("Managed fixture has no captured manifest authority")
    path = Path(raw_path)
    scope = Path(run["run_dir"])
    if owner := run.get("hermes_owner_root"):
        scope = selected_owner_root(Path(owner)) / "fixture-owner/runtime"
    if not path.is_absolute() or path.resolve() != path or not path.is_relative_to(scope):
        raise FixtureError("Managed fixture manifest lies outside the private run")
    return path


def _fixture_registry(run: dict[str, Any]) -> Path:
    """Select the private run registry or the shared test owner registry."""

    if owner := run.get("hermes_owner_root"):
        return selected_owner_root(Path(owner)) / "fixture-owner/registry"
    return Path(run["run_dir"]) / "registry"


def _manager_lineage(run: dict[str, Any], manifest: SessionManifestPayloadV4) -> dict[str, Any]:
    """Check that the manifest belongs to the fixture and return its stable owner facts."""

    config = run["configuration"]
    registry_root = str(_fixture_registry(run))
    binding = manifest.runtime.execution_binding
    if (
        manifest.agent_id != run["identity"].get("agent_id")
        or (manifest.tool, manifest.mode, manifest.backend)
        != (config["client"], config["mode"], run["backend"])
        or manifest.working_directory != run["workdir"]
        or manifest.registry_launch_authority != "runtime"
        or not manifest.runtime.session_id
        or binding is None
        or binding.registry_root != registry_root
        or manifest.tmux is None
        or manifest.tmux.socket_path is None
        or (binding.tmux_socket is not None and binding.tmux_socket != manifest.tmux.socket_path)
    ):
        raise FixtureError("Managed fixture runtime does not match the captured owner and identity")
    lineage = {
        "session_id": manifest.runtime.session_id,
        "execution_binding": binding.model_dump(mode="json"),
    }
    if owner := run.get("hermes_owner_root"):
        profile = manifest.launch_plan.hermes_profile
        root = selected_owner_root(Path(owner))
        if (
            profile is None
            or binding.runtime_root != str(root / "fixture-owner/runtime")
            or profile.prepared_root != root
            or profile.context_id != binding.context_id
            or not profile.project_home_link.is_relative_to(run["project_dir"])
        ):
            raise FixtureError(
                "Managed Hermes fixture did not bind its project and shared test owner"
            )
        lineage["hermes_profile"] = profile.model_dump(mode="json")
    return lineage


def _record_managed_tmux(run: dict[str, Any]) -> None:
    """Capture the managed launch's verified socket and runtime lineage."""

    path = _captured_manifest_path(run)
    identity = run["identity"]
    try:
        manifest = parse_session_manifest_payload(
            load_session_manifest(path).payload, source=str(path)
        )
    except (SessionManifestError, ValueError) as exc:
        raise FixtureError("Cannot read the managed fixture's runtime binding") from exc
    lineage = _manager_lineage(run, manifest)
    assert manifest.tmux is not None
    if manifest.tmux.session_name != identity.get("tmux_session_name"):
        raise FixtureError("Managed fixture manifest does not match the launched session")
    run["tmux_socket_path"] = manifest.tmux.socket_path
    run["manager_lineage"] = lineage
    identity["generation_id"] = manifest.registry_generation_id
    if owner := run.get("hermes_owner_root"):
        root = selected_owner_root(Path(owner))
        run["native_state"] = observe_profile(root, manifest, qualify_owner(root))


def _select_manager_fixture(
    run: dict[str, Any],
) -> tuple[ManagedAgentTarget, VerifiedRegistryManifest]:
    """Verify one captured local fixture with no selector, pair, or name fallback."""

    from houmao.srv_ctrl.commands.managed_agents import (
        VerifiedRegistryManifest,
        read_selected_manifest,
        select_local_managed_agent_record,
    )

    manifest_path = _captured_manifest_path(run)
    identity = run["identity"]
    agent_id = identity.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        raise FixtureError("Managed fixture has no captured agent identity")
    registry = _fixture_registry(run)
    if registry.resolve() != registry:
        raise FixtureError("Managed fixture registry lies outside the private run")
    try:
        record = load_managed_agent_record_by_agent_id(
            agent_id, env={HOUMAO_GLOBAL_REGISTRY_DIR_ENV_VAR: str(registry)}
        )
        if record is None:
            raise FixtureError("Captured managed fixture authority is unavailable")
        if (record.agent_id, record.runtime.manifest_path) != (agent_id, str(manifest_path)):
            raise FixtureError("Registered runtime does not match the captured fixture manifest")
        if record.lifecycle.state not in {"active", "stopped"}:
            raise FixtureError("Captured managed fixture lifecycle is unresolved")
        target = select_local_managed_agent_record(record, agent_ref=agent_id)
        authority = read_selected_manifest(target)
    except FixtureError:
        raise
    except (OSError, ValueError, SessionManifestError, click.ClickException):
        raise FixtureError("Cannot verify the captured managed fixture authority") from None
    if not isinstance(authority, VerifiedRegistryManifest):
        raise FixtureError("Captured managed fixture does not have a local registry authority")
    lineage = _manager_lineage(run, authority.payload)
    saved_lineage = run.get("manager_lineage")
    if saved_lineage is not None and saved_lineage != lineage:
        raise FixtureError("Registered runtime does not match the captured fixture lineage")
    tmux = authority.payload.tmux
    assert tmux is not None
    if tmux.socket_path != run.get("tmux_socket_path"):
        raise FixtureError("Registered runtime does not match the captured fixture socket")
    run["manager_lineage"] = lineage
    return target, authority


def _require_current_manager_fixture(authority: VerifiedRegistryManifest) -> None:
    """Fence an imminent effect to the selected registry generation and local owner."""

    record = authority.record
    require_active_managed_control_manifest(
        authority.manifest_path,
        generation_id=record.generation_id,
        agent_id=record.agent_id,
        execution_binding=record.execution_binding,
    )


def _refresh_manager_snapshot(
    run: dict[str, Any],
    authority: VerifiedRegistryManifest,
    *,
    gateway_status: GatewayStatusV1 | None = None,
) -> None:
    """Update observed metadata while keeping the captured fixture's stable identity."""

    identity = run["identity"]
    manifest = authority.payload
    tmux = manifest.tmux
    assert tmux is not None
    native = manifest.native_surface
    identity["native_surface"] = native.model_dump(mode="json") if native is not None else None
    run["native_surface"] = identity["native_surface"]
    identity["tmux_session_name"] = tmux.session_name
    if (
        identity.get("generation_id") != authority.record.generation_id
        or gateway_status is not None
    ):
        for key in ("gateway_host", "gateway_port", "gateway_tmux_window_index"):
            identity.pop(key, None)
    if gateway_status is not None and gateway_status.gateway_health == "healthy":
        identity["gateway_host"] = gateway_status.gateway_host
        identity["gateway_port"] = gateway_status.gateway_port
    identity["generation_id"] = authority.record.generation_id

    if authority.record.lifecycle.state == "active":
        run["status"] = "launched"
        run.pop("cleanup", None)
        run.pop("gateway_cleanup", None)


def _prepare_manager_prompt(
    run: dict[str, Any],
) -> tuple[ManagedAgentTarget, VerifiedRegistryManifest]:
    """Refresh the captured active runtime and any gateway used for fixture input."""

    from houmao.srv_ctrl.commands.managed_agents import gateway_status

    with command_environment(run_environment(run)):
        target, authority = _select_manager_fixture(run)
        if authority.record.lifecycle.state != "active":
            raise FixtureError("Captured managed fixture is stopped; relaunch it before prompting")
        try:
            _require_current_manager_fixture(authority)
        except (OSError, ValueError, SessionManifestError):
            raise FixtureError("Captured managed fixture generation is no longer active") from None
        status = None
        gateway_failed = False
        if run["configuration"]["client"] != "hermes":
            try:
                status = gateway_status(target)
            except click.ClickException:
                gateway_failed = True
        _refresh_manager_snapshot(run, authority, gateway_status=status)
    _save(run)
    if gateway_failed:
        raise FixtureError("Current fixture gateway authority is unavailable")
    return target, authority


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
    available = True
    if config["client"] == "hermes" and config["surface"] == "manager":
        owner = run.get("hermes_owner_root")
        if not owner:
            raise FixtureError("Prepare a new managed Hermes fixture with a selected test owner")
        prepared = qualify_owner(selected_owner_root(Path(owner)))
        if run["executable"] != prepared.executable:
            raise FixtureError("The prepared Hermes fixture executable has changed")
        run["client_version"] = prepared.evidence.version
    elif config["client"] == "hermes":
        try:
            run["executable"] = resolve_hermes_executable(
                environment=run_environment(run), working_directory=Path(run["workdir"])
            )
        except ValueError:
            available = False
    else:
        available = os.access(run["executable"], os.X_OK)
    if not available:
        run["status"] = "not_run"
        run["prerequisites"] = {"missing": ["client_executable"], "live_requested": True}
        _save(run)
        raise FixtureError("Client executable is unavailable; prepare a fresh fixture run")
    run["status"] = "launching"
    _save(run)
    initial_prompt = False
    try:
        if config["client"] != "hermes":
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

                allow_start = _select_raw_tmux(run)
                with _raw_web_environment(run, allow_start=allow_start):
                    launch_raw_web(run)
            elif config["mode"] == "tui":
                _raw_tui(run, allow_start=_select_raw_tmux(run), timeout=timeout)
            elif config["client"] == "hermes" and config["mode"] == "service":
                _raw_hermes_acp(run, timeout)
            else:
                raise FixtureError("This mode requires the managed fixture surface")
        elif config["surface"] == "manager":
            result = manager_call(
                Path(run["project_dir"]),
                [
                    "agents",
                    "launch",
                    "--profile" if run.get("project_profile") else "--specialist",
                    run.get("project_profile", "fixture-agent"),
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
            _record_managed_tmux(run)
        else:
            run["identity"] = _passive_launch(run, passive_url or "")
            if not run["identity"].get("tracked_agent_id"):
                raise FixtureError("Passive launch did not return an authoritative identity")
        _record_native_surface(run)
        run["status"] = "launched"
        _save(run)
        prompt_after_launch = config["surface"] != "raw" or config["mode"] in {"web", "service"}
        if config["client"] == "hermes" and config["mode"] == "tui":
            prompt_after_launch = True
        if prompt and prompt_after_launch:
            initial_prompt = True
            return prompt_run(path, prompt=prompt, timeout=timeout)
        return public_run(run)
    except (
        BackendExecutionError,
        FixtureError,
        OSError,
        subprocess.SubprocessError,
        TmuxCommandError,
    ) as exc:
        if initial_prompt:
            with suppress(FixtureError):
                observed = load_run(path)
                captured_identity = run.get("identity", {})
                observed_identity = observed.get("identity", {})
                if all(
                    captured_identity.get(key) == observed_identity.get(key)
                    for key in ("agent_id", "manifest_path", "tracked_agent_id")
                ):
                    run = observed
        elif isinstance(exc, ManagedCommandError) and (
            exc.payload.get("agent_id") or exc.payload.get("manifest_path")
        ):
            run["identity"] = dict(exc.payload)
            run["identity"].pop("gateway_auto_attach_error", None)
            if exc.payload.get("agent_id") and exc.payload.get("manifest_path"):
                with suppress(FixtureError, OSError):
                    _record_managed_tmux(run)
        if isinstance(exc, ManagedCommandError):
            run.update(exc.diagnostic_reference())
        run["status"] = "launch_failed"
        run["error"] = "Launch failed; private run state retained for inspection"
        _save(run)
        try:
            _cleanup(run)
        except ManagedCommandError as cleanup_error:
            if diagnostic_path := cleanup_error.diagnostic_reference().get("diagnostic_path"):
                run["cleanup_diagnostic_path"] = diagnostic_path
        except FixtureError:
            pass
        run["status"] = "launch_failed"
        _save(run)
        message = f"Launch failed; inspect {path / 'report.json'}"
        if isinstance(exc, ManagedCommandError):
            raise exc.with_message(message) from exc
        raise FixtureError(message) from exc


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
    config = run["configuration"]
    manager_selection = None
    if config["surface"] == "manager" and run.get("identity"):
        manager_selection = _prepare_manager_prompt(run)
    elif run["status"] != "launched":
        raise FixtureError("Prompt requires a launched run")
    identity = run.get("identity", {})
    if config["surface"] == "raw":
        if config["mode"] == "web":
            from fixturelib.web import prompt_raw_web

            try:
                with _raw_web_environment(run):
                    prompt_raw_web(run, prompt, timeout)
            finally:
                _save(run)
        elif config["mode"] == "headless":
            if not identity.get("provider_session_id"):
                raise FixtureError("Raw continuation requires a captured provider session ID")
            _raw_turn(run, prompt, timeout)
        elif config["client"] == "hermes" and config["mode"] == "service":
            from fixturelib.hermes import raw_acp_prompt

            worker = run.get("active_process", {})
            if not worker.get("birth") or _process_birth(worker["pid"]) != worker["birth"]:
                raise FixtureError("Raw Hermes ACP worker is unavailable")
            run.setdefault("turns", []).append(raw_acp_prompt(run, prompt, timeout))
        else:
            server = _fixture_tmux(run)
            if _owned_raw_tui_session(run, server) is None:
                raise FixtureError("Raw fixture session is unavailable")
            target = identity["native_surface"]["pane_id"]
            panes = server.observe_session(identity["tmux_session_name"])
            if panes is None or not any(
                pane.pane_id == target and not pane.pane_dead for pane in panes
            ):
                raise FixtureError("Raw fixture primary pane is unavailable")
            buffer_name = f"houmao-fixture-{uuid4().hex}"
            try:
                server.load_buffer(buffer_name, prompt)
                server.paste_buffer(
                    buffer_name, target, bracketed=False, delete_after=True, raw_newlines=True
                )
            except TmuxCommandError:
                with suppress(TmuxCommandError):
                    server.delete_buffer(buffer_name)
                raise
            time.sleep(0.25)
            server.send_keys(target, "Enter")
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
    elif config["client"] == "hermes":
        from houmao.srv_ctrl.commands.managed_agents import prompt_managed_agent

        if manager_selection is None:
            raise FixtureError("Managed fixture has no captured agent identity")
        target, authority = manager_selection

        def send_selected_prompt() -> object:
            """Submit once to the exact runtime generation read by the fixture."""

            _require_current_manager_fixture(authority)
            return prompt_managed_agent(target, prompt=prompt)

        receipt = manager_selected_call(
            "prompt",
            send_selected_prompt,
            env=run_environment(run),
            private_values=(prompt,),
        )
        delivery = receipt.get("delivery_state", "uncertain")
        run.setdefault("turns", []).append(
            {"request_id": receipt.get("request_id"), "status": delivery}
        )
        if not receipt.get("success") or delivery not in {"queued", "handed_off", "completed"}:
            _save(run)
            raise FixtureError("Managed Hermes prompt outcome was not verified")
    else:
        if manager_selection is None:
            raise FixtureError("Managed fixture has no captured agent identity")
        _, authority = manager_selection
        generation = authority.record.generation_id

        def selected_gateway_request(
            route: str, body: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            """Keep input and follow-up reads on the same verified generation."""

            if body is not None:
                try:
                    with command_environment(run_environment(run)):
                        _require_current_manager_fixture(authority)
                except (OSError, ValueError, SessionManifestError):
                    raise FixtureError(
                        "Captured managed fixture generation changed before input"
                    ) from None
            return _gateway_request(run, route, body, generation_id=generation)

        if config["mode"] == "tui":
            selected_gateway_request(
                "/v1/control/send-keys", {"sequence": prompt, "escape_special_keys": True}
            )
            time.sleep(0.25)
            selected_gateway_request("/v1/control/send-keys", {"sequence": "<[Enter]>"})
        else:
            before = selected_gateway_request("/v1/usage")
            previous = {record["record_id"] for record in before["records"]}
            accepted = selected_gateway_request("/v1/control/prompt", {"prompt": prompt})
            require_operation_id = (
                config["mode"] in {"service", "web"} or run.get("backend") == "dsh_headless"
            )
            operation_id = accepted.get("operation_id") if require_operation_id else None
            if require_operation_id and (not isinstance(operation_id, str) or not operation_id):
                raise FixtureError("Managed prompt has no exact admitted operation identity")
            deadline = time.monotonic() + timeout
            while True:
                usage = selected_gateway_request("/v1/usage")
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
            while selected_gateway_request("/v1/status").get("active_execution") == "running":
                if time.monotonic() >= deadline:
                    raise FixtureError(
                        "Completed usage is available but the current execution has not settled"
                    )
                time.sleep(0.05)
    _save(run)
    return public_run(run)


def _stop_manager_fixture(run: dict[str, Any]) -> None:
    """Stop the verified captured generation or confirm that it already stopped."""

    from houmao.srv_ctrl.commands.managed_agents import stop_managed_agent

    env = run_environment(run)
    with command_environment(env):
        target, authority = _select_manager_fixture(run)
    _refresh_manager_snapshot(run, authority)
    if authority.record.lifecycle.state == "stopped":
        return

    def stop_selected() -> object:
        """Use the normal manager stop, including its current gateway teardown."""

        _require_current_manager_fixture(authority)
        result = stop_managed_agent(target)
        if not result.success:
            raise click.ClickException(result.detail)
        return result

    manager_selected_call("stop", stop_selected, env=env)


def _cleanup(run: dict[str, Any]) -> None:
    """Stop only identities captured by this run; preserve its private evidence."""

    identity = run.get("identity", {})
    config = run["configuration"]
    stopped_owned = bool(identity)
    if config["surface"] == "manager" and identity:
        try:
            _stop_manager_fixture(run)
        except FixtureError:
            run["cleanup"] = "failed_requires_scoped_follow_up"
            raise
        run["cleanup"] = "stopped_owned_identity"
        return
    try:
        if config["surface"] == "raw" and config["mode"] == "web":
            if run.get("raw_web_state"):
                from fixturelib.web import control_raw_web

                with _raw_web_environment(run):
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
        elif config["surface"] == "passive-server" and identity.get("tracked_agent_id"):
            ref = quote(identity["tracked_agent_id"], safe="")
            _http(identity["passive_url"], f"/houmao/agents/{ref}/stop", {})
        elif config["surface"] == "raw" and (
            run.get("raw_tmux_owner") or identity.get("tmux_session_name")
        ):
            server = _fixture_tmux(run)
            session_id = _owned_raw_tui_session(run, server)
            if session_id is not None:
                server.checked_command(["kill-session", "-t", session_id], no_start=True)
                stopped_owned = True
        if config["surface"] == "raw" and config["client"] == "hermes":
            from fixturelib.hermes import raw_hermes_daemon

            raw_hermes_daemon(run, run_environment(run)).stop()
        run["cleanup"] = "stopped_owned_identity" if stopped_owned else "no_owned_identity"
    except (
        BackendExecutionError,
        FixtureError,
        OSError,
        subprocess.SubprocessError,
        TmuxCommandError,
    ):
        run["cleanup"] = "failed_requires_scoped_follow_up"


def stop_run(path: Path) -> dict[str, Any]:
    """Stop captured owned identities and keep metadata inspectable."""

    run = load_run(path)
    captured_manager = run["configuration"]["surface"] == "manager" and bool(run.get("identity"))
    if not captured_manager and (
        run["status"] == "stopped" or run.get("cleanup") == "stopped_owned_identity"
    ):
        run["status"] = "stopped"
        _save(run)
        return public_run(run)
    try:
        _cleanup(run)
    except FixtureError as exc:
        if isinstance(exc, ManagedCommandError):
            run.update(exc.diagnostic_reference())
        _save(run)
        raise
    if run["cleanup"] == "failed_requires_scoped_follow_up":
        _save(run)
        raise FixtureError("Cleanup failed; use the captured identity for scoped follow-up")
    run["status"] = "stopped"
    _save(run)
    return public_run(run)


def probe_configuration(config: ResolvedConfig) -> dict[str, str | int]:
    """Probe selected API routing without sending a turn or following redirects."""

    if config.auth_method == "native-login":
        validate_native_bundle(config)
        return {"status": "import_validated"}
    assert config.base_url is not None
    base = config.base_url
    key = config.api_key.get_secret_value()
    headers = {}
    if config.protocol == "anthropic_messages":
        if not base.endswith("/v1"):
            base += "/v1"
        headers["anthropic-version"] = "2023-06-01"
        if config.client == "dsh":
            headers["x-api-key"] = key
        else:
            headers["Authorization"] = f"Bearer {key}"
    elif config.protocol == "google_generative_ai":
        if not base.endswith(("/v1", "/v1beta")):
            base += "/v1beta"
        headers["x-goog-api-key"] = key
    else:
        headers["Authorization"] = f"Bearer {key or 'houmao-local-no-auth'}"
    try:
        with httpx.stream(
            "GET", base + "/models", headers=headers, follow_redirects=False, timeout=10
        ) as response:
            status = response.status_code
    except (httpx.HTTPError, ValueError):
        raise FixtureError("Selected model API endpoint could not be reached") from None
    if 200 <= status < 300:
        return {"status": "models_route_available", "http_status": status}
    if status in {404, 405}:
        return {"status": "endpoint_reachable", "http_status": status}
    raise FixtureError(f"Selected model API endpoint returned HTTP {status} to its models probe")


def check_run(path: Path, *, live: bool = False) -> dict[str, Any]:
    """Inspect a prepared run offline; contact only its authority when explicitly asked."""

    run = load_run(path)
    root = Path(run["run_dir"])
    config = run["configuration"]
    missing = []
    owner = run.get("hermes_owner_root")
    installation = None
    if owner:
        try:
            installation = qualify_owner(selected_owner_root(Path(owner)))
        except FixtureError:
            if live:
                raise
            missing.append("prepared_hermes_installation")
    elif config["client"] == "hermes":
        try:
            resolve_hermes_executable(working_directory=Path(run["workdir"]))
        except ValueError:
            missing.append("client_executable")
    elif not os.access(run["executable"], os.X_OK):
        missing.append("client_executable")
    local_tmux = config["surface"] == "manager" or (
        config["surface"] == "raw" and config["mode"] in {"tui", "web"}
    )
    if local_tmux and shutil.which("tmux") is None:
        missing.append("tmux")
    if not (root / "private-env.json").is_file():
        missing.append("private_environment")
    run["prerequisites"] = {"missing": missing, "live_requested": live}
    if live:
        identity = run.get("identity", {})
        if config["mode"] == "web" and config["surface"] == "raw":
            from fixturelib.web import observe_raw_web

            with _raw_web_environment(run):
                run["native_state"] = observe_raw_web(run)
        elif identity.get("passive_url"):
            ref = quote(identity["tracked_agent_id"], safe="")
            run["usage"] = _http(identity["passive_url"], f"/houmao/agents/{ref}/usage")
        elif config["surface"] == "manager" and identity.get("agent_id"):
            scope = ["agents", "single", "--agent-id", identity["agent_id"]]
            env = run_environment(run)
            if config["client"] == "hermes":
                state = manager_root_call([*scope, "state"], env=env)
                native_state = {
                    "mode": config["mode"],
                    "availability": state.get("availability"),
                }
                if installation is not None:
                    with command_environment(env):
                        _, authority = _select_manager_fixture(run)
                    if authority.record.lifecycle.state == "active":
                        native_state.update(
                            observe_profile(installation.root, authority.payload, installation)
                        )
                        native_state["native_availability"] = "verified"
                run["native_state"] = native_state
            else:
                status = manager_root_call([*scope, "gateway", "status"], env=env)
                if status.get("gateway_health") == "healthy" and status.get("gateway_port"):
                    live_identity = {**identity, "gateway_port": status["gateway_port"]}
                    run["usage"] = _gateway_request({**run, "identity": live_identity}, "/v1/usage")
                else:
                    manager_root_call([*scope, "state"], env=env)
        elif config["surface"] == "raw" and config["client"] == "hermes":
            from fixturelib.hermes import raw_hermes_daemon

            try:
                daemon = raw_hermes_daemon(run, run_environment(run)).discover()
            except BackendExecutionError as exc:
                raise FixtureError("Raw Hermes native daemon is unavailable") from exc
            if daemon is None:
                raise FixtureError("Raw Hermes native daemon is unavailable")
            if config["mode"] == "tui" and _owned_raw_tui_session(run, _fixture_tmux(run)) is None:
                raise FixtureError("Raw Hermes TUI session is unavailable")
            if config["mode"] == "service":
                worker = run.get("active_process", {})
                if not worker.get("birth") or _process_birth(worker["pid"]) != worker["birth"]:
                    raise FixtureError("Raw Hermes ACP worker is unavailable")
            run["native_state"] = {"mode": config["mode"], "availability": "observed"}
        elif identity.get("tmux_session_name"):
            if _owned_raw_tui_session(run, _fixture_tmux(run)) is None:
                raise FixtureError("Fixture tmux session is missing")
        elif config["surface"] != "raw":
            raise FixtureError("Live check requires a launched authority identity")
    _save(run)
    return public_run(run)
