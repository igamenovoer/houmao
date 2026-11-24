"""Protect scoped work request route and proof selection against implicit retries."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from click.testing import CliRunner
import pytest

from houmao.agents.realm_controller.errors import GatewayHttpError
from houmao.passive_server.models import PassiveWorkRequestReceipt
from houmao.srv_ctrl.commands.agents import request
from houmao.srv_ctrl.commands.main import cli


def test_signed_refusal_never_retries_as_anonymous_or_on_another_route(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Select one source and report its refusal without constructing another client."""

    endpoint = Mock()
    endpoint.signed_client.return_value.create_request.side_effect = GatewayHttpError(
        method="POST", url="", status_code=403, detail="Denied"
    )
    select = Mock(return_value=tmp_path / "fixture-signer")
    unsigned_client = Mock()
    detached_submission = Mock()
    monkeypatch.setattr(request, "_verified_endpoint", lambda *_args: endpoint)
    monkeypatch.setattr(request, "_select_signer", select)
    monkeypatch.setattr(request, "GatewayClient", unsigned_client)
    monkeypatch.setattr(request, "_submit_passive_request", detached_submission)

    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "bob",
            "request",
            "--text",
            "/new",
            "--source-agent-id",
            "alice",
        ],
    )

    assert result.exit_code == 1
    assert "403" in result.output
    select.assert_called_once_with("alice", False)
    endpoint.signed_client.assert_called_once_with(select.return_value)
    payload = endpoint.signed_client.return_value.create_request.call_args.args[0]
    assert payload.model_dump(mode="json") == {
        "schema_version": 1,
        "kind": "submit_work_request",
        "payload": {"text": "/new"},
    }
    unsigned_client.assert_not_called()
    detached_submission.assert_not_called()


def test_explicit_detached_route_reports_uncertainty_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep request identity and unconfirmed handoff visible on the selected route."""

    detached_submission = Mock(
        return_value=PassiveWorkRequestReceipt(
            request_id="work-42", outcome="unknown", error_code="handoff_unconfirmed"
        )
    )
    gateway_probe = Mock()
    monkeypatch.setattr(request, "_submit_passive_request", detached_submission)
    monkeypatch.setattr(request, "_verified_endpoint", gateway_probe)

    result = CliRunner().invoke(
        cli,
        [
            "--print-json",
            "agents",
            "single",
            "--agent-id",
            "bob",
            "request",
            "--text",
            "Review PR 42",
            "--passive-url",
            "http://127.0.0.1:9891",
            "--unsigned",
        ],
    )

    assert result.exit_code == 1
    assert "work-42" in result.stdout
    assert "handoff_unconfirmed" in result.stdout
    detached_submission.assert_called_once()
    assert detached_submission.call_args.kwargs["signer"] is None
    gateway_probe.assert_not_called()
