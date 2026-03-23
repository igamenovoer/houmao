## Why

Tailmux currently uses a hand-crafted tab strip and a single-active-pane frontend model, which prevents users from freely reordering terminal tabs and tightly couples terminal session lifecycle to custom DOM state. We want to replace that browser-level tab management with a Dockview-based workspace so users can arrange tabs more naturally without taking on multi-view split behavior yet.

## What Changes

- Introduce a Bun-managed frontend bundle for Dockview, xterm, and the xterm fit addon while keeping Tailmux framework-free and Node-hosted.
- Replace Tailmux's custom browser tab strip with a Dockview-managed terminal workspace.
- Add drag-and-drop tab reordering with single-group enforcement in this phase; if a drop would create another visible group, Tailmux will block that path when supported by the pinned Dockview version or normalize immediately back to one visible group.
- Persist versioned browser workspace state so restorable tmux-backed tabs recover in order after reload.
- Add a user-visible reset-layout action that clears persisted workspace state.
- Surface skipped non-restorable shell tabs after reload with a single summary notification.
- Refactor header actions, dashboard actions, and mobile controls to target the Dockview active terminal session instead of the current `activeTabId` / custom tab button model, and relocate tmux tab actions into a persistent external toolbar.
- Keep tmux pane splitting inside terminal sessions unchanged.
- Explicitly defer 2-view / 4-view split layouts, floating groups, and other multi-panel layout features to later work.

## Capabilities

### New Capabilities

- `tailmux-rearrangeable-terminal-tabs`: Tailmux browser sessions expose a workspace that lets users reorder, activate, close, and restore terminal tabs independently of the underlying session transport.

### Modified Capabilities

- None.

## Impact

- Affected code: `extern/tracked/tailmux/public/index.html`, `extern/tracked/tailmux/public/app.js`, and `extern/tracked/tailmux/public/styles.css`.
- Dependencies: add Dockview frontend dependency and Bun-managed frontend build/runtime wiring for Dockview, xterm, and the fit addon.
- Systems: browser-side session state management, workspace layout persistence, dashboard tab navigation, and mobile/header actions.
- API surface: no backend HTTP or WebSocket contract changes are expected for this phase.
