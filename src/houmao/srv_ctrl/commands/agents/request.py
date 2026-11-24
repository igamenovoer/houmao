"""Submit wrapped work through one explicitly selected managed-agent route."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import click

from houmao.agents.realm_controller.agent_identity import (
    AGENT_ID_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    SELF_TMUX_SESSION_ENV_VAR,
)
from houmao.agents.realm_controller.gateway_access_runtime import load_gateway_deployment
from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.agents.realm_controller.gateway_models import (
    GatewayRequestCreateV1,
    GatewayRequestPayloadSubmitWorkRequestV1,
)
from houmao.gateway.access_models import GatewayClientBinding, GatewayOwner, GatewayTarget
from houmao.passive_server.client import PassiveServerClient
from houmao.passive_server.models import PassiveProofEndpoint, PassiveWorkRequestReceipt
from houmao.srv_ctrl.commands.agents.access import (
    _access_errors,
    _endpoint_options,
    _owner_access,
    _peer_signer_path,
    _selected,
    _source_access,
    _verified_endpoint,
)
from houmao.srv_ctrl.commands.output import emit


def _select_signer(source_agent_id: str | None, unsigned: bool) -> Path | None:
    """Select a configured managed source or anonymous admission before submission."""

    if unsigned:
        if source_agent_id is not None:
            raise click.UsageError("Choose either --unsigned or --source-agent-id.")
        return None
    if source_agent_id is not None:
        return _peer_signer_path(_source_access(source_agent_id))
    try:
        source = _source_access(None)
    except ValueError:
        if any(
            os.environ.get(name)
            for name in (AGENT_ID_ENV_VAR, AGENT_MANIFEST_PATH_ENV_VAR, SELF_TMUX_SESSION_ENV_VAR)
        ):
            raise
        return None
    deployment = load_gateway_deployment(source.manifest_path)
    if deployment is None or deployment.peer_signer_path is None:
        return None
    return _peer_signer_path(source)


@click.command(name="request")
@_endpoint_options
@click.option("--text", required=True, help="Task text to deliver as an attributed request.")
@click.option("--source-agent-id", help="Use the peer signer of this verified owned source.")
@click.option("--unsigned", is_flag=True, help="Submit as an anonymous caller.")
@click.option("--passive-url", help="Use the direct detached route at this trusted listener.")
def work_request_command(
    text: str,
    source_agent_id: str | None,
    unsigned: bool,
    url: str | None,
    passive_url: str | None,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
) -> None:
    """Ask the selected agent to do work under its existing instructions."""

    with _access_errors():
        payload = GatewayRequestCreateV1(
            kind="submit_work_request", payload=GatewayRequestPayloadSubmitWorkRequestV1(text=text)
        )
        if passive_url is not None:
            if url is not None:
                raise click.UsageError("Choose either --url or --passive-url.")
            receipt = _submit_passive_request(
                passive_url,
                payload=payload,
                context_id=context_id,
                generation=generation,
                presence=presence,
                ca_bundle=ca_bundle,
                signer=_select_signer(source_agent_id, unsigned),
            )
            emit(receipt.model_dump(mode="json", exclude_none=True))
            if receipt.outcome != "handed_off":
                raise click.exceptions.Exit(1)
            return

        endpoint = _verified_endpoint(url, context_id, generation, presence, ca_bundle)
        signer = _select_signer(source_agent_id, unsigned)
        client = (
            endpoint.signed_client(signer)
            if signer is not None
            else GatewayClient(
                base_url=endpoint.base_url,
                ca_bundle_path=endpoint.ca_bundle,
                respect_proxy_env=False,
            )
        )
        accepted = client.create_request(payload)
        emit(accepted.model_dump(mode="json", exclude_none=True))


def _submit_passive_request(
    url: str,
    *,
    payload: GatewayRequestCreateV1,
    context_id: str | None,
    generation: str | None,
    presence: str | None,
    ca_bundle: Path | None,
    signer: Path | None,
) -> PassiveWorkRequestReceipt:
    """Pin the passive target and listener before submitting on the detached route."""

    if context_id is None and generation is None:
        expected = _owner_access().target
    else:
        scope = _selected()
        if not (scope.agent_id and context_id and generation and presence):
            raise click.UsageError(
                "For a remote passive target use --agent-id, --context-id, --generation, and --presence."
            )
        expected = GatewayTarget(
            owner=GatewayOwner(agent_id=scope.agent_id, context_id=context_id),
            incarnation=generation,
        )
    route = f"/houmao/agents/{quote(expected.owner.agent_id, safe='')}"
    transport = GatewayClient(base_url=url, ca_bundle_path=ca_bundle, respect_proxy_env=False)
    descriptor = transport._request_model("GET", f"{route}/auth/endpoint", PassiveProofEndpoint)
    if (
        descriptor.target != expected
        or descriptor.challenge_path != f"{route}/auth/challenge"
        or (presence is not None and descriptor.presence_id != presence)
    ):
        raise click.ClickException("The passive listener differs from the selected target.")
    if signer is None:
        return transport._request_model(
            "POST",
            f"{route}/work-requests",
            PassiveWorkRequestReceipt,
            body=payload.model_dump(mode="json"),
            timeout_seconds=8.0,
        )
    binding = GatewayClientBinding(
        base_url=url,
        owner=expected.owner,
        purpose="caller",
        private_key_path=str(signer),
        ca_bundle_path=str(ca_bundle) if ca_bundle is not None else None,
    )
    return PassiveServerClient(
        url,
        timeout_seconds=8.0,
        binding=binding,
        target_incarnation=expected.incarnation,
        target_presence_id=descriptor.presence_id,
    ).submit_detached_work_request(expected.owner.agent_id, payload)
