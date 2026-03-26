"""Shared managed-agent discovery and direct-control helpers for `houmao-mgr`."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
import uuid

import click

from houmao.agents.mailbox_runtime_models import FilesystemMailboxResolvedConfig
from houmao.agents.realm_controller.backends.headless_base import HeadlessInteractiveSession
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessProcessMetadata,
    load_headless_process_metadata,
    load_headless_turn_events,
    read_headless_turn_return_code,
)
from houmao.agents.realm_controller.backends.tmux_runtime import (
    HEADLESS_AGENT_WINDOW_NAME,
    tmux_session_exists,
)
from houmao.agents.realm_controller.errors import GatewayHttpError, SessionManifestError
from houmao.agents.realm_controller.gateway_client import GatewayClient, GatewayEndpoint
from houmao.agents.realm_controller.gateway_models import (
    GatewayAcceptedRequestV1,
    GatewayMailAttachmentUploadV1,
    GatewayRequestPayloadInterruptV1,
    GatewayRequestPayloadSubmitPromptV1,
    GatewayStatusV1,
)
from houmao.agents.realm_controller.gateway_storage import (
    build_offline_gateway_status,
    gateway_paths_from_manifest_path,
    load_gateway_status,
    resolve_internal_gateway_attach_contract,
)
from houmao.agents.realm_controller.mail_commands import (
    MailPromptRequest,
    ensure_mailbox_command_ready,
    prepare_mail_prompt,
    run_mail_prompt,
)
from houmao.agents.realm_controller.registry_models import LiveAgentRegistryRecordV2
from houmao.agents.realm_controller.registry_storage import (
    global_registry_paths,
    resolve_live_agent_record_by_agent_id,
    resolve_live_agent_records_by_name,
)
from houmao.agents.realm_controller.runtime import RuntimeSessionController, resume_runtime_session
from houmao.agents.realm_controller.manifest import (
    load_session_manifest,
    parse_session_manifest_payload,
)
from houmao.agents.realm_controller.boundary_models import SessionManifestPayloadV4
from houmao.agents.realm_controller.session_authority import resolve_manifest_session_authority
from houmao.cao.rest_client import CaoApiError
from houmao.shared_tui_tracking.ownership import SingleSessionTrackingRuntime
from houmao.server.models import (
    HoumaoErrorDetail,
    HoumaoHeadlessTurnAcceptedResponse,
    HoumaoHeadlessTurnEvent,
    HoumaoHeadlessTurnEventsResponse,
    HoumaoHeadlessTurnRequest,
    HoumaoHeadlessTurnStatusResponse,
    HoumaoManagedAgentActionResponse,
    HoumaoManagedAgentDetailResponse,
    HoumaoManagedAgentGatewayRequestCreate,
    HoumaoManagedAgentGatewaySummaryView,
    HoumaoManagedAgentHeadlessDetailView,
    HoumaoManagedAgentIdentity,
    HoumaoManagedAgentLastTurnView,
    HoumaoManagedAgentListResponse,
    HoumaoManagedAgentMailboxSummaryView,
    HoumaoManagedAgentRequestAcceptedResponse,
    HoumaoManagedAgentStateResponse,
    HoumaoManagedAgentTuiDetailView,
    HoumaoManagedAgentTurnView,
    ManagedAgentAvailability,
    ManagedAgentLastTurnResult,
    ManagedAgentTransportKind,
    ManagedAgentTurnStatus,
    HoumaoTerminalStateResponse,
    HoumaoTrackedSessionIdentity,
)
from houmao.server.pair_client import PairAuthorityClientProtocol

from .common import (
    pair_request,
    require_supported_houmao_pair,
    resolve_managed_agent_selector,
    resolve_managed_agent_identity,
    resolve_server_base_url,
)

_HEADLESS_BACKENDS = frozenset({"claude_headless", "codex_headless", "gemini_headless"})
_SUPPORTED_LOCAL_TUI_PROCESSES: dict[str, tuple[str, ...]] = {
    "claude": ("claude", "claude-code"),
    "codex": ("codex",),
    "gemini": ("gemini",),
}


@dataclass(frozen=True)
class ManagedAgentTarget:
    """Resolved managed-agent control target."""

    mode: str
    agent_ref: str
    identity: HoumaoManagedAgentIdentity
    client: PairAuthorityClientProtocol | None = None
    controller: RuntimeSessionController | None = None
    record: LiveAgentRegistryRecordV2 | None = None


@dataclass(frozen=True)
class _LocalHeadlessTurnSnapshot:
    """One local headless-turn snapshot derived from runtime artifacts."""

    turn_id: str
    turn_index: int
    status: str
    started_at_utc: str
    completed_at_utc: str | None
    completion_source: str | None
    stdout_path: Path | None
    stderr_path: Path | None
    status_path: Path | None
    returncode: int | None
    history_summary: str | None
    error: str | None


def list_managed_agents(*, port: int | None) -> HoumaoManagedAgentListResponse:
    """List managed agents from the registry first, with optional server enrichment."""

    if port is not None:
        client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
        return pair_request(client.list_managed_agents)

    merged: dict[str, HoumaoManagedAgentIdentity] = {}
    for identity in _list_registry_identities():
        merged[_identity_merge_key(identity)] = identity

    pair_client: PairAuthorityClientProtocol | None = _optional_pair_client(
        base_url=resolve_server_base_url()
    )
    if pair_client is not None:
        for identity in pair_request(pair_client.list_managed_agents).agents:
            merged[_identity_merge_key(identity)] = identity

    identities = sorted(merged.values(), key=lambda item: (item.transport, item.tracked_agent_id))
    return HoumaoManagedAgentListResponse(agents=identities)


def resolve_managed_agent_target(
    *,
    agent_id: str | None,
    agent_name: str | None,
    port: int | None,
) -> ManagedAgentTarget:
    """Resolve one managed-agent target through registry-first discovery."""

    normalized_agent_id, normalized_agent_name = resolve_managed_agent_selector(
        agent_id=agent_id,
        agent_name=agent_name,
    )
    normalized_ref = normalized_agent_id or normalized_agent_name
    assert normalized_ref is not None
    if port is not None:
        client = require_supported_houmao_pair(base_url=resolve_server_base_url(port=port))
        identity = resolve_managed_agent_identity(client, agent_ref=normalized_ref)
        return ManagedAgentTarget(
            mode="server",
            agent_ref=normalized_ref,
            identity=identity,
            client=client,
        )

    record = _resolve_local_managed_agent_record(
        agent_id=normalized_agent_id,
        agent_name=normalized_agent_name,
    )
    if record is not None:
        if record.identity.backend == "houmao_server_rest":
            client = require_supported_houmao_pair(base_url=_api_base_url_from_record(record))
            identity = _resolve_server_identity_from_record(client=client, record=record)
            return ManagedAgentTarget(
                mode="server",
                agent_ref=normalized_ref,
                identity=identity,
                client=client,
                record=record,
            )
        controller = _resume_controller_from_record(record)
        identity = _identity_from_controller(controller)
        return ManagedAgentTarget(
            mode="local",
            agent_ref=normalized_ref,
            identity=identity,
            controller=controller,
            record=record,
        )

    client = require_supported_houmao_pair(base_url=resolve_server_base_url())
    identity = resolve_managed_agent_identity(client, agent_ref=normalized_ref)
    return ManagedAgentTarget(
        mode="server",
        agent_ref=normalized_ref,
        identity=identity,
        client=client,
    )


def _resolve_local_managed_agent_record(
    *,
    agent_id: str | None,
    agent_name: str | None,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve one local registry-backed managed-agent record."""

    if agent_id is not None:
        return resolve_live_agent_record_by_agent_id(agent_id)

    assert agent_name is not None
    name_matches = resolve_live_agent_records_by_name(agent_name)
    if len(name_matches) > 1:
        raise click.ClickException(
            _format_ambiguous_local_registry_matches(
                selector_name="--agent-name",
                selector_value=agent_name,
                resolution_kind="friendly name",
                matches=name_matches,
            )
        )
    if len(name_matches) == 1:
        return name_matches[0]
    return None


def resolve_live_agent_record(agent_identity: str) -> LiveAgentRegistryRecordV2 | None:
    """Backward-compatible local record resolution without explicit ambiguity errors."""

    record = resolve_live_agent_record_by_agent_id(agent_identity)
    if record is not None:
        return record
    name_matches = resolve_live_agent_records_by_name(agent_identity)
    if len(name_matches) == 1:
        return name_matches[0]
    return None


def _format_ambiguous_local_registry_matches(
    *,
    selector_name: str,
    selector_value: str,
    resolution_kind: str,
    matches: Sequence[LiveAgentRegistryRecordV2],
) -> str:
    """Format one explicit local-registry ambiguity error."""

    candidate_lines = "\n".join(
        (
            f"- agent_id={record.agent_id} "
            f"agent_name={record.agent_name} "
            f"tmux_session_name={record.terminal.session_name}"
        )
        for record in matches
    )
    return (
        f"Local managed-agent resolution is ambiguous for {selector_name} `{selector_value}` "
        f"({resolution_kind}).\nCandidates:\n{candidate_lines}\n"
        "Retry with `--agent-id <id>`."
    )


def managed_agent_identity_payload(target: ManagedAgentTarget) -> HoumaoManagedAgentIdentity:
    """Return the resolved managed-agent identity payload."""

    if target.mode == "server":
        assert target.client is not None
        return resolve_managed_agent_identity(target.client, agent_ref=target.agent_ref)
    return target.identity


def managed_agent_state_payload(target: ManagedAgentTarget) -> HoumaoManagedAgentStateResponse:
    """Return a managed-agent state payload for one resolved target."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_state, target.agent_ref)
    assert target.controller is not None
    if target.identity.transport == "tui":
        tracked_state = _refresh_local_tui_state(controller=target.controller)
        return _local_tui_state_response_from_state(
            controller=target.controller,
            tracked_state=tracked_state,
        )
    return _local_headless_state_response(
        controller=target.controller,
        identity=target.identity,
    )


def managed_agent_detail_payload(target: ManagedAgentTarget) -> HoumaoManagedAgentDetailResponse:
    """Return a managed-agent detail payload for one resolved target."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_state_detail, target.agent_ref)
    assert target.controller is not None
    if target.identity.transport == "tui":
        tracked_state = _refresh_local_tui_state(controller=target.controller)
        summary_state = _local_tui_state_response_from_state(
            controller=target.controller,
            tracked_state=tracked_state,
        )
        tui_detail = _local_tui_detail_response_from_state(tracked_state=tracked_state)
        return HoumaoManagedAgentDetailResponse(
            tracked_agent_id=summary_state.tracked_agent_id,
            identity=summary_state.identity,
            summary_state=summary_state,
            detail=tui_detail,
        )
    summary_state = _local_headless_state_response(
        controller=target.controller,
        identity=target.identity,
    )
    latest_turn = _latest_local_headless_turn(controller=target.controller)
    detail = _local_headless_detail_response(
        controller=target.controller,
        summary_state=summary_state,
        latest_turn=latest_turn,
    )
    return HoumaoManagedAgentDetailResponse(
        tracked_agent_id=summary_state.tracked_agent_id,
        identity=summary_state.identity,
        summary_state=summary_state,
        detail=detail,
    )


def prompt_managed_agent(
    target: ManagedAgentTarget,
    *,
    prompt: str,
) -> object:
    """Submit the default prompt path for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentSubmitPromptRequest

        return pair_request(
            target.client.submit_managed_agent_request,
            target.agent_ref,
            HoumaoManagedAgentSubmitPromptRequest(prompt=prompt),
        )

    assert target.controller is not None
    target.controller.send_prompt(prompt)
    return HoumaoManagedAgentRequestAcceptedResponse(
        success=True,
        tracked_agent_id=target.identity.tracked_agent_id,
        request_id=_new_request_id(prefix="prompt"),
        request_kind="submit_prompt",
        disposition="accepted",
        detail="Prompt submitted through the local runtime controller.",
    )


def interrupt_managed_agent(target: ManagedAgentTarget) -> object:
    """Interrupt one managed agent through the resolved control path."""

    if target.mode == "server":
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentInterruptRequest

        return pair_request(
            target.client.submit_managed_agent_request,
            target.agent_ref,
            HoumaoManagedAgentInterruptRequest(),
        )

    assert target.controller is not None
    result = target.controller.interrupt()
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=target.identity.tracked_agent_id,
        detail=result.detail,
    )


def stop_managed_agent(target: ManagedAgentTarget) -> HoumaoManagedAgentActionResponse:
    """Stop one managed agent through the resolved control path."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.stop_managed_agent, target.agent_ref)

    assert target.controller is not None
    result = target.controller.stop(force_cleanup=True)
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=target.identity.tracked_agent_id,
        detail=result.detail,
    )


def relaunch_managed_agent(target: ManagedAgentTarget) -> HoumaoManagedAgentActionResponse:
    """Relaunch one tmux-backed managed agent through the resolved runtime authority."""

    if target.mode == "server":
        if target.record is None:
            raise click.ClickException(
                "Managed-agent relaunch requires local manifest authority on the owning host. "
                "This target is only resolvable through pair HTTP metadata."
            )
        controller = _resume_controller_from_record(target.record)
        tracked_agent_id = target.identity.tracked_agent_id
    else:
        assert target.controller is not None
        controller = target.controller
        tracked_agent_id = target.identity.tracked_agent_id

    result = controller.relaunch()
    return HoumaoManagedAgentActionResponse(
        success=result.status == "ok",
        tracked_agent_id=tracked_agent_id,
        detail=result.detail,
    )


def gateway_status(target: ManagedAgentTarget) -> GatewayStatusV1:
    """Return gateway status for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_gateway_status, target.agent_ref)

    assert target.controller is not None
    return _gateway_status_for_controller(target.controller)


def attach_gateway(target: ManagedAgentTarget, *, foreground: bool = False) -> GatewayStatusV1:
    """Attach or reuse a live gateway for one managed agent."""

    target = _local_gateway_target_for_passive_pair(target, operation="attach")
    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.attach_managed_agent_gateway, target.agent_ref)

    assert target.controller is not None
    result = target.controller.attach_gateway(
        execution_mode_override="tmux_auxiliary_window" if foreground else None
    )
    if result.status != "ok":
        raise click.ClickException(result.detail)
    return _gateway_status_for_controller(target.controller)


def detach_gateway(target: ManagedAgentTarget) -> GatewayStatusV1:
    """Detach one live gateway for the resolved managed agent."""

    target = _local_gateway_target_for_passive_pair(target, operation="detach")
    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.detach_managed_agent_gateway, target.agent_ref)

    assert target.controller is not None
    result = target.controller.detach_gateway()
    if result.status != "ok":
        raise click.ClickException(result.detail)
    return _gateway_status_for_controller(target.controller)


def gateway_prompt(target: ManagedAgentTarget, *, prompt: str) -> GatewayAcceptedRequestV1:
    """Submit a gateway prompt for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.submit_managed_agent_gateway_request,
            target.agent_ref,
            HoumaoManagedAgentGatewayRequestCreate(
                kind="submit_prompt",
                payload=GatewayRequestPayloadSubmitPromptV1(prompt=prompt),
            ),
        )

    assert target.controller is not None
    return target.controller.send_prompt_via_gateway(prompt)


def gateway_interrupt(target: ManagedAgentTarget) -> GatewayAcceptedRequestV1:
    """Submit a gateway interrupt for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.submit_managed_agent_gateway_request,
            target.agent_ref,
            HoumaoManagedAgentGatewayRequestCreate(
                kind="interrupt",
                payload=GatewayRequestPayloadInterruptV1(),
            ),
        )

    assert target.controller is not None
    return target.controller.interrupt_via_gateway()


def mailbox_status(target: ManagedAgentTarget) -> dict[str, object]:
    """Return late filesystem-mailbox posture for one local managed agent."""

    controller = _require_local_filesystem_mailbox_target(target, operation="status")
    mailbox = controller.launch_plan.mailbox
    if mailbox is not None and not isinstance(mailbox, FilesystemMailboxResolvedConfig):
        raise click.ClickException(
            "`houmao-mgr agents mailbox ...` only supports filesystem mailbox bindings in v1."
        )

    activation_state = controller.mailbox_activation_state()
    payload: dict[str, object] = {
        "schema_version": 1,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "backend": controller.launch_plan.backend,
        "joined_session": bool(
            controller.agent_launch_authority is not None
            and controller.agent_launch_authority.session_origin == "joined_tmux"
        ),
        "posture_kind": (
            controller.agent_launch_authority.posture_kind
            if controller.agent_launch_authority is not None
            else None
        ),
        "registered": mailbox is not None,
        "activation_state": activation_state,
        "runtime_mailbox_enabled": mailbox is not None and activation_state == "active",
        "relaunch_required": activation_state == "pending_relaunch",
    }
    if mailbox is not None:
        payload.update(
            {
                "transport": mailbox.transport,
                "principal_id": mailbox.principal_id,
                "address": mailbox.address,
                "mailbox_root": str(mailbox.filesystem_root),
                "bindings_version": mailbox.bindings_version,
            }
        )
    return payload


def register_mailbox_binding(
    target: ManagedAgentTarget,
    *,
    mailbox_root: Path | None,
    principal_id: str | None,
    address: str | None,
    mode: str,
) -> dict[str, object]:
    """Register one late filesystem mailbox binding for a local managed agent."""

    controller = _require_local_filesystem_mailbox_target(target, operation="register")
    result = controller.register_filesystem_mailbox(
        mailbox_root=mailbox_root,
        principal_id=principal_id,
        address=address,
        mode=cast(Any, mode),
    )
    mailbox = result.mailbox
    assert mailbox is not None
    return {
        "schema_version": 1,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "transport": mailbox.transport,
        "principal_id": mailbox.principal_id,
        "address": mailbox.address,
        "mailbox_root": str(mailbox.filesystem_root),
        "bindings_version": mailbox.bindings_version,
        "activation_state": result.activation_state,
        "relaunch_required": result.activation_state == "pending_relaunch",
        "shared_registration": result.shared_lifecycle_result,
    }


def unregister_mailbox_binding(
    target: ManagedAgentTarget,
    *,
    mode: str,
) -> dict[str, object]:
    """Unregister one late filesystem mailbox binding for a local managed agent."""

    controller = _require_local_filesystem_mailbox_target(target, operation="unregister")
    previous_mailbox = controller.launch_plan.mailbox
    if previous_mailbox is None:
        raise click.ClickException("Target session is not mailbox-enabled.")
    if not isinstance(previous_mailbox, FilesystemMailboxResolvedConfig):
        raise click.ClickException(
            "`houmao-mgr agents mailbox ...` only supports filesystem mailbox bindings in v1."
        )

    result = controller.unregister_filesystem_mailbox(mode=cast(Any, mode))
    return {
        "schema_version": 1,
        "tracked_agent_id": target.identity.tracked_agent_id,
        "agent_name": controller.agent_identity,
        "agent_id": controller.agent_id,
        "transport": previous_mailbox.transport,
        "principal_id": previous_mailbox.principal_id,
        "address": previous_mailbox.address,
        "mailbox_root": str(previous_mailbox.filesystem_root),
        "activation_state": result.activation_state,
        "relaunch_required": result.activation_state == "pending_relaunch",
        "shared_unregistration": result.shared_lifecycle_result,
    }


def mail_status(target: ManagedAgentTarget) -> object:
    """Return mailbox status for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_managed_agent_mail_status, target.agent_ref)

    assert target.controller is not None
    activation_state = target.controller.mailbox_activation_state()
    mailbox_summary = _local_mailbox_summary(target.controller)
    if mailbox_summary is None:
        raise click.ClickException("Target session is not mailbox-enabled.")
    if activation_state == "pending_relaunch":
        raise click.ClickException(
            "Target session has a persisted mailbox binding, but runtime-owned mail commands "
            "remain pending relaunch."
        )
    if activation_state == "unsupported_joined_session":
        raise click.ClickException(
            "Target session cannot activate late mailbox support because joined-session relaunch "
            "authority is unavailable."
        )
    return {
        "schema_version": 1,
        "transport": mailbox_summary.transport,
        "principal_id": mailbox_summary.principal_id,
        "address": mailbox_summary.address,
        "bindings_version": getattr(
            target.controller.launch_plan.mailbox, "bindings_version", "v1"
        ),
    }


def mail_check(
    target: ManagedAgentTarget,
    *,
    unread_only: bool,
    limit: int | None,
    since: str | None,
) -> object:
    """Check mailbox contents for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailCheckRequest

        return pair_request(
            target.client.check_managed_agent_mail,
            target.agent_ref,
            HoumaoManagedAgentMailCheckRequest(
                unread_only=unread_only,
                limit=limit,
                since=since,
            ),
        )

    assert target.controller is not None
    return _run_local_mail_prompt(
        controller=target.controller,
        operation="check",
        args={
            "unread_only": unread_only,
            "limit": limit,
            "since": since,
        },
    )


def mail_send(
    target: ManagedAgentTarget,
    *,
    to_recipients: list[str],
    cc_recipients: list[str],
    subject: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
) -> object:
    """Send a mailbox message for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailSendRequest

        return pair_request(
            target.client.send_managed_agent_mail,
            target.agent_ref,
            HoumaoManagedAgentMailSendRequest(
                to=to_recipients,
                cc=cc_recipients,
                subject=subject,
                body_content=body_content,
                attachments=list(attachments),
            ),
        )

    assert target.controller is not None
    return _run_local_mail_prompt(
        controller=target.controller,
        operation="send",
        args={
            "to": to_recipients,
            "cc": cc_recipients,
            "subject": subject,
            "body_content": body_content,
            "attachments": [attachment.model_dump(mode="json") for attachment in attachments],
        },
    )


def mail_reply(
    target: ManagedAgentTarget,
    *,
    message_ref: str,
    body_content: str,
    attachments: Sequence[GatewayMailAttachmentUploadV1],
) -> object:
    """Reply to a mailbox message for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        from houmao.server.models import HoumaoManagedAgentMailReplyRequest

        return pair_request(
            target.client.reply_managed_agent_mail,
            target.agent_ref,
            HoumaoManagedAgentMailReplyRequest(
                message_ref=message_ref,
                body_content=body_content,
                attachments=list(attachments),
            ),
        )

    assert target.controller is not None
    return _run_local_mail_prompt(
        controller=target.controller,
        operation="reply",
        args={
            "message_ref": message_ref,
            "body_content": body_content,
            "attachments": [attachment.model_dump(mode="json") for attachment in attachments],
        },
    )


def submit_headless_turn(
    target: ManagedAgentTarget,
    *,
    prompt: str,
) -> HoumaoHeadlessTurnAcceptedResponse:
    """Submit one headless turn for a managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.submit_headless_turn,
            target.agent_ref,
            HoumaoHeadlessTurnRequest(prompt=prompt),
        )

    assert target.controller is not None
    turn_index = _next_turn_index(target.controller)
    turn_id = f"turn-{turn_index:04d}"
    target.controller.send_prompt(prompt)
    snapshot = _turn_snapshot_from_id(controller=target.controller, turn_id=turn_id)
    return HoumaoHeadlessTurnAcceptedResponse(
        success=True,
        tracked_agent_id=target.identity.tracked_agent_id,
        turn_id=turn_id,
        turn_index=snapshot.turn_index,
        status=_managed_agent_turn_status(snapshot.status),
        detail="Headless turn completed through the local runtime controller.",
    )


def headless_turn_status(
    target: ManagedAgentTarget,
    *,
    turn_id: str,
) -> HoumaoHeadlessTurnStatusResponse:
    """Return headless turn status for one managed agent."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_headless_turn_status, target.agent_ref, turn_id)

    assert target.controller is not None
    snapshot = _turn_snapshot_from_id(controller=target.controller, turn_id=turn_id)
    return HoumaoHeadlessTurnStatusResponse(
        tracked_agent_id=target.identity.tracked_agent_id,
        turn_id=snapshot.turn_id,
        turn_index=snapshot.turn_index,
        status=_managed_agent_turn_status(snapshot.status),
        started_at_utc=snapshot.started_at_utc,
        completed_at_utc=snapshot.completed_at_utc,
        returncode=snapshot.returncode,
        completion_source=snapshot.completion_source,
        stdout_path=str(snapshot.stdout_path) if snapshot.stdout_path is not None else None,
        stderr_path=str(snapshot.stderr_path) if snapshot.stderr_path is not None else None,
        status_path=str(snapshot.status_path) if snapshot.status_path is not None else None,
        history_summary=snapshot.history_summary,
        error=snapshot.error,
    )


def headless_turn_events(
    target: ManagedAgentTarget,
    *,
    turn_id: str,
) -> HoumaoHeadlessTurnEventsResponse:
    """Return structured events for one headless turn."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(target.client.get_headless_turn_events, target.agent_ref, turn_id)

    assert target.controller is not None
    snapshot = _turn_snapshot_from_id(controller=target.controller, turn_id=turn_id)
    events = _load_turn_events(snapshot)
    return HoumaoHeadlessTurnEventsResponse(
        tracked_agent_id=target.identity.tracked_agent_id,
        turn_id=turn_id,
        entries=events,
    )


def headless_turn_artifact_text(
    target: ManagedAgentTarget,
    *,
    turn_id: str,
    artifact_name: str,
) -> str:
    """Return one raw headless artifact text payload."""

    if target.mode == "server":
        assert target.client is not None
        return pair_request(
            target.client.get_headless_turn_artifact_text,
            target.agent_ref,
            turn_id,
            artifact_name=artifact_name,
        )

    assert target.controller is not None
    snapshot = _turn_snapshot_from_id(controller=target.controller, turn_id=turn_id)
    if artifact_name == "stdout":
        artifact_path = snapshot.stdout_path
    elif artifact_name == "stderr":
        artifact_path = snapshot.stderr_path
    else:
        raise click.ClickException(f"Unknown headless artifact `{artifact_name}`.")
    if artifact_path is None or not artifact_path.exists():
        return ""
    return artifact_path.read_text(encoding="utf-8")


def _list_registry_identities() -> list[HoumaoManagedAgentIdentity]:
    """Return current fresh registry identities."""

    return [_identity_from_record(record) for record in _list_registry_records()]


def _list_registry_records() -> list[LiveAgentRegistryRecordV2]:
    """Return current fresh shared-registry records."""

    paths = global_registry_paths()
    if not paths.live_agents_dir.exists():
        return []
    records: list[LiveAgentRegistryRecordV2] = []
    for candidate in sorted(paths.live_agents_dir.iterdir()):
        if not candidate.is_dir():
            continue
        record = resolve_live_agent_record_by_agent_id(candidate.name)
        if record is not None:
            records.append(record)
    return records


def _identity_merge_key(identity: HoumaoManagedAgentIdentity) -> str:
    """Return one stable merge key for mixed registry/server identity aggregation."""

    for value in (
        identity.agent_id,
        identity.manifest_path,
        identity.session_name,
        identity.tracked_agent_id,
    ):
        if value is not None and value.strip():
            return value
    return identity.tracked_agent_id


def _identity_from_record(record: LiveAgentRegistryRecordV2) -> HoumaoManagedAgentIdentity:
    """Project one registry record into the shared identity payload."""

    transport: ManagedAgentTransportKind = (
        "headless" if record.identity.backend in _HEADLESS_BACKENDS else "tui"
    )
    tracked_agent_id = record.agent_id or record.agent_name or record.terminal.session_name
    tmux_window_name = _managed_tmux_window_name_from_manifest_path(
        manifest_path=Path(record.runtime.manifest_path),
        default=(
            HEADLESS_AGENT_WINDOW_NAME
            if transport == "headless" or record.identity.backend == "local_interactive"
            else None
        ),
    )
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=tracked_agent_id,
        transport=transport,
        tool=record.identity.tool,
        session_name=record.terminal.session_name if transport == "tui" else None,
        terminal_id=None,
        runtime_session_id=tracked_agent_id,
        tmux_session_name=record.terminal.session_name,
        tmux_window_name=tmux_window_name,
        manifest_path=record.runtime.manifest_path,
        session_root=record.runtime.session_root,
        agent_name=record.agent_name,
        agent_id=record.agent_id,
    )


def _resume_controller_from_record(record: LiveAgentRegistryRecordV2) -> RuntimeSessionController:
    """Resume one local runtime controller from a registry record."""

    agent_def_dir_raw = record.runtime.agent_def_dir
    if agent_def_dir_raw is None:
        raise click.ClickException(
            f"Managed agent `{record.agent_name}` is missing registry agent_def_dir metadata."
        )
    agent_def_dir = Path(agent_def_dir_raw).expanduser().resolve()
    manifest_path = Path(record.runtime.manifest_path).expanduser().resolve()
    return resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=manifest_path,
    )


def _identity_from_controller(controller: RuntimeSessionController) -> HoumaoManagedAgentIdentity:
    """Project one resumed controller into the shared identity model."""

    tracked_agent_id = (
        controller.agent_id or controller.agent_identity or controller.manifest_path.parent.name
    )
    transport: ManagedAgentTransportKind = (
        "headless" if controller.launch_plan.backend in _HEADLESS_BACKENDS else "tui"
    )
    tmux_window_name = _managed_tmux_window_name_from_manifest_path(
        manifest_path=controller.manifest_path,
        default=(
            HEADLESS_AGENT_WINDOW_NAME
            if transport == "headless" or controller.launch_plan.backend == "local_interactive"
            else None
        ),
    )
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=tracked_agent_id,
        transport=transport,
        tool=controller.launch_plan.tool,
        session_name=controller.tmux_session_name if transport == "tui" else None,
        terminal_id=None,
        runtime_session_id=controller.manifest_path.parent.name,
        tmux_session_name=controller.tmux_session_name,
        tmux_window_name=tmux_window_name,
        manifest_path=str(controller.manifest_path),
        session_root=str(controller.manifest_path.parent),
        agent_name=controller.agent_identity,
        agent_id=controller.agent_id,
    )


def _optional_pair_client(*, base_url: str) -> PairAuthorityClientProtocol | None:
    """Return one reachable pair client or `None` when unavailable."""

    try:
        return require_supported_houmao_pair(base_url=base_url)
    except click.ClickException:
        return None


def _resolve_server_identity_from_record(
    *,
    client: PairAuthorityClientProtocol,
    record: LiveAgentRegistryRecordV2,
) -> HoumaoManagedAgentIdentity:
    """Resolve the server-side identity described by one registry record."""

    candidates = (
        record.agent_id,
        record.agent_name,
        record.terminal.session_name,
    )
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            return resolve_managed_agent_identity(client, agent_ref=candidate)
        except click.ClickException:
            continue
        except CaoApiError:
            continue
    raise click.ClickException(
        f"Managed agent `{record.agent_name}` is registered in the shared registry but "
        "could not be resolved from the owning houmao-server."
    )


def _local_gateway_target_for_passive_pair(
    target: ManagedAgentTarget,
    *,
    operation: str,
) -> ManagedAgentTarget:
    """Convert passive-server gateway attach and detach onto the local authority path."""

    if target.mode != "server":
        return target
    assert target.client is not None
    if target.client.pair_authority_kind != "houmao-passive-server":
        return target
    record = _resolve_local_gateway_record_for_passive_pair(target)
    if record is None or record.identity.backend == "houmao_server_rest":
        raise click.ClickException(
            f"Passive-server gateway {operation} requires local authority on the owning host; "
            "remote pair HTTP control is unsupported."
        )
    controller = _resume_controller_from_record(record)
    return ManagedAgentTarget(
        mode="local",
        agent_ref=target.agent_ref,
        identity=_identity_from_controller(controller),
        controller=controller,
        record=record,
    )


def _resolve_local_gateway_record_for_passive_pair(
    target: ManagedAgentTarget,
) -> LiveAgentRegistryRecordV2 | None:
    """Resolve one local registry record for passive-server gateway attach and detach."""

    if target.identity.agent_id is not None:
        return resolve_live_agent_record_by_agent_id(target.identity.agent_id)
    return _resolve_local_managed_agent_record(
        agent_id=None,
        agent_name=target.identity.agent_name or target.agent_ref,
    )


def _api_base_url_from_record(record: LiveAgentRegistryRecordV2) -> str:
    """Extract one `houmao-server` base URL from a registry-backed manifest."""

    handle = load_session_manifest(Path(record.runtime.manifest_path))
    payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    authority = resolve_manifest_session_authority(
        manifest_path=handle.path,
        payload=payload,
    )
    api_base_url = authority.attach.api_base_url
    if api_base_url is None or not api_base_url.strip():
        raise click.ClickException(
            f"Managed agent `{record.agent_name}` is missing a usable houmao-server api_base_url."
        )
    return api_base_url.strip()


def _gateway_status_for_controller(controller: RuntimeSessionController) -> GatewayStatusV1:
    """Return gateway status for one local runtime controller."""

    paths = gateway_paths_from_manifest_path(controller.manifest_path)
    if paths is None:
        raise click.ClickException(
            "Managed agent does not publish manifest-backed gateway capability."
        )
    if paths.state_path.is_file():
        try:
            return load_gateway_status(paths.state_path)
        except SessionManifestError as exc:
            raise click.ClickException(str(exc)) from exc
    try:
        attach_contract = resolve_internal_gateway_attach_contract(paths)
    except SessionManifestError as exc:
        raise click.ClickException(str(exc)) from exc
    return build_offline_gateway_status(
        attach_contract=attach_contract,
        managed_agent_instance_epoch=0,
    )


def _live_gateway_client_for_controller(
    controller: RuntimeSessionController,
) -> GatewayClient | None:
    """Return a live gateway client when the controller has one attached."""

    status = _gateway_status_for_controller(controller)
    if (
        status.gateway_health != "healthy"
        or status.gateway_host is None
        or status.gateway_port is None
    ):
        return None
    client = GatewayClient(
        endpoint=GatewayEndpoint(host=status.gateway_host, port=status.gateway_port)
    )
    try:
        client.health()
    except GatewayHttpError:
        return None
    return client


def _local_gateway_summary(
    controller: RuntimeSessionController,
) -> HoumaoManagedAgentGatewaySummaryView | None:
    """Return one optional gateway summary for local direct control."""

    try:
        status = _gateway_status_for_controller(controller)
    except click.ClickException:
        return None
    return HoumaoManagedAgentGatewaySummaryView(
        gateway_health=status.gateway_health,
        managed_agent_connectivity=status.managed_agent_connectivity,
        managed_agent_recovery=status.managed_agent_recovery,
        request_admission=status.request_admission,
        active_execution=status.active_execution,
        queue_depth=status.queue_depth,
        gateway_host=status.gateway_host,
        gateway_port=status.gateway_port,
    )


def _local_mailbox_summary(
    controller: RuntimeSessionController,
) -> HoumaoManagedAgentMailboxSummaryView | None:
    """Return one optional mailbox summary for the local controller."""

    mailbox = controller.launch_plan.mailbox
    if mailbox is None:
        return None
    return HoumaoManagedAgentMailboxSummaryView(
        transport=mailbox.transport,
        principal_id=mailbox.principal_id,
        address=mailbox.address,
    )


def _local_tui_runtime_for_controller(
    controller: RuntimeSessionController,
) -> SingleSessionTrackingRuntime:
    """Return one ephemeral single-session tracker for a local TUI controller."""

    return SingleSessionTrackingRuntime(
        identity=_tracked_tui_identity_for_controller(controller),
        supported_tui_processes=_SUPPORTED_LOCAL_TUI_PROCESSES,
    )


def _tracked_tui_identity_for_controller(
    controller: RuntimeSessionController,
) -> HoumaoTrackedSessionIdentity:
    """Build one tracked-session identity for local TUI discovery."""

    tracked_agent_id = (
        controller.agent_id or controller.agent_identity or controller.manifest_path.parent.name
    )
    tmux_session_name = (
        controller.tmux_session_name
        or controller.agent_identity
        or controller.manifest_path.parent.name
    )
    return HoumaoTrackedSessionIdentity(
        tracked_session_id=tracked_agent_id,
        session_name=tmux_session_name,
        tool=controller.launch_plan.tool,
        tmux_session_name=tmux_session_name,
        tmux_window_name=_managed_tmux_window_name_from_manifest_path(
            manifest_path=controller.manifest_path,
            default=HEADLESS_AGENT_WINDOW_NAME,
        ),
        agent_name=controller.agent_identity,
        agent_id=controller.agent_id,
        manifest_path=str(controller.manifest_path),
        session_root=str(controller.manifest_path.parent),
    )


def _managed_tmux_window_name_from_manifest_path(
    *,
    manifest_path: Path,
    default: str | None,
) -> str | None:
    """Return the best persisted tmux window name for one managed session."""

    try:
        handle = load_session_manifest(manifest_path)
        payload = parse_session_manifest_payload(handle.payload, source=str(handle.path))
    except SessionManifestError:
        return default

    if isinstance(payload, SessionManifestPayloadV4):
        if payload.tmux is not None and payload.tmux.primary_window_name is not None:
            return payload.tmux.primary_window_name
        if payload.interactive is not None and payload.interactive.tmux_window_name is not None:
            return payload.interactive.tmux_window_name
    backend_window_name = payload.backend_state.get("tmux_window_name")
    if isinstance(backend_window_name, str) and backend_window_name.strip():
        return backend_window_name.strip()
    return default


def _refresh_local_tui_state(
    *,
    controller: RuntimeSessionController,
) -> HoumaoTerminalStateResponse:
    """Poll one local interactive session once and return the tracked state."""

    return _local_tui_runtime_for_controller(controller).refresh_once()


def _local_tui_state_response_from_state(
    *,
    controller: RuntimeSessionController,
    tracked_state: HoumaoTerminalStateResponse,
) -> HoumaoManagedAgentStateResponse:
    """Project one local TUI tracked-state sample into managed-agent summary state."""

    diagnostics = _tracked_errors(tracked_state=tracked_state)
    turn_phase = tracked_state.turn.phase
    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=tracked_state.tracked_session.tracked_session_id,
        identity=_managed_identity_from_local_tui_state(
            controller=controller,
            tracked_state=tracked_state,
        ),
        availability=_availability_from_local_tui_state(tracked_state),
        turn=HoumaoManagedAgentTurnView(
            phase=turn_phase,
            active_turn_id=(
                f"tui-anchor:{tracked_state.tracked_session.tracked_session_id}"
                if turn_phase == "active"
                else None
            ),
        ),
        last_turn=HoumaoManagedAgentLastTurnView(
            result=tracked_state.last_turn.result,
            turn_id=None,
            turn_index=None,
            updated_at_utc=tracked_state.last_turn.updated_at_utc,
        ),
        diagnostics=diagnostics,
        mailbox=_local_mailbox_summary(controller),
        gateway=_local_gateway_summary(controller),
    )


def _local_tui_detail_response_from_state(
    *,
    tracked_state: HoumaoTerminalStateResponse,
) -> HoumaoManagedAgentTuiDetailView:
    """Project one local TUI tracked-state sample into managed-agent detail."""

    terminal_id = tracked_state.terminal_id
    return HoumaoManagedAgentTuiDetailView(
        terminal_id=terminal_id,
        canonical_terminal_state_route=f"/houmao/terminals/{terminal_id}/state",
        canonical_terminal_history_route=f"/houmao/terminals/{terminal_id}/history",
        diagnostics=tracked_state.diagnostics,
        probe_snapshot=tracked_state.probe_snapshot,
        parsed_surface=tracked_state.parsed_surface,
        surface=tracked_state.surface,
        stability=tracked_state.stability,
    )


def _managed_identity_from_local_tui_state(
    *,
    controller: RuntimeSessionController,
    tracked_state: HoumaoTerminalStateResponse,
) -> HoumaoManagedAgentIdentity:
    """Project one local tracked TUI identity into the shared managed-agent model."""

    tracked = tracked_state.tracked_session
    return HoumaoManagedAgentIdentity(
        tracked_agent_id=tracked.tracked_session_id,
        transport="tui",
        tool=tracked.tool,
        session_name=tracked.session_name,
        terminal_id=tracked_state.terminal_id,
        runtime_session_id=controller.manifest_path.parent.name,
        tmux_session_name=tracked.tmux_session_name,
        tmux_window_name=tracked.tmux_window_name,
        manifest_path=tracked.manifest_path or str(controller.manifest_path),
        session_root=tracked.session_root or str(controller.manifest_path.parent),
        agent_name=tracked.agent_name or controller.agent_identity,
        agent_id=tracked.agent_id or controller.agent_id,
    )


def _availability_from_local_tui_state(
    tracked_state: HoumaoTerminalStateResponse,
) -> ManagedAgentAvailability:
    """Map one TUI tracked-state sample into the coarse managed-agent availability."""

    if tracked_state.diagnostics.availability == "error":
        return "error"
    if tracked_state.diagnostics.availability in {"unavailable", "tui_down"}:
        return "unavailable"
    return "available"


def _tracked_errors(*, tracked_state: HoumaoTerminalStateResponse) -> list[HoumaoErrorDetail]:
    """Return surfaced probe / parse errors from one tracked TUI sample."""

    diagnostics: list[HoumaoErrorDetail] = []
    if tracked_state.diagnostics.probe_error is not None:
        diagnostics.append(tracked_state.diagnostics.probe_error)
    if tracked_state.diagnostics.parse_error is not None:
        diagnostics.append(tracked_state.diagnostics.parse_error)
    return diagnostics


def _local_headless_state_response(
    *,
    controller: RuntimeSessionController,
    identity: HoumaoManagedAgentIdentity,
) -> HoumaoManagedAgentStateResponse:
    """Build one local managed-agent state response for a headless controller."""

    latest_turn = _latest_local_headless_turn(controller=controller)
    gateway_summary = _local_gateway_summary(controller)
    mailbox_summary = _local_mailbox_summary(controller)
    if latest_turn is None:
        turn_view = HoumaoManagedAgentTurnView(phase="ready", active_turn_id=None)
        last_turn = HoumaoManagedAgentLastTurnView(result="none", turn_id=None, turn_index=None)
    else:
        turn_view = HoumaoManagedAgentTurnView(
            phase="active" if latest_turn.status == "active" else "ready",
            active_turn_id=latest_turn.turn_id if latest_turn.status == "active" else None,
        )
        last_turn = HoumaoManagedAgentLastTurnView(
            result=_last_turn_result_from_snapshot(latest_turn),
            turn_id=latest_turn.turn_id,
            turn_index=latest_turn.turn_index,
            updated_at_utc=latest_turn.completed_at_utc or latest_turn.started_at_utc,
        )

    return HoumaoManagedAgentStateResponse(
        tracked_agent_id=identity.tracked_agent_id,
        identity=identity,
        availability="available",
        turn=turn_view,
        last_turn=last_turn,
        diagnostics=[],
        mailbox=mailbox_summary,
        gateway=gateway_summary,
    )


def _local_headless_detail_response(
    *,
    controller: RuntimeSessionController,
    summary_state: HoumaoManagedAgentStateResponse,
    latest_turn: _LocalHeadlessTurnSnapshot | None,
) -> HoumaoManagedAgentHeadlessDetailView:
    """Build one local headless detail payload."""

    tmux_session_name = controller.tmux_session_name
    tmux_session_live = (
        tmux_session_exists(session_name=tmux_session_name)
        if tmux_session_name is not None
        else False
    )
    active = latest_turn is not None and latest_turn.status == "active"
    return HoumaoManagedAgentHeadlessDetailView(
        runtime_resumable=True,
        tmux_session_live=tmux_session_live,
        can_accept_prompt_now=not active,
        interruptible=active,
        turn=summary_state.turn,
        last_turn=summary_state.last_turn,
        active_turn_started_at_utc=(
            latest_turn.started_at_utc if active and latest_turn is not None else None
        ),
        active_turn_interrupt_requested_at_utc=None,
        last_turn_status=(
            _managed_agent_turn_status(latest_turn.status) if latest_turn is not None else None
        ),
        last_turn_started_at_utc=latest_turn.started_at_utc if latest_turn is not None else None,
        last_turn_completed_at_utc=(
            latest_turn.completed_at_utc if latest_turn is not None else None
        ),
        last_turn_completion_source=(
            latest_turn.completion_source if latest_turn is not None else None
        ),
        last_turn_returncode=latest_turn.returncode if latest_turn is not None else None,
        last_turn_history_summary=latest_turn.history_summary if latest_turn is not None else None,
        last_turn_error=latest_turn.error if latest_turn is not None else None,
        mailbox=summary_state.mailbox,
        gateway=summary_state.gateway,
        diagnostics=[],
    )


def _turn_artifacts_root(controller: RuntimeSessionController) -> Path:
    """Return the persisted headless turn-artifact root for one controller."""

    return (
        controller.manifest_path.parent / f"{controller.manifest_path.stem}.turn-artifacts"
    ).resolve()


def _next_turn_index(controller: RuntimeSessionController) -> int:
    """Return the next local headless turn index."""

    backend_session = controller.backend_session
    if isinstance(backend_session, HeadlessInteractiveSession):
        return backend_session.state.turn_index + 1
    return len(_list_local_headless_turns(controller=controller)) + 1


def _list_local_headless_turns(
    controller: RuntimeSessionController,
) -> list[_LocalHeadlessTurnSnapshot]:
    """List persisted local headless turns newest-first."""

    root = _turn_artifacts_root(controller)
    if not root.exists():
        return []
    snapshots: list[_LocalHeadlessTurnSnapshot] = []
    for candidate in sorted(root.iterdir(), reverse=True):
        if not candidate.is_dir():
            continue
        snapshots.append(_snapshot_from_turn_dir(candidate))
    return snapshots


def _latest_local_headless_turn(
    *,
    controller: RuntimeSessionController,
) -> _LocalHeadlessTurnSnapshot | None:
    """Return the latest local headless turn snapshot when available."""

    snapshots = _list_local_headless_turns(controller=controller)
    if not snapshots:
        return None
    return snapshots[0]


def _turn_snapshot_from_id(
    *,
    controller: RuntimeSessionController,
    turn_id: str,
) -> _LocalHeadlessTurnSnapshot:
    """Return one local turn snapshot or fail clearly."""

    candidate = (_turn_artifacts_root(controller) / turn_id).resolve()
    if not candidate.is_dir():
        raise click.ClickException(f"Headless turn `{turn_id}` was not found.")
    return _snapshot_from_turn_dir(candidate)


def _snapshot_from_turn_dir(turn_dir: Path) -> _LocalHeadlessTurnSnapshot:
    """Read one local headless turn snapshot from a persisted artifact directory."""

    stdout_path = (turn_dir / "stdout.jsonl").resolve()
    stderr_path = (turn_dir / "stderr.log").resolve()
    status_path = (turn_dir / "exitcode").resolve()
    process_path = (turn_dir / "process.json").resolve()
    process_metadata = _read_process_metadata(process_path)
    started_at_utc = (
        process_metadata.launched_at_utc
        if process_metadata is not None and process_metadata.launched_at_utc is not None
        else _isoformat_from_mtime(turn_dir)
    )
    returncode: int | None = None
    completed_at_utc: str | None = None
    status = "active"
    error: str | None = None
    if status_path.exists():
        try:
            returncode = read_headless_turn_return_code(status_path=status_path)
        except Exception as exc:
            error = str(exc)
            status = "failed"
        else:
            status = "completed" if returncode == 0 else "failed"
            completed_at_utc = _isoformat_from_mtime(status_path)
            if returncode != 0 and stderr_path.exists():
                raw_error = stderr_path.read_text(encoding="utf-8").strip()
                error = raw_error or None
    turn_index = _turn_index_from_name(turn_dir.name)
    completion_source = _completion_source_from_stdout(stdout_path, turn_index=turn_index)
    history_summary = f"{turn_dir.name} {status}"
    return _LocalHeadlessTurnSnapshot(
        turn_id=turn_dir.name,
        turn_index=turn_index,
        status=status,
        started_at_utc=started_at_utc,
        completed_at_utc=completed_at_utc,
        completion_source=completion_source,
        stdout_path=stdout_path if stdout_path.exists() else None,
        stderr_path=stderr_path if stderr_path.exists() else None,
        status_path=status_path if status_path.exists() else None,
        returncode=returncode,
        history_summary=history_summary,
        error=error,
    )


def _load_turn_events(snapshot: _LocalHeadlessTurnSnapshot) -> list[HoumaoHeadlessTurnEvent]:
    """Load structured events for one persisted local headless turn."""

    if snapshot.stdout_path is None or not snapshot.stdout_path.exists():
        return []
    entries: list[HoumaoHeadlessTurnEvent] = []
    for event in load_headless_turn_events(
        stdout_path=snapshot.stdout_path,
        output_format="stream-json",
        turn_index=snapshot.turn_index,
    ):
        entries.append(
            HoumaoHeadlessTurnEvent(
                kind=event.kind,
                message=event.message,
                turn_index=event.turn_index,
                timestamp_utc=snapshot.completed_at_utc or snapshot.started_at_utc,
                payload=event.payload,
            )
        )
    return entries


def _read_process_metadata(process_path: Path) -> HeadlessProcessMetadata | None:
    """Read one optional local process metadata artifact."""

    if not process_path.exists():
        return None
    try:
        return load_headless_process_metadata(process_path=process_path)
    except Exception:
        return None


def _turn_index_from_name(turn_id: str) -> int:
    """Extract one integer turn index from a `turn-0001` directory name."""

    suffix = turn_id.rsplit("-", maxsplit=1)[-1]
    try:
        return int(suffix)
    except ValueError:
        return 0


def _completion_source_from_stdout(stdout_path: Path, *, turn_index: int) -> str | None:
    """Extract the completion source from persisted stdout events when present."""

    if not stdout_path.exists():
        return None
    try:
        events = load_headless_turn_events(
            stdout_path=stdout_path,
            output_format="stream-json",
            turn_index=turn_index,
        )
    except Exception:
        return None
    for event in reversed(events):
        payload = event.payload
        if not isinstance(payload, dict):
            continue
        value = payload.get("completion_source")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _isoformat_from_mtime(path: Path) -> str:
    """Return one UTC ISO-8601 timestamp from a filesystem mtime."""

    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds")


def _last_turn_result_from_snapshot(
    snapshot: _LocalHeadlessTurnSnapshot,
) -> ManagedAgentLastTurnResult:
    """Map one local headless turn snapshot to the managed-agent last-turn result."""

    if snapshot.status == "active":
        return "unknown"
    if snapshot.status == "completed":
        return "success" if snapshot.returncode == 0 else "known_failure"
    if snapshot.status == "failed":
        return "known_failure"
    return "unknown"


def _run_local_mail_prompt(
    *,
    controller: RuntimeSessionController,
    operation: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Run one local mailbox operation through the runtime-owned mail prompt path."""

    activation_state = controller.mailbox_activation_state()
    mailbox = ensure_mailbox_command_ready(controller.launch_plan)
    if activation_state == "pending_relaunch":
        raise click.ClickException(
            "Target session has a persisted mailbox binding, but runtime-owned mail commands "
            "remain pending relaunch."
        )
    if activation_state == "unsupported_joined_session":
        raise click.ClickException(
            "Target session cannot activate late mailbox support because joined-session relaunch "
            "authority is unavailable."
        )
    prefer_live_gateway = _live_gateway_client_for_controller(controller) is not None
    prompt_request = prepare_mail_prompt(
        launch_plan=controller.launch_plan,
        operation=cast(Any, operation),
        args=args,
        prefer_live_gateway=prefer_live_gateway,
    )
    return run_mail_prompt(
        send_prompt=controller.send_prompt,
        send_mail_prompt=(
            controller.send_mail_prompt
            if callable(getattr(controller, "send_mail_prompt", None))
            else None
        ),
        prompt_request=MailPromptRequest(
            request_id=prompt_request.request_id,
            operation=prompt_request.operation,
            prompt=prompt_request.prompt,
        ),
        mailbox=mailbox,
    )


def _managed_agent_turn_status(status: str) -> ManagedAgentTurnStatus:
    """Normalize one local runtime status into the public managed-agent enum."""

    if status in {"active", "completed", "failed", "interrupted", "unknown"}:
        return cast(ManagedAgentTurnStatus, status)
    return "unknown"


def _new_request_id(*, prefix: str) -> str:
    """Return one stable request id for direct local command responses."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}-{uuid.uuid4().hex[:10]}"


def _require_local_filesystem_mailbox_target(
    target: ManagedAgentTarget,
    *,
    operation: str,
) -> RuntimeSessionController:
    """Return the local controller for one late mailbox workflow target."""

    if target.mode == "server":
        raise click.ClickException(
            f"Late local mailbox {operation} is unavailable for server-backed managed agents."
        )
    assert target.controller is not None
    return target.controller
