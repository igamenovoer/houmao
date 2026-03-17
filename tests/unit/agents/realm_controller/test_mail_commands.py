from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from houmao.agents.realm_controller import cli
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
    MailboxResultParseError,
)
from houmao.agents.realm_controller.mail_commands import (
    parse_mail_result,
    prepare_mail_prompt,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionEvent,
)
from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox


def _build_launch_plan(tmp_path: Path, *, bootstrap_mailbox: bool = True) -> LaunchPlan:
    mailbox_root = tmp_path / "mailbox"
    principal_id = "AGENTSYS-research"
    address = "AGENTSYS-research@agents.localhost"
    if bootstrap_mailbox:
        bootstrap_filesystem_mailbox(
            mailbox_root,
            principal=MailboxPrincipal(principal_id=principal_id, address=address),
        )

    mailbox = MailboxResolvedConfig(
        transport="filesystem",
        principal_id=principal_id,
        address=address,
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-12T05:00:00.000001Z",
    )
    return LaunchPlan(
        backend="claude_headless",
        tool="claude",
        executable="claude",
        args=["-p"],
        working_directory=tmp_path,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env=mailbox_env_bindings(mailbox),
        env_var_names=sorted(mailbox_env_bindings(mailbox).keys()),
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt",
            role_name="r",
            prompt="Role prompt",
            bootstrap_message="bootstrap",
        ),
        metadata={},
        mailbox=mailbox,
    )


def test_prepare_mail_prompt_references_runtime_skill_and_contract(tmp_path: Path) -> None:
    launch_plan = _build_launch_plan(tmp_path)

    prompt_request = prepare_mail_prompt(
        launch_plan=launch_plan,
        operation="check",
        args={"unread_only": True, "limit": 5},
    )

    assert prompt_request.operation == "check"
    assert ".system/mailbox/email-via-filesystem" in prompt_request.prompt
    assert "AGENTSYS_MAIL_RESULT_BEGIN" in prompt_request.prompt
    assert '"operation": "check"' in prompt_request.prompt


def test_parse_mail_result_rejects_multiple_sentinel_payloads(tmp_path: Path) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    with pytest.raises(MailboxResultParseError, match="exactly one sentinel-delimited payload"):
        parse_mail_result(
            [
                SessionEvent(
                    kind="assistant",
                    message=(
                        "AGENTSYS_MAIL_RESULT_BEGIN\n"
                        '{"request_id":"r1","operation":"check"}\n'
                        "AGENTSYS_MAIL_RESULT_END\n"
                        "AGENTSYS_MAIL_RESULT_BEGIN\n"
                        '{"request_id":"r1","operation":"check"}\n'
                        "AGENTSYS_MAIL_RESULT_END"
                    ),
                    turn_index=1,
                )
            ],
            request_id="r1",
            operation="check",
            mailbox=mailbox,
        )


def test_parse_mail_result_accepts_cao_only_done_event_payload(tmp_path: Path) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    payload = parse_mail_result(
        [
            SessionEvent(
                kind="submitted",
                message="Prompt submitted to CAO terminal",
                turn_index=1,
            ),
            SessionEvent(
                kind="done",
                message=(
                    "AGENTSYS_MAIL_RESULT_BEGIN\n"
                    '{"ok":true,"request_id":"r1","operation":"check","transport":"filesystem","principal_id":"AGENTSYS-research","unread_count":1}\n'
                    "AGENTSYS_MAIL_RESULT_END"
                ),
                turn_index=1,
            ),
        ],
        request_id="r1",
        operation="check",
        mailbox=mailbox,
    )

    assert payload["ok"] is True
    assert payload["unread_count"] == 1


def test_parse_mail_result_accepts_shadow_only_dialog_projection_payload(tmp_path: Path) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    payload = parse_mail_result(
        [
            SessionEvent(
                kind="submitted",
                message="Prompt submitted to CAO terminal",
                turn_index=1,
            ),
            SessionEvent(
                kind="done",
                message="prompt completed",
                turn_index=1,
                payload={
                    "dialog_projection": {
                        "dialog_text": (
                            "AGENTSYS_MAIL_RESULT_BEGIN\n"
                            '{"ok":true,"request_id":"r1","operation":"check","transport":"filesystem","principal_id":"AGENTSYS-research","unread_count":3}\n'
                            "AGENTSYS_MAIL_RESULT_END"
                        )
                    }
                },
            ),
        ],
        request_id="r1",
        operation="check",
        mailbox=mailbox,
    )

    assert payload["ok"] is True
    assert payload["unread_count"] == 3


def test_mail_check_cli_prints_structured_result(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    captured_prompt: dict[str, str] = {}

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            captured_prompt["prompt"] = prompt
            request_id = prompt.split('"request_id": "', 1)[1].split('"', 1)[0]
            return [
                SessionEvent(
                    kind="assistant",
                    message=(
                        "AGENTSYS_MAIL_RESULT_BEGIN\n"
                        + json.dumps(
                            {
                                "ok": True,
                                "request_id": request_id,
                                "operation": "check",
                                "transport": "filesystem",
                                "principal_id": "AGENTSYS-research",
                                "unread_count": 2,
                            }
                        )
                        + "\nAGENTSYS_MAIL_RESULT_END"
                    ),
                    turn_index=1,
                )
            ]

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
            "mail",
            "check",
            "--agent-identity",
            "AGENTSYS-research",
            "--unread-only",
            "--limit",
            "5",
        ]
    )

    assert exit_code == 0
    assert '"operation": "check"' in captured_prompt["prompt"]
    assert '"unread_only": true' in captured_prompt["prompt"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["unread_count"] == 2


def test_mail_send_cli_reads_body_file_and_attachments_into_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text("# Hello\n", encoding="utf-8")
    attachment = tmp_path / "attachment.txt"
    attachment.write_text("attachment\n", encoding="utf-8")
    captured_prompt: dict[str, str] = {}

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            captured_prompt["prompt"] = prompt
            request_id = prompt.split('"request_id": "', 1)[1].split('"', 1)[0]
            return [
                SessionEvent(
                    kind="assistant",
                    message=(
                        "AGENTSYS_MAIL_RESULT_BEGIN\n"
                        + json.dumps(
                            {
                                "ok": True,
                                "request_id": request_id,
                                "operation": "send",
                                "transport": "filesystem",
                                "principal_id": "AGENTSYS-research",
                                "message_id": "msg-20260312T050000Z-abc",
                            }
                        )
                        + "\nAGENTSYS_MAIL_RESULT_END"
                    ),
                    turn_index=1,
                )
            ]

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
            "mail",
            "send",
            "--agent-identity",
            "AGENTSYS-research",
            "--to",
            "AGENTSYS-orchestrator@agents.localhost",
            "--subject",
            "Investigate parser drift",
            "--body-file",
            str(body_file),
            "--attach",
            str(attachment),
        ]
    )

    assert exit_code == 0
    assert "# Hello" in captured_prompt["prompt"]
    assert str(attachment.resolve()) in captured_prompt["prompt"]
    assert '"subject": "Investigate parser drift"' in captured_prompt["prompt"]
    assert '"body_content": "# Hello\\n"' in captured_prompt["prompt"]
    assert '"instruction"' not in captured_prompt["prompt"]


def test_mail_send_cli_rejects_short_recipient_names(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            raise AssertionError(f"send_prompt should not run for invalid CLI input: {prompt}")

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
            "mail",
            "send",
            "--agent-identity",
            "AGENTSYS-research",
            "--to",
            "bob",
            "--subject",
            "Investigate parser drift",
            "--body-content",
            "Hello",
        ]
    )

    assert exit_code == 2
    assert "full mailbox addresses" in capsys.readouterr().err


def test_mail_command_errors_for_missing_bootstrap_assets(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path, bootstrap_mailbox=False)

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            raise AssertionError(
                "send_prompt should not be called when bootstrap assets are missing"
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
            "mail",
            "check",
            "--agent-identity",
            "AGENTSYS-research",
        ]
    )

    assert exit_code == 2
    assert "bootstrap assets are missing" in capsys.readouterr().err


def test_mail_command_errors_for_busy_session(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            del prompt
            raise BackendExecutionError("session busy")

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
            "mail",
            "check",
            "--agent-identity",
            "AGENTSYS-research",
        ]
    )

    assert exit_code == 2
    assert "session is busy" in capsys.readouterr().err


def test_mail_command_errors_on_malformed_sentinel_payload(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            del prompt
            return [SessionEvent(kind="assistant", message="no sentinels here", turn_index=1)]

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
            "mail",
            "check",
            "--agent-identity",
            "AGENTSYS-research",
        ]
    )

    assert exit_code == 2
    assert "parsing failed" in capsys.readouterr().err
