## 1. Tracker Boundary Cleanup

- [x] 1.1 Replace tracker-facing Codex app-family naming from `codex_app_server` to `codex_tui` in the shared tracking registry, `app_id_from_tool()` mapping, detector identity, and tracker-facing docs/tests, while leaving runtime/backend identifiers such as `BackendKind = "codex_app_server"` unchanged.
- [x] 1.2 Keep Codex headless/backend identifiers, runtime schemas, and backend modules outside the shared tracked-TUI app-family registry, and update tracker-facing selection helpers so only the interactive raw-snapshot path resolves to `codex_tui`.

## 2. Shared Profile And Engine Support

- [x] 2.1 Refactor the shared tracked-TUI detector boundary so shared modules define contracts/helpers only, move app-specific logic into `shared_tui_tracking/apps/<app_id>/` modules, and extract the existing `CodexTrackedTurnSignalDetector` into `apps/codex_tui/` seed modules rather than duplicating it.
- [x] 2.2 Extend the shared tracker/profile contract so a profile provides single-snapshot analysis plus a separate temporal-hint callback over recent ordered profile frames, while preserving the public tracker-session API (`on_snapshot`, `on_input_submitted`, `current_state`, `drain_events`).
- [x] 2.3 Implement shared engine support for a session-owned, injected-scheduler-driven sliding recent-frame window and an explicit merge/gating step that combines single-snapshot `DetectedTurnSignals` with separate temporal hints before reduction, including success guards that depend on prior armed turn authority.

## 3. Codex TUI Profile Implementation

- [x] 3.1 Create a `codex_tui` app-owned module structure for single-snapshot Codex TUI signal families such as activity rows/tool cells, blocking overlays, exact interruption, generic error cells, steer handoff, and ready composer posture.
- [x] 3.2 Implement Codex TUI temporal inference on top of the shared temporal-hint support from 2.2-2.3, using a sliding recent-snapshot window so active answering can still be inferred when the visible running row disappears during streaming.
- [x] 3.3 Implement Codex TUI success settlement rules by removing the current `Worked for ...` success gate, treating that separator as supporting evidence only, and requiring prior armed turn authority from either `explicit_input` or `surface_inference` before ready-return success can settle; overlays/current errors/exact interruption must still block success and initial idle ready posture must not settle success.
- [x] 3.4 Add focused Codex TUI tests for active detection, overlay degradation, exact interruption, steer handoff, generic error-cell blocking, sparse-window degradation, stable ready-return success, and initial-idle non-success; verify temporal behavior through `TuiTrackerSession` + `TestScheduler`, and migrate the existing `codex_app_server`-named tracker test to `codex_tui`.

## 4. Live Adapter And Documentation

- [x] 4.1 Update the official live TUI tracking adapter to resolve interactive Codex tracking through `codex_tui` only, preserve ordered raw snapshots for Codex temporal inference, and leave runtime/backend names unchanged outside tracker-facing resolution.
- [x] 4.2 Verify that structured headless Codex control paths are not routed through the shared tracked-TUI subsystem by default, and keep snapshot-only replay/live flows compatible with success settlement that relies on surface-inferred turn authority.
- [x] 4.3 Update tracker-facing docs/spec references to describe `codex_tui` as the interactive tracked-TUI family, document v1 as one `codex_tui` profile with profile-private latest-turn signatures, and clarify that headless Codex contracts remain outside TUI-tracking scope.
