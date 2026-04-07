from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import click
import pytest
from click.testing import CliRunner

from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
)
from houmao.agents.realm_controller.gateway_models import GatewayPromptControlErrorV1
from houmao.agents.realm_controller.errors import LaunchPolicyResolutionError
from houmao.server.pair_client import PairAuthorityConnectionError, PairAuthorityHealthProbe
from houmao.server.models import (
    HoumaoCurrentInstance,
    HoumaoHealthResponse,
    HoumaoManagedAgentIdentity,
)
from houmao.srv_ctrl.commands.managed_agents import GatewayPromptControlCliError
from houmao.srv_ctrl.commands.main import cli, main
from houmao.srv_ctrl.server_startup import (
    HoumaoDetachedServerStartResult,
    HoumaoServerStartLogPaths,
)


class _FakeSession:
    def __init__(self, session_id: str) -> None:
        self.id = session_id

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        del mode
        return {"id": self.id}


class _FakePairClient:
    def __init__(self) -> None:
        self.m_delete_session_calls: list[str] = []

    def list_sessions(self) -> list[_FakeSession]:
        return [_FakeSession("sess-a"), _FakeSession("sess-b")]

    def delete_session(self, session_name: str) -> object:
        self.m_delete_session_calls.append(session_name)
        return SimpleNamespace(success=True)


_ACTIONABLE_SELECTOR_ERROR = "\n".join(
    (
        "No local managed agent matched friendly name `agent-test`.",
        "`--agent-name` expects the published friendly managed-agent name. "
        "`agent-test` matches the live local tmux/session alias for agent_name `gpu` "
        "(agent_id `agent-1234`).",
        "Fallback lookup through the default pair authority also failed: "
        "Failed to reach a Houmao pair authority at http://127.0.0.1:9889: connection refused",
        "Retry with `--agent-name gpu`, `--agent-id agent-1234`, "
        "or inspect `houmao-mgr agents list`.",
    )
)


def _decode_json_stream(output: str) -> list[dict[str, object]]:
    """Decode one whitespace-separated JSON object stream."""

    decoder = json.JSONDecoder()
    payloads: list[dict[str, object]] = []
    index = 0
    length = len(output)
    while index < length:
        while index < length and output[index].isspace():
            index += 1
        if index >= length:
            break
        payload, index = decoder.raw_decode(output, index)
        payloads.append(payload)
    return payloads


def _make_native_launch_target(
    *,
    working_directory: Path,
    tool: str,
    role_name: str,
    operator_prompt_mode: str | None,
    auth: str = "default",
    setup: str = "default",
) -> SimpleNamespace:
    """Build one preset-backed native launch target test double."""

    preset = SimpleNamespace(
        tool=tool,
        skills=[],
        setup=setup,
        auth=auth,
        launch_overrides=None,
        launch_env_records=None,
        operator_prompt_mode=operator_prompt_mode,
        mailbox=None,
        extra={},
    )
    preset_path = (working_directory / "preset.yaml").resolve()
    return SimpleNamespace(
        tool=tool,
        agent_def_dir=working_directory / "agents",
        role_name=role_name,
        preset=preset,
        preset_path=preset_path,
    )


def test_top_level_command_inventory_exposes_new_native_surface() -> None:
    assert set(cli.commands.keys()) == {
        "admin",
        "agents",
        "brains",
        "mailbox",
        "project",
        "server",
        "system-skills",
    }


def test_bare_invocation_prints_help() -> None:
    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    assert "Usage: houmao-mgr" in result.output
    assert "server" in result.output
    assert "agents" in result.output
    assert "mailbox" in result.output
    assert "system-skills" in result.output
    assert "cao" not in result.output
    assert "\nTraceback" not in result.output


def test_main_renders_mailbox_click_exception_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _raise_mailbox_failure(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise click.ClickException("expected mailbox failure")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mailbox.resolve_managed_agent_target",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mailbox.register_mailbox_binding",
        _raise_mailbox_failure,
    )

    exit_code = main(["agents", "mailbox", "register", "--agent-id", "agent-123"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "expected mailbox failure" in captured.err
    assert "Traceback" not in captured.err


def test_agents_mailbox_register_accepts_yes_and_forwards_confirmation_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mailbox.resolve_managed_agent_target",
        lambda **kwargs: object(),
    )

    def _register_mailbox_binding(target: object, **kwargs: object) -> dict[str, object]:
        observed["target"] = target
        observed.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mailbox.register_mailbox_binding",
        _register_mailbox_binding,
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "mailbox", "register", "--agent-id", "agent-123", "--yes"],
    )

    assert result.exit_code == 0, result.output
    callback = observed["confirm_destructive_replace"]
    assert callable(callback)
    assert callback("Replace mailbox?") is True


def test_main_renders_gateway_mail_notifier_click_exception_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _raise_notifier_failure(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise click.ClickException("expected notifier failure")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._resolve_gateway_command_target",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_mail_notifier_enable",
        _raise_notifier_failure,
    )

    exit_code = main(
        [
            "agents",
            "gateway",
            "mail-notifier",
            "enable",
            "--agent-id",
            "agent-123",
            "--interval-seconds",
            "60",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "expected notifier failure" in captured.err
    assert "Traceback" not in captured.err


def test_agents_gateway_attach_help_mentions_foreground_mode() -> None:
    result = CliRunner().invoke(cli, ["agents", "gateway", "attach", "--help"])

    assert result.exit_code == 0
    assert "--foreground" in result.output
    assert "--target-tmux-session" in result.output
    assert "--pair-port" in result.output
    assert "Window `0` remains" in result.output
    assert "surface; inspect status" in result.output
    assert "window index" in result.output


def test_agents_gateway_help_mentions_send_keys_and_mail_notifier() -> None:
    result = CliRunner().invoke(cli, ["agents", "gateway", "--help"])

    assert result.exit_code == 0
    assert "send-keys" in result.output
    assert "tui" in result.output
    assert "mail-notifier" in result.output


def test_agents_gateway_tui_help_mentions_subcommands() -> None:
    result = CliRunner().invoke(cli, ["agents", "gateway", "tui", "--help"])

    assert result.exit_code == 0
    assert "state" in result.output
    assert "history" in result.output
    assert "watch" in result.output
    assert "note-prompt" in result.output


def test_agents_gateway_mail_notifier_help_mentions_subcommands() -> None:
    result = CliRunner().invoke(cli, ["agents", "gateway", "mail-notifier", "--help"])

    assert result.exit_code == 0
    assert "status" in result.output
    assert "enable" in result.output
    assert "disable" in result.output


def test_agents_help_mentions_relaunch_and_omits_retired_cao_tree() -> None:
    result = CliRunner().invoke(cli, ["agents", "--help"])

    assert result.exit_code == 0
    assert "mailbox" in result.output
    assert "relaunch" in result.output
    assert "\n  show" not in result.output
    assert "cao" not in result.output


def test_top_level_mailbox_help_mentions_local_admin_surface() -> None:
    result = CliRunner().invoke(cli, ["mailbox", "--help"])

    assert result.exit_code == 0
    assert "local filesystem mailbox administration" in result.output.lower()
    assert "accounts" in result.output
    assert "messages" in result.output
    assert "init" in result.output
    assert "status" in result.output
    assert "register" in result.output
    assert "unregister" in result.output
    assert "repair" in result.output


def test_top_level_project_help_mentions_local_overlay_surface() -> None:
    result = CliRunner().invoke(cli, ["project", "--help"])

    assert result.exit_code == 0
    assert "selected houmao project overlay" in result.output.lower()
    assert "agents" in result.output
    assert "easy" in result.output
    assert "mailbox" in result.output
    assert "init" in result.output
    assert "status" in result.output
    assert "agent-tools" not in result.output
    assert "credential" not in result.output


def test_agents_mailbox_help_mentions_late_registration_surface() -> None:
    result = CliRunner().invoke(cli, ["agents", "mailbox", "--help"])

    assert result.exit_code == 0
    assert "late filesystem mailbox registration" in result.output.lower()
    assert "status" in result.output
    assert "register" in result.output
    assert "unregister" in result.output


@pytest.mark.parametrize(
    ("resolve_target", "argv"),
    [
        (
            "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
            ["agents", "state", "--agent-name", "agent-test"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
            ["agents", "prompt", "--agent-name", "agent-test", "--prompt", "hello"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
            ["agents", "gateway", "tui", "state", "--agent-name", "agent-test"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
            ["agents", "mail", "status", "--agent-name", "agent-test"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.turn.resolve_managed_agent_target",
            ["agents", "turn", "status", "--agent-name", "agent-test", "turn-123"],
        ),
    ],
)
def test_managed_agent_commands_surface_actionable_selector_errors(
    monkeypatch: pytest.MonkeyPatch,
    resolve_target: str,
    argv: list[str],
) -> None:
    monkeypatch.setattr(
        resolve_target,
        lambda **kwargs: (_ for _ in ()).throw(click.ClickException(_ACTIONABLE_SELECTOR_ERROR)),
    )

    result = CliRunner().invoke(cli, argv)

    assert result.exit_code == 1
    assert "No local managed agent matched friendly name `agent-test`." in result.output
    assert "`--agent-name` expects the published friendly managed-agent name." in result.output
    assert "Fallback lookup through the default pair authority also failed:" in result.output
    assert "Retry with `--agent-name gpu`, `--agent-id agent-1234`" in result.output


def test_agents_gateway_attach_forwards_foreground_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: captured.setdefault("resolved_target", kwargs) or "target",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.attach_gateway",
        lambda target, *, foreground=False: (
            captured.update({"target": target, "foreground": foreground}) or {"status": "ok"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "gateway", "attach", "--agent-id", "agent-123", "--foreground"],
    )

    assert result.exit_code == 0, result.output
    assert captured["foreground"] is True
    assert captured["resolved_target"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": None,
    }
    assert json.loads(result.output) == {"status": "ok"}


def test_agents_gateway_attach_current_session_uses_manifest_first_pair_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-pair",
        transport="tui",
        tool="codex",
        session_name="pair-session",
        terminal_id="term-123",
        runtime_session_id=None,
        tmux_session_name="pair-session",
        tmux_window_name="agent",
        manifest_path=str(manifest_path),
        session_root=str(tmp_path.resolve()),
        agent_name="HOUMAO-pair",
        agent_id="agent-123",
    )
    client = SimpleNamespace(
        pair_authority_kind="houmao-server",
        attach_managed_agent_gateway=lambda agent_ref: {
            "status": "ok",
            "agent_ref": agent_ref,
        },
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._try_current_tmux_session_name",
        lambda: "pair-session",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._require_current_tmux_session_name",
        lambda: "pair-session",
    )

    def _read_tmux_env(*, session_name: str, variable_name: str) -> str | None:
        assert session_name == "pair-session"
        assert variable_name == AGENT_MANIFEST_PATH_ENV_VAR
        return str(manifest_path)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        _read_tmux_env,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.load_session_manifest",
        lambda path: SimpleNamespace(path=Path(path), payload={"manifest": "payload"}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            backend="houmao_server_rest",
            tool="codex",
            tmux_session_name="pair-session",
            agent_name="HOUMAO-pair",
            agent_id="agent-123",
            houmao_server=SimpleNamespace(
                api_base_url="http://127.0.0.1:9889",
                session_name="pair-session",
                terminal_id="term-123",
                parsing_mode="shadow_only",
                tmux_window_name="agent",
            ),
        ),
    )

    def _require_pair(*, base_url: str) -> object:
        captured["base_url"] = base_url
        return client

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.require_houmao_server_pair",
        _require_pair,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_identity",
        lambda resolved_client, *, agent_ref: identity,
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach"])

    assert result.exit_code == 0, result.output
    assert captured["base_url"] == "http://127.0.0.1:9889"
    assert json.loads(result.output) == {"status": "ok", "agent_ref": "pair-session"}


def test_agents_gateway_attach_current_session_falls_back_to_registry_agent_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._try_current_tmux_session_name",
        lambda: "headless-session",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._require_current_tmux_session_name",
        lambda: "headless-session",
    )

    def _read_tmux_env(*, session_name: str, variable_name: str) -> str | None:
        assert session_name == "headless-session"
        mapping = {
            AGENT_MANIFEST_PATH_ENV_VAR: None,
            AGENT_ID_ENV_VAR: "published-alpha",
            AGENT_DEF_DIR_ENV_VAR: None,
        }
        return mapping[variable_name]

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        _read_tmux_env,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_live_agent_record_by_agent_id",
        lambda agent_id: SimpleNamespace(
            runtime=SimpleNamespace(
                manifest_path=str(manifest_path),
                agent_def_dir=str(agent_def_dir),
            )
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.load_session_manifest",
        lambda path: SimpleNamespace(path=Path(path), payload={"manifest": "payload"}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            backend="claude_headless",
            tool="claude",
            tmux_session_name="headless-session",
            agent_name="HOUMAO-headless",
            agent_id="published-alpha",
        ),
    )

    def _attach_gateway(*, execution_mode_override: str | None = None) -> object:
        captured["execution_mode_override"] = execution_mode_override
        return SimpleNamespace(status="ok", detail="")

    controller = SimpleNamespace(
        agent_id="published-alpha",
        agent_identity="HOUMAO-headless",
        manifest_path=manifest_path,
        attach_gateway=_attach_gateway,
        gateway_status=lambda: {"status": "local-attached"},
    )

    def _resume_runtime_session(*, agent_def_dir: Path, session_manifest_path: Path) -> object:
        captured["agent_def_dir"] = agent_def_dir
        captured["session_manifest_path"] = session_manifest_path
        return controller

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resume_runtime_session",
        _resume_runtime_session,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._identity_from_controller",
        lambda resolved_controller: HoumaoManagedAgentIdentity(
            tracked_agent_id="tracked-local",
            transport="headless",
            tool="claude",
            session_name=None,
            terminal_id=None,
            runtime_session_id="tracked-local",
            tmux_session_name="headless-session",
            tmux_window_name="agent",
            manifest_path=str(manifest_path),
            session_root=str(tmp_path.resolve()),
            agent_name="HOUMAO-headless",
            agent_id="published-alpha",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.attach_gateway",
        lambda target, *, foreground=False: (
            captured.update({"target": target, "foreground": foreground})
            or {"status": "local-attached"}
        ),
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "attach", "--foreground"])

    assert result.exit_code == 0, result.output
    assert captured["agent_def_dir"] == agent_def_dir
    assert captured["session_manifest_path"] == manifest_path
    assert captured["target"].agent_ref == "published-alpha"
    assert captured["foreground"] is True
    assert json.loads(result.output) == {"status": "local-attached"}


def test_agents_gateway_attach_target_tmux_session_falls_back_to_registry_terminal_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.tmux_session_exists",
        lambda *, session_name: session_name == "external-session",
    )

    def _read_tmux_env(*, session_name: str, variable_name: str) -> str | None:
        assert session_name == "external-session"
        mapping = {
            AGENT_MANIFEST_PATH_ENV_VAR: None,
            AGENT_DEF_DIR_ENV_VAR: None,
        }
        return mapping[variable_name]

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.read_tmux_session_environment_value",
        _read_tmux_env,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_live_agent_records_by_terminal_session_name",
        lambda session_name: (
            SimpleNamespace(
                runtime=SimpleNamespace(
                    manifest_path=str(manifest_path),
                    agent_def_dir=str(agent_def_dir),
                )
            ),
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.load_session_manifest",
        lambda path: SimpleNamespace(path=Path(path), payload={"manifest": "payload"}),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.parse_session_manifest_payload",
        lambda payload, source: SimpleNamespace(
            backend="claude_headless",
            tool="claude",
            tmux_session_name="external-session",
            agent_name="HOUMAO-headless",
            agent_id="published-alpha",
        ),
    )

    controller = SimpleNamespace(
        agent_id="published-alpha",
        agent_identity="HOUMAO-headless",
        manifest_path=manifest_path,
        attach_gateway=lambda *, execution_mode_override=None: (
            captured.setdefault("execution_mode_override", execution_mode_override),
            SimpleNamespace(status="ok", detail=""),
        )[1],
        gateway_status=lambda: {"status": "local-attached"},
    )

    def _resume_runtime_session(*, agent_def_dir: Path, session_manifest_path: Path) -> object:
        captured["agent_def_dir"] = agent_def_dir
        captured["session_manifest_path"] = session_manifest_path
        return controller

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resume_runtime_session",
        _resume_runtime_session,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._identity_from_controller",
        lambda resolved_controller: HoumaoManagedAgentIdentity(
            tracked_agent_id="tracked-local",
            transport="headless",
            tool="claude",
            session_name=None,
            terminal_id=None,
            runtime_session_id="tracked-local",
            tmux_session_name="external-session",
            tmux_window_name="agent",
            manifest_path=str(manifest_path),
            session_root=str(tmp_path.resolve()),
            agent_name="HOUMAO-headless",
            agent_id="published-alpha",
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.attach_gateway",
        lambda target, *, foreground=False: (
            captured.update({"target": target, "foreground": foreground})
            or {"status": "local-attached"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "attach",
            "--target-tmux-session",
            "external-session",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["agent_def_dir"] == agent_def_dir
    assert captured["session_manifest_path"] == manifest_path
    assert captured["target"].agent_ref == "published-alpha"
    assert captured["foreground"] is False
    assert json.loads(result.output) == {"status": "local-attached"}


def test_agents_gateway_send_keys_with_explicit_selector_forwards_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_send_keys",
        lambda resolved_target, *, sequence, escape_special_keys: (
            captured.update(
                {
                    "target": resolved_target,
                    "sequence": sequence,
                    "escape_special_keys": escape_special_keys,
                }
            )
            or {"status": "ok", "detail": "delivered"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "send-keys",
            "--agent-name",
            "gpu",
            "--pair-port",
            "9889",
            "--sequence",
            "<[Escape]>",
            "--escape-special-keys",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": None,
        "agent_name": "gpu",
        "port": 9889,
    }
    assert captured["target"] is target
    assert captured["sequence"] == "<[Escape]>"
    assert captured["escape_special_keys"] is True
    assert json.loads(result.output) == {"status": "ok", "detail": "delivered"}


def test_agents_gateway_prompt_with_explicit_selector_forwards_force_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_prompt",
        lambda resolved_target, *, prompt, force: (
            captured.update({"target": resolved_target, "prompt": prompt, "force": force})
            or {"status": "ok", "sent": True, "forced": force}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "prompt",
            "--agent-name",
            "gpu",
            "--pair-port",
            "9889",
            "--prompt",
            "hello",
            "--force",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": None,
        "agent_name": "gpu",
        "port": 9889,
    }
    assert captured["target"] is target
    assert captured["prompt"] == "hello"
    assert captured["force"] is True
    assert json.loads(result.output) == {"status": "ok", "sent": True, "forced": True}


def test_agents_gateway_prompt_renders_structured_json_error_and_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **_kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_prompt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            GatewayPromptControlCliError(
                GatewayPromptControlErrorV1(
                    forced=False,
                    error_code="not_ready",
                    detail="Gateway prompt rejected because the TUI is not submit-ready.",
                )
            )
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "prompt",
            "--agent-name",
            "gpu",
            "--prompt",
            "hello",
        ],
    )

    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "action": "submit_prompt",
        "detail": "Gateway prompt rejected because the TUI is not submit-ready.",
        "error_code": "not_ready",
        "forced": False,
        "sent": False,
        "status": "error",
    }


def test_agents_gateway_send_keys_inside_tmux_uses_current_session_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._try_current_tmux_session_name",
        lambda: "join-sess",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._resolve_gateway_current_session_target",
        lambda *, session_name=None: (
            captured.setdefault("session_name", session_name),
            target,
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("explicit resolution should not run")
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_send_keys",
        lambda resolved_target, *, sequence, escape_special_keys: (
            captured.update(
                {
                    "target": resolved_target,
                    "sequence": sequence,
                    "escape_special_keys": escape_special_keys,
                }
            )
            or {"status": "ok"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "send-keys",
            "--sequence",
            "abc",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["session_name"] == "join-sess"
    assert captured["target"] is target
    assert captured["sequence"] == "abc"
    assert captured["escape_special_keys"] is False
    assert json.loads(result.output) == {"status": "ok"}


def test_agents_gateway_send_keys_without_selector_outside_tmux_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._try_current_tmux_session_name",
        lambda: None,
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "gateway", "send-keys", "--sequence", "<[Escape]>"],
    )

    assert result.exit_code != 0
    assert (
        "Exactly one of `--agent-id`, `--agent-name`, or `--target-tmux-session` is required"
        in result.output
    )


def test_agents_gateway_rejects_pair_port_with_target_tmux_session() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "status",
            "--target-tmux-session",
            "gpu-session",
            "--pair-port",
            "9891",
        ],
    )

    assert result.exit_code != 0
    assert (
        "`--pair-port` is only supported with an explicit `--agent-id` or `--agent-name` "
        "`status` target."
    ) in result.output


def test_agents_gateway_mail_notifier_enable_current_session_forwards_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._resolve_gateway_current_session_target",
        lambda *, session_name=None: (
            captured.setdefault("session_name", session_name),
            target,
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_mail_notifier_enable",
        lambda resolved_target, *, interval_seconds: (
            captured.update({"target": resolved_target, "interval_seconds": interval_seconds})
            or {"enabled": True, "interval_seconds": interval_seconds}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "mail-notifier",
            "enable",
            "--current-session",
            "--interval-seconds",
            "60",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["session_name"] is None
    assert captured["target"] is target
    assert captured["interval_seconds"] == 60
    assert json.loads(result.output) == {"enabled": True, "interval_seconds": 60}


def test_agents_gateway_tui_state_inside_tmux_uses_current_session_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._try_current_tmux_session_name",
        lambda: "join-sess",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._resolve_gateway_current_session_target",
        lambda *, session_name=None: (
            captured.setdefault("session_name", session_name),
            target,
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("explicit resolution should not run")
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_tui_state",
        lambda resolved_target: (
            captured.update({"target": resolved_target}) or {"terminal_id": "term-123"}
        ),
    )

    result = CliRunner().invoke(cli, ["agents", "gateway", "tui", "state"])

    assert result.exit_code == 0, result.output
    assert captured["session_name"] == "join-sess"
    assert captured["target"] is target
    assert json.loads(result.output) == {"terminal_id": "term-123"}


def test_agents_gateway_tui_note_prompt_forwards_prompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_tui_note_prompt",
        lambda resolved_target, *, prompt: (
            captured.update({"target": resolved_target, "prompt": prompt})
            or {"terminal_id": "term-123"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "tui",
            "note-prompt",
            "--agent-id",
            "agent-123",
            "--prompt",
            "hello",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": None,
    }
    assert captured["target"] is target
    assert captured["prompt"] == "hello"
    assert json.loads(result.output) == {"terminal_id": "term-123"}


def test_agents_gateway_tui_watch_emits_polled_state_until_interrupted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    class _WatchedState:
        def model_dump(self, mode: str = "json") -> dict[str, object]:
            assert mode == "json"
            return {"terminal_id": "term-123", "turn": {"phase": "ready"}}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_tui_state",
        lambda resolved_target: captured.update({"target": resolved_target}) or _WatchedState(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.time.sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "gateway",
            "tui",
            "watch",
            "--agent-name",
            "gpu",
            "--interval-seconds",
            "0.2",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": None,
        "agent_name": "gpu",
        "port": None,
    }
    assert captured["target"] is target
    assert json.loads(result.output.strip()) == {
        "terminal_id": "term-123",
        "turn": {"phase": "ready"},
    }


def test_agents_relaunch_current_session_uses_manifest_first_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._require_current_tmux_session_name",
        lambda: "headless-session",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._resolve_current_session_manifest",
        lambda *, session_name: (
            captured.setdefault("session_name", session_name),
            SimpleNamespace(manifest_path=manifest_path, registry_record=None),
        )[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._resolve_current_session_agent_def_dir",
        lambda *, session_name, registry_record: (
            captured.update(
                {"agent_def_dir_session_name": session_name, "registry_record": registry_record}
            )
            or agent_def_dir
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resume_runtime_session",
        lambda *, agent_def_dir, session_manifest_path: (
            captured.update(
                {
                    "agent_def_dir": agent_def_dir,
                    "session_manifest_path": session_manifest_path,
                }
            )
            or SimpleNamespace(
                agent_id="published-alpha",
                agent_identity="HOUMAO-alpha",
                manifest_path=manifest_path,
                relaunch=lambda: SimpleNamespace(status="ok", detail="Runtime relaunched."),
            )
        ),
    )

    result = CliRunner().invoke(cli, ["agents", "relaunch"])

    assert result.exit_code == 0, result.output
    assert captured == {
        "session_name": "headless-session",
        "agent_def_dir_session_name": "headless-session",
        "registry_record": None,
        "agent_def_dir": agent_def_dir,
        "session_manifest_path": manifest_path,
    }
    assert json.loads(result.output) == {
        "success": True,
        "tracked_agent_id": "published-alpha",
        "detail": "Runtime relaunched.",
    }


def test_agents_relaunch_rejects_port_without_explicit_selector() -> None:
    result = CliRunner().invoke(cli, ["agents", "relaunch", "--port", "9889"])

    assert result.exit_code != 0
    assert (
        "`--port` is only supported with an explicit `--agent-id` or `--agent-name` relaunch target."
        in result.output
    )


def test_agents_relaunch_with_explicit_target_uses_managed_agent_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.relaunch_managed_agent",
        lambda resolved_target: (
            captured.setdefault("target", resolved_target),
            {
                "success": True,
                "tracked_agent_id": "tracked-alpha",
                "detail": "Relaunched through managed authority.",
            },
        )[1],
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "relaunch", "--agent-id", "agent-123", "--port", "9889"],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": 9889,
    }
    assert captured["target"] is target
    assert json.loads(result.output) == {
        "success": True,
        "tracked_agent_id": "tracked-alpha",
        "detail": "Relaunched through managed authority.",
    }


def test_server_status_reports_no_server_running(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_unavailable(*, base_url: str) -> object:
        raise PairAuthorityConnectionError(
            base_url=base_url,
            cause=RuntimeError("connection refused"),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        _raise_unavailable,
    )

    result = CliRunner().invoke(cli, ["server", "status"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "api_base_url": "http://127.0.0.1:9889",
        "detail": "No supported Houmao pair authority is running.",
        "running": False,
    }


def test_server_start_defaults_to_detached_startup_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_start_detached(config: object) -> HoumaoDetachedServerStartResult:
        captured["config"] = config
        return HoumaoDetachedServerStartResult(
            success=True,
            running=True,
            api_base_url="http://127.0.0.1:9999",
            detail="Started houmao-server.",
            pid=123,
            server_root=str((tmp_path / "runtime").resolve()),
            reused_existing=False,
            log_paths=HoumaoServerStartLogPaths(
                stdout=str((tmp_path / "stdout.log").resolve()),
                stderr=str((tmp_path / "stderr.log").resolve()),
            ),
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.start_detached_server", _fake_start_detached
    )

    result = CliRunner().invoke(
        cli,
        [
            "server",
            "start",
            "--api-base-url",
            "http://127.0.0.1:9999",
            "--runtime-root",
            str((tmp_path / "runtime").resolve()),
            "--no-startup-child",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["running"] is True
    assert payload["mode"] == "background"
    assert payload["api_base_url"] == "http://127.0.0.1:9999"
    assert payload["pid"] == 123
    assert payload["reused_existing"] is False
    assert payload["runtime_root"] == str((tmp_path / "runtime").resolve())
    assert (
        payload["runtime_root_detail"]
        == "Selected runtime root from the explicit `--runtime-root` override."
    )
    assert payload["log_paths"]["stdout"].endswith("stdout.log")
    assert captured["config"] is not None


def test_server_start_foreground_keeps_direct_run_server_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.start_detached_server",
        lambda config: (_ for _ in ()).throw(AssertionError("detached start should not run")),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.run_server",
        lambda **kwargs: run_calls.append(kwargs),
    )

    result = CliRunner().invoke(
        cli,
        [
            "server",
            "start",
            "--foreground",
            "--api-base-url",
            "http://127.0.0.1:9998",
            "--no-startup-child",
        ],
    )

    assert result.exit_code == 0, result.output
    assert result.output == ""
    assert len(run_calls) == 1
    assert run_calls[0]["api_base_url"] == "http://127.0.0.1:9998"
    assert run_calls[0]["startup_child"] is False


def test_brains_build_reports_project_aware_runtime_selection_and_bootstrap(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = (tmp_path / "repo").resolve()
    working_directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(working_directory)

    build_result = SimpleNamespace(
        home_id="brain-home-1",
        home_path=(working_directory / "home").resolve(),
        launch_helper_path=(working_directory / "launch.sh").resolve(),
        manifest_path=(working_directory / "brain.json").resolve(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.brains.build_brain_home",
        lambda request: build_result,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "brains",
            "build",
            "--tool",
            "codex",
            "--skill",
            "notes",
            "--setup",
            "default",
            "--auth",
            "work",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_overlay_root = (working_directory / ".houmao").resolve()
    assert payload["runtime_root"] == str((expected_overlay_root / "runtime").resolve())
    assert (
        payload["runtime_root_detail"]
        == "Selected the active project runtime root from the current project overlay."
    )
    assert payload["project_overlay_bootstrapped"] is True
    assert payload["overlay_root"] == str(expected_overlay_root)
    assert (
        payload["overlay_root_detail"]
        == "Selected overlay root from the default project-aware `<cwd>/.houmao` candidate."
    )
    assert (
        payload["overlay_bootstrap_detail"]
        == "Applied implicit bootstrap for the selected overlay root during this invocation."
    )


def test_agents_launch_reports_project_aware_root_details_in_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="codex",
        role_name="gpu-kernel-coder",
        operator_prompt_mode="unattended",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: controller,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "codex",
            "--headless",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_overlay_root = (working_directory / ".houmao").resolve()
    assert payload["runtime_root"] == str((expected_overlay_root / "runtime").resolve())
    assert payload["jobs_root"] == str((expected_overlay_root / "jobs").resolve())
    assert payload["mailbox_root"] == str((expected_overlay_root / "mailbox").resolve())
    assert payload["overlay_root"] == str(expected_overlay_root)
    assert (
        payload["runtime_root_detail"]
        == "Selected the active project runtime root from the current project overlay."
    )
    assert (
        payload["jobs_root_detail"] == "Selected the overlay-local jobs root for this invocation."
    )
    assert (
        payload["mailbox_root_detail"]
        == "Selected the active project mailbox root from the current project overlay."
    )
    assert payload["project_overlay_bootstrapped"] is True
    assert (
        payload["overlay_bootstrap_detail"]
        == "Applied implicit bootstrap for the selected overlay root during this invocation."
    )


def test_agents_launch_uses_invocation_project_roots_when_workdir_points_elsewhere(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_repo = (tmp_path / "source-repo").resolve()
    runtime_workdir = (tmp_path / "runtime-workdir").resolve()
    source_repo.mkdir(parents=True, exist_ok=True)
    runtime_workdir.mkdir(parents=True, exist_ok=True)

    manifest_path = source_repo / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    preset = SimpleNamespace(
        tool="codex",
        skills=[],
        setup="default",
        auth="default",
        launch_overrides=None,
        launch_env_records=None,
        operator_prompt_mode="unattended",
        mailbox=None,
        extra={},
    )
    target = SimpleNamespace(
        tool="codex",
        agent_def_dir=(source_repo / ".houmao" / "agents").resolve(),
        role_name="gpu-kernel-coder",
        preset=preset,
        preset_path=(source_repo / ".houmao" / "agents" / "presets" / "gpu.yaml").resolve(),
    )
    controller = SimpleNamespace(
        manifest_path=source_repo / ".houmao" / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )
    captured: dict[str, object] = {}

    monkeypatch.chdir(source_repo)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: (captured.setdefault("target_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "codex",
            "--headless",
            "--workdir",
            str(runtime_workdir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_overlay_root = (source_repo / ".houmao").resolve()
    assert payload["runtime_root"] == str((expected_overlay_root / "runtime").resolve())
    assert payload["jobs_root"] == str((expected_overlay_root / "jobs").resolve())
    assert payload["mailbox_root"] == str((expected_overlay_root / "mailbox").resolve())
    assert payload["overlay_root"] == str(expected_overlay_root)
    assert payload["project_overlay_bootstrapped"] is True
    assert captured["target_kwargs"]["working_directory"] == runtime_workdir
    assert captured["target_kwargs"]["agent_def_dir"] == (expected_overlay_root / "agents")
    assert captured["start_kwargs"]["working_directory"] == runtime_workdir
    assert not (runtime_workdir / ".houmao").exists()


def test_agents_launch_explicit_preset_path_uses_preset_source_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    invocation_directory = (tmp_path / "invocation").resolve()
    source_repo = (tmp_path / "source-repo").resolve()
    runtime_workdir = (tmp_path / "runtime-workdir").resolve()
    invocation_directory.mkdir(parents=True, exist_ok=True)
    runtime_workdir.mkdir(parents=True, exist_ok=True)
    preset_path = (
        source_repo / ".houmao" / "agents" / "presets" / "gpu-kernel-coder-codex-default.yaml"
    ).resolve()
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(
        "\n".join(
            [
                "role: gpu-kernel-coder",
                "tool: codex",
                "setup: default",
                "skills: []",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = source_repo / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    preset = SimpleNamespace(
        tool="codex",
        skills=[],
        setup="default",
        auth="default",
        launch_overrides=None,
        launch_env_records=None,
        operator_prompt_mode="unattended",
        mailbox=None,
        extra={},
    )
    target = SimpleNamespace(
        tool="codex",
        agent_def_dir=(source_repo / ".houmao" / "agents").resolve(),
        role_name="gpu-kernel-coder",
        preset=preset,
        preset_path=preset_path,
    )
    controller = SimpleNamespace(
        manifest_path=source_repo / ".houmao" / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )
    captured: dict[str, object] = {}

    monkeypatch.chdir(invocation_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: (captured.setdefault("target_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "launch",
            "--agents",
            str(preset_path),
            "--agent-name",
            "gpu",
            "--provider",
            "codex",
            "--headless",
            "--workdir",
            str(runtime_workdir),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_overlay_root = (source_repo / ".houmao").resolve()
    assert payload["runtime_root"] == str((expected_overlay_root / "runtime").resolve())
    assert payload["jobs_root"] == str((expected_overlay_root / "jobs").resolve())
    assert payload["overlay_root"] == str(expected_overlay_root)
    assert captured["target_kwargs"]["agent_def_dir"] == (expected_overlay_root / "agents")
    assert captured["target_kwargs"]["working_directory"] == runtime_workdir
    assert captured["start_kwargs"]["working_directory"] == runtime_workdir
    assert not (invocation_directory / ".houmao").exists()
    assert not (runtime_workdir / ".houmao").exists()


def test_agents_launch_help_exposes_workdir_not_working_directory() -> None:
    result = CliRunner().invoke(cli, ["agents", "launch", "--help"])

    assert result.exit_code == 0, result.output
    assert "--workdir DIRECTORY" in result.output
    assert "--working-directory" not in result.output


def test_server_sessions_shutdown_all_uses_pair_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakePairClient()

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.require_houmao_server_pair",
        lambda *, base_url: client,
    )

    result = CliRunner().invoke(cli, ["server", "sessions", "shutdown", "--all"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert client.m_delete_session_calls == ["sess-a", "sess-b"]
    assert payload["results"] == [
        {"session": "sess-a", "success": True},
        {"session": "sess-b", "success": True},
    ]


def test_agents_launch_builds_and_starts_local_runtime_then_attaches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attach_calls: list[str] = []
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="codex",
        role_name="gpu-kernel-coder",
        operator_prompt_mode="unattended",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (captured.setdefault("build_request", request), build_result)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._caller_has_interactive_terminal",
        lambda: True,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.attach_tmux_session_shared",
        lambda *, session_name: attach_calls.append(session_name),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "codex",
            "--session-name",
            "gpu-session",
        ],
    )

    assert result.exit_code == 0
    payloads = _decode_json_stream(result.output)
    assert payloads == [
        {
            "status": "Managed agent launch complete",
            "agent_name": "gpu",
            "agent_id": "agent-1234",
            "tmux_session_name": "gpu-session",
            "manifest_path": str(controller.manifest_path),
            "runtime_root": str(working_directory / ".houmao" / "runtime"),
            "runtime_root_detail": "Selected the active project runtime root from the current project overlay.",
            "jobs_root": str(working_directory / ".houmao" / "jobs"),
            "jobs_root_detail": "Selected the overlay-local jobs root for this invocation.",
            "mailbox_root": str(working_directory / ".houmao" / "mailbox"),
            "mailbox_root_detail": "Selected the active project mailbox root from the current project overlay.",
            "overlay_root": str(working_directory / ".houmao"),
            "overlay_root_detail": "Selected overlay root from the default project-aware `<cwd>/.houmao` candidate.",
            "project_overlay_bootstrapped": True,
            "overlay_bootstrap_detail": "Applied implicit bootstrap for the selected overlay root during this invocation.",
        }
    ]
    assert captured["build_request"].operator_prompt_mode == "unattended"
    assert captured["build_request"].agent_name == "gpu"
    assert captured["build_request"].agent_id is None
    assert captured["start_kwargs"]["backend"] == "local_interactive"
    assert captured["start_kwargs"]["agent_name"] == "gpu"
    assert captured["start_kwargs"]["agent_id"] is None
    assert attach_calls == ["gpu-session"]


def test_agents_launch_preserves_explicit_as_is_prompt_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="codex",
        role_name="gpu-kernel-coder",
        operator_prompt_mode="as_is",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (captured.setdefault("build_request", request), build_result)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._caller_has_interactive_terminal",
        lambda: False,
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "codex",
        ],
    )

    assert result.exit_code == 0
    assert captured["build_request"].operator_prompt_mode == "as_is"
    assert captured["start_kwargs"]["backend"] == "local_interactive"


def test_agents_launch_non_interactive_skips_tmux_attach_and_reports_manual_follow_up(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="claude",
        role_name="gpu-kernel-coder",
        operator_prompt_mode="unattended",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: controller,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._caller_has_interactive_terminal",
        lambda: False,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.attach_tmux_session_shared",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("attach should be skipped")),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "claude_code",
            "--session-name",
            "gpu-session",
        ],
    )

    assert result.exit_code == 0
    payloads = _decode_json_stream(result.output)
    assert payloads == [
        {
            "status": "Managed agent launch complete",
            "agent_name": "gpu",
            "agent_id": "agent-1234",
            "tmux_session_name": "gpu-session",
            "manifest_path": str(controller.manifest_path),
            "runtime_root": str(working_directory / ".houmao" / "runtime"),
            "runtime_root_detail": "Selected the active project runtime root from the current project overlay.",
            "jobs_root": str(working_directory / ".houmao" / "jobs"),
            "jobs_root_detail": "Selected the overlay-local jobs root for this invocation.",
            "mailbox_root": str(working_directory / ".houmao" / "mailbox"),
            "mailbox_root_detail": "Selected the active project mailbox root from the current project overlay.",
            "overlay_root": str(working_directory / ".houmao"),
            "overlay_root_detail": "Selected overlay root from the default project-aware `<cwd>/.houmao` candidate.",
            "project_overlay_bootstrapped": True,
            "overlay_bootstrap_detail": "Applied implicit bootstrap for the selected overlay root during this invocation.",
        },
        {
            "terminal_handoff": "skipped_non_interactive",
            "attach_command": "tmux attach-session -t gpu-session",
        },
    ]


def test_agents_launch_auth_override_wins_over_preset_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="claude",
        role_name="gpu-kernel-coder",
        operator_prompt_mode=None,
        auth="default",
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="gpu",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (captured.setdefault("build_request", request), build_result)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: controller,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._caller_has_interactive_terminal",
        lambda: False,
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--provider",
            "claude_code",
            "--auth",
            "kimi-coding",
        ],
    )

    assert result.exit_code == 0
    assert captured["build_request"].auth == "kimi-coding"


def test_agents_launch_allows_missing_agent_name(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="claude",
        role_name="gpu-kernel-coder",
        operator_prompt_mode=None,
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-1234",
        agent_identity="HOUMAO-claude-gpu-kernel-coder",
        tmux_session_name="gpu-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: (captured.setdefault("build_request", request), build_result)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._caller_has_interactive_terminal",
        lambda: False,
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--provider",
            "claude_code",
        ],
    )

    assert result.exit_code == 0
    payloads = _decode_json_stream(result.output)
    assert payloads[0]["agent_name"] == "HOUMAO-claude-gpu-kernel-coder"
    assert captured["build_request"].agent_name is None
    assert captured["start_kwargs"]["agent_name"] is None


def test_agents_launch_headless_keeps_native_headless_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="claude",
        role_name="researcher",
        operator_prompt_mode=None,
    )
    controller = SimpleNamespace(
        manifest_path=working_directory / "runtime" / "manifest.json",
        agent_id="agent-claude",
        agent_identity="claude",
        tmux_session_name="claude-session",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (captured.setdefault("start_kwargs", kwargs), controller)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.attach_tmux_session_shared",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("tmux attach should not run")),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "researcher",
            "--agent-name",
            "claude",
            "--provider",
            "claude_code",
            "--headless",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["start_kwargs"]["backend"] == "claude_headless"


def test_agents_launch_interactive_reports_launch_policy_compatibility_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="claude",
        role_name="researcher",
        operator_prompt_mode="unattended",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (_ for _ in ()).throw(
            LaunchPolicyResolutionError(
                requested_operator_prompt_mode="unattended",
                tool="claude",
                policy_backend="raw_launch",
                detected_version="2.1.83",
                detail=(
                    "No compatible unattended launch strategy exists for tool='claude', "
                    "backend='raw_launch', version='2.1.83', "
                    "requested_operator_prompt_mode='unattended'."
                ),
            )
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "researcher",
            "--agent-name",
            "claude",
            "--provider",
            "claude_code",
        ],
    )

    assert result.exit_code != 0
    assert "runtime backend `local_interactive`" in result.output
    assert "provider startup did not begin" in result.output
    assert "requested_operator_prompt_mode='unattended'" in result.output
    assert "policy_backend='raw_launch'" in result.output
    assert "detected_version='2.1.83'" in result.output


def test_agents_launch_headless_reports_launch_policy_compatibility_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = tmp_path.resolve()
    manifest_path = working_directory / "brain.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    build_result = SimpleNamespace(manifest_path=manifest_path)
    target = _make_native_launch_target(
        working_directory=working_directory,
        tool="claude",
        role_name="researcher",
        operator_prompt_mode="unattended",
    )

    monkeypatch.chdir(working_directory)
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_native_launch_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.build_brain_home",
        lambda request: build_result,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.start_runtime_session",
        lambda **kwargs: (_ for _ in ()).throw(
            LaunchPolicyResolutionError(
                requested_operator_prompt_mode="unattended",
                tool="claude",
                policy_backend="claude_headless",
                detected_version="2.1.83",
                detail=(
                    "No compatible unattended launch strategy exists for tool='claude', "
                    "backend='claude_headless', version='2.1.83', "
                    "requested_operator_prompt_mode='unattended'."
                ),
            )
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "researcher",
            "--agent-name",
            "claude",
            "--provider",
            "claude_code",
            "--headless",
        ],
    )

    assert result.exit_code != 0
    assert "runtime backend `claude_headless`" in result.output
    assert "provider startup did not begin" in result.output
    assert "policy_backend='claude_headless'" in result.output
    assert "detected_version='2.1.83'" in result.output


def test_agents_launch_rejects_unsupported_provider() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--agent-name",
            "gpu",
            "--provider",
            "kiro_cli",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid provider `kiro_cli`." in result.output


def test_agents_launch_rejects_removed_yolo_flag() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "launch",
            "--agents",
            "gpu-kernel-coder",
            "--provider",
            "codex",
            "--yolo",
        ],
    )

    assert result.exit_code != 0
    assert "No such option: --yolo" in result.output


def test_server_status_reports_health_and_current_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HealthyClient:
        def __init__(self, base_url: str) -> None:
            self.m_base_url = base_url

        def health_extended(self) -> HoumaoHealthResponse:
            return HoumaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def current_instance(self) -> HoumaoCurrentInstance:
            return HoumaoCurrentInstance(
                pid=123,
                api_base_url=self.m_base_url,
                server_root="/tmp/houmao-server",
            )

        def list_sessions(self) -> list[_FakeSession]:
            return [_FakeSession("sess-a")]

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=_HealthyClient(base_url),
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-server"),
        ),
    )

    result = CliRunner().invoke(cli, ["server", "status", "--port", "9999"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["running"] is True
    assert payload["api_base_url"] == "http://127.0.0.1:9999"
    assert payload["active_session_count"] == 1


def test_server_status_accepts_passive_pair_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PassiveClient:
        def __init__(self, base_url: str) -> None:
            self.m_base_url = base_url

        def current_instance(self) -> HoumaoCurrentInstance:
            return HoumaoCurrentInstance(
                pid=456,
                api_base_url=self.m_base_url,
                server_root="/tmp/houmao-passive-server",
            )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=_PassiveClient(base_url),
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-passive-server"),
        ),
    )

    result = CliRunner().invoke(cli, ["server", "status", "--port", "9891"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["running"] is True
    assert payload["api_base_url"] == "http://127.0.0.1:9891"
    assert payload["health"]["houmao_service"] == "houmao-passive-server"
    assert payload["active_session_count"] is None
    assert payload["active_sessions"] is None


def test_server_stop_accepts_passive_pair_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PassiveClient:
        def shutdown_server(self) -> object:
            return SimpleNamespace(success=True)

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.server.resolve_pair_authority_client",
        lambda *, base_url: SimpleNamespace(
            client=_PassiveClient(),
            health=PairAuthorityHealthProbe(status="ok", houmao_service="houmao-passive-server"),
        ),
    )

    result = CliRunner().invoke(cli, ["server", "stop", "--port", "9891"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "api_base_url": "http://127.0.0.1:9891",
        "detail": "Shutdown request accepted.",
        "running": False,
        "success": True,
    }
