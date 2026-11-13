"""Launch explicitly prepared clients and retain private, identity-scoped evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
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

from fixturelib.auth import private_write, write_json
from fixturelib.config import FixtureError
from fixturelib.prepare import (
    ManagedCommandError,
    command_environment,
    isolated_environment,
    load_run,
    manager_call,
    manager_root_call,
    _PROVIDER_PREFIXES,
)


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
    env = isolated_environment(selected, run_dir=root)
    if shutil.which("tmux") and (
        run["configuration"]["mode"] == "tui" or run["configuration"]["surface"] != "raw"
    ):
        inherited = subprocess.run(
            ["tmux", "show-environment", "-g"], capture_output=True, text=True, timeout=5
        )
        for line in inherited.stdout.splitlines():
            name = line.partition("=")[0].removeprefix("-")
            if name.startswith(_PROVIDER_PREFIXES) and name not in env:
                env[name] = ""
    if run["configuration"]["mode"] == "tui":
        env[f"HOUMAO_HOOK_OBSERVATION_{run['configuration']['client'].upper()}"] = "1"
    return env


def public_run(run: dict[str, Any]) -> dict[str, Any]:
    """Select report fields that exclude private native output and env values."""

    fields = (
        "schema_version",
        "status",
        "run_dir",
        "configuration",
        "identity",
        "turns",
        "error",
        "cleanup",
        "gateway_cleanup",
        "prerequisites",
        "usage",
        "client_version",
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


def raw_command(run: dict[str, Any], *, prompt: str | None = None) -> list[str]:
    """Build current native argv; Kimi prompt mode deliberately omits --auto."""

    client = run["configuration"]["client"]
    command = [run["executable"]]
    model = run["configuration"].get("model")
    session = run.get("identity", {}).get("provider_session_id")
    if client == "claude":
        command += ["--dangerously-skip-permissions"]
        if model:
            command += ["--model", model]
        if prompt is not None:
            command += ["-p", "--verbose", "--output-format", "stream-json"]
            if session:
                command += ["--resume", session]
            command += [prompt]
    elif client == "codex":
        command += ["--dangerously-bypass-approvals-and-sandbox"]
        if model:
            command += ["--model", model]
        if prompt is not None:
            command += ["exec", "--json", "--skip-git-repo-check"]
            if session:
                command += ["resume", session]
            command += [prompt]
    else:
        if prompt is None:
            command += ["--auto"]
        else:
            command += ["--output-format", "stream-json"]
            if session:
                command += ["--session", session]
            command += ["-p", prompt]
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


def _raw_turn(run: dict[str, Any], prompt: str, timeout: float) -> None:
    """Capture raw client output privately, terminating only the owned process group."""

    root = Path(run["run_dir"])
    index = len(run.get("turns", [])) + 1
    stdout = root / f"raw-turn-{index}.jsonl"
    stderr = root / f"raw-turn-{index}.stderr"
    private_write(stdout, b"")
    private_write(stderr, b"")
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen(
            raw_command(run, prompt=prompt),
            cwd=run["workdir"],
            env=run_environment(run),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
            umask=0o077,
        )
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = process.returncode
        run.setdefault("turns", []).append({"index": index, "returncode": code})
    session = _session_id(stdout, run["configuration"]["client"])
    if session:
        run.setdefault("identity", {})["provider_session_id"] = session
    _save(run)
    if code != 0:
        raise FixtureError("Raw client turn failed; inspect private stdout/stderr captures")


def _raw_tui(run: dict[str, Any]) -> None:
    """Start one named tmux session with bindings sourced from a private script."""

    name = "fixture-" + Path(run["run_dir"]).name
    command = [sys.executable, str(Path(__file__).with_name("raw_child.py")), run["run_dir"]]
    subprocess.run(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            name,
            "-c",
            run["workdir"],
            shlex.join(command),
        ],
        check=True,
        capture_output=True,
    )
    run["identity"] = {"tmux_session_name": name}


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
        # Only version lines with the expected client marker can enter reports.
        line = version.stdout.strip().splitlines()
        if version.returncode == 0 and line and len(line[0]) < 120:
            run["client_version"] = line[0]
        if config["surface"] == "raw":
            if config["mode"] == "headless":
                _raw_turn(run, prompt or "", timeout)
            else:
                _raw_tui(run)
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
                    "--headless" if config["mode"] == "headless" else "--no-headless",
                ],
                env=run_environment(run),
            )
            run["identity"] = result
            if not result.get("agent_id") or not result.get("manifest_path"):
                raise FixtureError("Managed launch did not return an authoritative identity")
        else:
            run["identity"] = _passive_launch(run, passive_url or "")
            if not run["identity"].get("tracked_agent_id"):
                raise FixtureError("Passive launch did not return an authoritative identity")
        run["status"] = "launched"
        _save(run)
        if prompt and config["surface"] != "raw":
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


def prompt_run(path: Path, *, prompt: str, timeout: float = 300) -> dict[str, Any]:
    """Continue an owned raw or managed headless session, or send direct TUI input."""

    run = load_run(path)
    if run["status"] != "launched":
        raise FixtureError("Prompt requires a launched run")
    config = run["configuration"]
    identity = run.get("identity", {})
    if config["surface"] == "raw":
        if config["mode"] == "headless":
            if not identity.get("provider_session_id"):
                raise FixtureError("Raw continuation requires a captured provider session ID")
            _raw_turn(run, prompt, timeout)
        else:
            target = identity["tmux_session_name"]
            subprocess.run(["tmux", "send-keys", "-t", target, "-l", prompt], check=True)
            time.sleep(0.25)
            subprocess.run(["tmux", "send-keys", "-t", target, "Enter"], check=True)
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
        base = f"http://{identity['gateway_host']}:{identity['gateway_port']}"
        if config["mode"] == "tui":
            _http(base, "/v1/control/send-keys", {"sequence": prompt, "escape_special_keys": True})
            time.sleep(0.25)
            _http(base, "/v1/control/send-keys", {"sequence": "<[Enter]>"})
        else:
            before = _http(base, "/v1/usage")
            previous = {record["record_id"] for record in before["records"]}
            _http(base, "/v1/control/prompt", {"prompt": prompt})
            deadline = time.monotonic() + timeout
            while True:
                usage = _http(base, "/v1/usage")
                rows = [
                    record for record in usage["records"] if record["record_id"] not in previous
                ]
                if rows:
                    break
                if time.monotonic() >= deadline:
                    raise FixtureError(
                        "Headless turn timed out; inspect usage and stop the captured run"
                    )
                time.sleep(0.25)
            run["usage"] = usage
            run.setdefault("turns", []).append(
                {"record_id": rows[0]["record_id"], "status": rows[0]["outcome"]}
            )
            if rows[0]["outcome"] != "completed":
                _save(run)
                raise FixtureError("Managed headless turn did not complete; inspect public usage")
    _save(run)
    return public_run(run)


def _cleanup(run: dict[str, Any]) -> None:
    """Stop only identities captured by this run; preserve its private evidence."""

    identity = run.get("identity", {})
    config = run["configuration"]
    try:
        if config["surface"] == "manager" and identity.get("agent_id"):
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
                ["tmux", "kill-session", "-t", identity["tmux_session_name"]],
                check=True,
                capture_output=True,
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
    if run["status"] == "stopped":
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
    if not Path(run["executable"]).is_file():
        missing.append("client_executable")
    if (
        run["configuration"]["mode"] == "tui" or run["configuration"]["surface"] != "raw"
    ) and shutil.which("tmux") is None:
        missing.append("tmux")
    if not (root / "private-env.json").is_file():
        missing.append("private_environment")
    run["prerequisites"] = {"missing": missing, "live_requested": live}
    if live:
        identity = run.get("identity", {})
        if identity.get("passive_url"):
            ref = quote(identity["tracked_agent_id"], safe="")
            run["usage"] = _http(identity["passive_url"], f"/houmao/agents/{ref}/usage")
        elif identity.get("gateway_port"):
            run["usage"] = _http(
                f"http://{identity['gateway_host']}:{identity['gateway_port']}", "/v1/usage"
            )
        elif identity.get("tmux_session_name"):
            subprocess.run(
                ["tmux", "has-session", "-t", identity["tmux_session_name"]],
                check=True,
                capture_output=True,
            )
        elif run["configuration"]["surface"] != "raw":
            raise FixtureError("Live check requires a launched authority identity")
    _save(run)
    return public_run(run)
