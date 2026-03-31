## Why

Mailbox association and mailbox actionability are currently described through too many overlapping surfaces: the session manifest, registry copies, `AGENTSYS_MAILBOX_*` launch env, tmux-published live mailbox env, and transport-owned state such as filesystem paths or session-local Stalwart credential files. That makes it unclear which layer is authoritative and forces mailbox behavior, status, and docs to reason about a mailbox-specific env projection that is no longer needed.

This change simplifies the contract by making the manifest-backed mailbox binding the single durable authority for a managed session and by removing mailbox-specific `AGENTSYS_*` env publication as a mailbox runtime requirement.

## What Changes

- **BREAKING** Remove mailbox-specific `AGENTSYS_MAILBOX_*` runtime env publication from managed-session mailbox behavior and stop treating tmux mailbox env as live mailbox authority.
- Make the persisted session mailbox binding the only authoritative mailbox association record for a managed session, with resolver output and transport-local prerequisites derived from that binding.
- Update `houmao-mgr agents mail resolve-live` to be the supported structured discovery surface for current mailbox work without requiring mailbox shell exports.
- Simplify managed-agent mailbox activation semantics so late mailbox registration and mailbox status no longer rely on `pending_relaunch` or tmux mailbox projection refresh.
- Update gateway notifier readiness to validate actionable mailbox state from the manifest-backed binding and transport-local checks instead of tmux mailbox env.
- Update mailbox and CLI reference docs to describe the manifest-first, resolver-first mailbox contract and remove mailbox-env-specific operator guidance.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `brain-launch-runtime`: mailbox binding authority moves to persisted session state and mailbox-specific tmux env publication is removed from the runtime contract.
- `agent-mailbox-fs-transport`: filesystem mailbox root resolution and active-registration path rules stop depending on mailbox env publication.
- `agent-mailbox-system-skills`: projected mailbox skills discover current mailbox state through structured `houmao-mgr agents mail resolve-live` output rather than mailbox env bindings.
- `managed-agent-mailbox-registration`: mailbox activation and status semantics no longer depend on live tmux mailbox projection or `pending_relaunch`.
- `agent-gateway-mail-notifier`: notifier readiness derives actionable mailbox state from the durable mailbox binding plus transport validation instead of tmux mailbox env projection.
- `mailbox-reference-docs`: mailbox docs describe resolver-first discovery and remove mailbox-env-specific operator guidance.
- `docs-cli-reference`: CLI reference documents the updated `agents mail resolve-live` contract without mailbox shell export guidance.

## Impact

- Affected code includes mailbox runtime helpers, session launch-plan assembly, managed-agent mailbox status/reporting, gateway notifier readiness, mailbox system skills, and `houmao-mgr agents mail` output shaping.
- Affected operator/documentation surfaces include mailbox contract docs, mailbox operations docs, and CLI reference coverage for `agents mail resolve-live`.
- Existing tests that assert mailbox env bindings, tmux mailbox projection refresh, or shell-export output will need to be replaced with manifest-backed and resolver-backed assertions.
