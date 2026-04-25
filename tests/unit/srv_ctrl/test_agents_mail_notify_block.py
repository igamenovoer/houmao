"""Tests for the `--notify-block` flag on `houmao-mgr agents mail send|post`."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from houmao.srv_ctrl.commands.agents.mail import mail_group


_FAKE_TARGET = MagicMock(name="ManagedAgentTarget")


@patch("houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target")
@patch("houmao.srv_ctrl.commands.agents.mail.mail_send")
@patch("houmao.srv_ctrl.commands.agents.mail.emit")
def test_send_passes_notify_block_through_to_mail_send(
    mock_emit: MagicMock,
    mock_mail_send: MagicMock,
    mock_resolve: MagicMock,
) -> None:
    mock_resolve.return_value = _FAKE_TARGET
    mock_mail_send.return_value = {"ok": True}
    mock_emit.return_value = None

    runner = CliRunner()
    result = runner.invoke(
        mail_group,
        [
            "send",
            "--agent-name",
            "alice",
            "--to",
            "bob@houmao.localhost",
            "--subject",
            "hello",
            "--body-content",
            "ordinary body",
            "--notify-block",
            "re-run on official path",
        ],
    )

    assert result.exit_code == 0, result.output
    mock_mail_send.assert_called_once()
    kwargs: dict[str, Any] = mock_mail_send.call_args.kwargs
    assert kwargs["notify_block"] == "re-run on official path"


@patch("houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target")
@patch("houmao.srv_ctrl.commands.agents.mail.mail_send")
@patch("houmao.srv_ctrl.commands.agents.mail.emit")
def test_send_omits_notify_block_when_flag_absent(
    mock_emit: MagicMock,
    mock_mail_send: MagicMock,
    mock_resolve: MagicMock,
) -> None:
    mock_resolve.return_value = _FAKE_TARGET
    mock_mail_send.return_value = {"ok": True}
    mock_emit.return_value = None

    runner = CliRunner()
    result = runner.invoke(
        mail_group,
        [
            "send",
            "--agent-name",
            "alice",
            "--to",
            "bob@houmao.localhost",
            "--subject",
            "hello",
            "--body-content",
            "ordinary body with ```houmao-notify\nfrom body\n```",
        ],
    )

    assert result.exit_code == 0, result.output
    kwargs: dict[str, Any] = mock_mail_send.call_args.kwargs
    assert kwargs["notify_block"] is None
    assert "```houmao-notify" in kwargs["body_content"]


@patch("houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target")
@patch("houmao.srv_ctrl.commands.agents.mail.mail_post")
@patch("houmao.srv_ctrl.commands.agents.mail.emit")
def test_post_passes_notify_block_through_to_mail_post(
    mock_emit: MagicMock,
    mock_mail_post: MagicMock,
    mock_resolve: MagicMock,
) -> None:
    mock_resolve.return_value = _FAKE_TARGET
    mock_mail_post.return_value = {"ok": True}
    mock_emit.return_value = None

    runner = CliRunner()
    result = runner.invoke(
        mail_group,
        [
            "post",
            "--agent-name",
            "alice",
            "--subject",
            "hello",
            "--body-content",
            "operator note",
            "--notify-block",
            "continue current task",
        ],
    )

    assert result.exit_code == 0, result.output
    kwargs: dict[str, Any] = mock_mail_post.call_args.kwargs
    assert kwargs["notify_block"] == "continue current task"
