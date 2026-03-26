## 1. Build the libtmux-backed tmux integration layer

- [x] 1.1 Introduce a repo-owned libtmux-first tmux integration module or wrapper layer for session, window, and pane discovery plus object-bound command fallback.
- [x] 1.2 Add unit coverage for session-wide pane enumeration, explicit pane/window lookup, and fallback format queries such as pane-dead inspection.

## 2. Migrate gateway tmux lifecycle resolution

- [x] 2.1 Replace the runtime-owned foreground gateway pane lookup and liveness helpers with the libtmux-backed session-wide resolver.
- [x] 2.2 Add regression tests proving foreground gateway liveness does not fail when the agent window is current and the gateway pane lives in an auxiliary window.

## 3. Migrate tracked-TUI target resolution

- [x] 3.1 Update tracked-TUI transport resolution and the affected identity producers to prefer explicit pane/window identity over current-focus heuristics for multi-window sessions.
- [x] 3.2 Add tests covering multi-window tracked sessions, including the local-interactive plus auxiliary-gateway case and ambiguous-target diagnostics.

## 4. Migrate recorder and duplicate tmux helpers

- [x] 4.1 Update terminal recorder target resolution to use full-session pane lookup through the libtmux-backed layer.
- [x] 4.2 Replace the known duplicate raw tmux helpers in explore/demo paths with the libtmux-backed resolver or object-bound fallback commands.
- [x] 4.3 Add regression coverage for explicit pane targeting and pane capture when the intended pane lives outside the current tmux window.

## 5. Verify the migration and document behavior

- [x] 5.1 Run targeted unit and integration coverage for the tmux integration layer, gateway lifecycle, tracked-TUI resolution, and terminal recorder targeting.
- [x] 5.2 Re-run the live foreground gateway repro and confirm gateway prompt delivery remains healthy while the agent window stays current.
