# CCCC Chat Integration

The optional `houmao-cccc` distribution connects a running Houmao agent to one external CCCC Actor through gateway SDK version `1`. The gateway authenticates as that Actor; the body uses its local loopback gateway. CCCC chat is independent of both Houmao email slots and the agent's canonical email identity.

## Install and Provision

Build the distribution with `pixi run python -m build --wheel packages/houmao-cccc`, then install the resulting wheel in the gateway environment. Its supported Houmao range is `>=2.4,<3`. Installation discovers the `cccc` entry point; an explicit plugin selection enables it.

Stock CCCC does not expose the required Actor receiver API. Use the pinned revision and patch series in [the receiver dependency](../../../extern/tracked/cccc-receiver/README.md). [Native tooling](../../../tools/cccc/README.md) prepares a separate reproducible source checkout, builds it through Pixi, and runs an isolated loopback service. The selected protocol is version `1`, with a fixed Actor bearer at `POST /api/v1/external-receiver/v1/rpc`.

The CCCC operator creates the Group and Actor, then explicitly issues an external-receiver grant. Grant issuance cannot adopt a running native body. The private export helper binds the grant to a Houmao agent UUID and writes a new owner-only `0600` JSON file outside the checkout. See [the deployment example](../../../examples/cccc-gateway/README.md). A remote operator must select an explicit private administrator credential file and use HTTPS. Runtime plugin operations always use the normal Actor grant.

The credential document contains `schema_version`, `agent_id`, `endpoint`, `group_id`, `actor_id`, `actor_generation`, and `token`. Only the credential file holds the token. The gateway rejects unsafe permissions, symlinks, owner mismatch, and mismatched routing descriptors. It does not discover ambient CCCC credentials. Status and exceptions omit secrets and provider response bodies.

## Attach and Reconfigure

[The example selection](../../../examples/cccc-gateway/plugins.yaml) declares `implementation: cccc`, an explicit `credential_ref.file`, and immutable `endpoint`, `group_id`, `actor_id`, and `actor_generation` settings. Select it with:

```bash
houmao-mgr agents single --agent-id AGENT_UUID gateway attach \
  --background --plugins-config /absolute/path/plugins.yaml
```

Detach and reattach the gateway when changing that selection or upgrading code. The agent body can keep running. A live connection operation cannot change the owner, Group, Actor, generation, or credential path. Creating a new Actor generation requires a new selection and grant. Rotating a grant for the same registration replaces the selected private file, followed by `connection refresh-credentials --binding-id BINDING_ID`.

Use `--instance NAME` when selecting a different instance. All routes are relative to `/v1/plugins/NAME`. The CLI requires `--gateway-url` with a loopback HTTP(S) URL and never opens CCCC credentials. Plugin activation also requires a loopback gateway listener.

## Inspect Connection State

```bash
houmao-cccc --gateway-url http://127.0.0.1:PORT binding
houmao-cccc --gateway-url http://127.0.0.1:PORT capabilities
houmao-cccc --gateway-url http://127.0.0.1:PORT members
```

`binding` reports the current owner, instance, binding ID, selected Actor descriptors, connection phase, and a sanitized error code. A provider outage can leave the host healthy while the plugin reconnects. `connected` means this receiver negotiated the protocol and holds a lease. A conflicting active receiver must release or expire before another normal receiver acquires it. The default lease lasts 45 seconds.

`connection connect`, `disconnect`, `reconnect`, and `refresh-credentials` require the current `--binding-id`. Reconnect restores transport and lease state; it does not replay history. Normal Actor grants and plugin routes cannot force takeover. An explicitly authenticated CCCC operator can fence an old receiver through `/api/v1/external-receiver/v1/takeover`; that action does not retry unsettled events.

## Send, Reply, and Inspect Receipts

```bash
houmao-cccc --gateway-url http://127.0.0.1:PORT chat send \
  --binding-id BINDING_ID --operation-id UNIQUE_OPERATION_ID \
  --to PEER_ACTOR_ID --mode request_reply --text 'Please review this result.'
houmao-cccc --gateway-url http://127.0.0.1:PORT chat reply \
  --binding-id BINDING_ID --operation-id NEW_OPERATION_ID \
  --event-ref INCOMING_EVENT_REF --text 'Reviewed.'
houmao-cccc --gateway-url http://127.0.0.1:PORT chat deliveries \
  --event-ref EVENT_REF --limit 20
```

Use explicit Actor recipients in the bound Group; `@user` must be the sole recipient for a human audience. Mixed human/Actor recipients and email addresses are rejected. Replies retain native `reply_to` ancestry. A `request_reply` mode obligates the receiving agent to author a reply; the gateway does not synthesize one.

The provider stores the chat event before attempting recipient handoff. Each recipient receives a separate persisted attempt. `accepted` confirms immediate ordinary gateway handoff, `refused` describes admission refusal, `failed` describes a known unsuccessful handoff, and `uncertain` preserves the possibility of delivery without confirmation. Storage success alone does not confirm handoff or task completion. There is no exactly-once guarantee.

The provider claims an attempt before offering it. The plugin checks the current lease and local connection generation, then dispatches once within the remaining deadline. Busy or unavailable bodies return errors. Body death/replacement or a lost acknowledgement can produce uncertainty. Neither layer caches prompt payloads for later dispatch. Lease expiration or daemon recovery settles old work; it never authorizes replay.

If a mutation response is lost, preserve the original operation ID. Repeating the same normalized send recovers the existing event; changing its request under that ID produces a conflict. Matching operation reuse does not start another delivery attempt. The original sender must explicitly retry selected recipients:

```bash
houmao-cccc --gateway-url http://127.0.0.1:PORT chat retry \
  --binding-id BINDING_ID --event-ref EVENT_REF --to PEER_ACTOR_ID
```

Add `--allow-uncertain-retry` only when acknowledging possible duplication after an uncertain handoff. Another Actor cannot retry the sender's event. Partial-recipient receipts remain separate; retry only the intended recipients. The CLI preserves safe uncertainty metadata and the operation ID when available.

## Recover History Without Redelivery

```bash
houmao-cccc --gateway-url http://127.0.0.1:PORT chat history --limit 20
houmao-cccc --gateway-url http://127.0.0.1:PORT chat history --limit 20 --cursor OPAQUE_CURSOR
houmao-cccc --gateway-url http://127.0.0.1:PORT chat history --event-ref EVENT_REF
```

History, exact event lookup, and delivery receipt reads are bounded and non-consuming. Page limits range from 1 to 100, subject to negotiated response byte caps. Opaque event references and cursors bind to the owner, instance, Actor generation, and query. Altered or foreign references fail before provider access. Preserve the page query when continuing a cursor. References survive a gateway-only restart for the same binding.

History reads cannot activate old chat as prompts and do not advance native Mail cursors. The initial chat-only plugin reports Mail unavailable. Version 0.2 adds [explicit deferred Mail](cccc-mail.md) when the provider advertises its complete bounded-read and durable-receipt contract. Content-free native Mail notices use ordinary admission and never consume a batch or import email reminder rules.

## Qualification and Cleanup

[Agent instructions](../../../examples/cccc-gateway/agent-instructions.md) explain the local commands and reply contract. Actual-provider integration, installed-wheel checks, deterministic failure tests, and the two-real-agent smoke are distinct acceptance gates. Missing service, model, or fixture prerequisites are failures of setup, not passing tests. Qualification artifacts retain only sanitized versions, identifiers, hashes, and outcomes; private credentials and native agent output stay outside the checkout.

Disconnect or detach the gateway to release the current receiver cleanly. Revoke only grants created for the test and stop only captured owned agent/service identities. CCCC owns retained ledger history. No plugin payload spool needs draining.
