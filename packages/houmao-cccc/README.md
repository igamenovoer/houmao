# Houmao CCCC Plugin

`houmao-cccc` is an optional distribution for owner-bound CCCC chat and deferred Mail. Install it with Houmao in the gateway or direct CLI environment.

```bash
pixi run python -m build --wheel packages/houmao-cccc
# In the selected Houmao environment:
python -m pip install packages/houmao-cccc/dist/houmao_cccc-0.3.0-py3-none-any.whl
```

The distribution requires Houmao `>=3.0.0rc8,<4` and CCCC external receiver protocol `2`. Its `cccc` entry point uses Houmao's public gateway SDK. In a managed agent, `houmao-cccc` can discover and authenticate to the agent's gateway. An enrolled caller can instead pass the exact `--gateway-url`, `--instance`, and `--signer-binding`. Replies use `chat reply --handle HANDLE --operation-id ID --text TEXT`. The handle identifies its plugin instance for managed-self selection and also works with `chat deliveries --handle HANDLE`. New gateway sends take `--connection-token` from `members`.

The selected gateway instance or direct Actor profile determines the CCCC Group. Use `members --group GROUP_ID` to assert that selection. A mismatch returns `group_conflict`. Run `houmao-cccc --version` to see the installed version and `houmao-cccc --help` for examples in both modes.

Build the pinned CCCC source with the tracked receiver patches. Each plugin instance selects one provisioned Group, Actor, and Actor generation for one Houmao owner. The gateway supports scheduled pull and two push policies. CCCC retains pending chat and delivery outcomes. A live receiver lease controls intake, and the original sender authorizes another attempt for terminal work. [Integration reference](../../docs/reference/gateway/cccc.md) · [Native example](../../examples/cccc-gateway/README.md)

## Direct Chat and Discovery

Use `--direct-profile` to select the same private Actor profile format used by the gateway. The profile contains schema version `1`, the Houmao `agent_id`, CCCC `endpoint`, `group_id`, `actor_id`, `actor_generation`, and an Actor grant `token`. Keep the file owner-only and outside the checkout. The CLI checks the current managed agent's identity when available. An unmanaged caller supplies the expected owner using `--agent-id`.

```bash
houmao-cccc --direct-profile "$CCCC_PROFILE" discovery
houmao-cccc --direct-profile "$CCCC_PROFILE" members --group "$GROUP_ID"
houmao-cccc --direct-profile "$CCCC_PROFILE" chat deliveries --event-id "$EVENT_ID"
houmao-cccc --direct-profile "$CCCC_PROFILE" chat pull --limit 16
houmao-cccc --direct-profile "$CCCC_PROFILE" chat ack --receipt "$RECEIPT"
houmao-cccc --direct-profile "$CCCC_PROFILE" chat reply \
  --event-ref "$EVENT_REF" --operation-id reply-1 --text 'I can take this.'
```

`chat pull` returns an ordered `messages` list and a batch `receipt`. Each entry includes the sender, original timestamp, mode, text, and Actor-scoped `event_ref`. A later invocation can use the reference to reply or read exact history. Acknowledge the receipt once you receive the batch. CCCC distinguishes that acknowledged direct read from gateway handoff. When the gateway already holds the receiver lease, direct pull reports a lease conflict.

`discovery` gives the CCCC endpoint, Actor registration, and advertised operations in either mode. Use those descriptors with an explicitly provisioned Actor credential in the native CCCC client for advanced operations. [Actor RPC](../../extern/tracked/cccc-receiver/PROTOCOL.md#actor-rpc)

## Direct Mail

Use the same explicit profile for CCCC Mail. Read the current native `cursor.event_id` with `mail cursor` and supply it as `--expected-cursor`. The initial cursor is an empty string. `mail peek` inspects without consuming. `mail reply --event-id` selects a native Mail parent from an Actor-visible result.

```bash
houmao-cccc --direct-profile "$CCCC_PROFILE" mail cursor
houmao-cccc --direct-profile "$CCCC_PROFILE" mail read \
  --operation-id read-1 --expected-cursor "$CURSOR_EVENT_ID"
houmao-cccc --direct-profile "$CCCC_PROFILE" mail reads --operation-id read-1
```

If a read outcome is uncertain, use the same operation ID to look up its authoritative receipt. CCCC Mail has its own cursor and receipts, independent of Houmao's offline and online email slots. [Mail contract](../../docs/reference/gateway/cccc-mail.md)
