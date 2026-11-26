# Proposal

## Why

In [issue #100](https://github.com/igamenovoer/houmao/issues/100), a 26-character CCCC chat message produced 1,592 characters of plugin text before the gateway added its own envelope. CCCC delivery also needs to handle bursts, wait through an active agent turn, and serve agents that use CCCC without a running Houmao gateway.

## What Changes

- Make pull and push selectable per CCCC gateway instance through launch arguments and a live gateway API. Default to scheduled pull, with one agent notification per non-empty pull.
- Add push policies for ASAP delivery and batching. ASAP prompts an idle agent immediately and sends later messages in order as the agent becomes ready. Batching closes on a configurable quiet interval or maximum wait measured from the first arrival.
- Keep durable pending chat deliveries and outcomes in CCCC. Use the Actor receiver lease to coordinate ownership across gateway and direct CLI sessions, including transport changes and recovery.
- Wrap each gateway chat delivery in one request fence. Put the single message or the entire ordered batch inside the fence with each message's sender, original timestamp, mode, body, and reply handle. The receiving agent decides how to handle the request under its existing rules and permissions.
- Show the agent's bound CCCC Group and Actor and one resolved gateway base URL in the host-written header. List relative endpoints for binding inspection, message details, and reply.
- Let the agent retrieve details and reply to an exact message by handle.
- Expose common chat and Mail operations through the gateway. Let agents discover their CCCC origin, identity, and authorized capabilities on demand for advanced direct calls.
- Add pull-only direct operation to `houmao-cccc` for use without a running gateway. The CLI provides common CCCC commands, ordered pull results, and discovery using a selected owner-bound Actor profile.
- **BREAKING** Require a new version of the external receiver protocol. It replaces chat readiness refusal with pending delivery and adds batch pull, push, and explicit handoff state. Gateway chat reply takes a short handle in place of the signed `event_ref` and full binding ID.

## Capabilities

### New Capabilities

None. The change extends the existing CCCC and gateway plugin contracts.

### Modified Capabilities

- `cccc-external-receiver` adds durable pending chat, batch pulls, a push stream, and leased delivery start, settlement, and recovery for gateway and direct receivers.
- `cccc-gateway-binding` adds per-instance delivery configuration, authorized CCCC discovery, and an owner-bound selection for direct CLI use.
- `cccc-chat` defines batching and ASAP admission, compact fenced requests, short reply handles, and gatewayless pull and common chat operations.
- `cccc-deferred-mail` makes the existing qualified Mail operations available through the direct CLI and defines how Mail notices coexist with chat delivery.
- `gateway-plugin-api` adds a host-rendered request presentation for ordinary events and a read-only readiness signal for supervised plugin schedulers.

## Impact

The provider changes live in the tracked CCCC receiver patch series and its provisioning and qualification tools. The Houmao changes affect the gateway SDK and host, `houmao-mgr` gateway launch options, the optional `houmao-cccc` distribution, and CCCC deployment and agent-facing documentation. Qualification exercises the pinned provider build, isolated gateway and CLI runs, and real-agent delivery and reply flows.
