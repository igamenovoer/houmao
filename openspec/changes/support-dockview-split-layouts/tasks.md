## 1. Workspace Layout Behavior

- [ ] 1.1 Remove the Tailmux-specific single-group Dockview restrictions so edge docking can create horizontal and vertical split groups while floating and pop-out behavior remain disabled.
- [ ] 1.2 Update tab add, move, and close flows to preserve valid multi-group layouts instead of collapsing everything back into one visible group.
- [ ] 1.3 Update workspace-derived ordering and dashboard/session enumeration helpers so they work correctly when panels live in multiple visible groups.

## 2. Active Pane And Interaction Routing

- [ ] 2.1 Change active-session routing so the focused Dockview panel becomes the workspace action target even when multiple panes are visible.
- [ ] 2.2 Forward interaction inside terminal content back to the owning Dockview panel so toolbar, keyboard, and tmux actions follow the pane the user is actually using.
- [ ] 2.3 Add visible focused-pane styling and workspace summary updates so users can tell which pane owns global actions.

## 3. Resize, Persistence, And Restore

- [ ] 3.1 Update resize and fit handling so visible panels are re-fit after split creation, divider moves, visibility changes, and window resize events.
- [ ] 3.2 Bump the persisted workspace state version and save split-aware Dockview layout state as the primary arrangement model.
- [ ] 3.3 Restore tmux-backed sessions into their saved multi-group layout using filtered Dockview JSON and the previously focused restorable session when available.
- [ ] 3.4 Keep skipped shell-tab notifications and reset-layout behavior correct for split layouts and version-mismatched saved state.

## 4. Documentation

- [ ] 4.1 Update Tailmux documentation to describe split layouts, current limitations, and the desktop-first interaction model.
- [ ] 4.2 Revise Tailmux TODO tracking so split layouts and multi-group support move from future ideas into the implemented Dockview workspace plan.

## 5. Verification

- [ ] 5.1 Verify users can create both horizontal and vertical splits, reorder tabs within groups, and move tabs between groups without reconnecting the session.
- [ ] 5.2 Verify active-session actions follow the focused visible pane across toolbar actions, tmux actions, and dashboard activation.
- [ ] 5.3 Verify tmux-backed split layouts restore after reload while shell tabs are skipped with one summary notification.
- [ ] 5.4 Verify reset-layout clears persisted split workspace state and reopens the default non-restored workspace.
