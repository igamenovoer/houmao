# CCCC Chat Integration

The optional `houmao-cccc` distribution connects a running Houmao agent to one external CCCC Actor through gateway SDK version `2`. The gateway authenticates as that Actor. Callers prove their gateway identity separately. CCCC chat is independent of both Houmao email slots and the agent's canonical email identity. [CCCC plugin declaration](../../../packages/houmao-cccc/src/houmao_cccc/__init__.py)

## Install and Provision

Build the distribution with `pixi run python -m build --wheel packages/houmao-cccc`, then install the resulting wheel in the gateway environment. Version 0.3 supports Houmao `>=3.0.0rc8,<4`. Installation makes the `cccc` entry point discoverable. An explicit plugin selection enables it. [Package metadata](../../../packages/houmao-cccc/pyproject.toml)

Use the pinned CCCC revision and patch series to provide the Actor receiver API. The native tooling prepares a separate source checkout, builds it through Pixi, and runs an isolated loopback service. The CCCC external-receiver protocol is version `2`. It uses a fixed Actor bearer at `POST /api/v1/external-receiver/v2/rpc`. [Receiver dependency](../../../extern/tracked/cccc-receiver/README.md) · [Native tooling](../../../tools/cccc/README.md) · [Receiver protocol](../../../extern/tracked/cccc-receiver/PROTOCOL.md)

The CCCC operator creates the Group and Actor, then explicitly issues an external-receiver grant. Grant issuance cannot adopt a running native body. The private export helper binds the grant to a Houmao agent UUID and writes a new owner-only `0600` JSON file outside the checkout. See [the deployment example](../../../examples/cccc-gateway/README.md). A remote operator selects an explicit caller credential with permission for the operation and uses HTTPS. Runtime plugin operations always use the normal Actor grant.

The credential document contains `schema_version`, `agent_id`, `endpoint`, `group_id`, `actor_id`, `actor_generation`, and `token`. Only the credential file holds the token. The gateway rejects unsafe permissions, symlinks, owner mismatch, and mismatched routing descriptors. It does not discover ambient CCCC credentials. Status and exceptions omit secrets and provider response bodies.

## Attach and Reconfigure

[The example selection](../../../examples/cccc-gateway/plugins.yaml) declares `implementation: cccc`, an explicit `credential_ref.file`, and immutable `endpoint`, `group_id`, `actor_id`, and `actor_generation` settings. Select it with:

```bash
houmao-mgr agents single --agent-id AGENT_UUID gateway attach \
  --background --plugins-config /absolute/path/plugins.yaml
```

Detach and reattach the gateway when changing that selection or upgrading code. The agent body can keep running. A live connection operation cannot change the owner, Group, Actor, generation, or credential path. Creating a new Actor generation requires a new selection and grant. Rotating a grant for the same registration replaces the selected private file, followed by `connection refresh-credentials --binding-id BINDING_ID`.

In a managed agent, omit the URL to select the verified owning gateway. For explicit gateway selection, pass the gateway base URL to `--gateway-url` and the instance name to `--instance` (default `cccc`). The CLI appends `/v1/plugins/NAME` and the operation path to the base. Use a numeric loopback HTTP base such as `http://127.0.0.1:PORT` or a verified HTTPS base with its configured proxy prefix.

The CLI can use the current managed self key when invoked from a managed generation. A keyed roster requires an explicitly authorized caller for CCCC operations. An external caller supplies `--signer-binding PATH` with private client binding JSON containing the exact `base_url`, `owner` (agent and context IDs), `purpose: caller`, `private_key_path`, and optional `ca_bundle_path`. The configured Actor credentials stay with the gateway worker.

For `invalid_gateway_url`, check the gateway base and pass the plugin name through `--instance`. For `managed_self_authority_unavailable`, verify the current managed generation and its owning gateway. Both errors end the call before it makes an HTTP request.

Each CCCC route has an action on its installed instance, such as `plugin.cccc.binding.read`, `plugin.cccc.chat.send`, or `plugin.cccc.connection.refresh-credentials`. With a keyed roster, the administrator and verified managed self can use the plugin routes on the owning agent. An enrolled peer needs a grant for the selected action on that instance. An empty administrator roster admits anonymous callers under the gateway's open policy. Worker delivery uses the configured Actor credential independently. [Gateway Authorization Policy](operations/authorization-policy.md)

## Select Delivery Mode

Each selected CCCC instance defaults to scheduled pull. It can receive a launch override with an explicit configuration file or with its retained plugin selection. Nested values overlay the selected config in argument order. Each scheduled pull with staging capacity sets one notification boundary.

```bash
houmao-mgr agents single --agent-id AGENT_UUID gateway attach --background \
  --plugin-config-override 'team={"delivery":{"transport":"push","push_policy":"asap"}}'
```

Push ASAP stages each arrival as one prompt and waits for ordinary readiness before starting the next. Timed push batches arrivals until the quiet interval after the latest arrival or the maximum wait after the first, whichever occurs first. The batch then waits intact until the agent is ready. Times are in seconds. Use `quiet_interval` and `max_wait` for `batch`, and set them to null when clearing an existing timed-push configuration.

`GET /v1/plugins/NAME/delivery` reports the settings revision, desired and effective settings, and transition state. An authorized caller can `PUT` the current revision and a complete `settings` object. The management action is `plugin.cccc.delivery.update`; read access uses `plugin.cccc.delivery.read`.

```json
{
  "revision": 0,
  "settings": {
    "transport": "push",
    "push_policy": "batch",
    "quiet_interval": 2.0,
    "max_wait": 8.0
  }
}
```

For pull, use `transport: pull` and a positive `pull_interval` (default one second). Set `push_policy`, `quiet_interval`, and `max_wait` to null when a launch override replaces retained push settings with pull. A policy edit closes the open push batch. A transport edit reports `applying` while the previous lease retires, then `active` after the replacement begins intake. Runtime edits apply to the current gateway run.

## Inspect Connection State

```bash
houmao-cccc --gateway-url http://127.0.0.1:PORT binding
houmao-cccc --gateway-url http://127.0.0.1:PORT capabilities
houmao-cccc --gateway-url http://127.0.0.1:PORT members
```

`houmao-cccc --version` reports the installed CLI version. Use `houmao-cccc --help` for common gateway and direct commands.

`binding` reports the current owner, instance, binding ID, selected Actor descriptors, connection phase, and a sanitized error code. A provider outage can leave the host healthy while the plugin reconnects. `connected` means this receiver negotiated the protocol and holds a lease. A conflicting active receiver must release or expire before another normal receiver acquires it. The default lease lasts 45 seconds.

Before a CCCC chat exercise, follow the gateway readiness procedure for the attached Web or headless agent. Separately, check `binding` on the selected plugin instance. Require the expected `agent_id` and `binding_id` and check that `connection` is `connected`. A connected plugin still depends on the body's live admission at handoff. [Readiness for Web and Headless Agents](contracts/protocol-and-state.md#readiness-for-web-and-headless-agents)

`connection connect`, `disconnect`, `reconnect`, and `refresh-credentials` require the current `--binding-id`. Reconnect restores transport and lease state; it does not replay history. Normal Actor grants and plugin routes cannot force takeover. An explicitly authenticated CCCC operator can fence an old receiver through `/api/v1/external-receiver/v2/takeover`; that action does not retry unsettled events.

## Send, Reply, and Inspect Receipts

Run `members` to get the current `connection_token` and select explicit Actor recipients in the bound Group. The selected gateway instance determines the Group. You can pass `members --group GROUP_ID` to check that it matches the Group you expect. A mismatch reports `group_conflict`. Use `@user` by itself for a human audience.

```bash
houmao-cccc --instance team members --group GROUP_ID
houmao-cccc --instance team chat send \
  --connection-token CONNECTION_TOKEN --operation-id UNIQUE_OPERATION_ID \
  --to PEER_ACTOR_ID --mode request_reply --text 'Please review this result.'
```

Each incoming prompt shows your bound CCCC Group and Actor, your gateway base URL, and its relevant endpoints. Its one request fence contains the ordered messages with sender, original CCCC timestamp, mode, body, and separate reply handles. Use your current instructions and tool permissions to decide how to handle the requests. A CCCC sender label gives attribution.

```bash
houmao-cccc chat details --handle "$HANDLE"
houmao-cccc chat reply --handle "$HANDLE" \
  --operation-id "$NEW_OPERATION_ID" --text="$REPLY_TEXT"
```

The CLI selects the instance from the handle when you omit `--instance`. For HTTP, append the relative endpoint from the notification to its gateway base URL. Send `handle`, `operation_id`, and `text` as JSON to the reply endpoint. Replies preserve the exact native parent.

The provider stores chat and its per-recipient pending attempts durably. An attempt may be pending or staged while the gateway is absent or the body is busy. `accepted` confirms ordinary gateway handoff, `direct_read` confirms a later direct acknowledgment, and `uncertain` records possible exposure without confirmed handoff. These receipts are separate from task completion.

For a message you sent or a reply you posted, use `event.handle` from the result. For an incoming message, use its handle from the request fence.

```bash
houmao-cccc chat deliveries --handle "$SENT_HANDLE" --limit 20
houmao-cccc chat deliveries --handle "$INCOMING_HANDLE" --limit 20
```

The HTTP route takes the same target as `GET /v1/plugins/{instance}/chat/deliveries?handle=HANDLE`. Gateway callers can also use `chat deliveries --event-ref EVENT_REF`. If a handle expires after time passes or the connection changes, use `chat history --event-id EVENT_ID` on the owning instance to obtain a fresh handle for the exact Actor-visible event.

The provider returns the newest attempts first and includes `has_more` when older matching attempts exceed the limit. An expired lease releases unstarted deliveries for the next receiver and reconciles or classifies started work. An uncertain attempt requires an explicit sender decision before a fresh delivery.

If a mutation response is lost, repeat the same operation ID and normalized inputs to reconcile the original result. An explicit delivery retry uses the sender's scoped history reference and selected recipients. Use `--allow-uncertain-retry` when acknowledging possible duplication.

```bash
houmao-cccc --instance team chat retry \
  --binding-id BINDING_ID --event-ref EVENT_REF --to PEER_ACTOR_ID
```

## Discover CCCC and Use Direct Operations

`houmao-cccc --instance team discovery` returns the CCCC endpoint, Group, Actor registration, and advertised Actor operations. For advanced calls, use that scope and the privately provisioned Actor grant against CCCC. The qualified Actor bearer works on the receiver interface and CCCC enforces authority per operation. The operator handles operations requiring broader CCCC permissions.

When a gateway is unavailable, explicitly select the private Actor profile with `--direct-profile PATH`. Direct mode supports common chat and qualified Mail operations and one ordered chat snapshot per `chat pull`. A current gateway receiver lease must expire or release before direct pull can acquire it. The [package guide](../../../packages/houmao-cccc/README.md) gives the direct pull and acknowledgment workflow.

The profile determines the Group in direct mode. Use `houmao-cccc --direct-profile PATH members --group GROUP_ID` to check the selection, and `houmao-cccc --direct-profile PATH chat deliveries --event-id EVENT_ID` to inspect receipts for an Actor-visible native event.

## Recover History Without Redelivery

```bash
houmao-cccc --gateway-url http://127.0.0.1:PORT chat history --limit 20
houmao-cccc --gateway-url http://127.0.0.1:PORT chat history --limit 20 --cursor OPAQUE_CURSOR
houmao-cccc --gateway-url http://127.0.0.1:PORT chat history --event-id EVENT_ID
```

History, exact event lookup, and delivery receipt reads are bounded and non-consuming. Page limits range from 1 to 100, subject to negotiated response byte caps. Opaque event references and cursors bind to the owner, instance, Actor generation, and query. Altered or foreign references fail before provider access. Preserve the page query when continuing a cursor. History cursors and receipt references survive a gateway-only restart for the same binding. Message handles are scoped to the current connection.

History reads cannot activate old chat as prompts and do not advance native Mail cursors. The integration offers [explicit deferred Mail](cccc-mail.md) when the provider advertises its complete bounded-read and durable-receipt contract. Content-free native Mail notices use ordinary admission and never consume a batch or import email reminder rules.

## Qualification and Cleanup

[Agent instructions](../../../examples/cccc-gateway/agent-instructions.md) explain the local commands and reply contract. Actual-provider integration, installed-wheel checks, deterministic failure tests, and the two-real-agent smoke are distinct acceptance gates. Missing service, model, or fixture prerequisites are failures of setup, not passing tests. Qualification artifacts retain only sanitized versions, identifiers, hashes, and outcomes; private credentials and native agent output stay outside the checkout.

Disconnect or detach the gateway to release the current receiver cleanly. Revoke only grants created for the test and stop only captured owned agent/service identities. CCCC owns retained ledger history. No plugin payload spool needs draining.
