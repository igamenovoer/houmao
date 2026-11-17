"""Qualify installed Codex and Claude refresh controls without model requests.

The probes use private temporary homes, a local stdio MCP fixture, and explicit
executables. They neither read ambient credentials nor send ordinary user turns.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, TextIO

_FIXTURE = Path(__file__).with_name("mcp_fixture.py").resolve()
_SKILL_NAME = "houmao-refresh-probe"


def _child_env(root: Path) -> dict[str, str]:
    """Build a child-only environment containing no ambient authentication."""
    os_home = root / "os-home"
    os_home.mkdir(parents=True)
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "LANG": "C.UTF-8",
        "HOME": str(os_home),
        "XDG_CONFIG_HOME": str(os_home / ".config"),
        "XDG_DATA_HOME": str(os_home / ".local/share"),
        "XDG_STATE_HOME": str(os_home / ".local/state"),
        "CODEX_HOME": str(root / "native-home"),
        "CLAUDE_CONFIG_DIR": str(root / "native-home"),
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
        "CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1",
        "ANTHROPIC_BASE_URL": "http://127.0.0.1:9",
        "OPENAI_BASE_URL": "http://127.0.0.1:9",
        "NO_PROXY": "127.0.0.1,localhost",
    }


class NativeControl:
    """Exchange bounded control frames with one owned native child process."""

    def __init__(self) -> None:
        """Initialize an unstarted control process."""
        self.m_process: subprocess.Popen[str] | None = None
        self.m_stderr: TextIO | None = None
        self.m_output: queue.Queue[dict[str, Any]] = queue.Queue()
        self.m_reader: threading.Thread | None = None
        self.m_next_id: int = 0
        self.m_pid: int | None = None

    @classmethod
    def from_command(cls, *, command: list[str], root: Path, env: dict[str, str]) -> NativeControl:
        """Start one isolated process without inherited tmux or credentials."""
        instance = cls()
        instance.m_stderr = (root / "native-stderr.txt").open("w", encoding="utf-8")
        instance.m_process = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=instance.m_stderr,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        instance.m_pid = instance.m_process.pid
        instance.m_reader = threading.Thread(target=instance._read, daemon=True)
        instance.m_reader.start()
        return instance

    @property
    def alive(self) -> bool:
        """Return whether the original owned process still runs."""
        return self.m_process is not None and self.m_process.poll() is None

    @property
    def pid(self) -> int | None:
        """Return the originally captured owned PID."""
        return self.m_pid

    def _read(self) -> None:
        """Queue JSON frames from the owned process."""
        assert self.m_process is not None and self.m_process.stdout is not None
        for line in self.m_process.stdout:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(message, dict):
                self.m_output.put(message)

    def _exchange(self, frame: dict[str, Any], request_id: int) -> dict[str, Any]:
        """Await the matching control result without replaying native mutations."""
        assert self.m_process is not None and self.m_process.stdin is not None
        self.m_process.stdin.write(json.dumps(frame) + "\n")
        self.m_process.stdin.flush()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                message = self.m_output.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if message.get("id") == request_id:
                return message
            response = message.get("response")
            if isinstance(response, dict) and response.get("request_id") == str(request_id):
                return message
        raise TimeoutError("Native control did not confirm completion before its deadline")

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a Codex RPC and require a successful structured response."""
        self.m_next_id += 1
        frame: dict[str, Any] = {"id": self.m_next_id, "method": method}
        if params is not None:
            frame["params"] = params
        response = self._exchange(frame, self.m_next_id)
        if "error" in response:
            raise RuntimeError(f"Native {method} RPC failed: {response['error']}")
        return dict(response["result"])

    def control(self, subtype: str, **kwargs: Any) -> dict[str, Any]:
        """Send a Claude SDK control request and require confirmed completion."""
        self.m_next_id += 1
        response = self._exchange(
            {
                "type": "control_request",
                "request_id": str(self.m_next_id),
                "request": {"subtype": subtype, **kwargs},
            },
            self.m_next_id,
        )["response"]
        if response.get("subtype") != "success":
            raise RuntimeError(f"Native {subtype} control failed: {response.get('error')}")
        return dict(response.get("response", {}))

    def close(self) -> None:
        """Close only this owned child and its process group if it remains running."""
        process = self.m_process
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            if self.m_reader is not None:
                self.m_reader.join(timeout=1)
            if process.stdout is not None:
                process.stdout.close()
        if self.m_stderr is not None:
            self.m_stderr.close()


def _write_skill(home: Path, description: str) -> Path:
    """Write one harmless native user skill used by both clients."""
    path = home / "skills" / _SKILL_NAME / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nname: {_SKILL_NAME}\ndescription: {description}\n---\n\nBody {description}.\n",
        encoding="utf-8",
    )
    return path


def _version(executable: Path, root: Path, env: dict[str, str]) -> str:
    """Read the selected executable's version without reading a personal home."""
    result = subprocess.run(
        [str(executable), "--version"],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _mcp_config(marker: Path) -> dict[str, Any]:
    """Describe only the local MCP fixture and its synthetic marker file."""
    return {
        "type": "stdio",
        "command": sys.executable,
        "args": [str(_FIXTURE), "--marker", str(marker)],
    }


def _mcp_rows(response: dict[str, Any], *, claude: bool = False) -> list[dict[str, Any]]:
    """Keep server names, tool names, and fixture markers as activation evidence."""
    rows = []
    for server in response.get("mcpServers" if claude else "data", []):
        tools = server.get("tools", {})
        rows.append(
            {
                "name": server["name"],
                "version": (server.get("serverInfo") or {}).get("version"),
                "tools": sorted(
                    [tool["name"] for tool in tools] if isinstance(tools, list) else tools.keys()
                ),
                "status": server.get("status", server.get("runtimeStatus")),
            }
        )
    return rows


def _codex_probe(executable: Path, root: Path) -> dict[str, Any]:
    """Test Codex skill rescanning and process-wide MCP replacement without turns."""
    root.mkdir()
    home = root / "native-home"
    home.mkdir()
    env = _child_env(root)
    report: dict[str, Any] = {"version": _version(executable, root, env)}
    native = NativeControl.from_command(
        command=[
            str(executable),
            "app-server",
            "--stdio",
            "-c",
            "skills.bundled.enabled=false",
            "-c",
            "features.apps=false",
        ],
        root=root,
        env=env,
    )
    report["pid"] = native.pid
    try:
        report["initialize"] = native.rpc(
            "initialize",
            {
                "clientInfo": {"name": "houmao_native_refresh_probe", "version": "1"},
                "capabilities": {"experimentalApi": True},
            },
        )

        def skills() -> list[dict[str, Any]]:
            """Read only the test skill from the native rescan result."""
            result = native.rpc("skills/list", {"cwds": [str(root)], "forceReload": True})
            return [
                {"name": skill["name"], "description": skill["description"]}
                for row in result["data"]
                for skill in row["skills"]
                if skill["name"] == _SKILL_NAME
            ]

        report["skills_before"] = skills()
        path = _write_skill(home, "before")
        report["skills_added"] = skills()
        _write_skill(home, "after")
        report["skills_updated"] = skills()
        shutil.rmtree(path.parent)
        report["skills_removed"] = skills()
        assert report["skills_added"][0]["description"] == "before"
        assert report["skills_updated"][0]["description"] == "after"
        assert report["skills_removed"] == []

        marker = root / "mcp-marker.txt"
        marker.write_text("v1\n", encoding="utf-8")
        fixture = _mcp_config(marker)
        prefix = (
            'model="refresh-probe"\nmodel_provider="local-refresh-probe"\n'
            '[model_providers.local-refresh-probe]\nname="local only"\n'
            'base_url="http://127.0.0.1:9/v1"\nwire_api="responses"\n'
            "requires_openai_auth=false\n"
        )
        declaration = (
            f"command={json.dumps(fixture['command'])}\nargs={json.dumps(fixture['args'])}\n"
        )
        config_path = home / "config.toml"
        config_path.write_text(
            prefix + "[mcp_servers.refreshprobe]\n" + declaration, encoding="utf-8"
        )
        native.rpc("config/mcpServer/reload")
        report["mcp_added"] = _mcp_rows(native.rpc("mcpServerStatus/list", {"detail": "full"}))
        assert report["mcp_added"][0]["tools"] == ["probe_v1"]

        thread_ids = []
        for _ in range(2):
            result = native.rpc(
                "thread/start",
                {
                    "cwd": str(root),
                    "model": "refresh-probe",
                    "modelProvider": "local-refresh-probe",
                    "approvalPolicy": "never",
                },
            )
            thread_ids.append(result["thread"]["id"])
        report["thread_ids"] = thread_ids
        report["threads_before"] = {
            thread_id: _mcp_rows(
                native.rpc("mcpServerStatus/list", {"threadId": thread_id, "detail": "full"})
            )
            for thread_id in thread_ids
        }
        marker.write_text("v2\n", encoding="utf-8")
        native.rpc("config/mcpServer/reload")
        report["threads_after"] = {
            thread_id: _mcp_rows(
                native.rpc("mcpServerStatus/list", {"threadId": thread_id, "detail": "full"})
            )
            for thread_id in thread_ids
        }
        assert all(rows[0]["tools"] == ["probe_v2"] for rows in report["threads_after"].values())
        config_path.write_text(
            prefix + "[mcp_servers.renamedprobe]\n" + declaration, encoding="utf-8"
        )
        native.rpc("config/mcpServer/reload")
        report["mcp_renamed"] = _mcp_rows(native.rpc("mcpServerStatus/list", {"detail": "full"}))
        assert [row["name"] for row in report["mcp_renamed"]] == ["renamedprobe"]
        config_path.write_text(prefix, encoding="utf-8")
        native.rpc("config/mcpServer/reload")
        report["mcp_removed"] = _mcp_rows(native.rpc("mcpServerStatus/list", {"detail": "full"}))
        assert report["mcp_removed"] == []
        report["original_process_alive"] = native.alive
        assert native.alive
        report["status"] = "passed"
    finally:
        native.close()
    report["limitations"] = [
        "MCP reload affects every loaded thread in the app-server process.",
        "No model turn was sent; skill bodies and model-visible activation were not tested.",
        "General configuration reload is not established by the MCP-only RPC.",
        "Houmao codex_app_server is unmaintained and blocked; maintained surfaces lack this RPC.",
    ]
    return report


def _claude_probe(executable: Path, root: Path) -> dict[str, Any]:
    """Test Claude user-skill reload and bounded MCP reconnect limitations."""
    root.mkdir()
    home = root / "native-home"
    home.mkdir()
    env = _child_env(root)
    report: dict[str, Any] = {"version": _version(executable, root, env)}
    _write_skill(home, "before")
    marker = root / "mcp-marker.txt"
    marker.write_text("v1\n", encoding="utf-8")
    fixture = _mcp_config(marker)
    config_path = home / ".claude.json"
    config_path.write_text(
        json.dumps({"hasCompletedOnboarding": True, "mcpServers": {"refreshprobe": fixture}}),
        encoding="utf-8",
    )
    native = NativeControl.from_command(
        command=[
            str(executable),
            "--setting-sources",
            "user",
            "--print",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--settings",
            "{}",
        ],
        root=root,
        env=env,
    )
    report["pid"] = native.pid
    try:
        initialized = native.control("initialize")
        report["relevant_commands"] = [
            command["name"]
            for command in initialized.get("commands", [])
            if command["name"] in {_SKILL_NAME, "reload-skills", "reload-plugins", "mcp"}
        ]

        def skills() -> list[dict[str, Any]]:
            """Read the test skill's reloaded catalog entry."""
            return [
                {"name": skill["name"], "description": skill["description"]}
                for skill in native.control("reload_skills")["skills"]
                if skill["name"] == _SKILL_NAME
            ]

        report["skills_before"] = skills()
        path = _write_skill(home, "after")
        report["skills_updated"] = skills()
        shutil.rmtree(path.parent)
        report["skills_removed"] = skills()
        _write_skill(home, "added-again")
        report["skills_added"] = skills()
        assert report["skills_before"][0]["description"].startswith("before")
        assert report["skills_updated"][0]["description"].startswith("after")
        assert report["skills_removed"] == []
        assert report["skills_added"][0]["description"].startswith("added-again")

        native.control("mcp_reconnect", serverName="refreshprobe")
        report["mcp_before"] = _mcp_rows(native.control("mcp_status"), claude=True)
        assert report["mcp_before"][0]["tools"] == ["probe_v1"]
        marker.write_text("v2\n", encoding="utf-8")
        native.control("mcp_reconnect", serverName="refreshprobe")
        report["mcp_after_reconnect"] = _mcp_rows(native.control("mcp_status"), claude=True)
        assert report["mcp_after_reconnect"][0]["tools"] == ["probe_v2"]

        current = json.loads(config_path.read_text(encoding="utf-8"))
        current["mcpServers"] = {"renamedprobe": fixture}
        config_path.write_text(json.dumps(current), encoding="utf-8")
        reloaded = native.control("reload_plugins")
        report["plugin_reload_error_count"] = reloaded.get("error_count")
        time.sleep(1)
        report["mcp_after_home_declaration_edit"] = _mcp_rows(
            native.control("mcp_status"), claude=True
        )
        report["mcp_declaration_reread"] = [
            row["name"] for row in report["mcp_after_home_declaration_edit"]
        ] == ["renamedprobe"]
        report["original_process_alive"] = native.alive
        assert native.alive
        report["status"] = "passed"
    finally:
        native.close()
    report["limitations"] = [
        "Skill results establish catalog metadata, not model-visible body use or history changes.",
        "MCP reconnect refreshes a known server, not arbitrary declaration additions or removals.",
        "General native configuration rereading and conversation continuation were not tested.",
        "Houmao headless uses stdin=DEVNULL; its maintained TUI has no owned SDK control stream.",
        "Bare mode skips native user skills and is not this qualification profile.",
    ]
    return report


def main() -> int:
    """Run both selected native probes and save a credential-free JSON report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-executable", required=True, type=Path)
    parser.add_argument("--claude-executable", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    report: dict[str, Any] = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "model_requests_sent": 0,
        "tmux_used": False,
        "ambient_auth_used": False,
    }
    with tempfile.TemporaryDirectory(prefix="houmao-native-refresh-") as directory:
        root = Path(directory)
        for name, probe, executable in [
            ("codex", _codex_probe, args.codex_executable),
            ("claude", _claude_probe, args.claude_executable),
        ]:
            try:
                report[name] = probe(executable.expanduser().absolute(), root / name)
            except Exception as error:
                report[name] = {"status": "failed", "error": str(error)}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: report[name]["status"] for name in ("codex", "claude")}))
    print(f"Report: {args.report}")
    return 0 if all(report[name]["status"] == "passed" for name in ("codex", "claude")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
