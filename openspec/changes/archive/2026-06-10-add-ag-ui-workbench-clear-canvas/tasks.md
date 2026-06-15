## 1. Agent Pane Clear Action

- [x] 1.1 Add a clear-canvas icon button to AG-UI workbench agent pane headers with a deterministic tooltip and test id.
- [x] 1.2 Implement the clear-canvas handler so it resets pane-local `PaneEventState` without clearing prompt text, target configuration, connection status, or active streams.
- [x] 1.3 For watched agent panes, call the watched-target clear path from the same handler so cached watched output and runtime display state are cleared immediately.
- [x] 1.4 Remove or align the existing watched-strip cache control so the pane exposes one user-facing clear-canvas concept.

## 2. Watched Target Cache Semantics

- [x] 2.1 Verify watched-target cache clearing removes IndexedDB cached events and resets in-memory reduced state while preserving the watcher controller and reconnect loop.
- [x] 2.2 Surface a deterministic pane error if client-side cache clearing fails, without disconnecting or changing agent lifecycle state.
- [x] 2.3 Ensure future AG-UI events after clear are cached and rendered from an empty display baseline.

## 3. Browser Coverage and Verification

- [x] 3.1 Add Playwright coverage showing an agent pane graphic disappears after Clear canvas and no detach or lifecycle request is sent.
- [x] 3.2 Add Playwright coverage showing watched-target graphics do not reappear after clear plus pane reopen or reconnect.
- [x] 3.3 Add Playwright coverage showing new events render normally after a clear.
- [x] 3.4 Run `bun run typecheck` and the relevant `bun run e2e` or focused Playwright tests for the workbench.
