"""Unit tests for runtime CLI output and argument wiring."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from houmao.agents.realm_controller import cli
from houmao.agents.realm_controller.models import SessionControlResult


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
        "houmao.agents.realm_controller.cli.start_runtime_session",
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
        "houmao.agents.realm_controller.cli.start_runtime_session",
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


def test_start_session_forwards_mailbox_overrides(monkeypatch, tmp_path: Path) -> None:
    manifest_path = tmp_path / "session.json"
    manifest_path.write_text("{}", encoding="utf-8")
    captured_kwargs: dict[str, object] = {}

    def _fake_start_runtime_session(**kwargs: object) -> object:
        captured_kwargs.update(kwargs)
        return SimpleNamespace(
            manifest_path=manifest_path,
            launch_plan=SimpleNamespace(backend="codex_headless", tool="codex", mailbox=None),
            agent_identity=None,
            agent_identity_warnings=(),
            startup_warnings=(),
            parsing_mode=None,
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.start_runtime_session",
        _fake_start_runtime_session,
    )

    mailbox_root = tmp_path / "shared-mail"
    exit_code = cli.main(
        [
            "start-session",
            "--brain-manifest",
            "tmp/brain.yaml",
            "--role",
            "gpu-kernel-coder",
            "--mailbox-transport",
            "filesystem",
            "--mailbox-root",
            str(mailbox_root),
            "--mailbox-principal-id",
            "AGENTSYS-research",
            "--mailbox-address",
            "AGENTSYS-research@agents.localhost",
        ]
    )

    assert exit_code == 0
    assert captured_kwargs["mailbox_transport"] == "filesystem"
    assert captured_kwargs["mailbox_root"] == mailbox_root.resolve()
    assert captured_kwargs["mailbox_principal_id"] == "AGENTSYS-research"
    assert captured_kwargs["mailbox_address"] == "AGENTSYS-research@agents.localhost"


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
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
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
        "houmao.agents.realm_controller.cli.start_runtime_session",
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
        "houmao.agents.realm_controller.cli.start_runtime_session",
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
        "houmao.agents.realm_controller.cli.start_runtime_session",
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


def test_cleanup_registry_outputs_summary(monkeypatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.cleanup_stale_live_agent_records",
        lambda **kwargs: SimpleNamespace(
            registry_root=(tmp_path / "registry").resolve(),
            removed_agent_keys=("dead",),
            preserved_agent_keys=("live",),
            failed_agent_keys=("stuck",),
        ),
    )

    exit_code = cli.main(["cleanup-registry", "--grace-seconds", "0"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["grace_seconds"] == 0
    assert payload["removed_agent_keys"] == ["dead"]
    assert payload["preserved_agent_keys"] == ["live"]
    assert payload["failed_agent_keys"] == ["stuck"]


def test_send_prompt_name_based_uses_tmux_resolved_agent_def_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    env_agent_def_dir = tmp_path / "env-agent-def"
    tmux_agent_def_dir = tmp_path / "tmux-agent-def"
    monkeypatch.setenv("AGENTSYS_AGENT_DEF_DIR", str(env_agent_def_dir))
    captured_resume_kwargs: dict[str, object] = {}

    class _FakeController:
        def send_prompt(self, prompt: str) -> list[object]:
            del prompt
            return []

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=tmux_agent_def_dir.resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
        lambda **kwargs: captured_resume_kwargs.update(kwargs) or _FakeController(),
    )

    exit_code = cli.main(
        [
            "send-prompt",
            "--agent-identity",
            "AGENTSYS-gpu",
            "--prompt",
            "hello",
        ]
    )

    assert exit_code == 0
    assert captured_resume_kwargs["agent_def_dir"] == tmux_agent_def_dir.resolve()


def test_send_prompt_prints_controller_operation_warnings(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    class _FakeController:
        def send_prompt(self, prompt: str) -> list[object]:
            del prompt
            return []

        def consume_operation_warnings(self) -> tuple[str, ...]:
            return ("registry refresh warning",)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    exit_code = cli.main(
        [
            "send-prompt",
            "--agent-identity",
            "AGENTSYS-gpu",
            "--prompt",
            "hello",
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "warning: registry refresh warning" in captured.err


def test_send_prompt_manifest_path_keeps_ambient_agent_def_dir_resolution(
    monkeypatch,
    tmp_path: Path,
) -> None:
    env_agent_def_dir = tmp_path / "env-agent-def"
    monkeypatch.setenv("AGENTSYS_AGENT_DEF_DIR", str(env_agent_def_dir))
    monkeypatch.chdir(tmp_path)
    captured_resolve_kwargs: dict[str, object] = {}
    captured_resume_kwargs: dict[str, object] = {}

    class _FakeController:
        def send_prompt(self, prompt: str) -> list[object]:
            del prompt
            return []

    def _fake_resolve_agent_identity(**kwargs: object) -> object:
        captured_resolve_kwargs.update(kwargs)
        return SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            warnings=(),
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        _fake_resolve_agent_identity,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
        lambda **kwargs: captured_resume_kwargs.update(kwargs) or _FakeController(),
    )

    exit_code = cli.main(
        [
            "send-prompt",
            "--agent-identity",
            str(tmp_path / "session.json"),
            "--prompt",
            "hello",
        ]
    )

    assert exit_code == 0
    assert captured_resolve_kwargs == {
        "agent_identity": str(tmp_path / "session.json"),
        "base": tmp_path.resolve(),
    }
    assert captured_resume_kwargs["agent_def_dir"] == env_agent_def_dir.resolve()


def test_stop_session_name_based_forwards_explicit_agent_def_dir_override(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    override_agent_def_dir = tmp_path / "override-agent-def"
    captured_resolve_kwargs: dict[str, object] = {}
    captured_resume_kwargs: dict[str, object] = {}

    class _FakeController:
        def stop(self, *, force_cleanup: bool = False) -> SessionControlResult:
            del force_cleanup
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="cleaned",
            )

    def _fake_resolve_agent_identity(**kwargs: object) -> object:
        captured_resolve_kwargs.update(kwargs)
        return SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=override_agent_def_dir.resolve(),
            warnings=(),
        )

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        _fake_resolve_agent_identity,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
        lambda **kwargs: captured_resume_kwargs.update(kwargs) or _FakeController(),
    )

    exit_code = cli.main(
        [
            "stop-session",
            "--agent-identity",
            "AGENTSYS-gpu",
            "--agent-def-dir",
            str(override_agent_def_dir),
        ]
    )

    assert exit_code == 0
    assert captured_resolve_kwargs["explicit_agent_def_dir"] == override_agent_def_dir.resolve()
    assert captured_resume_kwargs["agent_def_dir"] == override_agent_def_dir.resolve()
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"


def test_stop_session_prints_controller_operation_warnings(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    class _FakeController:
        def stop(self, *, force_cleanup: bool = False) -> SessionControlResult:
            del force_cleanup
            return SessionControlResult(
                status="ok",
                action="terminate",
                detail="cleaned",
            )

        def consume_operation_warnings(self) -> tuple[str, ...]:
            return ("registry cleanup warning",)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    exit_code = cli.main(
        [
            "stop-session",
            "--agent-identity",
            "AGENTSYS-gpu",
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "warning: registry cleanup warning" in captured.err


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
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
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
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
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
