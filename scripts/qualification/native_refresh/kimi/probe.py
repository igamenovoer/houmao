"""Qualify installed Kimi native-server reload without credentials or model turns.

The probe prepares an explicit self-hosted fixture, starts one private loopback
native server, and edits only that fixture's home. It does not qualify Houmao's
Kimi TUI transport or claim that all native configuration fields reload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
import urllib.error
import urllib.request


def parse_arguments() -> argparse.Namespace:
    """Parse explicit binary selection and qualification output paths."""

    repo = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--fixture-script", type=Path, default=repo / "scripts/agents/test-fixtures/fixture.py"
    )
    parser.add_argument("--source-checkout", type=Path, default=repo / "extern/orphan/kimi-code")
    parser.add_argument("--scratch-parent", type=Path)
    parser.add_argument("--keep-scratch", action="store_true")
    return parser.parse_args()


def _skill_catalog(payload: dict[str, Any]) -> dict[str, str]:
    """Select only caller-authored probe skills from a native catalog."""

    return {
        item["name"]: item["description"]
        for item in payload.get("data", {}).get("skills", [])
        if item["name"].startswith("refresh-")
    }


def _mcp_tools(payload: dict[str, Any]) -> list[str]:
    """Select only tool names exposed by the isolated test MCP server."""

    return sorted(
        item["name"]
        for item in payload.get("data", {}).get("tools", [])
        if item.get("source") == "mcp"
    )


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    """Exercise installed native reload with skill, MCP, and configuration edits.

    Parameters
    ----------
    args : argparse.Namespace
        Explicit installed executable, fixture, and scratch selections.

    Returns
    -------
    dict[str, Any]
        Credential-free observations and named checks. The result distinguishes
        native-server behavior from unqualified maintained Houmao controls.
    """

    binary = args.executable.resolve(strict=True)
    fixture_script = args.fixture_script.resolve(strict=True)
    root = Path(tempfile.mkdtemp(prefix="houmao-kimi-refresh-", dir=args.scratch_parent))
    fake_home = root / "os-home"
    fake_home.mkdir()
    env = {"PATH": os.environ["PATH"], "HOME": str(fake_home), "TERM": "dumb"}
    env_file = root / "selected.env"
    env_file.write_text("HOUMAO_TEST_SELF_HOSTED_API_KEY=native-refresh-test-only\n")
    process: subprocess.Popen[str] | None = None
    log_path = root / "native.log"
    with binary.open("rb") as executable_file:
        executable_sha256 = hashlib.file_digest(executable_file, "sha256").hexdigest()
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "failed",
        "installed": {
            "executable": str(binary),
            "sha256": executable_sha256,
            "version": subprocess.check_output(
                [str(binary), "--version"], env=env, text=True
            ).strip(),
        },
        "fixture": {
            "case": "self-hosted",
            "model": "native-refresh-probe",
            "model_endpoint": "http://127.0.0.1:1/v1",
            "model_prompts_submitted": 0,
            "ambient_auth_used": False,
            "native_watchers_enabled": False,
            "tmux_used": False,
        },
        "checks": {},
        "limitations": [
            "Native server REST reload only; Houmao currently owns Kimi TUI/headless controls.",
            "A separate native server cannot reload the resource objects of an existing TUI.",
            "No TUI slash-command delivery or completion matcher is qualified by this probe.",
            "An empty session retains its ID; nonempty conversation history is not exercised.",
            "No headless next-invocation or automatic-watcher behavior is qualified here.",
            "Skill catalog metadata is checked; model consumption of skill bodies is not tested.",
            "One reloadable configuration field is tested, not all native configuration.",
            "Active-turn refusal is source evidence only; this probe submits no model turns.",
        ],
    }
    if args.source_checkout.is_dir():
        source = args.source_checkout.resolve()
        result["source_reference"] = {
            "commit": subprocess.check_output(
                ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
            ).strip(),
            "package_version": json.loads((source / "apps/kimi-code/package.json").read_text())[
                "version"
            ],
        }
    try:
        prepared = subprocess.run(
            [
                sys.executable,
                str(fixture_script),
                "prepare",
                "--client",
                "kimi",
                "--case",
                "self-hosted",
                "--model",
                "native-refresh-probe",
                "--context-window",
                "8192",
                "--base-url",
                "http://127.0.0.1:1/v1",
                "--env-file",
                str(env_file),
                "--surface",
                "raw",
                "--mode",
                "headless",
                "--run-root",
                str(root / "runs"),
                "--executable",
                str(binary),
            ],
            cwd=fixture_script.parents[3],
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        public_fixture = json.loads(prepared.stdout)
        run_dir = Path(public_fixture["run_dir"])
        fixture = json.loads((run_dir / "run.json").read_text())
        home = Path(fixture["home_path"])
        cwd = Path(fixture["workdir"])
        config_path = home / "config.toml"
        config = (
            "telemetry = false\nauto_session_title = false\n"
            "disable_feedback_survey = false\n\n[watch]\nenabled = false\n"
        )
        config_path.write_text(config)
        skill_root = home / "skills"
        skill_root.mkdir(exist_ok=True)
        skill = skill_root / "refresh-probe"
        skill.mkdir()
        skill_file = skill / "SKILL.md"
        skill_file.write_text(
            "---\nname: refresh-probe\ndescription: initial probe\n---\nInitial body.\n"
        )
        (home / "mcp.json").write_text('{"mcpServers":{}}\n')
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        env.update(json.loads((run_dir / "private-env.json").read_text()))
        env["KIMI_CODE_HOME"] = str(home)
        with log_path.open("w") as log:
            process = subprocess.Popen(
                [
                    str(binary),
                    "web",
                    "--no-open",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--dangerous-bypass-auth",
                    "--log-level",
                    "silent",
                ],
                cwd=cwd,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )

        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def request(route: str, body: object | None = None) -> dict[str, Any]:
            """Call the private loopback native server without invoking model work."""

            data = None if body is None else json.dumps(body).encode()
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/api/v1{route}",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            try:
                with opener.open(req, timeout=15) as response:
                    return json.load(response)  # type: ignore[no-any-return]
            except urllib.error.HTTPError as exc:
                return {"http_status": exc.code, "body": json.load(exc)}

        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError("native server exited before readiness")
            try:
                request("/meta")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.1)
        else:
            raise RuntimeError("native server readiness timed out")
        created = request("/sessions", {"metadata": {"cwd": str(cwd)}, "title": "refresh probe"})
        sid = created["data"]["id"]
        checks = result["checks"]
        observed: dict[str, Any] = {}
        observed["initial_skills"] = _skill_catalog(request(f"/sessions/{sid}/skills"))
        checks["initial_skill_discovered"] = observed["initial_skills"] == {
            "refresh-probe": "initial probe"
        }
        skill_file.write_text(
            "---\nname: refresh-probe\ndescription: updated probe\n---\nUpdated body.\n"
        )
        second = skill_root / "refresh-added"
        second.mkdir()
        (second / "SKILL.md").write_text(
            "---\nname: refresh-added\ndescription: added probe\n---\nNew body.\n"
        )
        checks["skill_catalog_stale_before_reload"] = (
            _skill_catalog(request(f"/sessions/{sid}/skills")) == observed["initial_skills"]
        )
        reloaded = request(f"/sessions/{sid}:reload", {})
        observed["updated_skills"] = _skill_catalog(request(f"/sessions/{sid}/skills"))
        checks["skill_add_update_reload"] = observed["updated_skills"] == {
            "refresh-probe": "updated probe",
            "refresh-added": "added probe",
        }
        checks["session_preserved_after_reload"] = reloaded.get("data", {}).get("id") == sid
        shutil.rmtree(skill)
        request(f"/sessions/{sid}:reload", {})
        observed["removed_skills"] = _skill_catalog(request(f"/sessions/{sid}/skills"))
        checks["skill_remove_reload"] = observed["removed_skills"] == {
            "refresh-added": "added probe"
        }
        config_path.write_text(
            config.replace("disable_feedback_survey = false", "disable_feedback_survey = true")
        )
        checks["config_stale_before_reload"] = (
            request("/config")["data"]["disable_feedback_survey"] is False
        )
        request(f"/sessions/{sid}:reload", {})
        checks["config_reloaded"] = request("/config")["data"]["disable_feedback_survey"] is True
        mcp_script = root / "mcp_server.py"
        shutil.copyfile(Path(__file__).with_name("mcp_server.py"), mcp_script)

        def set_mcp(revision: str | None) -> None:
            """Edit caller-owned MCP declarations in the isolated native home."""

            servers = (
                {}
                if revision is None
                else {
                    "refresh-probe": {
                        "command": sys.executable,
                        "args": [str(mcp_script), revision],
                        "deferred": False,
                    }
                }
            )
            (home / "mcp.json").write_text(json.dumps({"mcpServers": servers}) + "\n")

        def wait_mcp(expected: list[str]) -> list[str]:
            """Observe bounded native MCP startup without any tool invocation."""

            tools: list[str] = []
            for _ in range(50):
                tools = _mcp_tools(request("/tools?session_id=" + sid))
                if tools == expected:
                    break
                time.sleep(0.1)
            return tools

        for action, revision, expected in (
            ("add", "one", ["mcp__refresh-probe__probe_one"]),
            ("update", "two", ["mcp__refresh-probe__probe_two"]),
            ("remove", None, []),
        ):
            set_mcp(revision)
            request(f"/sessions/{sid}:reload", {})
            actual = wait_mcp(expected)
            observed["mcp_" + action + "_tools"] = actual
            checks["mcp_" + action + "_reload"] = actual == expected
        final = request(f"/sessions/{sid}")
        checks["final_session_preserved"] = final.get("data", {}).get("id") == sid
        checks["native_process_preserved"] = process.poll() is None
        result["identity"] = {"server_pid": process.pid, "session_id": sid}
        result["observed"] = observed
        result["status"] = "passed" if all(checks.values()) else "failed"
    except Exception as exc:
        result["error_type"] = type(exc).__name__
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if args.keep_scratch:
            result["scratch_root"] = str(root)
        else:
            shutil.rmtree(root)
    return result


def main() -> int:
    """Write a reproducible, credential-free qualification report."""

    args = parse_arguments()
    result = qualify(args)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {"status": result["status"], "report": str(args.report), "checks": result["checks"]},
            indent=2,
        )
    )
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
