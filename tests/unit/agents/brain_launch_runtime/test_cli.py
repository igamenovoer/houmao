"""Unit tests for runtime CLI output and argument wiring."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from gig_agents.agents.brain_launch_runtime import cli
from gig_agents.agents.brain_launch_runtime.models import SessionControlResult


def test_start_session_outputs_canonical_agent_identity_for_cao(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text("{}", encoding="utf-8")

    def _fake_start_runtime_session(**kwargs: object) -> object:
        return SimpleNamespace(
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(backend="cao_rest", tool="codex"),
            agent_identity="AGENTSYS-gpu",
            agent_identity_warnings=("prefix warning",),
            startup_warnings=("cleanup warning",),
            parsing_mode="cao_only",
        )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.start_runtime_session",
        _fake_start_runtime_session,
    )

    exit_code = cli.main(
        [
            "start-session",
            "--brain-manifest",
            "tmp/brain.yaml",
            "--role",
            "gpu-kernel-coder",
            "--backend",
            "cao_rest",
            "--agent-identity",
            "gpu",
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["agent_identity"] == "AGENTSYS-gpu"
    assert payload["parsing_mode"] == "cao_only"
    assert payload["session_manifest"] == str(manifest_path)
    assert "warning: prefix warning" in captured.err
    assert "warning: cleanup warning" in captured.err


def test_start_session_forwards_cao_parsing_mode_override(monkeypatch, tmp_path: Path) -> None:
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text("{}", encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(backend="cao_rest", tool="codex"),
            agent_identity="AGENTSYS-gpu",
            agent_identity_warnings=(),
            startup_warnings=(),
            parsing_mode="shadow_only",
        )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.start_runtime_session",
        _fake_start_runtime_session,
    )

    exit_code = cli.main(
        [
            "start-session",
            "--brain-manifest",
            "tmp/brain.yaml",
            "--role",
            "gpu-kernel-coder",
            "--backend",
            "cao_rest",
            "--cao-parsing-mode",
            "shadow_only",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["cao_parsing_mode"] == "shadow_only"


def test_stop_session_forwards_force_cleanup(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    class _FakeController:
        def stop(self, *, force_cleanup: bool = False) -> SessionControlResult:
            captured["force_cleanup"] = force_cleanup
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="cleaned",
            )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    exit_code = cli.main(
        [
            "stop-session",
            "--agent-identity",
            "AGENTSYS-gpu",
            "--force-cleanup",
        ]
    )

    assert exit_code == 0
    assert captured["force_cleanup"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"


def test_start_session_prefers_cli_agent_def_dir_over_env(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("AGENTSYS_AGENT_DEF_DIR", str(tmp_path / "env-agent-def"))

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(backend="codex_headless", tool="codex"),
            agent_identity=None,
            agent_identity_warnings=(),
            startup_warnings=(),
            parsing_mode=None,
        )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.start_runtime_session",
        _fake_start_runtime_session,
    )

    exit_code = cli.main(
        [
            "start-session",
            "--agent-def-dir",
            str(tmp_path / "cli-agent-def"),
            "--brain-manifest",
            "tmp/brain.yaml",
            "--role",
            "gpu-kernel-coder",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["agent_def_dir"] == (tmp_path / "cli-agent-def").resolve()


def test_start_session_uses_env_agent_def_dir_when_cli_flag_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text("{}", encoding="utf-8")

    env_agent_def_dir = tmp_path / "env-agent-def"
    monkeypatch.setenv("AGENTSYS_AGENT_DEF_DIR", str(env_agent_def_dir))

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(backend="codex_headless", tool="codex"),
            agent_identity=None,
            agent_identity_warnings=(),
            startup_warnings=(),
            parsing_mode=None,
        )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.start_runtime_session",
        _fake_start_runtime_session,
    )

    exit_code = cli.main(
        [
            "start-session",
            "--brain-manifest",
            "tmp/brain.yaml",
            "--role",
            "gpu-kernel-coder",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["agent_def_dir"] == env_agent_def_dir.resolve()


def test_start_session_uses_default_agent_def_dir_when_cli_and_env_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured_kwargs: dict[str, object] = {}
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text("{}", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AGENTSYS_AGENT_DEF_DIR", raising=False)

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(backend="codex_headless", tool="codex"),
            agent_identity=None,
            agent_identity_warnings=(),
            startup_warnings=(),
            parsing_mode=None,
        )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.start_runtime_session",
        _fake_start_runtime_session,
    )

    exit_code = cli.main(
        [
            "start-session",
            "--brain-manifest",
            "tmp/brain.yaml",
            "--role",
            "gpu-kernel-coder",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["agent_def_dir"] == (tmp_path / ".agentsys" / "agents").resolve()


def test_send_keys_forwards_sequence_and_escape_mode(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    class _FakeController:
        def send_input_ex(
            self,
            sequence: str,
            *,
            escape_special_keys: bool = False,
        ) -> SessionControlResult:
            captured["sequence"] = sequence
            captured["escape_special_keys"] = escape_special_keys
            return SessionControlResult(
                status="ok",
                action="control_input",
                detail="sent",
            )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    exit_code = cli.main(
        [
            "send-keys",
            "--agent-identity",
            "AGENTSYS-gpu",
            "--sequence",
            "/model<[Enter]>",
            "--escape-special-keys",
        ]
    )

    assert exit_code == 0
    assert captured["sequence"] == "/model<[Enter]>"
    assert captured["escape_special_keys"] is True
    payload = json.loads(capsys.readouterr().out)
    assert payload["action"] == "control_input"
    assert payload["status"] == "ok"


def test_send_keys_returns_error_exit_code_on_control_input_failure(
    monkeypatch,
    tmp_path: Path,
) -> None:
    class _FakeController:
        def send_input_ex(
            self,
            sequence: str,
            *,
            escape_special_keys: bool = False,
        ) -> SessionControlResult:
            del sequence, escape_special_keys
            return SessionControlResult(
                status="error",
                action="control_input",
                detail="unsupported backend",
            )

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    exit_code = cli.main(
        [
            "send-keys",
            "--agent-identity",
            "AGENTSYS-gpu",
            "--sequence",
            "<[Escape]>",
        ]
    )

    assert exit_code == 2
