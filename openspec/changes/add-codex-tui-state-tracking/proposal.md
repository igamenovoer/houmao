## Why

The standalone tracker currently leaks Codex backend naming into the TUI-tracking boundary and does not cleanly separate interactive screen-scraped Codex TUI tracking from Codex headless control modes. That makes the design harder to reason about and pushes Codex-specific lifecycle logic into the wrong abstraction.

Codex interactive TUI tracking also needs time-aware inference across recent snapshots, because snapshot cadence is external to the tracker and cannot be assumed to be stable enough for simple adjacent-snapshot heuristics. We need a Codex TUI design that stays inside the shared Rx tracker architecture without mixing in upstream headless contracts that do not require TUI scraping at all.

## What Changes

- Add a dedicated `codex_tui` tracked-TUI capability for the standalone tracker, scoped only to interactive Codex TUI snapshots captured from tmux-like surfaces.
- Separate tracker app-family naming from runtime backend naming so tracker-facing identities move to `codex_tui` while runtime/backend names such as `codex_app_server` remain unchanged outside the tracked-TUI boundary.
- Extend the shared tracker/profile architecture so a TUI profile can combine single-snapshot signal detection with a separate temporal-hint callback over a sliding time window of recent profile frames, with the shared engine performing the merge/gating step before reduction.
- Define Codex TUI signal families for active work, blocking overlays, exact interruption, steer-resubmission handoff, generic error-cell success blocking, and stable ready-return success.
- Extract the existing Codex tracked-turn detector logic into app-owned `codex_tui` modules as seed logic rather than duplicating it under a second tracker identity.
- Update the official live tracking path and related docs/specs to resolve Codex TUI tracking through `codex_tui` rather than the current backend-leaking `codex_app_server` label, while preserving snapshot-only replay/live flows that rely on surface-inferred turn authority.

## Capabilities

### New Capabilities
- `codex-tui-state-tracking`: define the interactive Codex TUI signal and temporal-tracking contract for the standalone shared tracker.

### Modified Capabilities
- `shared-tui-tracking-core`: clarify that the shared tracker is for screen-scraped interactive TUIs and allow profile-owned temporal hint streams over sliding windows of recent snapshots.
- `versioned-tui-signal-profiles`: revise the profile contract so tracker app families are TUI-surface contracts rather than runtime backend names and so profiles may contribute temporal inference logic in addition to single-snapshot matching.
- `official-tui-state-tracking`: update the official live tracking contract so Codex TUI sessions resolve through `codex_tui` at the tracker boundary and keep headless Codex modes out of TUI-tracking scope.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/*`, `src/houmao/server/tui/tracking.py`, and associated tests/docs.
- Affected docs/specs: shared tracker docs, official TUI tracking docs, and detector/profile reference material.
- Architectural impact: clarifies the standalone tracker boundary around interactive TUI surfaces only and keeps upstream headless Codex contracts outside the screen-scraping subsystem.
