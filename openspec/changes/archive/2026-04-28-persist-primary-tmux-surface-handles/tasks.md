## 1. Manifest And State Model

- [x] 1.1 Extend headless/local-interactive runtime state to carry optional primary `tmux_window_id` and `tmux_pane_id`.
- [x] 1.2 Extend session manifest boundary models and JSON schemas with optional primary tmux object-handle fields while preserving `primary_window_index = "0"`.
- [x] 1.3 Update manifest build/load/resume paths to read, validate, and persist primary tmux handles without rejecting older manifests that omit them.
- [x] 1.4 Decide whether shared registry records expose primary tmux handles or keep them manifest-local, then update registry payloads only if needed.

## 2. Primary Surface Tmux Primitives

- [x] 2.1 Add a structured primary-surface record for session name, window id, window index, window name, pane id, and pane index.
- [x] 2.2 Update primary-surface preparation to discover the bootstrap window/pane by live tmux identity, move the window to index `0` when needed, rename/select by window id, and return the resolved handles.
- [x] 2.3 Add validation helpers that confirm persisted handles still exist in the expected session and belong to primary window index `0`.
- [x] 2.4 Add stale-handle recovery helpers that re-resolve a single actionable primary surface from window index `0` and refresh handles when possible.
- [x] 2.5 Ensure primary-surface preparation fails closed when a fresh Houmao-owned session has unexpected extra windows or cannot establish window index `0`.

## 3. Launch And Join Integration

- [x] 3.1 Store primary tmux handles during new headless backend session creation.
- [x] 3.2 Store primary tmux handles during local interactive backend launch.
- [x] 3.3 Update `houmao-mgr agents launch` publication flow so active registry metadata is published only after primary-surface preparation and handle capture succeed.
- [x] 3.4 Update TUI and headless join flows to persist handles for the existing window `0`, pane `0` surface without moving or renaming operator-owned tmux surfaces.
- [x] 3.5 Keep join failure behavior explicit when window `0`, pane `0` is missing or provider authority is inconsistent.

## 4. Runtime Operation Routing

- [x] 4.1 Route headless turn launch, interrupt, terminate, and server fallback interruption through the persisted primary pane id when valid.
- [x] 4.2 Route local interactive prompt submission, capture, interrupt, process inspection, and readiness polling through the validated primary pane id.
- [x] 4.3 Update relaunch and resume paths to refresh stale primary handles before using the tmux surface.
- [x] 4.4 Update tmux-backed authority health checks to distinguish missing session, missing primary window, missing primary pane, stale handles, and healthy primary handle state.
- [x] 4.5 Ensure gateway attach/status behavior continues to reject auxiliary gateway window index `0` while remaining compatible with primary agent handles.

## 5. Tests And Verification

- [x] 5.1 Add tmux runtime unit coverage for preparing a primary surface when new sessions start at window index `1`.
- [x] 5.2 Add tmux runtime unit coverage for pane-base-index handling and operation targeting by `%pane_id`.
- [x] 5.3 Add manifest/schema tests for optional primary `tmux_window_id` and `tmux_pane_id` persistence and older-manifest compatibility.
- [x] 5.4 Add launch integration or high-level unit coverage for `base-index 1` and `pane-base-index 1` launch success without active registry publication on preparation failure.
- [x] 5.5 Add join tests proving handles are persisted for window `0`, pane `0` and that join does not rearrange operator-owned tmux layouts.
- [x] 5.6 Add stale-handle recovery tests for valid refresh, missing primary window, ambiguous primary surface, and no-current-focus fallback.
- [x] 5.7 Run `pixi run test` and targeted runtime/tmux test suites, then record any remaining verification gaps.
