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
    MAIL_RESULT_BEGIN_SENTINEL,
    MAIL_RESULT_END_SENTINEL,
    MAIL_RESULT_SURFACES_PAYLOAD_KEY,
    MailPromptRequest,
    extract_sentinel_blocks,
    parse_mail_result,
    prepare_mail_prompt,
    run_mail_prompt,
    shadow_mail_result_contract_reached,
    shadow_mail_result_for_request_reached,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionEvent,
)
from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import (
    install_runtime_mailbox_system_skills_for_tool,
    mailbox_env_bindings,
)
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox


def _build_launch_plan(tmp_path: Path, *, bootstrap_mailbox: bool = True) -> LaunchPlan:
    home_path = tmp_path / "home"
    install_runtime_mailbox_system_skills_for_tool(tool="claude", home_path=home_path)
    mailbox_root = tmp_path / "mailbox"
    principal_id = "HOUMAO-research"
    address = "HOUMAO-research@agents.localhost"
    if bootstrap_mailbox:
        bootstrap_filesystem_mailbox(
            mailbox_root,
            principal=MailboxPrincipal(principal_id=principal_id, address=address),
        )

    mailbox = FilesystemMailboxResolvedConfig(
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
        home_path=home_path,
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
        prefer_live_gateway=True,
    )

    assert prompt_request.operation == "check"
    assert "`houmao-email-via-agent-gateway`" in prompt_request.prompt
    assert "skills/mailbox/houmao-email-via-filesystem/SKILL.md" not in prompt_request.prompt
    assert "skills/mailbox/email-via-filesystem/SKILL.md" not in prompt_request.prompt
    assert (
        "Do not inspect the current project, repository, or runtime home to rediscover skill "
        "files or infer install locations."
    ) in prompt_request.prompt
    assert "pixi run houmao-mgr agents mail resolve-live" in prompt_request.prompt
    assert "gateway.base_url" in prompt_request.prompt
    assert "attached gateway env vars" not in prompt_request.prompt
    assert "HOUMAO_MAIL_RESULT_BEGIN" in prompt_request.prompt
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
                        "HOUMAO_MAIL_RESULT_BEGIN\n"
                        '{"request_id":"r1","operation":"check"}\n'
                        "HOUMAO_MAIL_RESULT_END\n"
                        "HOUMAO_MAIL_RESULT_BEGIN\n"
                        '{"request_id":"r1","operation":"check"}\n'
                        "HOUMAO_MAIL_RESULT_END"
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
                    "HOUMAO_MAIL_RESULT_BEGIN\n"
                    '{"ok":true,"request_id":"r1","operation":"check","transport":"filesystem","principal_id":"HOUMAO-research","unread_count":1}\n'
                    "HOUMAO_MAIL_RESULT_END"
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
                            "HOUMAO_MAIL_RESULT_BEGIN\n"
                            '{"ok":true,"request_id":"r1","operation":"check","transport":"filesystem","principal_id":"HOUMAO-research","unread_count":3}\n'
                            "HOUMAO_MAIL_RESULT_END"
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


def test_parse_mail_result_prefers_normalized_shadow_surface_for_sentinel_payload(
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    payload = parse_mail_result(
        [
            SessionEvent(
                kind="done",
                message="prompt completed",
                turn_index=1,
                payload={
                    "dialog_projection": {
                        "normalized_text": (
                            "HOUMAO_MAIL_RESULT_BEGIN\n"
                            '{"ok":true,"request_id":"r1","operation":"check","transport":"filesystem","principal_id":"HOUMAO-research","unread_count":7}\n'
                            "HOUMAO_MAIL_RESULT_END"
                        ),
                        "dialog_text": "messy tui chrome without sentinels",
                    }
                },
            ),
        ],
        request_id="r1",
        operation="check",
        mailbox=mailbox,
    )

    assert payload["ok"] is True
    assert payload["unread_count"] == 7


def test_parse_mail_result_prefers_scoped_mail_result_surfaces(tmp_path: Path) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    payload = parse_mail_result(
        [
            SessionEvent(
                kind="done",
                message="prompt completed",
                turn_index=1,
                payload={
                    MAIL_RESULT_SURFACES_PAYLOAD_KEY: [
                        {
                            "surface_id": "shadow_post_submit.raw_text",
                            "text": (
                                "HOUMAO_MAIL_RESULT_BEGIN\n"
                                '{"ok":true,"request_id":"r1","operation":"check","transport":"filesystem","principal_id":"HOUMAO-research","unread_count":9}\n'
                                "HOUMAO_MAIL_RESULT_END"
                            ),
                        }
                    ],
                    "dialog_projection": {
                        "normalized_text": "prompt resumed without any sentinels",
                    },
                },
            ),
        ],
        request_id="r1",
        operation="check",
        mailbox=mailbox,
    )

    assert payload["ok"] is True
    assert payload["unread_count"] == 9


def test_run_mail_prompt_returns_submission_only_result_without_exact_parse(
    tmp_path: Path,
) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    result = run_mail_prompt(
        send_prompt=None,
        send_mail_prompt=lambda _request: [
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
                    "canonical_runtime_status": "completed",
                    "parser_family": "shadow",
                },
            ),
        ],
        prompt_request=MailPromptRequest(
            request_id="mailreq-1",
            operation="send",
            prompt="send mail",
        ),
        mailbox=mailbox,
    )

    assert result["authoritative"] is False
    assert result["status"] == "submitted"
    assert result["execution_path"] == "tui_submission"
    assert result["request_id"] == "mailreq-1"
    assert "preview_result" not in result


def test_run_mail_prompt_maps_busy_backend_error_to_submission_status(tmp_path: Path) -> None:
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    def _raise_busy(_request: MailPromptRequest) -> list[SessionEvent]:
        raise BackendExecutionError("Mailbox command could not start because the target session is busy.")

    result = run_mail_prompt(
        send_prompt=None,
        send_mail_prompt=_raise_busy,
        prompt_request=MailPromptRequest(
            request_id="mailreq-2",
            operation="check",
            prompt="check mail",
        ),
        mailbox=mailbox,
    )

    assert result["authoritative"] is False
    assert result["status"] == "busy"
    assert result["execution_path"] == "tui_submission"


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
                        "HOUMAO_MAIL_RESULT_BEGIN\n"
                        + json.dumps(
                            {
                                "ok": True,
                                "request_id": request_id,
                                "operation": "check",
                                "transport": "filesystem",
                                "principal_id": "HOUMAO-research",
                                "unread_count": 2,
                            }
                        )
                        + "\nHOUMAO_MAIL_RESULT_END"
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
            "HOUMAO-research",
            "--unread-only",
            "--limit",
            "5",
        ]
    )

    assert exit_code == 0
    assert '"operation": "check"' in captured_prompt["prompt"]
    assert '"unread_only": true' in captured_prompt["prompt"]
    payload = json.loads(capsys.readouterr().out)
    assert payload["authoritative"] is False
    assert payload["status"] == "submitted"
    assert payload["preview_result"]["ok"] is True
    assert payload["preview_result"]["unread_count"] == 2


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
                        "HOUMAO_MAIL_RESULT_BEGIN\n"
                        + json.dumps(
                            {
                                "ok": True,
                                "request_id": request_id,
                                "operation": "send",
                                "transport": "filesystem",
                                "principal_id": "HOUMAO-research",
                                "message_ref": "filesystem:msg-20260312T050000Z-abc",
                            }
                        )
                        + "\nHOUMAO_MAIL_RESULT_END"
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
            "HOUMAO-research",
            "--to",
            "HOUMAO-orchestrator@agents.localhost",
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
            "HOUMAO-research",
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
            "HOUMAO-research",
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
            "HOUMAO-research",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["authoritative"] is False
    assert payload["status"] == "busy"
    assert "session busy" in payload["detail"]


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
            "HOUMAO-research",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["authoritative"] is False
    assert payload["status"] == "submitted"
    assert "preview_result" not in payload


# ---------------------------------------------------------------------------
# extract_sentinel_blocks: standalone vs inline sentinel mentions
# ---------------------------------------------------------------------------


def test_extract_sentinel_blocks_finds_standalone_block() -> None:
    text = (
        "Some preamble\n"
        "HOUMAO_MAIL_RESULT_BEGIN\n"
        '{"ok": true}\n'
        "HOUMAO_MAIL_RESULT_END\n"
        "trailing text"
    )
    blocks = extract_sentinel_blocks(text)
    assert len(blocks) == 1
    assert blocks[0].payload_text == '{"ok": true}'
    assert blocks[0].begin_line == 1
    assert blocks[0].end_line == 3


def test_extract_sentinel_blocks_ignores_inline_sentinel_mentions() -> None:
    """Sentinel names inside prose or JSON values are NOT standalone blocks."""
    text = (
        "Return exactly one JSON result between "
        "`HOUMAO_MAIL_RESULT_BEGIN` and `HOUMAO_MAIL_RESULT_END`.\n"
        '{"sentinel_begin": "HOUMAO_MAIL_RESULT_BEGIN", '
        '"sentinel_end": "HOUMAO_MAIL_RESULT_END"}\n'
    )
    blocks = extract_sentinel_blocks(text)
    assert blocks == []


def test_extract_sentinel_blocks_ignores_prompt_echo_finds_real_block() -> None:
    """Prompt echo with inline sentinel names followed by a real standalone block."""
    text = (
        "Return exactly one JSON result between "
        "`HOUMAO_MAIL_RESULT_BEGIN` and `HOUMAO_MAIL_RESULT_END`.\n"
        "\n"
        "HOUMAO_MAIL_REQUEST:\n```json\n"
        '{"response_contract": {"sentinel_begin": "HOUMAO_MAIL_RESULT_BEGIN", '
        '"sentinel_end": "HOUMAO_MAIL_RESULT_END"}}\n'
        "```\n"
        "\n"
        "HOUMAO_MAIL_RESULT_BEGIN\n"
        '{"ok": true, "request_id": "r1", "operation": "check"}\n'
        "HOUMAO_MAIL_RESULT_END\n"
    )
    blocks = extract_sentinel_blocks(text)
    assert len(blocks) == 1
    assert '"ok": true' in blocks[0].payload_text


def test_extract_sentinel_blocks_returns_multiple_blocks() -> None:
    text = (
        "HOUMAO_MAIL_RESULT_BEGIN\n"
        '{"a": 1}\n'
        "HOUMAO_MAIL_RESULT_END\n"
        "HOUMAO_MAIL_RESULT_BEGIN\n"
        '{"b": 2}\n'
        "HOUMAO_MAIL_RESULT_END\n"
    )
    blocks = extract_sentinel_blocks(text)
    assert len(blocks) == 2


def test_extract_sentinel_blocks_begin_without_end() -> None:
    text = 'HOUMAO_MAIL_RESULT_BEGIN\n{"ok": true}\n'
    blocks = extract_sentinel_blocks(text)
    assert blocks == []


# ---------------------------------------------------------------------------
# shadow_mail_result_contract_reached: prompt-echo regression
# ---------------------------------------------------------------------------


def _build_prompt_echo_surface() -> str:
    """Return text mimicking a runtime-owned mailbox prompt echo.

    The surface contains sentinel names in both prose and JSON values but
    no actual standalone sentinel-delimited result block.
    """
    return (
        "Use the installed Houmao mailbox gateway skill `houmao-email-via-agent-gateway` for this mailbox operation.\n"
        "Use the installed runtime-owned Houmao mailbox skills directly from the tool's native skill surface. Do not inspect the current project, repository, or runtime home to rediscover skill files or infer install locations.\n"
        "Use the transport-specific Houmao mailbox skill `houmao-email-via-filesystem` only for transport-local context and no-gateway fallback.\n"
        "Return exactly one JSON result between "
        f"`{MAIL_RESULT_BEGIN_SENTINEL}` and `{MAIL_RESULT_END_SENTINEL}`.\n"
        "\n"
        "HOUMAO_MAIL_REQUEST:\n"
        "```json\n"
        + json.dumps(
            {
                "version": 1,
                "request_id": "mailreq-test",
                "operation": "check",
                "response_contract": {
                    "format": "json",
                    "sentinel_begin": MAIL_RESULT_BEGIN_SENTINEL,
                    "sentinel_end": MAIL_RESULT_END_SENTINEL,
                },
            },
            indent=2,
        )
        + "\n```\n"
    )


def test_shadow_contract_not_reached_for_prompt_echo_only() -> None:
    """Prompt-echo-only surface must NOT satisfy mailbox completion gating."""
    surface_payloads = (
        {"surface_id": "shadow_post_submit.normalized_text", "text": _build_prompt_echo_surface()},
    )
    assert shadow_mail_result_contract_reached(surface_payloads) is False


def test_shadow_contract_reached_when_real_block_follows_echo() -> None:
    """Prompt echo followed by a real standalone result block should satisfy gating."""
    text = (
        _build_prompt_echo_surface()
        + "\n"
        + "HOUMAO_MAIL_RESULT_BEGIN\n"
        + '{"ok": true, "request_id": "r1", "operation": "check"}\n'
        + "HOUMAO_MAIL_RESULT_END\n"
    )
    surface_payloads = ({"surface_id": "shadow_post_submit.normalized_text", "text": text},)
    assert shadow_mail_result_contract_reached(surface_payloads) is True


def test_shadow_contract_for_request_requires_active_request_match(tmp_path: Path) -> None:
    """Shadow completion must ignore sentinel blocks that belong to an earlier mail request."""
    mailbox = _build_launch_plan(tmp_path).mailbox
    assert mailbox is not None
    text = (
        "HOUMAO_MAIL_RESULT_BEGIN\n"
        + '{"ok": true, "request_id": "old", "operation": "send", "transport": "filesystem", "principal_id": "HOUMAO-research", "message_id": "msg-old"}\n'
        + "HOUMAO_MAIL_RESULT_END\n"
    )
    surface_payloads = ({"surface_id": "shadow_post_submit.raw_text", "text": text},)

    assert (
        shadow_mail_result_for_request_reached(
            surface_payloads,
            request_id="new",
            operation="send",
            mailbox=mailbox,
        )
        is False
    )


# ---------------------------------------------------------------------------
# parse_mail_result: prompt-echo + valid result
# ---------------------------------------------------------------------------


def test_parse_mail_result_succeeds_with_prompt_echo_plus_real_block(tmp_path: Path) -> None:
    """Parser must ignore prompt-echo sentinel mentions and accept the standalone block."""
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    result_json = json.dumps(
        {
            "ok": True,
            "request_id": "r1",
            "operation": "check",
            "transport": "filesystem",
            "principal_id": "HOUMAO-research",
            "unread_count": 5,
        }
    )
    text = (
        _build_prompt_echo_surface()
        + "\n"
        + f"HOUMAO_MAIL_RESULT_BEGIN\n{result_json}\nHOUMAO_MAIL_RESULT_END\n"
    )

    payload = parse_mail_result(
        [SessionEvent(kind="assistant", message=text, turn_index=1)],
        request_id="r1",
        operation="check",
        mailbox=mailbox,
    )
    assert payload["ok"] is True
    assert payload["unread_count"] == 5


def test_parse_mail_result_rejects_prompt_echo_only_surface(tmp_path: Path) -> None:
    """Surface with only prompt-echo sentinel mentions and no standalone block must fail."""
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    with pytest.raises(MailboxResultParseError, match="no standalone sentinel-delimited payload"):
        parse_mail_result(
            [SessionEvent(kind="assistant", message=_build_prompt_echo_surface(), turn_index=1)],
            request_id="r1",
            operation="check",
            mailbox=mailbox,
        )


def test_parse_mail_result_still_rejects_malformed_standalone_block(tmp_path: Path) -> None:
    """A real standalone block with invalid JSON must still produce an explicit parse error."""
    launch_plan = _build_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    text = "HOUMAO_MAIL_RESULT_BEGIN\nnot valid json\nHOUMAO_MAIL_RESULT_END\n"
    with pytest.raises(MailboxResultParseError, match="not valid JSON"):
        parse_mail_result(
            [SessionEvent(kind="assistant", message=text, turn_index=1)],
            request_id="r1",
            operation="check",
            mailbox=mailbox,
        )
