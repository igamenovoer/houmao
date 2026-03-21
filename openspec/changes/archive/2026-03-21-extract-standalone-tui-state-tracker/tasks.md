## 1. Standalone Tracker Contracts

- [x] 1.1 Define a thread-safe standalone tracked-TUI session API, configuration models, tracker-owned state outputs, transition-event models, and scheduler-injection seam.
- [x] 1.2 Replace replay-shaped shared tracker inputs with raw snapshot and explicit-input event interfaces, and specify that parsed-surface context and host diagnostics remain outside the public tracker boundary.

## 2. Reactive Tracker Engine

- [x] 2.1 Implement the standalone Rx tracker session that owns internal state transitions, current-state caching, and transition-event emission.
- [x] 2.2 Move settle-window and other timer-driven behavior onto injected schedulers with deterministic virtual-time coverage.

## 3. App Plugins And Versioned Signal Profiles

- [x] 3.1 Introduce the shared app plugin registry, replace public tool-string selection, and define exact-match or closest-compatible semver-floor profile resolution for supported TUI apps.
- [x] 3.2 Rewrite Claude Code and Codex signal detection into raw-text-driven profile-owned detector suites that emit normalized tracker signals while keeping matched-signal evidence on internal/debug surfaces.

## 4. Host Adapter Migration

- [x] 4.1 Adapt `houmao-server` live tracking to feed raw snapshots and explicit input events into the standalone tracker while keeping tmux/process/parse diagnostics, lifecycle readiness/completion, visible stability, and public response assembly outside the tracker.
- [x] 4.2 Adapt `replay_timeline()` and `terminal_record` analysis/replay paths to drive the same tracker through injected virtual schedulers from raw snapshot streams.
- [x] 4.3 Adapt `explore/claude_code_state_tracking` compatibility wrappers and interactive-watch paths to the new standalone session API.

## 5. Verification And Cleanup

- [x] 5.1 Add unit coverage for the standalone session API, thread-safety expectations, scheduler-driven timing behavior, raw-text profile detection over direct tmux-captured pane text fixtures, profile resolution, and compatibility wrappers.
- [x] 5.2 Remove obsolete replay-shaped tracker seams and update maintainer-facing docs and references for the new standalone architecture.
