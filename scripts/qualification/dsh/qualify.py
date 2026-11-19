"""Qualify native DSH one-shot execution with an explicitly selected model route."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any

_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "scripts/agents/test-fixtures"))

from fixturelib.auth import private_write, validate_external_path  # noqa: E402
from fixturelib.config import FixtureError, fixture_run_mode, resolve_config  # noqa: E402
from fixturelib.launch import (  # noqa: E402
    check_run,
    interrupt_run,
    launch_run,
    prompt_run,
    stop_run,
)
from fixturelib.prepare import load_run, prepare_run  # noqa: E402


def _native_identity(run_dir: Path) -> tuple[str, str]:
    """Read the exact saved native binding without invoking any native lifecycle."""

    run = load_run(run_dir)
    if run["configuration"]["surface"] == "raw":
        return run["identity"]["provider_session_id"], run["home_path"]
    manifest = json.loads(Path(run["identity"]["manifest_path"]).read_text())
    native = manifest.get("headless", {}).get("session_id") or manifest.get(
        "backend_state", {}
    ).get("session_id")
    home = manifest["launch_plan"]["home_selector"]["home_path"]
    if not isinstance(native, str) or not native:
        raise FixtureError("Qualification found no persisted exact native session")
    return native, home


def _new_native_work(run_dir: Path, earlier: set[Path], *, raw: bool) -> bool:
    """Require native start evidence from the new attempt before cancellation."""

    name = "raw-turn-*.jsonl" if raw else "dsh-native-evidence.jsonl"
    for path in run_dir.rglob(name):
        if path in earlier:
            continue
        for line in path.read_text().splitlines(keepends=True):
            if not line.endswith("\n"):
                continue
            event = json.loads(line)
            if raw and event.get("type") == "status" and event.get("phase") == "turn_start":
                return True
            if not raw and event.get("event") == "claimed":
                return True
    return False


def _interrupt_attempt(run_dir: Path, timeout: float) -> None:
    """Exercise native cancellation without signalling a shared process or server."""

    raw = load_run(run_dir)["configuration"]["surface"] == "raw"
    earlier = set(run_dir.rglob("raw-turn-*.jsonl" if raw else "dsh-native-evidence.jsonl"))
    stdout, stderr = (
        run_dir / "interrupt-controller.stdout",
        run_dir / "interrupt-controller.stderr",
    )
    private_write(stdout, b"")
    private_write(stderr, b"")
    with stdout.open("wb") as out, stderr.open("wb") as err:
        process = subprocess.Popen(
            [
                sys.executable,
                str(_REPO / "scripts/agents/test-fixtures/fixture.py"),
                "prompt",
                "--run-dir",
                str(run_dir),
                "--timeout",
                str(timeout),
                "--prompt",
                "Use the shell tool to run sleep 30. Wait for it to finish before replying.",
            ],
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + timeout
            while not _new_native_work(run_dir, earlier, raw=raw):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise FixtureError("Cancellation qualification did not reach a native claim")
                time.sleep(0.1)
            interrupt_run(run_dir)
            process.wait(timeout=timeout)
            latest = load_run(run_dir)["turns"][-1]
            if latest.get("status") != "interrupted":
                raise FixtureError("Native cancellation did not preserve an interrupted outcome")
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    """Run selected live checks, returning only metadata and explicit limitations."""

    report: dict[str, Any] = {
        "schema_version": 1,
        "case": args.case,
        "surface": args.surface,
        "mode": "headless",
        "backend": None,
        "native_surface": None,
        "status": "not_run",
        "checks": {},
        "limits": ["Interactive Web is not qualified by this headless run"],
    }
    if args.case == "cloud-api":
        report["self_hosted"] = {
            "status": "not_run",
            "reason": "Run separately with an explicitly configured compatible self-hosted env file and model",
        }
    try:
        selection = fixture_run_mode("dsh", "headless", args.surface)
    except FixtureError as error:
        report["reason"] = str(error)
        report["error"] = "unsupported_run_mode"
        return report
    report["backend"] = selection.backend
    if args.env_file is None:
        report["reason"] = (
            "Select an explicit external --env-file; ambient credentials are disabled"
        )
        return report
    config = resolve_config(
        case=args.case,
        client="dsh",
        mode=selection.mode,
        surface=args.surface,
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
    if args.check_only:
        report["reason"] = "Offline configuration validated; no live provider request executed"
        return report
    if args.executable is None:
        report["reason"] = "Select the qualified DSH executable with --executable"
        return report
    identity = subprocess.run(
        [
            sys.executable,
            str(_REPO / "tools/dsh/prepare.py"),
            "inspect",
            "--executable",
            str(args.executable),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    report["runtime_build"] = json.loads(identity.stdout)
    runs: list[Path] = []
    try:
        primary = prepare_run(config, run_root=args.run_root, executable=str(args.executable))
        root = Path(primary["run_dir"])
        runs.append(root)
        launch_run(
            root,
            passive_url=args.passive_url,
            prompt="Use the shell tool to write exactly DSH_TOOL_OK into qualification-tool.txt, then reply DONE.",
            timeout=args.timeout,
        )
        if (root / "workdir/qualification-tool.txt").read_text().strip() != "DSH_TOOL_OK":
            raise FixtureError("Native tool result did not satisfy its explicit oracle")
        first_id, first_home = _native_identity(root)
        report["checks"]["prompt_tool_complete"] = "passed"
        prompt_run(
            root,
            prompt="Read qualification-tool.txt with a tool and report its contents.",
            timeout=args.timeout,
        )
        resumed_id, _ = _native_identity(root)
        if first_id != resumed_id:
            raise FixtureError("Exact continuation changed the selected native session")
        report["checks"]["exact_resume"] = "passed"
        if args.surface == "raw":
            report["checks"]["usage"] = "not_run"
            report["limits"].append(
                "Raw native execution does not establish managed usage-route acceptance"
            )
        else:
            usage = check_run(root, live=True).get("usage", {})
            records = usage.get("records", [])
            if len(records) < 2 or not any(
                row.get("token_usage", {}).get("total_tokens", {}).get("value") is not None
                for row in records
            ):
                raise FixtureError("Managed journal consumption was not available after completion")
            report["checks"]["usage"] = "passed"
            report["usage_records"] = len(records)
        _interrupt_attempt(root, args.timeout)
        report["checks"]["interruption"] = "passed"
        secondary = prepare_run(config, run_root=args.run_root, executable=str(args.executable))
        other = Path(secondary["run_dir"])
        runs.append(other)
        launch_run(
            other,
            passive_url=args.passive_url,
            prompt="Reply exactly ISOLATED. Do not use tools.",
            timeout=args.timeout,
        )
        other_id, other_home = _native_identity(other)
        if first_id == other_id or first_home == other_home:
            raise FixtureError("Two fixture agents shared a native session or home")
        report["checks"]["two_isolated_homes"] = "passed"
        report["status"] = "passed" if args.surface != "raw" else "partial"
        report["private_runs"] = [str(path) for path in runs]
    except (FixtureError, OSError, subprocess.SubprocessError, ValueError) as error:
        report["status"] = "failed"
        report["error"] = type(error).__name__
        report["reason"] = (
            str(error)
            if isinstance(error, FixtureError)
            else "Inspect the external private run evidence; no prompt is retried"
        )
        report["private_runs"] = [str(path) for path in runs]
    finally:
        for root in reversed(runs):
            try:
                stop_run(root)
            except (FixtureError, OSError):
                report["status"] = "failed"
                report["limits"].append(
                    "Owned cleanup failed; use the captured private run identity"
                )
    return report


def main() -> int:
    """Require deliberate inputs before any credential-bearing or paid operation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("cloud-api", "self-hosted"), default="cloud-api")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model")
    parser.add_argument("--executable", type=Path)
    parser.add_argument(
        "--surface", choices=("raw", "manager", "passive-server"), default="manager"
    )
    parser.add_argument("--passive-url")
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    output: Path | None = None
    try:
        if args.output is not None:
            output = validate_external_path(args.output)
        report = qualify(args)
    except (FixtureError, OSError, ValueError, subprocess.SubprocessError) as error:
        report = {
            "schema_version": 1,
            "status": "not_run",
            "error": type(error).__name__,
            "reason": "Selected configuration or runtime prerequisite is unavailable",
        }
    payload = json.dumps(report, indent=2) + "\n"
    if output is not None:
        private_write(output, payload.encode())
    print(payload, end="")
    return (
        0
        if report["status"] in {"passed", "partial"} or (args.check_only and "error" not in report)
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
