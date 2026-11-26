# Proposal

## Why

Launch, execution-owner dispatch, and gateway setup each contain decisions that callers must coordinate across several modules. The Brooks Lint assessment also reproduced inconsistent cleanup, mailbox summaries, version diagnostics, and receipt validation on those boundaries.

## What Changes

- Give required runtime startup an explicit commit point and release resources owned by the failed attempt when publication fails. Report optional gateway auto-attach failures with the live agent identity.
- Return a typed launch result to the CLI and owner stdio adapters, including when delegated startup succeeds and optional gateway attachment fails. Share operation argument validation and read-only classification before owner setup.
- Consolidate repeated backend capability decisions, starting with gateway tracking-timing eligibility across attach and both gateway launch modes.
- Use one filesystem mailbox state update for message flags and unread thread summaries.
- Share TUI detector qualification and parser invocation across maintained observers using saved managed-launch evidence.
- Share durable Hermes TUI receipt validation across backend and owner recovery.
- Compose the maintained passive client from shared HTTP transport and supported operations. Keep its signed calls, response models, and wire contracts available to current consumers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `brain-launch-runtime` specifies cleanup for resources acquired by a failed required startup attempt.
- `agent-mailbox-fs-transport` specifies consistent mailbox-local flags and unread summaries after state mutation.
- `versioned-tui-signal-profiles` applies the existing version contract consistently across managed observation paths.
- `hermes-agent-runtime` specifies how incomplete durable receipts affect owner recovery.

## Impact

The changes focus on `src/houmao/agents/realm_controller/`, `src/houmao/execution/`, `src/houmao/mailbox/`, `src/houmao/shared_tui_tracking/`, and their manager, server, and gateway callers. The CLI, HTTP and stdio v1 payloads, authorization rules, and valid persisted formats are the compatibility baseline. The shared TUI observer work follows [retire-manual-agent-adoption](../retire-manual-agent-adoption/proposal.md). The remaining refactors can proceed independently within their respective boundaries.
