# Proposal

## Why

An agent can yield its turn and receive the next CCCC notification when it becomes ready. An agent that stays active to collect replies also needs a way to inspect and consume chat staged by its gateway.

## What Changes

- Expose gateway-backed `houmao-cccc chat peek` and `chat pop` commands for the selected CCCC plugin instance. Peek shows the next eligible batch and can wait for more staged chat within a finite deadline.
- Let the agent choose when to pop. The gateway selects a bounded FIFO prefix of whole queued batches and delivers it as one tool result with the existing compact message fields and per-message reply handles.
- Give pop and automatic notification one claim on queued messages. The gateway continues ordinary notification when the agent yields and is ready for another prompt.
- Record the selected attempts in CCCC before returning a pop result. Support operation-ID reconciliation and exact read acknowledgment so a lost response cannot consume a different batch.
- Advertise gateway queue access through receiver capability negotiation. Qualify both delivery choices with the same managed agent.

## Capabilities

### New Capabilities

None. The existing chat and receiver capabilities own this behavior.

### Modified Capabilities

- `cccc-chat` adds per-instance peek, a bounded wait, and tool-driven batch pop alongside ordinary prompt delivery.
- `cccc-external-receiver` adds durable tool-read claims on a current gateway lease, with exact membership, reconciliation, and acknowledgment.

## Impact

The change affects the CCCC gateway plugin, the `houmao-cccc` CLI, and the tracked CCCC external receiver patch. It adds gateway routes under the selected CCCC plugin namespace and corresponding authorization actions. Agent instructions and qualification cover yielding for a notification and actively collecting replies through the gateway.
