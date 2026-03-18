## Why

Tailmux now uses Dockview for browser tabs, but the current workspace intentionally collapses everything back into a single visible group. That prevents the main benefit users expect from a docking workspace: dragging terminal tabs into side-by-side panes so multiple sessions stay visible at once.

## What Changes

- Allow Dockview to create multiple visible workspace groups from terminal tab drag and drop.
- Support vertical and horizontal split layouts so users can place terminal tabs side by side or stacked.
- Allow tabs to move between groups while preserving the existing live terminal session, terminal buffer, and reconnect state.
- Update workspace focus, toolbar targeting, and resize behavior so actions follow the actively focused visible pane rather than assuming a single visible terminal.
- Keep the dashboard as a flat session list for this phase and rely on Dockview drag-and-drop as the split-creation interaction in this release.
- Persist and restore multi-group Dockview layouts for restorable tmux-backed tabs, using the Dockview layout tree as the primary arrangement model while continuing to skip non-restorable shell tabs on reload.
- Keep floating groups, pop-out windows, and duplicate views of the same terminal session out of scope for this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `tailmux-rearrangeable-terminal-tabs`: expand the Dockview workspace from a single visible group to multi-group split layouts, including focus, restore, and action-routing behavior when multiple terminal panes are visible.

## Impact

- Affected code: `extern/tracked/tailmux/public/app.js`, `extern/tracked/tailmux/public/index.html`, `extern/tracked/tailmux/public/styles.css`, `extern/tracked/tailmux/README.md`, `extern/tracked/tailmux/TODO.md`
- Dependencies: existing Dockview integration in the Tailmux frontend bundle
- Systems: browser-side workspace persistence/versioning, xterm fitting/resizing, active-session routing for tmux and keyboard controls
