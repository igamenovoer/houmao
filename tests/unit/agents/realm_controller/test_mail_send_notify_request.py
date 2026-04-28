"""Tests for `notify_block` and `notify_auth` on gateway mail send/post/reply request models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from houmao.agents.realm_controller.gateway_models import (
    GatewayMailPostRequestV1,
    GatewayMailReplyRequestV1,
    GatewayMailSendRequestV1,
)
from houmao.mailbox.protocol import HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE


def test_send_request_accepts_optional_notify_block_and_auth() -> None:
    payload = GatewayMailSendRequestV1(
        to=["bob@houmao.localhost"],
        subject="hello",
        body_content="ordinary body",
        notify_block={"text": "re-run on official path", "placement": "append"},
        notify_auth={"scheme": "none"},
    )

    assert payload.notify_block is not None
    assert payload.notify_block.text == "re-run on official path"
    assert payload.notify_block.placement == "append"
    assert payload.notify_auth is not None
    assert payload.notify_auth.scheme == "none"


def test_send_request_omits_notify_fields_by_default() -> None:
    payload = GatewayMailSendRequestV1(
        to=["bob@houmao.localhost"],
        subject="hello",
        body_content="ordinary body",
    )

    assert payload.notify_block is None
    assert payload.notify_auth is None


def test_send_request_rejects_unsupported_notify_auth_scheme() -> None:
    with pytest.raises(ValidationError, match="verifier not yet supported"):
        GatewayMailSendRequestV1(
            to=["bob@houmao.localhost"],
            subject="hello",
            body_content="ordinary body",
            notify_auth={"scheme": "shared-token"},
        )


def test_post_request_accepts_optional_notify_block_with_prepend() -> None:
    payload = GatewayMailPostRequestV1(
        subject="hello",
        body_content="ordinary body",
        reply_policy=HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
        notify_block={"text": "continue current task", "placement": "prepend"},
    )

    assert payload.notify_block is not None
    assert payload.notify_block.text == "continue current task"
    assert payload.notify_block.placement == "prepend"
    assert payload.notify_auth is None


def test_post_request_rejects_unsupported_notify_auth_scheme() -> None:
    with pytest.raises(ValidationError, match="verifier not yet supported"):
        GatewayMailPostRequestV1(
            subject="hello",
            body_content="ordinary body",
            reply_policy=HOUMAO_OPERATOR_MAILBOX_REPLY_POLICY_VALUE,
            notify_auth={"scheme": "jws"},
        )


def test_reply_request_accepts_optional_notify_block() -> None:
    payload = GatewayMailReplyRequestV1(
        message_ref="filesystem:msg-20260425T120000Z-a1b2c3d4e5f64798aabbccddeeff0011",
        body_content="reply body",
        notify_block={"text": "ack"},
    )

    assert payload.notify_block is not None
    assert payload.notify_block.text == "ack"
    assert payload.notify_block.placement == "append"
    assert payload.notify_auth is None
