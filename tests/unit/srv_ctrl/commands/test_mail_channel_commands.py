"""Channel selection and stale-binding admission at maintained manager surfaces."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

import click
from click.testing import CliRunner
import pytest

from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxResolvedConfig,
    MailboxesResolvedConfig,
    MailboxSlotConfig,
)
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    mutate_session_mailbox_binding,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan
from houmao.mailbox.models import (
    GatewayMailActionResponseV1,
    GatewayMailboxAttachmentV1,
    GatewayMailboxMessageV1,
    GatewayMailboxParticipantV1,
)
from houmao.mailbox.protocol import HOUMAO_OPERATOR_ADDRESS
from houmao.server.models import HoumaoManagedAgentIdentity
from houmao.srv_ctrl.commands import managed_agents
from houmao.srv_ctrl.commands.agents.mail import mail_group
from houmao.srv_ctrl.commands.main import cli


def _mail_target(root: Path) -> managed_agents.ManagedAgentTarget:
    """Persist an offline binding while keeping a deliberately stale controller copy."""

    binding = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        agent_id="owner-a",
        principal_id="owner-a",
        binding_id="registration-a",
        address="alice@houmao.localhost",
        filesystem_root=root / "store",
        bindings_version="initial-revision",
    )
    plan = LaunchPlan(
        backend="local_interactive",
        tool="claude",
        executable="claude",
        args=[],
        working_directory=root,
        home_env_var="CLAUDE_CONFIG_DIR",
        home_path=root / "home",
        env={},
        env_var_names=[],
        role_injection=RoleInjectionPlan(
            method="native_append_system_prompt", role_name="worker", prompt="Work."
        ),
        mailboxes=MailboxesResolvedConfig(offline=MailboxSlotConfig(binding=binding)),
    )
    path = root / "manifest.json"
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=plan,
            role_name="worker",
            brain_manifest_path=root / "brain.yaml",
            agent_name="alice",
            agent_id="owner-a",
            tmux_session_name="HOUMAO-alice",
            session_id="session-a",
            backend_state={"working_directory": str(root)},
        )
    )
    write_session_manifest(path, payload)
    return managed_agents.ManagedAgentTarget(
        mode="local",
        agent_ref="owner-a",
        identity=HoumaoManagedAgentIdentity(
            tracked_agent_id="owner-a",
            agent_id="owner-a",
            transport="tui",
            tool="claude",
        ),
        controller=SimpleNamespace(agent_id="owner-a", manifest_path=path, launch_plan=plan),
    )


def test_cli_requires_channel_before_target_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
        lambda **kwargs: pytest.fail("missing channel must fail before resolution"),
    )
    result = CliRunner().invoke(mail_group, ["list", "--agent-id", "owner-a"])
    assert result.exit_code == 2
    assert "Missing option '--channel'" in result.output


@pytest.mark.parametrize("scope", [["single", "--agent-id", "owner-a"], ["self"]])
def test_scoped_cli_preserves_explicit_channel_and_round_binding(
    monkeypatch: pytest.MonkeyPatch, scope: list[str]
) -> None:
    observed: dict[str, Any] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.mail_list",
        lambda target, **kwargs: observed.update(kwargs) or {"ok": True},
    )
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            *scope,
            "mail",
            "list",
            "--channel",
            "online",
            "--expected-binding-id",
            "account-round-a",
        ],
    )
    assert result.exit_code == 0, result.output
    assert observed["channel"] == "online"
    assert observed["expected_binding_id"] == "account-round-a"


def test_fresh_send_rejects_replaced_binding_before_backend_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _mail_target(tmp_path)
    controller = target.controller
    assert controller is not None
    old_slot = controller.launch_plan.mailboxes.offline
    replacement = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        agent_id="owner-a",
        principal_id="owner-a",
        binding_id="registration-b",
        address="alice@houmao.localhost",
        filesystem_root=tmp_path / "store",
        bindings_version="replacement-revision",
    )
    mutate_session_mailbox_binding(
        controller.manifest_path,
        channel="offline",
        expected_revision=old_slot.revision,
        binding=replacement,
        agent_id="owner-a",
        session_id="session-a",
    )
    monkeypatch.setattr(
        managed_agents,
        "build_gateway_mailbox_adapter",
        lambda binding: pytest.fail("stale fresh send must not create a backend"),
    )
    with pytest.raises(click.ClickException, match="binding changed"):
        managed_agents.mail_send(
            target,
            channel="offline",
            expected_binding_id="registration-a",
            to_recipients=["bob@houmao.localhost"],
            cc_recipients=[],
            subject="Work",
            body_content="Hello",
            attachments=[],
        )
    assert (
        managed_agents._resolve_mail_expected_binding(target, "offline", None) == "registration-b"
    )
    assert controller.launch_plan.mailboxes.offline.binding.binding_id == "registration-a"


def test_empty_other_channel_never_falls_back_to_offline(tmp_path: Path) -> None:
    target = _mail_target(tmp_path)
    with pytest.raises(click.ClickException, match="no configured online"):
        managed_agents._resolve_mail_expected_binding(target, "online", None)


def test_offline_membership_help_excludes_takeover_and_legacy_commands() -> None:
    runner = CliRunner()
    group = runner.invoke(cli, ["agents", "self", "mailbox", "offline", "--help"])
    assert group.exit_code == 0, group.output
    assert all(command in group.output for command in ("join", "leave", "status"))
    join = runner.invoke(cli, ["agents", "self", "mailbox", "offline", "join", "--help"])
    assert join.exit_code == 0, join.output
    assert "--registry-url" in join.output
    assert all(flag not in join.output for flag in ("--yes", "--mode", "--principal-id"))
    removed = runner.invoke(cli, ["agents", "self", "mailbox", "register"])
    assert removed.exit_code == 2


def test_pair_send_forwards_channel_and_pinned_binding_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from houmao.mailbox.models import GatewayMailStatusV1, MailboxChannelStatusV1

    calls: list[tuple[str, object]] = []
    summary = GatewayMailStatusV1(
        agent_id="remote-agent",
        online=MailboxChannelStatusV1(
            agent_id="remote-agent",
            channel="online",
            binding_id="account-a",
            revision="revision-a",
            address="alice@example.test",
            transport="stalwart",
            available=True,
        ),
    )

    def status(agent_ref: str) -> GatewayMailStatusV1:
        calls.append(("status", agent_ref))
        return summary

    def send(agent_ref: str, request: object, *, channel: str) -> GatewayMailActionResponseV1:
        calls.append(("send", (agent_ref, channel, getattr(request, "expected_binding_id"))))
        return GatewayMailActionResponseV1(
            operation="send",
            transport="stalwart",
            principal_id="remote-agent",
            address="alice@example.test",
            message=GatewayMailboxMessageV1(
                message_ref="scoped-stalwart-ref",
                created_at_utc="2026-11-24T00:00:00Z",
                subject="Work",
                sender=GatewayMailboxParticipantV1(address="alice@example.test"),
                to=[GatewayMailboxParticipantV1(address="bob@example.test")],
            ),
        )

    target = managed_agents.ManagedAgentTarget(
        mode="server",
        agent_ref="remote-ref",
        identity=HoumaoManagedAgentIdentity(
            tracked_agent_id="remote-agent",
            agent_id="remote-agent",
            transport="headless",
            tool="codex",
        ),
        client=SimpleNamespace(get_managed_agent_mail_status=status, send_managed_agent_mail=send),
    )
    result = managed_agents.mail_send(
        target,
        channel="online",
        expected_binding_id="account-a",
        to_recipients=["bob@example.test"],
        cc_recipients=[],
        subject="Work",
        body_content="Hello",
        attachments=[],
    )
    assert result["authoritative"] is True
    assert result["binding_id"] == "account-a"
    assert result["channel"] == "online"
    assert result["transport"] == "stalwart"
    assert result["message_ref"] == "scoped-stalwart-ref"
    assert calls == [("status", "remote-ref"), ("send", ("remote-ref", "online", "account-a"))]
    calls.clear()
    with pytest.raises(click.ClickException, match="binding changed"):
        managed_agents.mail_send(
            target,
            channel="online",
            expected_binding_id="replaced-account",
            to_recipients=["bob@example.test"],
            cc_recipients=[],
            subject="Work",
            body_content="Hello",
            attachments=[],
        )
    assert calls == [("status", "remote-ref")]


@pytest.mark.parametrize("scope", [["single", "--agent-id", "owner-a"], ["self"]])
@pytest.mark.parametrize("style", ["plain", "fancy", "json"])
@pytest.mark.parametrize("operation", ["send", "reply", "post"])
def test_gateway_mail_write_prints_one_scoped_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scope: list[str],
    style: str,
    operation: Literal["send", "reply", "post"],
) -> None:
    """Print the actual envelope and full references from one gateway request."""

    target = _mail_target(tmp_path)
    mailbox = "alice@houmao.localhost"
    sender = HOUMAO_OPERATOR_ADDRESS if operation == "post" else mailbox
    to = [mailbox] if operation == "post" else ["actual@example.test", "second@example.test"]
    cc = [] if operation == "post" else ["copy@example.test", "other-copy@example.test"]
    reference = "hmail1." + "opaque-reference." * 12
    subject = "Actual [result]\nwith unicode \u2603"
    response = GatewayMailActionResponseV1(
        operation=operation,
        transport="filesystem",
        principal_id="owner-a",
        address=mailbox,
        message=GatewayMailboxMessageV1(
            message_ref=reference,
            created_at_utc="2026-11-24T00:00:00Z",
            subject=subject,
            sender=GatewayMailboxParticipantV1(address=sender),
            to=[GatewayMailboxParticipantV1(address=address) for address in to],
            cc=[GatewayMailboxParticipantV1(address=address) for address in cc],
            body_text="private message body",
            attachments=[
                GatewayMailboxAttachmentV1(
                    attachment_id="private-attachment",
                    kind="file",
                    media_type="application/pdf",
                    label="private.pdf",
                    size_bytes=100,
                )
            ],
        ),
    )
    calls: list[tuple[str, str]] = []

    def dispatch(request: Any, *, channel: str) -> GatewayMailActionResponseV1:
        calls.append((channel, request.expected_binding_id))
        if operation == "reply":
            assert request.message_ref == "parent-ref"
        return response

    gateway = SimpleNamespace(**{f"{operation}_mail": dispatch})
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
        lambda **kwargs: target,
    )
    monkeypatch.setattr(
        managed_agents, "_live_gateway_client_for_controller", lambda *args, **kwargs: gateway
    )
    args = {
        "send": ["--to", "requested@example.test", "--subject", "Requested"],
        "reply": ["--message-ref", "parent-ref"],
        "post": ["--subject", "Requested"],
    }[operation]
    result = CliRunner().invoke(
        cli,
        [
            f"--print-{style}",
            "agents",
            *scope,
            "mail",
            operation,
            "--channel",
            "offline",
            "--body-content",
            "requested message body",
            *args,
        ],
        env={"COLUMNS": "48"},
    )
    assert result.exit_code == 0, result.output
    assert calls == [("offline", "registration-a")]
    expected = {
        "schema_version": 1,
        "operation": operation,
        "status": "verified",
        "authoritative": True,
        "execution_path": "gateway_backed",
        "channel": "offline",
        "binding_id": "registration-a",
        "transport": "filesystem",
        "principal_id": "owner-a",
        "address": mailbox,
        "sender_address": sender,
        "to": to,
        "cc": cc,
        "subject": subject,
        "message_ref": reference,
        "created_at_utc": "2026-11-24T00:00:00Z",
    }
    if operation == "reply":
        expected["parent_message_ref"] = "parent-ref"
    if style == "json":
        assert json.loads(result.output) == expected
    else:
        from rich.ansi import AnsiDecoder

        lines = (line.plain for line in AnsiDecoder().decode(result.output))
        actual = dict(line.strip().split(maxsplit=1) for line in lines)
        assert actual == {
            field: value if isinstance(value, str) and value.isprintable() else json.dumps(value)
            for field, value in expected.items()
        }
    assert "private message body" not in result.output
    assert "private.pdf" not in result.output


def test_offline_mixed_recipient_batch_fails_before_staging_or_delivery(tmp_path: Path) -> None:
    from houmao.mailbox import bootstrap_filesystem_mailbox
    from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox
    from houmao.mailbox.scope import MailScope
    from houmao.mailbox.services import (
        GatewayMailboxError,
        ScopedMailboxAdapter,
        build_gateway_mailbox_adapter,
    )

    paths = bootstrap_filesystem_mailbox(tmp_path / "store")
    registrations: dict[str, dict[str, object]] = {}
    for owner in ("alice", "bob"):
        address = f"{owner}@houmao.localhost"
        registrations[owner] = register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=address,
                owner_principal_id=owner,
                mailbox_kind="in_root",
                mailbox_path=paths.mailbox_entry_path(address),
            ),
        )
    binding = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        agent_id="alice",
        principal_id="alice",
        binding_id=str(registrations["alice"]["active_registration_id"]),
        address="alice@houmao.localhost",
        filesystem_root=paths.root,
        bindings_version="revision-a",
    )
    adapter = ScopedMailboxAdapter.from_backend(
        build_gateway_mailbox_adapter(binding),
        MailScope("alice", "offline", binding.binding_id),
    )
    before_messages = set(paths.messages_dir.rglob("*"))
    before_staging = set(paths.staging_dir.rglob("*"))
    with pytest.raises(GatewayMailboxError, match="not an active registered"):
        adapter.send(
            to_addresses=["bob@houmao.localhost", "cloud-only@example.test"],
            cc_addresses=[],
            subject="Work",
            body_content="Hello",
            attachments=[],
        )
    assert set(paths.messages_dir.rglob("*")) == before_messages
    assert set(paths.staging_dir.rglob("*")) == before_staging


def test_wrong_channel_reference_is_a_cli_error_before_backend_io(tmp_path: Path) -> None:
    from houmao.mailbox.scope import MailScope

    target = _mail_target(tmp_path)
    foreign = MailScope("owner-a", "online", "account-a").encode("stalwart:shared-id")
    with pytest.raises(click.ClickException, match="another owner, channel, or binding"):
        managed_agents.mail_reply(
            target,
            channel="offline",
            expected_binding_id="registration-a",
            message_ref=foreign,
            body_content="Reply",
            attachments=[],
        )


def test_forged_foreign_storage_id_cannot_reply_or_partially_mark_owned_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from houmao.mailbox import bootstrap_filesystem_mailbox
    from houmao.mailbox.managed import RegisterMailboxRequest, register_mailbox
    from houmao.mailbox.scope import MailScope
    from houmao.mailbox.services import (
        GatewayMailboxError,
        ScopedMailboxAdapter,
        build_gateway_mailbox_adapter,
    )

    paths = bootstrap_filesystem_mailbox(tmp_path / "store")
    backends = {}
    scopes = {}
    for owner in ("alice", "bob", "carol"):
        address = f"{owner}@houmao.localhost"
        registration = register_mailbox(
            paths.root,
            RegisterMailboxRequest(
                mode="safe",
                address=address,
                owner_principal_id=owner,
                mailbox_kind="in_root",
                mailbox_path=paths.mailbox_entry_path(address),
            ),
        )
        binding = FilesystemMailboxResolvedConfig(
            transport="filesystem",
            agent_id=owner,
            principal_id=owner,
            binding_id=str(registration["active_registration_id"]),
            address=address,
            filesystem_root=paths.root,
            bindings_version="revision-a",
        )
        backends[owner] = build_gateway_mailbox_adapter(binding)
        scopes[owner] = MailScope(owner, "offline", binding.binding_id)
    foreign = backends["bob"].send(
        to_addresses=["carol@houmao.localhost"],
        cc_addresses=[],
        subject="Private Bob/Carol",
        body_content="Private content",
        attachments=[],
    )
    owned = backends["bob"].send(
        to_addresses=["alice@houmao.localhost"],
        cc_addresses=[],
        subject="Alice task",
        body_content="Work",
        attachments=[],
    )
    alice = ScopedMailboxAdapter.from_backend(backends["alice"], scopes["alice"])
    forged = scopes["alice"].encode(foreign.message_ref)
    owned_ref = scopes["alice"].encode(owned.message_ref)
    before_messages = set(paths.messages_dir.rglob("*"))
    before_staging = set(paths.staging_dir.rglob("*"))
    with monkeypatch.context() as context:
        context.setattr(
            backends["alice"],
            "_load_message_by_id",
            lambda message_id: pytest.fail("foreign canonical message must not be opened"),
        )
        with pytest.raises(GatewayMailboxError, match="state is missing"):
            alice.reply(message_ref=forged, body_content="Forged reply", attachments=[])
    for operation in ("mark", "archive"):
        with pytest.raises(GatewayMailboxError, match="state is missing"):
            if operation == "mark":
                alice.mark(
                    message_refs=[owned_ref, forged], read=True, answered=None, archived=None
                )
            else:
                alice.archive(message_refs=[owned_ref, forged])
        unchanged = alice.peek(message_ref=owned_ref, box="inbox")
        assert unchanged.unread is True
        assert unchanged.archived is False
    assert set(paths.messages_dir.rglob("*")) == before_messages
    assert set(paths.staging_dir.rglob("*")) == before_staging


@pytest.mark.parametrize("foreign_in_cc", [False, True])
def test_online_mixed_address_and_foreign_scope_batch_never_reaches_provider(
    foreign_in_cc: bool,
) -> None:
    from houmao.mailbox.scope import MailScope
    from houmao.mailbox.services import GatewayMailboxError, ScopedMailboxAdapter

    calls: list[object] = []
    adapter = ScopedMailboxAdapter.from_backend(
        SimpleNamespace(send=lambda **kwargs: calls.append(kwargs)),
        MailScope("owner-a", "online", "account-a"),
    )
    foreign = MailScope("other", "offline", "registration-b").encode("filesystem:message-a")
    recipients = ["bob@example.test"] if foreign_in_cc else ["bob@example.test", foreign]
    copied = [foreign] if foreign_in_cc else []
    with pytest.raises(GatewayMailboxError, match="selected channel"):
        adapter.send(
            to_addresses=recipients,
            cc_addresses=copied,
            subject="Work",
            body_content="Hello",
            attachments=[],
        )
    assert calls == []


@pytest.mark.parametrize(
    "page_args,expected_limit,expected_cursor",
    [([], 50, None), (["--limit", "7", "--cursor", "opaque-page-cursor"], 7, "opaque-page-cursor")],
)
def test_cli_forwards_finite_metadata_page_and_exact_cursor(
    monkeypatch: pytest.MonkeyPatch,
    page_args: list[str],
    expected_limit: int,
    expected_cursor: str | None,
) -> None:
    """Forward finite defaults and opaque page continuations without rewriting them."""
    observed: dict[str, Any] = {}
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
        lambda **kwargs: object(),
    )
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.mail_list",
        lambda target, **kwargs: observed.update(kwargs) or {"messages": []},
    )
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "owner-a",
            "mail",
            "list",
            "--channel",
            "online",
            "--expected-binding-id",
            "binding-round",
            *page_args,
        ],
    )
    assert result.exit_code == 0, result.output
    assert observed["limit"] == expected_limit
    assert observed["cursor"] == expected_cursor
    assert observed["channel"] == "online" and observed["expected_binding_id"] == "binding-round"
    assert "include_body" not in observed


def test_cli_rejects_list_body_flag_with_explicit_content_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse removed body-listing before resolving an agent or performing mail I/O."""
    monkeypatch.setattr(
        "houmao.srv_ctrl.commands.agents.mail.resolve_managed_agent_mail_target",
        lambda **kwargs: pytest.fail("removed option must fail before target resolution"),
    )
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "single",
            "--agent-id",
            "owner-a",
            "mail",
            "list",
            "--channel",
            "online",
            "--include-body",
        ],
    )
    assert result.exit_code == 2
    assert "--include-body was removed" in result.output
    assert "peek/read" in result.output
