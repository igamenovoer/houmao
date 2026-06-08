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
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    SessionManifestError,
)
from houmao.agents.realm_controller.gateway_models import (
    GatewayPromptControlErrorV1,
    GatewayReminderCreateResultV1,
    GatewayReminderListV1,
    GatewayReminderSendKeysV1,
    GatewayReminderV1,
    GatewayStatusV1,
    GatewayTuiTrackingTimingOverridesV1,
)
from houmao.server.models import (
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentListResponse,
)
from houmao.mailbox.protocol import (
    HOUMAO_NO_REPLY_POLICY_VALUE,
    HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
)
from houmao.srv_ctrl.commands.managed_agents import GatewayPromptControlCliError, ManagedAgentTarget
from houmao.srv_ctrl.commands.main import cli, main
from houmao.version import get_version

_HOUMAO_DOCS_URL = "https://igamenovoer.github.io/houmao/"


def _manifest_gateway_authority(
    *,
    api_base_url: str | None = None,
    managed_agent_ref: str | None = None,
    terminal_id: str | None = None,
    profile_name: str | None = None,
    profile_path: str | None = None,
    parsing_mode: str | None = None,
    tmux_window_name: str | None = None,
) -> SimpleNamespace:
    """Build a current v4 gateway-authority test double."""

    endpoint = SimpleNamespace(
        api_base_url=api_base_url,
        managed_agent_ref=managed_agent_ref,
        terminal_id=terminal_id,
        profile_name=profile_name,
        profile_path=profile_path,
        parsing_mode=parsing_mode,
        tmux_window_name=tmux_window_name,
    )
    return SimpleNamespace(attach=endpoint, control=endpoint)


_ACTIONABLE_SELECTOR_ERROR = "\n".join(
    (
        "No local managed agent matched friendly name `agent-test`.",
        "`--agent-name` expects the published friendly managed-agent name. "
        "`agent-test` matches the live local tmux/session alias for agent_name `gpu` "
        "(agent_id `agent-1234`).",
        "Fallback lookup through the default pair authority also failed: "
        "Failed to reach a Houmao pair authority at http://127.0.0.1:9891: connection refused",
        "Retry with `--agent-name gpu`, `--agent-id agent-1234`, "
        "or inspect `houmao-mgr agents global list`.",
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


def test_top_level_command_inventory_exposes_new_native_surface() -> None:
    assert set(cli.commands.keys()) == {
        "admin",
        "agents",
        "internals",
        "mailbox",
        "project",
        "system-skills",
    }


def test_bare_invocation_prints_help() -> None:
    result = CliRunner().invoke(cli, [])

    assert result.exit_code == 0
    assert "Usage: houmao-mgr" in result.output
    assert "agents" in result.output
    assert "internals" in result.output
    assert "mailbox" in result.output
    assert "system-skills" in result.output
    assert "More detailed docs:" in result.output
    assert _HOUMAO_DOCS_URL in result.output
    assert "cao" not in result.output
    assert "\nTraceback" not in result.output


def test_root_help_lists_version_flag() -> None:
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "--version" in result.output
    assert "More detailed docs:" in result.output
    assert _HOUMAO_DOCS_URL in result.output


def test_root_version_reports_packaged_version() -> None:
    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert get_version() in result.output
    assert "Error:" not in result.output


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

    exit_code = main(["agents", "single", "--agent-id", "agent-123", "mailbox", "register"])
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
        ["agents", "single", "--agent-id", "agent-123", "mailbox", "register", "--yes"],
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
            "single",
            "--agent-id",
            "agent-123",
            "gateway",
            "mail-notifier",
            "enable",
            "--interval-seconds",
            "60",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "expected notifier failure" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize(
    "runtime_error",
    [
        SessionManifestError("expected missing manifest"),
        BackendExecutionError("expected stale runtime"),
    ],
)
def test_main_renders_runtime_domain_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    runtime_error: SessionManifestError | BackendExecutionError,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
        lambda **kwargs: (_ for _ in ()).throw(runtime_error),
    )

    exit_code = main(["agents", "single", "--agent-id", "agent-123", "stop"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert str(runtime_error) in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_uncaught_mailbox_exception_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.mailbox.list_mailbox_accounts",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("unexpected mailbox failure")),
    )

    mailbox_root = (tmp_path / "mailbox").resolve()
    mailbox_root.mkdir(parents=True, exist_ok=True)

    exit_code = main(["mailbox", "accounts", "list", "--mailbox-root", str(mailbox_root)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unexpected internal error while running `houmao-mgr`" in captured.err
    assert "unexpected mailbox failure" in captured.err
    assert "Traceback" not in captured.err


def test_main_renders_empty_uncaught_assertion_as_internal_error_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.mailbox.list_mailbox_accounts",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError()),
    )

    mailbox_root = (tmp_path / "mailbox").resolve()
    mailbox_root.mkdir(parents=True, exist_ok=True)

    exit_code = main(["mailbox", "accounts", "list", "--mailbox-root", str(mailbox_root)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unexpected internal error while running `houmao-mgr`" in captured.err
    assert "exception: AssertionError" in captured.err
    assert captured.err.strip() != "Error: AssertionError"
    assert "Traceback" not in captured.err


def test_main_renders_uncaught_native_recipe_exception_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.native_agent._list_recipe_summaries",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("unexpected recipe failure")),
    )

    exit_code = main(
        [
            "internals",
            "native-agent",
            "recipes",
            "list",
            "--native-agent-root",
            str((tmp_path / "native-agents").resolve()),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Unexpected internal error while running `houmao-mgr`" in captured.err
    assert "unexpected recipe failure" in captured.err
    assert "Traceback" not in captured.err


def test_main_recovers_stale_local_managed_agent_stop_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A stale active local record now retires through stop instead of bubbling a runtime error."""

    from houmao.agents.realm_controller.backends.tmux_runtime import (
        TmuxBackedAuthorityHealth,
    )

    record = SimpleNamespace(
        agent_name="gpu",
        agent_id="agent-1234",
        generation_id="gen-1",
        lifecycle=SimpleNamespace(state="active"),
        identity=SimpleNamespace(backend="codex_headless", tool="codex"),
        runtime=SimpleNamespace(
            agent_def_dir=str((tmp_path / "agent-def").resolve()),
            manifest_path=str((tmp_path / "missing-manifest.json").resolve()),
            session_root=str((tmp_path / "session-root").resolve()),
        ),
        terminal=SimpleNamespace(session_name="gpu-session"),
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents._resolve_local_managed_agent_record_with_miss_context",
        lambda **kwargs: (record, None),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.probe_tmux_backed_authority",
        lambda **kwargs: TmuxBackedAuthorityHealth(
            state="stale_missing_session",
            session_exists=False,
            primary_window_exists=False,
            primary_pane_exists=False,
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.remove_managed_agent_record",
        lambda agent_id, *, generation_id=None: True,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.resume_runtime_session",
        lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("resume should not run for stale active record")
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.managed_agents.require_supported_houmao_pair",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("server fallback should not run")),
    )

    exit_code = main(["agents", "single", "--agent-name", "gpu", "stop"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Broken active managed-agent registry record for `gpu` was already gone" in captured.out
    assert "Traceback" not in captured.err


def test_agents_gateway_attach_help_mentions_foreground_default() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "gateway", "attach", "--help"],
    )

    assert result.exit_code == 0
    assert "--background" in result.output
    assert "--foreground" not in result.output
    assert "--target-tmux-session" not in result.output
    assert "--pair-port" in result.output
    assert "--gateway-tui-watch-poll-interval-seconds FLOAT RANGE" in result.output
    assert "--gateway-tui-stale-active-recovery-seconds FLOAT RANGE" in result.output
    assert "--gateway-tui-final-stable-active-recovery-seconds FLOAT RANGE" in result.output
    assert "Window `0` remains" in result.output
    assert "foreground by default" in result.output


def test_agents_single_gateway_status_surfaces_stale_target_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="agent-stale-1",
        transport="headless",
        tool="codex",
        session_name=None,
        terminal_id=None,
        runtime_session_id="agent-stale-1",
        tmux_session_name="HOUMAO-alice",
        tmux_window_name=None,
        manifest_path="/tmp/missing/manifest.json",
        session_root="/tmp/missing",
        agent_name="alice",
        agent_id="agent-stale-1",
    )
    record = SimpleNamespace(
        agent_name="alice",
        agent_id="agent-stale-1",
        lifecycle=SimpleNamespace(state="active"),
        runtime=SimpleNamespace(
            manifest_path="/tmp/missing/manifest.json",
            session_root="/tmp/missing",
        ),
        terminal=SimpleNamespace(session_name="HOUMAO-alice"),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: ManagedAgentTarget(
            mode="local_stale",
            agent_ref="alice",
            identity=identity,
            record=record,
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-name", "alice", "gateway", "status"],
    )

    assert result.exit_code == 1
    assert "Cannot show gateway status for managed agent `alice`." in result.output
    assert "stale or missing" in result.output
    assert "agent_id=`agent-stale-1`" in result.output
    assert "tmux_session=`HOUMAO-alice`" in result.output
    assert "houmao-mgr agents single --agent-id agent-stale-1 stop" in result.output
    assert "Error: AssertionError" not in result.output


def test_agents_list_plain_renders_rows_from_pydantic_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity = HoumaoManagedAgentIdentity(
        tracked_agent_id="tracked-alpha",
        transport="headless",
        tool="claude",
        session_name=None,
        terminal_id=None,
        runtime_session_id="tracked-alpha",
        tmux_session_name="HOUMAO-alpha",
        tmux_window_name=None,
        manifest_path="/tmp/alpha/manifest.json",
        session_root="/tmp/alpha",
        agent_name="alpha",
        agent_id="agent-alpha",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.list_managed_agents",
        lambda *, port=None: HoumaoManagedAgentListResponse(agents=[identity]),
    )

    result = CliRunner().invoke(cli, ["--print-plain", "agents", "global", "list"])

    assert result.exit_code == 0, result.output
    assert "Managed Agents (1):" in result.output
    assert "alpha" in result.output
    assert "tracked-alpha" in result.output
    assert "claude" in result.output


def test_agents_list_forwards_lifecycle_state_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.list_managed_agents",
        lambda *, port=None, lifecycle_state="active": (
            captured.update({"port": port, "lifecycle_state": lifecycle_state})
            or HoumaoManagedAgentListResponse(agents=[])
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["--print-plain", "agents", "global", "list", "--state", "stopped"],
    )

    assert result.exit_code == 0, result.output
    assert captured == {"port": None, "lifecycle_state": "stopped"}


def test_agents_gateway_status_plain_renders_fields_from_pydantic_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._resolve_gateway_command_target",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_status",
        lambda target: GatewayStatusV1(
            attach_identity="published-alpha",
            backend="claude_headless",
            tmux_session_name="HOUMAO-alpha",
            gateway_health="healthy",
            managed_agent_connectivity="connected",
            managed_agent_recovery="idle",
            request_admission="open",
            terminal_surface_eligibility="ready",
            active_execution="idle",
            execution_mode="tmux_auxiliary_window",
            queue_depth=0,
            gateway_host="127.0.0.1",
            gateway_port=9901,
            gateway_tmux_window_id="@2",
            gateway_tmux_window_index="2",
            managed_agent_instance_epoch=1,
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-plain",
            "agents",
            "single",
            "--agent-name",
            "alpha",
            "gateway",
            "status",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Gateway Status:" in result.output
    assert "attach_identity" in result.output
    assert "published-alpha" in result.output
    assert "gateway_health" in result.output
    assert "healthy" in result.output
    assert "execution_mode" in result.output
    assert "tmux_auxiliary_window" in result.output
    assert "gateway_tmux_window_index" in result.output
    assert "2" in result.output


def test_agents_gateway_help_mentions_send_keys_reminders_and_mail_notifier() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "gateway", "--help"],
    )

    assert result.exit_code == 0
    assert "send-keys" in result.output
    assert "reminders" in result.output
    assert "tui" in result.output
    assert "mail-notifier" in result.output


def test_agents_gateway_tui_help_mentions_subcommands() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "gateway", "tui", "--help"],
    )

    assert result.exit_code == 0
    assert "state" in result.output
    assert "history" in result.output
    assert "watch" in result.output
    assert "note-prompt" in result.output


def test_agents_gateway_mail_notifier_help_mentions_subcommands() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "gateway",
            "mail-notifier",
            "--help",
        ],
    )

    assert result.exit_code == 0
    assert "status" in result.output
    assert "enable" in result.output
    assert "disable" in result.output

    enable_result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "gateway",
            "mail-notifier",
            "enable",
            "--help",
        ],
    )
    assert enable_result.exit_code == 0
    assert "--mode [any_inbox|unread_only]" in enable_result.output
    assert "--appendix-text TEXT" in enable_result.output
    assert "--context-error-policy [continue_current|clear_context]" in enable_result.output
    assert "--pre-notification-context-action [none|compact]" in enable_result.output


def test_agents_gateway_reminders_help_mentions_subcommands() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "gateway", "reminders", "--help"],
    )

    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "create" in result.output
    assert "set" in result.output
    assert "remove" in result.output


def test_agents_help_mentions_relaunch_and_omits_retired_cao_tree() -> None:
    result = CliRunner().invoke(cli, ["agents", "--help"])

    assert result.exit_code == 0
    assert "global" in result.output
    assert "single" in result.output
    assert "self" in result.output
    assert "external" in result.output
    assert "\n  mailbox" not in result.output
    assert "\n  relaunch" not in result.output
    assert "\n  launch" not in result.output
    assert "\n  join" not in result.output
    assert "\n  show" not in result.output
    assert "cao" not in result.output


def test_agents_scoped_join_memory_and_mail_move_help_exposes_current_shapes() -> None:
    runner = CliRunner()

    self_join = runner.invoke(cli, ["agents", "self", "join", "--help"])
    assert self_join.exit_code == 0, self_join.output
    assert "--agent-name" in self_join.output
    assert "--name " not in self_join.output

    self_memory = runner.invoke(cli, ["agents", "self", "memory", "--help"])
    assert self_memory.exit_code == 0, self_memory.output
    assert "path" in self_memory.output
    assert "memo" in self_memory.output

    single_memory = runner.invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "memory", "--help"],
    )
    assert single_memory.exit_code == 0, single_memory.output
    assert "path" in single_memory.output
    assert "memo" in single_memory.output

    mail_move = runner.invoke(cli, ["agents", "self", "mail", "move", "--help"])
    assert mail_move.exit_code == 0, mail_move.output
    assert "--destination-box" in mail_move.output
    assert "--box" not in mail_move.output


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
    assert "first-class local houmao project workflows" in result.output.lower()
    assert "agents" in result.output
    assert "easy" not in result.output
    assert "specialist" in result.output
    assert "profile" in result.output
    assert "mailbox" in result.output
    assert "init" in result.output
    assert "status" in result.output
    assert "credentials" in result.output
    assert "agent-tools" not in result.output


def test_agents_mailbox_help_mentions_late_registration_surface() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "mailbox", "--help"],
    )

    assert result.exit_code == 0
    assert "late filesystem mailbox registration" in result.output.lower()
    assert "status" in result.output
    assert "register" in result.output
    assert "unregister" in result.output


def test_agents_mail_post_help_reports_operator_mailbox_default() -> None:
    result = CliRunner().invoke(cli, ["agents", "self", "mail", "post", "--help"])

    assert result.exit_code == 0
    normalized_output = " ".join(result.output.split())
    assert "[default: operator_mailbox]" in normalized_output
    assert "none" in result.output
    assert "operator_mailbox" in result.output


@pytest.mark.parametrize(
    ("extra_args", "expected_policy"),
    [
        ([], HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE),
        (["--reply-policy", "none"], HOUMAO_NO_REPLY_POLICY_VALUE),
    ],
)
def test_agents_mail_post_forwards_reply_policy_default_and_explicit_none(
    monkeypatch: pytest.MonkeyPatch,
    extra_args: list[str],
    expected_policy: str,
) -> None:
    recorded: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="agent-1234")
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
        lambda **kwargs: target,
    )

    def _mail_post(target_arg: object, **kwargs: object) -> dict[str, object]:
        recorded["target"] = target_arg
        recorded.update(kwargs)
        return {"schema_version": 1, "operation": "post", "status": "verified"}

    monkeypatch.setattr("houmao.srv_ctrl.commands.agents.mail.mail_post", _mail_post)

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-name",
            "agent-test",
            "mail",
            "post",
            "--subject",
            "Operator note",
            "--body-content",
            "Hello",
            *extra_args,
        ],
    )

    assert result.exit_code == 0
    assert recorded["target"] is target
    assert recorded["reply_policy"] == expected_policy


@pytest.mark.parametrize(
    ("resolve_target", "argv"),
    [
        (
            "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
            ["agents", "single", "--agent-name", "agent-test", "state"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.core.resolve_managed_agent_target",
            [
                "agents",
                "single",
                "--agent-name",
                "agent-test",
                "prompt",
                "--prompt",
                "hello",
            ],
        ),
        (
            "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
            ["agents", "single", "--agent-name", "agent-test", "gateway", "tui", "state"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
            ["agents", "single", "--agent-name", "agent-test", "mail", "status"],
        ),
        (
            "houmao.srv_ctrl.commands.agents.turn.resolve_managed_agent_target",
            ["agents", "single", "--agent-name", "agent-test", "turn", "status", "turn-123"],
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


def test_agents_gateway_attach_defaults_to_foreground_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: captured.setdefault("resolved_target", kwargs) or "target",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.attach_gateway",
        lambda target, *, background=False, tui_tracking_timing_overrides=None: (
            captured.update(
                {
                    "target": target,
                    "background": background,
                    "tui_tracking_timing_overrides": tui_tracking_timing_overrides,
                }
            )
            or {"status": "ok"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "single", "--agent-id", "agent-123", "gateway", "attach"],
    )

    assert result.exit_code == 0, result.output
    assert captured["background"] is False
    assert captured["tui_tracking_timing_overrides"] is None
    assert captured["resolved_target"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": None,
    }
    assert json.loads(result.output) == {"status": "ok"}


def test_agents_gateway_attach_forwards_background_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: captured.setdefault("resolved_target", kwargs) or "target",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.attach_gateway",
        lambda target, *, background=False, tui_tracking_timing_overrides=None: (
            captured.update(
                {
                    "target": target,
                    "background": background,
                    "tui_tracking_timing_overrides": tui_tracking_timing_overrides,
                }
            )
            or {"status": "ok"}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "gateway",
            "attach",
            "--background",
            "--gateway-tui-watch-poll-interval-seconds",
            "0.25",
            "--gateway-tui-stale-active-recovery-seconds",
            "6",
            "--gateway-tui-final-stable-active-recovery-seconds",
            "18",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["background"] is True
    timings = captured["tui_tracking_timing_overrides"]
    assert isinstance(timings, GatewayTuiTrackingTimingOverridesV1)
    assert timings.watch_poll_interval_seconds == 0.25
    assert timings.stale_active_recovery_seconds == 6.0
    assert timings.final_stable_active_recovery_seconds == 18.0
    assert captured["resolved_target"] == {
        "agent_id": "agent-123",
        "agent_name": None,
        "port": None,
    }
    assert json.loads(result.output) == {"status": "ok"}


def test_agents_gateway_attach_current_session_rejects_retired_pair_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    manifest_path.write_text("{}\n", encoding="utf-8")

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
            tmux=SimpleNamespace(session_name="pair-session"),
            agent_name="HOUMAO-pair",
            agent_id="agent-123",
            gateway_authority=_manifest_gateway_authority(
                api_base_url="http://127.0.0.1:9889",
                managed_agent_ref="pair-session",
                terminal_id="term-123",
                parsing_mode="shadow_only",
                tmux_window_name="agent",
            ),
            houmao_server=SimpleNamespace(
                api_base_url="http://127.0.0.1:9889",
                session_name="pair-session",
                terminal_id="term-123",
                parsing_mode="shadow_only",
                tmux_window_name="agent",
            ),
        ),
    )

    result = CliRunner().invoke(cli, ["agents", "self", "gateway", "attach"])

    assert result.exit_code != 0
    assert "retired backend `houmao_server_rest`" in result.output
    assert "houmao-passive-server" in result.output


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
            tmux=SimpleNamespace(session_name="headless-session"),
            agent_name="HOUMAO-headless",
            agent_id="published-alpha",
            gateway_authority=_manifest_gateway_authority(),
            houmao_server=None,
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
        lambda target, *, background=False, tui_tracking_timing_overrides=None: (
            captured.update(
                {
                    "target": target,
                    "background": background,
                    "tui_tracking_timing_overrides": tui_tracking_timing_overrides,
                }
            )
            or {"status": "local-attached"}
        ),
    )

    result = CliRunner().invoke(cli, ["agents", "self", "gateway", "attach"])

    assert result.exit_code == 0, result.output
    assert captured["agent_def_dir"] == agent_def_dir
    assert captured["session_manifest_path"] == manifest_path
    assert captured["target"].agent_ref == "published-alpha"
    assert captured["background"] is False
    assert captured["tui_tracking_timing_overrides"] is None
    assert json.loads(result.output) == {"status": "local-attached"}


def test_agents_gateway_target_tmux_session_option_is_not_public_under_scopes() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "gateway",
            "attach",
            "--target-tmux-session",
            "external-session",
        ],
    )

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--target-tmux-session" in result.output


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
            "single",
            "--agent-name",
            "gpu",
            "gateway",
            "send-keys",
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
        lambda resolved_target, *, prompt, force, model=None, reasoning_level=None: (
            captured.update(
                {
                    "target": resolved_target,
                    "prompt": prompt,
                    "force": force,
                    "model": model,
                    "reasoning_level": reasoning_level,
                }
            )
            or {"status": "ok", "sent": True, "forced": force}
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-name",
            "gpu",
            "gateway",
            "prompt",
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
    assert captured["model"] is None
    assert captured["reasoning_level"] is None
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
            "single",
            "--agent-name",
            "gpu",
            "gateway",
            "prompt",
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
            "self",
            "gateway",
            "send-keys",
            "--sequence",
            "abc",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["session_name"] is None
    assert captured["target"] is target
    assert captured["sequence"] == "abc"
    assert captured["escape_special_keys"] is False
    assert json.loads(result.output) == {"status": "ok"}


def test_agents_gateway_send_keys_without_selector_outside_tmux_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway._require_current_tmux_session_name",
        lambda: (_ for _ in ()).throw(
            click.ClickException(
                "Current-session attach must be run from inside the target tmux session."
            )
        ),
    )

    result = CliRunner().invoke(
        cli,
        ["agents", "self", "gateway", "send-keys", "--sequence", "<[Escape]>"],
    )

    assert result.exit_code != 0
    assert (
        "Current-session attach must be run from inside the target tmux session." in result.output
    )


def test_agents_self_gateway_rejects_pair_port() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "self",
            "gateway",
            "status",
            "--pair-port",
            "9891",
        ],
    )

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--pair-port" in result.output


def test_agents_gateway_mail_notifier_enable_current_session_forwards_interval_and_mode(
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
        lambda resolved_target, *, interval_seconds, mode, appendix_text=None, context_error_policy="continue_current", pre_notification_context_action="none": (
            captured.update(
                {
                    "target": resolved_target,
                    "interval_seconds": interval_seconds,
                    "mode": mode,
                    "appendix_text": appendix_text,
                    "context_error_policy": context_error_policy,
                    "pre_notification_context_action": pre_notification_context_action,
                }
            )
            or {
                "enabled": True,
                "interval_seconds": interval_seconds,
                "mode": mode,
                "appendix_text": appendix_text,
                "context_error_policy": context_error_policy,
                "pre_notification_context_action": pre_notification_context_action,
            }
        ),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "self",
            "gateway",
            "mail-notifier",
            "enable",
            "--interval-seconds",
            "60",
            "--mode",
            "unread_only",
            "--appendix-text",
            "Handle release-blocking mail first.",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["session_name"] is None
    assert captured["target"] is target
    assert captured["interval_seconds"] == 60
    assert captured["mode"] == "unread_only"
    assert captured["appendix_text"] == "Handle release-blocking mail first."
    assert captured["context_error_policy"] == "continue_current"
    assert captured["pre_notification_context_action"] == "none"
    assert json.loads(result.output) == {
        "enabled": True,
        "interval_seconds": 60,
        "mode": "unread_only",
        "appendix_text": "Handle release-blocking mail first.",
        "context_error_policy": "continue_current",
        "pre_notification_context_action": "none",
    }


def test_agents_gateway_mail_notifier_enable_rejects_invalid_mode() -> None:
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "self",
            "gateway",
            "mail-notifier",
            "enable",
            "--interval-seconds",
            "60",
            "--mode",
            "bad_mode",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--mode'" in result.output


def test_agents_gateway_reminders_create_with_explicit_selector_builds_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: (captured.setdefault("resolve_kwargs", kwargs), target)[1],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_list_reminders",
        lambda resolved_target: (
            captured.setdefault("list_target", resolved_target),
            GatewayReminderListV1(
                effective_reminder_id="greminder-current",
                reminders=[
                    GatewayReminderV1(
                        reminder_id="greminder-current",
                        mode="one_off",
                        delivery_kind="prompt",
                        title="current",
                        prompt="current prompt",
                        ranking=-10,
                        paused=False,
                        selection_state="effective",
                        delivery_state="scheduled",
                        created_at_utc="2026-04-09T00:00:00+00:00",
                        next_due_at_utc="2026-04-09T00:05:00+00:00",
                    ),
                    GatewayReminderV1(
                        reminder_id="greminder-lower",
                        mode="one_off",
                        delivery_kind="prompt",
                        title="lower",
                        prompt="lower prompt",
                        ranking=5,
                        paused=False,
                        selection_state="blocked",
                        delivery_state="scheduled",
                        created_at_utc="2026-04-09T00:00:01+00:00",
                        next_due_at_utc="2026-04-09T00:10:00+00:00",
                        blocked_by_reminder_id="greminder-current",
                    ),
                ],
            ),
        )[1],
    )

    def _create_reminders(
        resolved_target: object, *, payload: object
    ) -> GatewayReminderCreateResultV1:
        captured["create_target"] = resolved_target
        captured["payload"] = payload
        return GatewayReminderCreateResultV1(
            effective_reminder_id="greminder-new",
            reminders=[
                GatewayReminderV1(
                    reminder_id="greminder-new",
                    mode="one_off",
                    delivery_kind="send_keys",
                    title="Dismiss dialog",
                    send_keys=GatewayReminderSendKeysV1(
                        sequence="<[Escape]>",
                        ensure_enter=False,
                    ),
                    ranking=-11,
                    paused=False,
                    selection_state="effective",
                    delivery_state="scheduled",
                    created_at_utc="2026-04-09T00:00:02+00:00",
                    next_due_at_utc="2026-04-09T00:00:07+00:00",
                )
            ],
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_create_reminders",
        _create_reminders,
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-name",
            "gpu",
            "gateway",
            "reminders",
            "create",
            "--pair-port",
            "9889",
            "--title",
            "Dismiss dialog",
            "--mode",
            "one_off",
            "--sequence",
            "<[Escape]>",
            "--no-ensure-enter",
            "--before-all",
            "--start-after-seconds",
            "5",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["resolve_kwargs"] == {
        "agent_id": None,
        "agent_name": "gpu",
        "port": 9889,
    }
    assert captured["list_target"] is target
    assert captured["create_target"] is target
    payload = captured["payload"]
    definition = payload.reminders[0]
    assert definition.ranking == -11
    assert definition.prompt is None
    assert definition.send_keys is not None
    assert definition.send_keys.sequence == "<[Escape]>"
    assert definition.send_keys.ensure_enter is False
    assert definition.start_after_seconds == 5
    assert json.loads(result.output)["effective_reminder_id"] == "greminder-new"


def test_agents_gateway_reminders_set_preserves_unspecified_fields_and_reranks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")
    existing = GatewayReminderV1(
        reminder_id="greminder-edit",
        mode="repeat",
        delivery_kind="prompt",
        title="existing title",
        prompt="existing prompt",
        ranking=5,
        paused=False,
        selection_state="blocked",
        delivery_state="scheduled",
        created_at_utc="2026-04-09T00:00:00+00:00",
        next_due_at_utc="2026-04-09T01:00:00+00:00",
        interval_seconds=300,
        blocked_by_reminder_id="greminder-current",
    )
    reminder_lists = iter(
        [
            GatewayReminderListV1(
                effective_reminder_id="greminder-current",
                reminders=[
                    GatewayReminderV1(
                        reminder_id="greminder-current",
                        mode="one_off",
                        delivery_kind="prompt",
                        title="current",
                        prompt="current prompt",
                        ranking=-10,
                        paused=False,
                        selection_state="effective",
                        delivery_state="scheduled",
                        created_at_utc="2026-04-09T00:00:01+00:00",
                        next_due_at_utc="2026-04-09T00:05:00+00:00",
                    ),
                    existing,
                ],
            ),
            GatewayReminderListV1(
                effective_reminder_id="greminder-edit",
                reminders=[
                    GatewayReminderV1(
                        reminder_id="greminder-edit",
                        mode="repeat",
                        delivery_kind="prompt",
                        title="existing title",
                        prompt="existing prompt",
                        ranking=-11,
                        paused=False,
                        selection_state="effective",
                        delivery_state="scheduled",
                        created_at_utc="2026-04-09T00:00:00+00:00",
                        next_due_at_utc="2026-04-09T01:00:00+00:00",
                        interval_seconds=300,
                    )
                ],
            ),
        ]
    )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.resolve_managed_agent_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_get_reminder",
        lambda resolved_target, *, reminder_id: (
            captured.setdefault("get_target", resolved_target),
            captured.setdefault("get_reminder_id", reminder_id),
            existing,
        )[2],
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_list_reminders",
        lambda resolved_target: (
            captured.setdefault("list_targets", []).append(resolved_target),
            next(reminder_lists),
        )[1],
    )

    def _put_reminder(
        resolved_target: object, *, reminder_id: str, payload: object
    ) -> GatewayReminderV1:
        captured["put_target"] = resolved_target
        captured["put_reminder_id"] = reminder_id
        captured["put_payload"] = payload
        return GatewayReminderV1(
            reminder_id="greminder-edit",
            mode="repeat",
            delivery_kind="prompt",
            title="existing title",
            prompt="existing prompt",
            ranking=-11,
            paused=False,
            selection_state="effective",
            delivery_state="scheduled",
            created_at_utc="2026-04-09T00:00:00+00:00",
            next_due_at_utc="2026-04-09T01:00:00+00:00",
            interval_seconds=300,
        )

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.gateway.gateway_put_reminder",
        _put_reminder,
    )

    result = CliRunner().invoke(
        cli,
        [
            "--print-plain",
            "agents",
            "single",
            "--agent-name",
            "gpu",
            "gateway",
            "reminders",
            "set",
            "--reminder-id",
            "greminder-edit",
            "--before-all",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = captured["put_payload"]
    assert payload.title == "existing title"
    assert payload.prompt == "existing prompt"
    assert payload.mode == "repeat"
    assert payload.ranking == -11
    assert payload.deliver_at_utc == "2026-04-09T01:00:00+00:00"
    assert payload.interval_seconds == 300
    assert "effective_reminder_id" in result.output
    assert "greminder-edit" in result.output


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

    result = CliRunner().invoke(cli, ["agents", "self", "gateway", "tui", "state"])

    assert result.exit_code == 0, result.output
    assert captured["session_name"] is None
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
            "single",
            "--agent-id",
            "agent-123",
            "gateway",
            "tui",
            "note-prompt",
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
            "single",
            "--agent-name",
            "gpu",
            "gateway",
            "tui",
            "watch",
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

    result = CliRunner().invoke(cli, ["agents", "self", "relaunch"])

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
    result = CliRunner().invoke(cli, ["agents", "self", "relaunch", "--port", "9889"])

    assert result.exit_code != 0
    assert "No such option" in result.output
    assert "--port" in result.output


def test_agents_relaunch_rejects_chat_session_id_without_exact_mode() -> None:
    result = CliRunner().invoke(
        cli,
        ["agents", "self", "relaunch", "--chat-session-id", "provider-session-1"],
    )

    assert result.exit_code != 0
    assert "`--chat-session-id` requires `--chat-session-mode exact`" in result.output


def test_agents_relaunch_current_session_forwards_chat_session_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    manifest_path = (tmp_path / "manifest.json").resolve()
    agent_def_dir = (tmp_path / "agent-def").resolve()
    agent_def_dir.mkdir(parents=True)
    captured: dict[str, object] = {}

    class _Controller:
        agent_id = "published-alpha"
        agent_identity = "HOUMAO-alpha"

        def relaunch(self, *, chat_session=None) -> SimpleNamespace:
            captured["chat_session"] = chat_session
            return SimpleNamespace(status="ok", detail="Runtime relaunched.")

    _Controller.manifest_path = manifest_path

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._require_current_tmux_session_name",
        lambda: "headless-session",
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._resolve_current_session_manifest",
        lambda *, session_name: SimpleNamespace(
            manifest_path=manifest_path,
            registry_record=None,
        ),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core._resolve_current_session_agent_def_dir",
        lambda *, session_name, registry_record: agent_def_dir,
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resume_runtime_session",
        lambda *, agent_def_dir, session_manifest_path: _Controller(),
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "self",
            "relaunch",
            "--chat-session-mode",
            "exact",
            "--chat-session-id",
            "provider-session-1",
        ],
    )

    assert result.exit_code == 0, result.output
    chat_session = captured["chat_session"]
    assert chat_session.mode == "exact"
    assert chat_session.session_id == "provider-session-1"


def test_agents_relaunch_with_explicit_target_uses_managed_agent_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_relaunch_managed_agent_target",
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
        [
            "agents",
            "single",
            "--agent-id",
            "agent-123",
            "relaunch",
            "--port",
            "9889",
        ],
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


def test_agents_relaunch_explicit_target_forwards_chat_session_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    target = SimpleNamespace(agent_ref="published-alpha")

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.resolve_relaunch_managed_agent_target",
        lambda **kwargs: target,
    )

    def _relaunch_managed_agent(resolved_target, *, relaunch_chat_session=None):
        captured["target"] = resolved_target
        captured["relaunch_chat_session"] = relaunch_chat_session
        return {
            "success": True,
            "tracked_agent_id": "tracked-alpha",
            "detail": "Relaunched through managed authority.",
        }

    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.core.relaunch_managed_agent",
        _relaunch_managed_agent,
    )

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-name",
            "alpha",
            "relaunch",
            "--chat-session-mode",
            "tool_last_or_new",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["target"] is target
    chat_session = captured["relaunch_chat_session"]
    assert chat_session.mode == "tool_last_or_new"
    assert chat_session.session_id is None


def test_native_agent_brain_build_reports_direct_root_and_runtime_selection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = (tmp_path / "repo").resolve()
    working_directory.mkdir(parents=True, exist_ok=True)
    native_agent_root = (working_directory / "native-agents").resolve()
    native_agent_root.mkdir(parents=True, exist_ok=True)
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
            "internals",
            "native-agent",
            "brain",
            "build",
            "--native-agent-root",
            str(native_agent_root),
            "--tool",
            "codex",
            "--skill",
            "notes",
            "--setup",
            "default",
            "--auth",
            "work",
            "--runtime-root",
            "runtime",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    expected_runtime_root = (working_directory / "runtime").resolve()
    assert payload["native_agent_root"] == str(native_agent_root)
    assert payload["native_agent_root_source"] == "cli"
    assert payload["runtime_root"] == str(expected_runtime_root)
    assert (
        payload["runtime_root_detail"]
        == "Selected runtime root from the explicit `--runtime-root` override."
    )
    assert "overlay_root" not in payload


def test_native_agent_brain_build_accepts_cwd_relative_preset_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = (tmp_path / "repo").resolve()
    working_directory.mkdir(parents=True, exist_ok=True)
    native_agent_root = (working_directory / "native-agents").resolve()
    native_agent_root.mkdir(parents=True, exist_ok=True)
    preset_path = working_directory / "tests/fixtures/plain-agent-def/presets/smoke.yaml"
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(
        "\n".join(
            [
                "role: server-api-smoke",
                "tool: codex",
                "setup: default",
                "skills: []",
                "auth: yunwu-openai",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(working_directory)

    captured: dict[str, object] = {}
    build_result = SimpleNamespace(
        home_id="brain-home-1",
        home_path=(working_directory / "home").resolve(),
        launch_helper_path=(working_directory / "launch.sh").resolve(),
        manifest_path=(working_directory / "brain.json").resolve(),
    )

    def _build_brain_home(request):
        captured["request"] = request
        return build_result

    monkeypatch.setattr("houmao.srv_ctrl.commands.brains.build_brain_home", _build_brain_home)

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "internals",
            "native-agent",
            "brain",
            "build",
            "--native-agent-root",
            str(native_agent_root),
            "--preset",
            "tests/fixtures/plain-agent-def/presets/smoke.yaml",
            "--runtime-root",
            "runtime",
        ],
    )

    assert result.exit_code == 0, result.output
    request = captured["request"]
    assert request.preset_path == preset_path.resolve()
    assert request.tool == "codex"
    assert request.skills == []
    assert request.setup == "default"
    assert request.auth == "yunwu-openai"


def test_native_agent_brain_build_accepts_bare_preset_with_empty_skills(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    working_directory = (tmp_path / "repo").resolve()
    native_agent_root = (working_directory / "native-agents").resolve()
    preset_path = native_agent_root / "presets/smoke.yaml"
    preset_path.parent.mkdir(parents=True, exist_ok=True)
    preset_path.write_text(
        "\n".join(
            [
                "role: server-api-smoke",
                "tool: codex",
                "setup: default",
                "skills: []",
                "auth: yunwu-openai",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(working_directory)

    captured: dict[str, object] = {}
    build_result = SimpleNamespace(
        home_id="brain-home-1",
        home_path=(working_directory / "home").resolve(),
        launch_helper_path=(working_directory / "launch.sh").resolve(),
        manifest_path=(working_directory / "brain.json").resolve(),
    )

    def _build_brain_home(request):
        captured["request"] = request
        return build_result

    monkeypatch.setattr("houmao.srv_ctrl.commands.brains.build_brain_home", _build_brain_home)

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "internals",
            "native-agent",
            "brain",
            "build",
            "--native-agent-root",
            str(native_agent_root),
            "--preset",
            "smoke",
            "--runtime-root",
            "runtime",
        ],
    )

    assert result.exit_code == 0, result.output
    request = captured["request"]
    assert request.preset_path == preset_path.resolve()
    assert request.skills == []


def test_native_agent_brain_build_rejects_missing_skill_without_preset(
    tmp_path: Path,
) -> None:
    native_agent_root = (tmp_path / "native-agents").resolve()
    native_agent_root.mkdir(parents=True, exist_ok=True)

    result = CliRunner().invoke(
        cli,
        [
            "internals",
            "native-agent",
            "brain",
            "build",
            "--native-agent-root",
            str(native_agent_root),
            "--tool",
            "codex",
            "--setup",
            "default",
            "--auth",
            "work",
        ],
    )

    assert result.exit_code != 0
    assert "Missing required build inputs: --skill" in result.output


def test_agents_launch_paths_are_not_public() -> None:
    runner = CliRunner()
    launch_paths = (
        ["agents", "launch", "--help"],
        ["agents", "global", "launch", "--help"],
        ["agents", "single", "--agent-id", "agent-123", "launch", "--help"],
    )

    for argv in launch_paths:
        result = runner.invoke(cli, argv)
        assert result.exit_code != 0
        assert "No such command 'launch'" in result.output
