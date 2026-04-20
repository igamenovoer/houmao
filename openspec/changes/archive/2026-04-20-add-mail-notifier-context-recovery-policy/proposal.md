## Why

Recent Codex compaction failures show that recoverable degraded chat context is not one uniform condition: sometimes continuing in the current thread is the right default, while unattended mail-driven work may benefit from an explicit pre-notification compaction or an operator-selected clear-context fallback. Houmao needs policy-controlled recovery that preserves the current safe default while surfacing enough structured diagnostics for operators and automation to choose a different behavior deliberately.

## What Changes

- Add explicit gateway mail-notifier context policies:
  - a default `continue_current` compaction-error policy that preserves current behavior,
  - an opt-in `clear_context` compaction-error policy that starts the next notifier prompt from clean context after a recognized degraded compaction error,
  - a default `none` pre-notification context action,
  - an opt-in `compact` pre-notification context action that runs a tool-supported compaction step before delivering a mail-notifier prompt.
- Extend degraded chat-context reporting with structured diagnostic metadata that can identify the owning CLI tool and a tool-scoped degraded error type.
- Require degraded error type labels to be namespaced by the CLI tool profile, except for a shared `unknown` fallback. For example, Codex-specific compaction labels must not become shared labels for Claude, Gemini, or other tools unless those tools explicitly define their own profile-local mapping.
- Preserve the existing default gateway and notifier behavior: degraded context remains current-context eligible unless an explicit caller-configured policy requests clean-context recovery.
- Record notifier audit evidence for context preflight, degraded diagnostics, policy decisions, and recovery failures without mutating mailbox read/archive/answered state.
- Document backend support boundaries so unsupported pre-notification compaction requests fail explicitly instead of pretending every CLI tool supports the same compaction command.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: add notifier context policies, pre-notification compaction, policy-driven clear-context recovery, status/audit behavior, and unsupported-backend rejection rules.
- `agent-gateway`: preserve explicit clean-context prompt control while allowing notifier-owned policy to request the same clean-context behavior deliberately.
- `codex-tui-state-tracking`: expose Codex-specific degraded compaction diagnostics with tool-scoped error type labels derived from bounded prompt-adjacent error surfaces.
- `official-tui-state-tracking`: define the cross-profile diagnostic contract so tools can publish degraded context metadata without sharing tool-specific error labels.

## Impact

- Affected runtime code includes Codex TUI signal classification, shared tracked-state models, gateway status/proxy models, gateway mail-notifier storage/status/audit state, notifier polling, and prompt-control reset/selector paths.
- Affected CLI/API surfaces include `PUT|GET /v1/mail-notifier`, server-managed gateway mail-notifier proxy routes, and `houmao-mgr agents gateway mail-notifier enable|status` output/help.
- Documentation updates are needed for gateway mail-notifier behavior, gateway protocol/state contracts, and TUI degraded-context diagnostics.
- No external dependency or mailbox storage migration is required, but gateway-owned notifier SQLite schema/state needs forward-compatible fields for the new policies and audit metadata.
