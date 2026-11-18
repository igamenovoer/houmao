"""Fence raw Web fixture ownership, private connection handoff, and terminal routing."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from houmao.agents.realm_controller.models import SessionEvent
from houmao.agents.realm_controller.native_surface import WebNativeSurfaceV1


@pytest.fixture
def raw_web_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], ModuleType, ModuleType, list[dict[str, Any]]]:
    """Prepare real private fixture inputs while replacing only the unavailable native host."""

    repo = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    web = importlib.import_module("fixturelib.web")
    selected = config.resolve_config(
        case="cloud-api",
        client="dsh",
        mode="tui",
        surface="raw",
        process_env={
            "DEEPSEEK_API_KEY": "synthetic-private-key",
            "DEEPSEEK_BASE_URL_ANTHROPIC": "http://127.0.0.1:19090",
            "HOUMAO_TEST_CLOUD_MODEL": "controlled",
            "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "8192",
            "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS": "128",
            "HOUMAO_TEST_CLOUD_DSH_REASONING": "false",
        },
    )
    run = prepare.prepare_run(selected, run_root=tmp_path / "runs", executable=sys.executable)
    root = Path(run["run_dir"])
    bootstrap = root / "private-bootstrap.json"
    bootstrap.write_text(
        json.dumps(
            {
                "version": 1,
                "origin": "http://127.0.0.1:19095",
                "launch_token": "synthetic-browser-token",
            }
        )
    )
    bootstrap.chmod(0o600)
    calls: list[dict[str, Any]] = []

    class State:
        """Represent opaque private runtime state with a validated public native surface."""

        tmux_session_name = "fixture-owned-web"
        native_surface = WebNativeSurfaceV1(
            origin="http://127.0.0.1:19095", native_session_id="native-exact"
        )

        @classmethod
        def from_payload(cls, payload: dict[str, Any]) -> State:
            """Refuse reconstruction if the exact captured binding changes."""

            assert payload["web_identity"]["native_session_id"] == "native-exact"
            return cls()

        def to_payload(self) -> dict[str, Any]:
            """Return credential references that ordinary public reports must exclude."""

            return {
                "origin": "http://127.0.0.1:19095",
                "web_identity": {"native_session_id": "native-exact"},
                "bootstrap_path": str(bootstrap),
                "cookie_path": str(root / "private-cookie.json"),
            }

    class Session:
        """Expose an exact owned runtime boundary, recording only fixture control choices."""

        state = State()

        @classmethod
        def from_launch_plan(cls, **kwargs: Any) -> Session:
            """Check explicit lifecycle authorization before returning the controlled boundary."""

            calls.append({"action": "construct", "provider_start": kwargs["provider_start"]})
            assert (kwargs["state"] is None) is kwargs["provider_start"]
            plan = kwargs["launch_plan"]
            assert plan.backend == "dsh_web"
            assert plan.native_surface_kind == "web"
            assert plan.metadata["dsh"]["operator_prompt_mode"] == "unattended"
            manifest = json.loads(kwargs["session_manifest_path"].read_text())
            assert manifest["working_directory"] == str(plan.working_directory)
            assert manifest["runtime"]["session_id"]
            return cls()

        def send_web_prompt(self, prompt: str, **kwargs: Any) -> list[SessionEvent]:
            """Record ordinary conditional delivery and explicit selected timeout."""

            calls.append({"action": "prompt", **kwargs})
            return [
                SessionEvent(
                    kind="done", message="", turn_index=1, payload={"outcome": "completed"}
                )
            ]

        def close_control_connection(self) -> None:
            """Record connection release independently of host termination."""

            calls.append({"action": "close"})

        def interrupt(self) -> SimpleNamespace:
            """Record exact native interruption without host replacement."""

            calls.append({"action": "interrupt"})
            return SimpleNamespace(status="ok")

        def terminate(self) -> SimpleNamespace:
            """Record owned termination without terminal key injection."""

            calls.append({"action": "terminate"})
            return SimpleNamespace(status="ok")

    native = ModuleType("houmao.agents.realm_controller.backends.dsh_web")
    native.DshWebSession = Session
    native.DshWebSessionState = State
    monkeypatch.setitem(sys.modules, native.__name__, native)
    return run, launch, web, calls


def test_raw_web_followup_reconstructs_without_start_and_keeps_auth_private(
    raw_web_fixture: tuple[dict[str, Any], ModuleType, ModuleType, list[dict[str, Any]]],
) -> None:
    """Only first launch starts a host; prompt, interrupt, and stop keep exact ownership."""

    run, launch, _web, calls = raw_web_fixture
    root = Path(run["run_dir"])
    first = launch.launch_run(root)
    assert first["identity"]["native_surface"]["native_session_id"] == "native-exact"
    second = launch.prompt_run(root, prompt="One explicit prompt", timeout=17)
    assert second["turns"] == [{"index": 1, "status": "completed"}]
    assert "raw_web_state" not in second
    assert "bootstrap_path" not in json.dumps(second)
    assert "cookie_path" not in json.dumps(second)
    assert "synthetic-browser-token" not in (root / "report.json").read_text()
    launch.interrupt_run(root)
    launch.stop_run(root)
    assert [row["provider_start"] for row in calls if row["action"] == "construct"] == [
        True,
        False,
        False,
        False,
    ]
    assert [row for row in calls if row["action"] == "prompt"] == [
        {
            "action": "prompt",
            "admission_policy": "ready_only",
            "operator": False,
            "timeout_seconds": 17,
        }
    ]
    assert len([row for row in calls if row["action"] == "close"]) == 4


def test_browser_handoff_is_deliberate_private_and_origin_bound(
    raw_web_fixture: tuple[dict[str, Any], ModuleType, ModuleType, list[dict[str, Any]]],
) -> None:
    """Publish a path only on the explicit operator action and reject mismatched authority."""

    run, launch, web, _calls = raw_web_fixture
    root = Path(run["run_dir"])
    launch.launch_run(root)
    assert not (root / "browser-connection.json").exists()
    stored = json.loads((root / "run.json").read_text())
    descriptor = web.browser_connection_file(stored)
    assert descriptor.stat().st_mode & 0o777 == 0o600
    assert json.loads(descriptor.read_text()) == {
        "origin": "http://127.0.0.1:19095",
        "launch_token": "synthetic-browser-token",
        "native_session_id": "native-exact",
    }
    assert "synthetic-browser-token" not in (root / "report.json").read_text()
    descriptor.unlink()
    stored["raw_web_state"]["origin"] = "http://127.0.0.1:19096"
    with pytest.raises(web.FixtureError, match="does not match"):
        web.browser_connection_file(stored)
    assert not descriptor.exists()


def test_manager_web_waits_for_exact_operation_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A human turn finishing during the managed wait never satisfies that operation."""

    repo = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    launch = importlib.import_module("fixturelib.launch")
    run = {
        "run_dir": str(tmp_path),
        "status": "launched",
        "configuration": {"client": "dsh", "mode": "tui", "surface": "manager"},
        "identity": {"gateway_host": "127.0.0.1", "gateway_port": 19095},
    }
    human = {
        "record_id": "human-record",
        "turn_id": "human-turn",
        "outcome": "completed",
        "turn_origin": "native_observed",
    }
    managed = {
        "record_id": "managed-record",
        "turn_id": "admitted-operation",
        "outcome": "completed",
        "turn_origin": "managed",
    }
    reads = 0

    def gateway_request(run: dict[str, Any], path: str, body: Any = None) -> dict[str, Any]:
        """Expose an unrelated completed row before the exact managed record arrives."""

        nonlocal reads
        if path == "/v1/control/prompt":
            return {"operation_id": "admitted-operation"}
        if path == "/v1/status":
            return {"active_execution": "idle"}
        assert path == "/v1/usage"
        reads += 1
        return {"records": [] if reads == 1 else [human] if reads == 2 else [human, managed]}

    monkeypatch.setattr(launch, "load_run", lambda path: run)
    monkeypatch.setattr(launch, "_save", lambda run: None)
    monkeypatch.setattr(launch, "_gateway_request", gateway_request)
    monkeypatch.setattr(launch.time, "sleep", lambda seconds: None)
    result = launch.prompt_run(tmp_path, prompt="Explicit managed input", timeout=1)
    assert reads == 3
    assert result["turns"] == [{"record_id": "managed-record", "status": "completed"}]


def test_web_live_runner_refuses_ambient_auth_and_validates_only_selected_file(
    tmp_path: Path,
) -> None:
    """No external provider or native process starts from ambient credentials or offline checks."""

    repo = Path(__file__).resolve().parents[3]
    command = [sys.executable, str(repo / "scripts/qualification/dsh/qualify_web.py")]
    values = {
        "DEEPSEEK_API_KEY": "synthetic-runner-key",
        "DEEPSEEK_BASE_URL_ANTHROPIC": "http://127.0.0.1:19090",
        "HOUMAO_TEST_CLOUD_MODEL": "controlled",
        "HOUMAO_TEST_CLOUD_CONTEXT_WINDOW": "8192",
        "HOUMAO_TEST_CLOUD_MAX_OUTPUT_TOKENS": "128",
        "HOUMAO_TEST_CLOUD_DSH_REASONING": "false",
    }
    ambient = subprocess.run(
        command, capture_output=True, text=True, env={**os.environ, **values}, timeout=15
    )
    refused = json.loads(ambient.stdout)
    assert ambient.returncode == 2
    assert refused["status"] == "not_run" and refused["checks"] == {}
    assert "explicit external --env-file" in refused["reason"]
    selected = tmp_path / "synthetic-selected.env"
    selected.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
    selected.chmod(0o600)
    offline = subprocess.run(
        [*command, "--check-only", "--env-file", str(selected)],
        capture_output=True,
        text=True,
        timeout=15,
    )
    checked = json.loads(offline.stdout)
    assert offline.returncode == 0
    assert checked["status"] == "not_run" and checked["checks"] == {}
    assert checked["configuration_valid"] is True
    assert checked["native_surface"] == "web"
    assert (
        "synthetic-runner-key"
        not in ambient.stdout + ambient.stderr + offline.stdout + offline.stderr
    )


def test_failed_launch_with_completed_cleanup_does_not_stop_an_inactive_agent_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the first launch failure visible after its owned host was already stopped."""

    repo = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    launch = importlib.import_module("fixturelib.launch")
    run = {"run_dir": str(tmp_path), "status": "launch_failed", "cleanup": "stopped_owned_identity"}
    monkeypatch.setattr(launch, "load_run", lambda path: run)
    monkeypatch.setattr(launch, "_save", lambda run: None)

    def duplicate_stop(run: dict[str, Any]) -> None:
        """Reject any repeated mutation against the already stopped authority."""

        raise AssertionError("Cleanup already completed")

    monkeypatch.setattr(launch, "_cleanup", duplicate_stop)
    assert launch.stop_run(tmp_path)["status"] == "stopped"
