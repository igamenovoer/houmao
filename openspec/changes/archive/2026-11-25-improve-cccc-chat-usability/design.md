# Design

## Context

The CCCC CLI appends `/v1/plugins/{instance}` to the selected gateway base URL. An incoming hint currently exposes the complete local plugin URL, and managed-self selection requires the exact owner-local base URL. The CLI catches endpoint and authority errors through the same fallback. [Proposal](proposal.md) · [CLI](../../../packages/houmao-cccc/src/houmao_cccc/cli.py) · [Gateway client](../../../src/houmao/gateway/client.py)

## Goals / Non-Goals

### Goals

Make replies discoverable from the ordinary chat envelope and diagnose common endpoint mistakes before sending a request. Give drivers one reference for interpreting readiness and bounded attempt lists.

### Non-Goals

The scope ends at CLI validation, chat guidance, and documentation of existing observations. The gateway owns caller authorization and live admission. CCCC owns event and attempt storage, and the original sender authorizes fresh delivery attempts.

## Decisions

### Validate the Gateway Base Before Self Selection

Use the shared gateway base URL validator for URL syntax and transport. Identify a pasted owner-local `/v1/plugins/INSTANCE` URL or one of its operation URLs at the CLI boundary. When a signer binding supplies an authoritative base, honor an exact match and diagnose an appended plugin route relative to that base. The selected endpoint and configured proxy prefix participate in signing, so the user supplies the corrected base URL explicitly. [Gateway base validation](../../../src/houmao/gateway/access_models.py#L307) · [Authenticated access](../../specs/authenticated-gateway-access/spec.md#requirement-client-proof-is-bound-to-the-expected-endpoint)

Report `invalid_gateway_url` for bad URL input and `managed_self_authority_unavailable` when current managed-self selection fails for a valid base. Use short fixed repair messages in JSON on stderr with the existing failure exit status. Suggest the gateway base and `--instance` for endpoint mistakes, and verification of the current owner gateway and generation for authority failures. Selection ends on failure under the chosen caller identity. A post-request failure retains the existing uncertainty and operation ID handling.

### Render a Reply Example From the Live Plugin Context

Add `gateway_base_url` from the same resolved listener that supplies `local_plugin_url`. Label the latter as the HTTP plugin base. The ordinary chat hint shows the command below, identifying the advertised values and the inputs the caller supplies. Use the current `plugin_instance` even when the operator chose a name other than `cccc`. The normal `/chat/reply` handler checks the binding and scoped event reference. [Chat hint](../../../packages/houmao-cccc/src/houmao_cccc/plugin.py#L459) · [Chat requirements](specs/cccc-chat/spec.md)

```bash
houmao-cccc --gateway-url "$GATEWAY_BASE_URL" --instance "$PLUGIN_INSTANCE" chat reply \
  --binding-id "$BINDING_ID" --event-ref "$EVENT_REF" \
  --operation-id "$NEW_OPERATION_ID" --text "$REPLY_TEXT"
```

Use the supplied `event_ref` and a fresh caller operation ID for a new reply. Keep the deferred Mail notice on its own guidance. Resolve URL-specific guidance from the live listener when available. The template uses references to the values already present in the envelope, which avoids duplicating the long event reference within its byte budget.

### Use the Readiness Observation in Gateway Status

Put the recipe under `GET /v1/status` in the gateway protocol reference, with a link from the CCCC guide. Read the snapshot under normal status permissions. Require `gateway_health: healthy`, `observation.freshness: current`, and `observation.can_accept_prompt_now: true` as positive preflight evidence. Interpret a missing observation as unconfirmed. The common projection already combines gateway work posture with evidence from the selected surface. [Status projection](../../../src/houmao/agents/realm_controller/gateway_service.py#L9724) · [Reference requirements](specs/agent-gateway-reference-docs/spec.md)

For Web diagnostics, inspect `web.availability`, `web.host_process_alive`, and `web.can_accept_prompt_now`. For a known headless agent, use `GET /v1/control/headless/state` and its execution, liveness, and admission fields. Check the selected CCCC `binding` separately for the expected owner, binding ID, and connected phase. Every actual handoff evaluates current readiness and can refuse a body that became busy after the observation.

### Document Provider Order and Declared Versions

The pinned CCCC provider walks persisted attempts in reverse creation order before applying the event filter and count limit. The plugin returns that order. Specify it in CLI help, the gateway response reference, and the provider protocol reference. A client can reverse the returned window for chronological display, using `has_more` to see whether the window omits earlier attempts. Attempt times would require authoritative provider metadata beyond the ordering already available. [Receiver patch](../../../extern/tracked/cccc-receiver/patches/0001-external-receiver.patch#L551) · [Provider protocol](../../../extern/tracked/cccc-receiver/PROTOCOL.md)

Correct the CCCC and plugin author guides from the corresponding package metadata and plugin declarations. At this revision they use gateway SDK `2` and Houmao `>=3.0.0rc1,<4`. CCCC negotiates external-receiver protocol `1` separately. Link those declarations from the references and compare the documented values with them during verification. [CCCC package](../../../packages/houmao-cccc/pyproject.toml) · [Example package](../../../examples/gateway-plugin/pyproject.toml)

## Risks / Trade-offs

- A proxy prefix can resemble a plugin path. Cover exact prefixed signer bindings and pasted local routes in CLI tests.
- Additional hint text counts against the existing envelope limit. Keep the hint compact and exercise it through the ordinary event dispatch test.

## Migration Plan

Install the updated optional package in the environment used by the gateway and its CLI. Use the documented gateway detach and attach procedure to load the new plugin code against the existing body and CCCC binding. Roll back by reinstalling the prior package and following the same procedure. [Plugin operations](../../../docs/reference/gateway/cccc.md#attach-and-reconfigure)
