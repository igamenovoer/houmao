## 1. Workspace Layout Behavior

- [ ] 1.1 Remove the live single-group Dockview restrictions in `initializeWorkspace` by eliminating `ensureSingleVisibleGroup()` from `onDidMovePanel` and `onDidLayoutChange`, and by explicitly updating or removing `isAllowedDropEvent`, `onWillShowOverlay`, and `onWillDrop` so edge docking can create horizontal and vertical split groups while floating and pop-out behavior remain disabled.
- [ ] 1.2 Update tab add, move, and close flows to preserve valid multi-group layouts instead of collapsing everything back into one visible group.
- [ ] 1.3 Define a stable flattened session enumeration derived from the Dockview layout tree for dashboard display and fallback activation, while keeping Dockview JSON as the source of layout truth.

## 2. Active Pane And Interaction Routing

- [ ] 2.1 Change active-session routing so the focused Dockview panel becomes the workspace action target even when multiple panes are visible.
- [ ] 2.2 Require terminal-content focus to activate the owning Dockview panel, using xterm focus events or an equivalent terminal DOM focus path, so toolbar, keyboard, and tmux actions follow the pane the user is actually using.
- [ ] 2.3 Add an unmistakable focused-pane signal on the visible panel content area, plus workspace summary updates, so users can tell which pane owns global actions.

## 3. Resize, Persistence, And Restore

- [ ] 3.1 Make container-level size changes call `workspace.layout()` and keep per-panel fitting in the terminal component `layout()` hook, covering browser resize plus keyboard and tmux panel toggles and verifying that manual visible-panel iteration is unnecessary.
- [ ] 3.2 Bump the persisted workspace payload version, keep the existing storage key unless implementation exposes a concrete migration issue, and save split-aware Dockview layout state as the primary arrangement model.
- [ ] 3.3 Restore tmux-backed sessions into their saved multi-group layout using filtered Dockview JSON, remove restore-path single-group normalization from `onDidLayoutFromJSON` and `restoreWorkspaceState`, and reactivate the previously focused restorable session when available.
- [ ] 3.4 Keep skipped shell-tab notifications and reset-layout behavior correct for split layouts and version-mismatched saved state.

## 4. Documentation

- [ ] 4.1 Update Tailmux documentation to describe drag-and-drop split creation, flat dashboard behavior, current limitations, and the desktop-first interaction model.
- [ ] 4.2 Revise Tailmux TODO tracking so implemented split-layout and multi-group items move out of `Future Layout Ideas`, leaving only still-deferred ideas such as floating/pop-out layouts, richer saved workspaces, and mobile-specific enhancements.

## 5. Verification

- [ ] 5.1 Verify users can create both horizontal and vertical splits, reorder tabs within groups, move tabs between groups, and drag the last tab out of a group without leaving an empty visible group or reconnecting the session.
- [ ] 5.2 Verify terminal-content focus and toolbar, tmux, and dashboard actions all follow the focused visible pane, while the dashboard remains a flat session list.
- [ ] 5.3 Verify tmux-backed split layouts restore after reload without group collapse, while shell tabs are skipped with one summary notification.
- [ ] 5.4 Verify reset-layout clears persisted split workspace state and reopens the default non-restored workspace.
