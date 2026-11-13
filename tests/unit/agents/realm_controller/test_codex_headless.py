from __future__ import annotations

import subprocess
import json
from pathlib import Path
from typing import Any

import pytest

from houmao.agents.realm_controller.backends.codex_headless import (
    CodexHeadlessSession,
)
from houmao.agents.realm_controller.backends.headless_base import (
    HeadlessSessionState,
)
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessRunResult,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionEvent,
)
from houmao.agents.realm_controller.usage_support import UsageService
from houmao.agents.realm_controller.usage_store import UsageStoreError
from houmao.agents.realm_controller.errors import BackendExecutionError
from houmao.agents.model_selection import ModelConfig, ModelReasoningConfig


def _sample_codex_launch_plan(tmp_path: Path, *, prompt: str = "role prompt") -> LaunchPlan:
    return LaunchPlan(
        backend="codex_headless",
        tool="codex",
        executable="codex",
        args=["--x"],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "sk-secret"},
        env_var_names=["OPENAI_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="gpu-kernel-coder",
            prompt=prompt,
        ),
        metadata={"codex_headless_cli_mode": "exec_json_resume"},
    )


@pytest.fixture(autouse=True)
def _stub_tmux_and_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.ensure_tmux_available_shared",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.has_tmux_session_shared",
        lambda *, session_name: subprocess.CompletedProcess(
            args=["tmux", "has-session", "-t", session_name],
            returncode=0,
            stdout="",
            stderr="",
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.set_tmux_session_environment_shared",
        lambda *, session_name, env_vars: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.prepare_headless_agent_window_shared",
        lambda *, session_name: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.headless_base.ensure_codex_home_bootstrap",
        lambda *, home_path, env, working_directory: None,
    )


def test_codex_headless_builds_new_turn_command(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
            **_kwargs,
        ) -> HeadlessRunResult:
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    events = session.send_prompt("hello world")

    assert captured["command"] == [
        "codex",
        "--x",
        "-c",
        "developer_instructions=role prompt",
        "exec",
        "--json",
        "hello world",
    ]
    assert session.state.turn_index == 1
    assert session.state.session_id == "thread-1"
    assert events[-1].payload == {
        "turn_id": events[-1].payload["turn_id"],
        "session_id": "thread-1",
        "tmux_session_name": "HOUMAO-codex",
        "stdout_path": None,
        "stderr_path": None,
        "canonical_path": None,
        "completion_source": "direct_process",
    }
    assert str(events[-1].payload["turn_id"]).startswith("turn-")


def test_codex_headless_builds_resume_turn_command(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            session_id="thread-1",
            turn_index=1,
            role_bootstrap_applied=True,
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
            **_kwargs,
        ) -> HeadlessRunResult:
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt("next turn")

    assert captured["command"] == [
        "codex",
        "--x",
        "-c",
        "developer_instructions=role prompt",
        "exec",
        "--json",
        "resume",
        "thread-1",
        "next turn",
    ]


def test_codex_headless_skips_empty_developer_instructions(tmp_path: Path) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path, prompt=""),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
            **_kwargs,
        ) -> HeadlessRunResult:
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt("hello world")

    assert captured["command"] == ["codex", "--x", "exec", "--json", "hello world"]


def test_codex_headless_passes_execution_model_as_cli_config_overrides(
    tmp_path: Path,
) -> None:
    session = CodexHeadlessSession(
        launch_plan=_sample_codex_launch_plan(tmp_path),
        role_name="gpu-kernel-coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
            tmux_session_name="HOUMAO-codex",
        ),
    )
    captured: dict[str, object] = {}

    class _FakeRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
            **_kwargs,
        ) -> HeadlessRunResult:
            captured["command"] = command
            return HeadlessRunResult(
                events=[],
                stderr="",
                returncode=0,
                session_id="thread-1",
            )

    session._runner = _FakeRunner()  # type: ignore[attr-defined]
    session.send_prompt(
        "hello world",
        execution_model=ModelConfig(
            name="gpt-5.4-mini",
            reasoning=ModelReasoningConfig(level=2),
        ),
    )

    assert captured["command"] == [
        "codex",
        "--x",
        "-c",
        "developer_instructions=role prompt",
        '--config=model="gpt-5.4-mini"',
        '--config=model_reasoning_effort="medium"',
        "exec",
        "--json",
        "hello world",
    ]


class _AccountingRunner:
    """A controlled process boundary that emits real-shaped accounting payloads."""

    def __init__(self, outcomes: list[int]) -> None:
        """Retain successive process outcomes and dispatched artifact IDs."""
        self.m_outcomes = list(outcomes)
        self.m_turn_ids: list[str] = []
        self.m_interrupt_requested: bool = False
        self.active_process_running: bool = False

    def run(self, **kwargs: Any) -> HeadlessRunResult:
        """Return one identified structured completion, including failure evidence."""
        turn_id = str(kwargs["turn_artifact_dir_name"])
        self.m_turn_ids.append(turn_id)
        session_id = f"thread-{len(self.m_turn_ids)}"
        return HeadlessRunResult(
            events=[
                SessionEvent(
                    kind="completion",
                    message="complete",
                    turn_index=kwargs["turn_index"],
                    payload={
                        "raw": {
                            "type": "turn.completed",
                            "usage": {
                                "input_tokens": 10,
                                "output_tokens": 5,
                            },
                        }
                    },
                )
            ],
            stderr="failed" if self.m_outcomes[0] else "",
            returncode=self.m_outcomes.pop(0),
            session_id=session_id,
        )


def _accounting_session(tmp_path: Path) -> CodexHeadlessSession:
    """Construct a hermetic backend with a durable runtime identity."""
    plan = _sample_codex_launch_plan(tmp_path)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "agent_id": "agent-a",
                "backend": "codex_headless",
                "tool": "codex",
                "runtime": {"session_id": "runtime-a"},
                "registry_generation_id": "generation-a",
                "launch_plan": plan.redacted_payload(),
                "backend_state": {},
            }
        )
    )
    return CodexHeadlessSession(
        launch_plan=plan,
        role_name="gpu-kernel-coder",
        session_manifest_path=manifest,
        state=HeadlessSessionState(working_directory=str(tmp_path), tmux_session_name="unit-codex"),
    )


def test_failed_retry_uses_distinct_artifacts_and_records(tmp_path: Path) -> None:
    """A failed attempt cannot reuse its provider index or overwrite its evidence."""
    session = _accounting_session(tmp_path)
    runner = _AccountingRunner([1, 0])
    session._runner = runner  # type: ignore[assignment]
    with pytest.raises(BackendExecutionError):
        session.send_prompt("first")
    assert session.state.turn_index == 0
    events = session.send_prompt("retry")
    assert len(set(runner.m_turn_ids)) == 2
    assert events[-1].payload["turn_id"] == runner.m_turn_ids[1]
    page = UsageService.from_manifest(tmp_path / "manifest.json").get_usage()
    assert [record.outcome for record in page.records] == ["failed", "completed"]
    assert [record.turn_index for record in page.records] == [1, 1]
    for turn_id in runner.m_turn_ids:
        assert (tmp_path / "manifest.turn-artifacts" / turn_id / "usage-final.json").exists()


def test_explicit_turn_id_reuse_fails_without_overwrite(tmp_path: Path) -> None:
    """A caller's explicit ID is preserved and conflicting reuse is rejected."""
    session = _accounting_session(tmp_path)
    runner = _AccountingRunner([0, 0])
    session._runner = runner  # type: ignore[assignment]
    session.send_prompt("first", turn_artifact_dir_name="explicit-id")
    artifact = tmp_path / "manifest.turn-artifacts" / "explicit-id" / "usage-start.json"
    original = artifact.read_bytes()
    with pytest.raises(ValueError, match="already been used"):
        session.send_prompt("second", turn_artifact_dir_name="explicit-id")
    assert artifact.read_bytes() == original and runner.m_turn_ids == ["explicit-id"]


def test_interrupted_failed_attempt_preserves_partial_accounting(tmp_path: Path) -> None:
    """Interruption facts survive the backend's ordinary nonzero-exit exception."""
    session = _accounting_session(tmp_path)
    runner = _AccountingRunner([143])
    runner.m_interrupt_requested = True
    session._runner = runner  # type: ignore[assignment]
    with pytest.raises(BackendExecutionError):
        session.send_prompt("work")
    page = UsageService.from_manifest(tmp_path / "manifest.json").get_usage()
    assert page.records[0].outcome == "interrupted"
    assert page.records[0].token_usage.input_tokens.value == 10
    assert page.records[0].token_usage.input_tokens.availability == "partial"


def test_live_timeout_retains_pending_accounting(tmp_path: Path) -> None:
    """A controller timeout cannot classify a still-running provider as terminal."""
    session = _accounting_session(tmp_path)

    class LiveRunner:
        """Model an active provider that outlives the controller's wait."""

        active_process_running = True

        def run(self, **kwargs: Any) -> HeadlessRunResult:
            """Report controller timeout while retaining active process evidence."""
            raise BackendExecutionError("controller timed out")

    session._runner = LiveRunner()  # type: ignore[assignment]
    with pytest.raises(BackendExecutionError, match="timed out"):
        session.send_prompt("work")
    service = UsageService.from_manifest(tmp_path / "manifest.json")
    assert service.get_usage().records == []
    pending = service.store.list_pending_turns()
    assert len(pending) == 1 and pending[0].finalization is None


def test_launch_failure_records_terminal_attempt_without_metrics(tmp_path: Path) -> None:
    """A launch error retains its accounting attempt even without provider output."""
    session = _accounting_session(tmp_path)

    class MissingExecutableRunner:
        """Model an executable disappearing between setup and process launch."""

        active_process_running = False

        def run(self, **kwargs: Any) -> HeadlessRunResult:
            """Fail before a provider process or structured output exists."""
            raise FileNotFoundError("provider executable unavailable")

    session._runner = MissingExecutableRunner()  # type: ignore[assignment]
    with pytest.raises(FileNotFoundError, match="executable unavailable"):
        session.send_prompt("work", turn_artifact_dir_name="launch-failed")
    service = UsageService.from_manifest(tmp_path / "manifest.json")
    page = service.get_usage()
    assert len(page.records) == 1
    record = page.records[0]
    assert record.turn_id == "launch-failed" and record.outcome == "failed"
    assert record.token_usage.input_tokens.value is None
    assert record.token_usage.input_tokens.availability == "unavailable"
    assert record.wall_time_ms.value is not None
    service.reconcile()
    assert service.get_usage().records == page.records
    assert service.get_usage(after=page.next_cursor).records == []


def test_recorder_outage_preserves_successful_execution_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accounting failure retains evidence without making successful work retry."""
    session = _accounting_session(tmp_path)
    runner = _AccountingRunner([0])
    session._runner = runner  # type: ignore[assignment]

    def unavailable(*args: Any, **kwargs: Any) -> None:
        """Simulate a ledger outage after terminal evidence became durable."""
        raise UsageStoreError("ledger unavailable")

    monkeypatch.setattr(UsageService, "finalize_headless_turn", unavailable)
    events = session.send_prompt("work")
    assert session.state.turn_index == 1 and session.state.session_id == "thread-1"
    assert events[-1].payload["diagnostic"] == "usage_finalization_pending"
    assert (
        tmp_path / "manifest.turn-artifacts" / runner.m_turn_ids[0] / "usage-final.json"
    ).exists()
