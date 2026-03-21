## Why

TUI state tracking is a critical subsystem, but the current implementation is split across a replay-shaped shared reducer, server-owned live tracking logic, and tool-specific wrappers. That makes the tracker harder to maintain, harder to test in isolation, and too tightly coupled to `houmao-server` and Claude-first assumptions.

We now want a general standalone tracker boundary that can be reused by live server tracking, replay tools, and future TUI hosts without inheriting tmux-, recorder-, or server-specific contracts.

## What Changes

- Extract the shared tracked-TUI logic into a standalone reactive tracker session that consumes raw TUI snapshot strings, including externally captured direct tmux pane text, plus explicit input-authority events and derives app-specific signals from raw text inside versioned profiles.
- Replace caller-managed timestamp reduction with internally owned Rx timing, while allowing hosts to inject either realtime or virtual schedulers for live use, replay, and deterministic tests.
- Introduce a unified app plugin contract so Claude Code, Codex, and future TUI apps use the same tracker/session interface while keeping app-specific signal detection separate.
- Introduce versioned signal profiles so supported TUI apps can resolve different detector suites by observed version through explicit closest-compatible semver-floor matching without changing the shared state machine.
- Adapt `houmao-server` live tracking to use the standalone tracker as a host adapter while keeping diagnostics, lifecycle readiness/completion, and effective visible stability under server ownership.
- **BREAKING**: reshape the current `shared_tui_tracking` internals and public adapter seams away from replay-specific observation models and tool-string dispatch.

## Capabilities

### New Capabilities
- `versioned-tui-signal-profiles`: unify app-specific and version-specific TUI signal detector selection behind one shared plugin/profile contract.

### Modified Capabilities
- `shared-tui-tracking-core`: change the shared core from a replay-shaped reducer over timestamped observations into a thread-safe standalone reactive tracker session over raw TUI snapshots and injected scheduler time.
- `official-tui-state-tracking`: change server live tracking to adapt probe/parser/runtime observations into the standalone tracker boundary while keeping server-owned diagnostics, lifecycle readiness/completion, visible stability, identity, and in-memory authority outside the tracker.

## Impact

- Affected code: `src/houmao/shared_tui_tracking/`, `src/houmao/server/tui/`, `src/houmao/terminal_record/`, `src/houmao/explore/claude_code_state_tracking/`, and related unit tests.
- Affected APIs: internal tracker/session APIs, detector registration/selection APIs, and server-to-tracker adapter seams.
- Affected systems: live TUI tracking in `houmao-server`, offline replay, interactive watch tooling, and future non-tmux TUI hosts.
