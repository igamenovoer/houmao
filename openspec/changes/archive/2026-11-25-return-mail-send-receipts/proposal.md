# Proposal

## Why

In the R12 mail round, Kimi repeated a successful `mail send` with `--print-json` because text output hid the reference. Both commands delivered a message. Other manager commands also hide confirmation fields, echo entire records, or can fail while formatting a successful action. [Issue #96](https://github.com/igamenovoer/houmao/issues/96)

## What Changes

- **BREAKING** Scoped `mail send`, `reply`, and `post` return compact receipts. JSON consumers migrate from `message.message_ref` to top-level `message_ref`. Each verified receipt identifies the mailbox binding that owns the reference and the actual sender and recipients.
- Preserve the available evidence for TUI-mediated sends and replies. Submission-only receipts identify the request and direct callers to read-only reconciliation.
- Show gateway prompt admission, handoff status, and available operation and native IDs in every output mode.
- **BREAKING** `memory memo set` and `append` return a receipt with the memo path. `memo show` returns the contents.
- **BREAKING** `gateway reminders set` returns a receipt from the update response. `reminders get` and `list` provide detailed inspection.
- Serialize the `open-browser` result as a short outcome in plain, fancy, and JSON output.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-native-cli` defines the result contracts for the affected commands and their read-only follow-ups.
- `agent-gateway` describes the queue and handoff outcomes the existing direct prompt endpoint can return.
- `houmao-agent-email-comms-skill` teaches agents to confirm mail writes from their receipts and inspect the correct binding.
- `houmao-agent-messaging-skill` teaches agents to distinguish prompt admission from handoff and observe an existing submission.
- `houmao-memory-mgr-skill` teaches agents to confirm memo writes from receipts and read contents through `memo show`.

## Impact

The change updates manager command results, packaged agent guidance, and command references. Repository consumers of the affected CLI JSON outputs migrate to the receipts and use the corresponding read commands for details. Gateway and pair APIs continue to return their existing result models.
