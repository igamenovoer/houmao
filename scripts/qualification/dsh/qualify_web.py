"""Qualify an explicitly chosen live Web provider with separate browser/API peers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts/agents/test-fixtures"))

from houmao.agents.realm_controller.backends.dsh_web_client import DshWebClient  # noqa: E402
from fixturelib.auth import private_write, validate_external_path  # noqa: E402
from fixturelib.config import FixtureError, resolve_config  # noqa: E402
from fixturelib.launch import (  # noqa: E402
    check_run,
    interrupt_run,
    launch_run,
    prompt_run,
    run_environment,
    stop_run,
)
from fixturelib.prepare import load_run, manager_root_call, prepare_run  # noqa: E402
from fixturelib.web import browser_connection_file  # noqa: E402
from tests.integration.agents.dsh.web.browser import NativeBrowser  # noqa: E402


def _binding(root: Path) -> dict[str, Any]:
    """Read only the exact captured managed Web binding without native activation."""

    run = load_run(root)
    manifest = json.loads(Path(run["identity"]["manifest_path"]).read_text())
    return dict(manifest["backend_state"])


def _connect(root: Path) -> tuple[DshWebClient, NativeBrowser, dict[str, Any]]:
    """Open independent peers using a deliberately requested private local handoff."""

    handoff = browser_connection_file(load_run(root))
    connection = json.loads(handoff.read_text())
    client = DshWebClient.from_connection(
        connection["origin"], launch_token=connection["launch_token"]
    )
    try:
        browser = NativeBrowser.from_connection_file(handoff)
    except BaseException:
        client.close()
        raise
    identity = _binding(root)["web_identity"]
    if browser.metadata["session_id"] != identity["native_session_id"]:
        browser.close()
        client.close()
        raise FixtureError("Browser selection differs from the captured native binding")
    return client, browser, identity


def _wait_turn(
    client: DshWebClient,
    identity: dict[str, Any],
    *,
    after_turn: int,
    timeout: float,
    active: bool = False,
) -> dict[str, Any]:
    """Inspect native progress once per poll without repeating a prompt or lifecycle action."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = client.state(identity)
        running = snapshot.get("active_turn")
        if active and running is not None and running["turn"] > after_turn:
            return snapshot
        terminal = snapshot.get("last_turn") or {}
        if not active and terminal.get("turn", 0) > after_turn and running is None:
            return snapshot
        time.sleep(0.1)
    raise FixtureError("Selected native Web activity did not reach the required boundary")


def _build_identity(executable: Path) -> dict[str, Any]:
    """Identify tested bytes while excluding local installation and reference paths."""

    inspected = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools/dsh/prepare.py"),
            "inspect",
            "--executable",
            str(executable),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(inspected.stdout)
    return {
        "source_revision": payload["source"]["revision"],
        "source_version": payload["source"]["version"],
        **{
            key: payload[key]
            for key in [
                "executable_sha256",
                "package_version",
                "reported_version",
                "dsh_package_code_sha256",
                "runtime_source_revision",
                "provenance",
            ]
        },
    }


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    """Run only deliberately selected paid requests and publish sanitized factual outcomes."""

    report: dict[str, Any] = {
        "schema_version": 1,
        "case": args.case,
        "surface": "manager",
        "mode": "web",
        "backend": "dsh_web",
        "native_surface": "web",
        "status": "not_run",
        "checks": {},
        "limits": [],
        "operator_prompt_mode": "unattended",
    }
    if args.case == "cloud-api":
        report["self_hosted"] = {
            "status": "not_run",
            "reason": "No self-hosted deployment/model was selected; qualify that case separately",
        }
    if args.env_file is None:
        report["reason"] = (
            "Select an explicit external --env-file; ambient credentials are disabled"
        )
        return report
    config = resolve_config(
        case=args.case,
        client="dsh",
        mode="web",
        surface="manager",
        env_file=args.env_file,
        model=args.model,
    )
    report.update(
        {
            "model": config.model,
            "protocol": config.protocol,
            "adapter": config.dsh.adapter if config.dsh else None,
        }
    )
    report["configuration_valid"] = True
    if args.check_only:
        report["reason"] = (
            "Offline explicit Web configuration validated; no provider request executed"
        )
        return report
    if args.executable is None:
        report["reason"] = "Select the qualified DSH executable with --executable"
        return report
    report["runtime_build"] = _build_identity(args.executable)
    roots: list[Path] = []
    browser: NativeBrowser | None = None
    observer: DshWebClient | None = None
    try:
        primary = prepare_run(
            config, run_root=args.run_root, executable=str(args.executable), tmux_server="new"
        )
        root = Path(primary["run_dir"])
        roots.append(root)
        launch_run(
            root,
            prompt="Use the bash tool to write exactly API_TOOL_OK into web-api-tool.txt, then reply API_COMPLETE.",
            timeout=args.timeout,
        )
        if (root / "workdir/web-api-tool.txt").read_text().strip() != "API_TOOL_OK":
            raise FixtureError("Native API shell-tool oracle did not match")
        report["checks"]["api_tool_complete"] = "passed"
        observer, browser, identity = _connect(root)
        report["browser"] = browser.metadata
        report["native_protocol_version"] = observer.describe()["protocol_version"]
        before = observer.state(identity)["last_turn"]["turn"]
        browser.call(
            "submit",
            text="Use the bash tool to write exactly BROWSER_TOOL_OK into web-browser-tool.txt, then reply BROWSER_COMPLETE.",
        )
        settled = _wait_turn(observer, identity, after_turn=before, timeout=args.timeout)
        if (
            settled["last_turn"]["result"] != "completed"
            or (root / "workdir/web-browser-tool.txt").read_text().strip() != "BROWSER_TOOL_OK"
        ):
            raise FixtureError("Native browser shell-tool oracle did not match")
        report["checks"]["browser_tool_complete"] = "passed"
        prompt_run(
            root,
            prompt="Read web-api-tool.txt and web-browser-tool.txt with a tool, then reply CONTINUED.",
            timeout=args.timeout,
        )
        if _binding(root)["web_identity"] != identity:
            raise FixtureError("API/browser continuation changed the bound native identity")
        report["checks"]["exact_continuation"] = "passed"
        usage = check_run(root, live=True)["usage"]["records"]
        if not any(
            row["turn_origin"] == "native_observed"
            and row["outcome"] == "completed"
            and row["token_usage"]["total_tokens"]["value"] is not None
            for row in usage
        ):
            raise FixtureError("Completed human-origin journal usage was not available")
        report["checks"]["human_usage"] = "passed"
        before = observer.state(identity)["last_turn"]["turn"]
        browser.call(
            "submit", text="Use the bash tool to run sleep 30 and wait for it before replying."
        )
        active = _wait_turn(
            observer, identity, after_turn=before, timeout=args.timeout, active=True
        )
        interrupt_run(root)
        interrupted = _wait_turn(observer, identity, after_turn=before, timeout=args.timeout)
        if (
            interrupted["last_turn"]["turn"] != active["active_turn"]["turn"]
            or interrupted["last_turn"]["result"] != "aborted"
        ):
            raise FixtureError("Interruption did not settle the exact human-started turn")
        report["checks"]["human_turn_interruption"] = "passed"
        browser.close()
        observer.close()
        browser = observer = None
        selected = load_run(root)
        manager_root_call(
            [
                "agents",
                "single",
                "--agent-id",
                selected["identity"]["agent_id"],
                "relaunch",
                "--chat-session-mode",
                "exact",
                "--chat-session-id",
                identity["native_session_id"],
            ],
            env=run_environment(selected),
        )
        restored = _binding(root)["web_identity"]
        if (
            restored["native_session_id"] != identity["native_session_id"]
            or restored["host_incarnation"] == identity["host_incarnation"]
            or restored["agent_incarnation"] == identity["agent_incarnation"]
        ):
            raise FixtureError(
                "Explicit relaunch did not preserve session and replace execution identity"
            )
        prompt_run(
            root,
            prompt="Read web-browser-tool.txt with a tool and reply RESTORED.",
            timeout=args.timeout,
        )
        report["checks"]["exact_host_relaunch"] = "passed"
        other = prepare_run(
            config, run_root=args.run_root, executable=str(args.executable), tmux_server="new"
        )
        other_root = Path(other["run_dir"])
        roots.append(other_root)
        launch_run(other_root, prompt="Reply ISOLATED. Do not use tools.", timeout=args.timeout)
        if (
            _binding(other_root)["web_identity"]["native_session_id"]
            == identity["native_session_id"]
            or other["home_path"] == primary["home_path"]
        ):
            raise FixtureError("Two Web fixtures shared a home or native conversation")
        report["checks"]["two_isolated_homes"] = "passed"
        report["status"] = "passed"
    except (FixtureError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        report["status"] = "failed"
        report["error"] = type(exc).__name__
        report["reason"] = (
            "Inspect the external private run evidence; no prompt or lifecycle action was retried"
        )
    finally:
        if browser is not None:
            browser.close()
        if observer is not None:
            observer.close()
        for root in reversed(roots):
            try:
                stop_run(root)
            except (FixtureError, OSError):
                report["status"] = "failed"
                report["limits"].append("Owned cleanup failed; use the captured private authority")
        report["private_runs"] = [str(root) for root in roots]
    return report


def main() -> int:
    """Require an explicit credential choice before any native host or paid request."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("cloud-api", "self-hosted"), default="cloud-api")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    output = None
    try:
        output = validate_external_path(args.output) if args.output is not None else None
        report = qualify(args)
    except (FixtureError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        report = {
            "schema_version": 1,
            "status": "not_run",
            "native_surface": "web",
            "error": type(exc).__name__,
            "reason": "Selected configuration or runtime prerequisite is unavailable",
        }
    rendered = json.dumps(report, indent=2) + "\n"
    if output is not None:
        private_write(output, rendered.encode())
    print(rendered, end="")
    return (
        0
        if report["status"] == "passed"
        or (args.check_only and report.get("configuration_valid") is True)
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
