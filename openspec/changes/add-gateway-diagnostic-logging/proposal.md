## Why

Gateway failures that occur before or around mailbox delivery can currently be hard to reconstruct after the fact. The existing `gateway.log` is useful for live tailing, but issue-style investigations need an opt-in, bounded diagnostic trail that captures HTTP validation errors, mailbox facade decisions, and repeated warning/error conditions without flooding disk or exposing message bodies by default.

## What Changes

- Add opt-in rotating gateway diagnostic log files under the gateway-owned log directory.
- Record compact diagnostic entries for gateway HTTP requests, validation failures, mailbox facade operations, queue/control failures, and notifier/reminder warnings or errors when diagnostic logging is enabled.
- Redact sensitive content by default: no mailbox message bodies, attachment contents, auth secrets, or raw prompt text in diagnostic log entries.
- Support consecutive warning/error deduplication so repeated equivalent diagnostics are summarized with suppressed counts instead of emitted endlessly.
- Keep the existing `gateway.log` as the stable human-oriented tail log; the new diagnostic logs are a bounded postmortem artifact rather than the primary status or queue contract.
- Document how operators enable, locate, inspect, rotate, and clean up diagnostic logs.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-gateway`: add opt-in rotating diagnostic logging with redaction and consecutive warning/error deduplication.
- `agent-gateway-reference-docs`: document the diagnostic logging contract, file layout, redaction boundary, and troubleshooting workflow.
- `houmao-mgr-cleanup-cli`: classify gateway diagnostic log files as cleanup-sensitive runtime log artifacts while preserving durable gateway state.

## Impact

- Affected code: `src/houmao/agents/realm_controller/gateway_service.py`, `gateway_storage.py`, and gateway model/config plumbing for opt-in settings.
- Affected code: gateway launch/attach paths that persist desired gateway configuration and start the live gateway process.
- Affected code: cleanup planning under `src/houmao/srv_ctrl/commands/runtime_cleanup.py`.
- Affected docs: gateway reference pages, system-files reference, and troubleshooting guidance.
- Affected tests: gateway runtime/support tests for opt-in logging, rotation, redaction, HTTP validation capture, mailbox error capture, and dedup summaries.
