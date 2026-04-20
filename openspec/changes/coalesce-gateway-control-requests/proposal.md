## Why

Gateway-delivered control commands can accumulate as durable queued work even when only the newest control intent remains meaningful. This causes stale `/compact`, `/clear`, `/new`, and `interrupt` requests to execute one by one, which is noisy at best and can be semantically wrong when later context-control commands supersede earlier pending ones.

## What Changes

- Add gateway-owned coalescing for adjacent accepted control-intent queue records before they execute.
- Classify only recognized control intents as coalescible:
  - queued `interrupt` requests,
  - queued `submit_prompt` requests whose entire trimmed prompt is a recognized context-control command such as `/compact`, `/clear`, or `/new`.
- Preserve ordinary prompt order and content by treating all non-control prompts as hard coalescing boundaries.
- Preserve internal notifier prompt behavior by excluding `mail_notifier_prompt` records from coalescing.
- Record durable audit evidence for requests removed from execution by coalescing.
- Expose coalescing behavior through gateway events and queue state so operators can inspect what happened.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: Gateway queue policy gains explicit coalescing semantics for adjacent accepted special control requests while preserving ordinary prompt sequencing.

## Impact

- Affected runtime: `GatewayServiceRuntime` durable queue admission/dequeue behavior.
- Affected storage: `queue.sqlite` request state and result metadata for coalesced records.
- Affected events/logs: gateway events should include explicit coalescing records.
- Affected docs/specs: gateway protocol and queue-recovery documentation should describe control-intent coalescing and guardrails.
- Affected tests: gateway unit tests should cover duplicate interrupts, context-command supersession, mixed interrupt/context runs, ordinary prompt boundaries, notifier exclusion, epoch boundaries, and audit evidence.
