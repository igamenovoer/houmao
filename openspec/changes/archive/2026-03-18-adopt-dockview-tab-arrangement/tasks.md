## 1. Frontend foundation

- [x] 1.1 Add a Bun-driven ESM frontend entry point and build output under `public/build/` so Tailmux can serve bundled browser assets without introducing a framework migration.
- [x] 1.2 Move Dockview, xterm, and the xterm fit addon into the same bundled frontend dependency graph and replace the existing CDN-global frontend loading path.
- [x] 1.3 Replace the custom browser tab-strip markup with a Dockview workspace container while relocating tmux tab actions into a persistent external toolbar and preserving the existing header, dashboard, and mobile control shells.
- [x] 1.4 Define the frontend workspace/session state boundary and the versioned persistence payload shape for the new Dockview-based tab manager.

## 2. Session registry refactor

- [x] 2.1 Refactor the current `tabs` state into a terminal session registry that owns session identity, xterm lifecycle, socket lifecycle, reconnect state, and restore metadata.
- [x] 2.2 Implement the stable session-owned terminal host/root invariant so Dockview panels attach existing terminal roots instead of recreating terminal DOM or transport on panel mount.
- [x] 2.3 Remove direct UI dependence on `activeTabId` and derive active-session state from Dockview active-panel events instead.
- [x] 2.4 Preserve existing close, reconnect, scroll, and status-update behavior against session records that are no longer tied to custom tab DOM.

## 3. Dockview workspace integration

- [x] 3.1 Initialize Dockview with a custom terminal panel component and custom tab renderer that exposes title, connection status, and close behavior.
- [x] 3.2 Create one Dockview panel per terminal session and wire panel add, activate, move, and close events to the session registry.
- [x] 3.3 Constrain drag/drop behavior so users can freely reorder tabs while the workspace remains a single visible group in this phase, using pre-drop blocking when supported by the pinned Dockview version and otherwise normalizing immediately after drop.
- [x] 3.4 Ensure tab activation and movement refit/focus xterm terminals from Dockview activation and panel-dimension events without recreating or reconnecting sessions purely because of workspace changes.

## 4. Action routing and restore behavior

- [x] 4.1 Rewire the persistent toolbar tmux actions, dashboard switch/close actions, and mobile controls to target the active Dockview-backed terminal session.
- [x] 4.2 Persist versioned workspace state, including stable storage keys, schema version, Dockview layout JSON, restorable session descriptors, and stale-reference handling rules.
- [x] 4.3 Restore restorable tmux-backed tabs after reload, reapply their persisted order and active state, and surface skipped non-restorable shell tabs with one summary notification.
- [x] 4.4 Add the reset-layout action to the dashboard so users can clear persisted workspace state and reopen the workspace from a default non-restored state.

## 5. Verification

- [x] 5.1 Verify across `new`, `tmux`, and `attach` tabs that drag-reorder, activate, and close operations preserve the expected active-session targeting and never create a second visible workspace group.
- [x] 5.2 Verify that tab moves and visibility changes preserve terminal continuity: no socket close/reopen solely from workspace moves, no xterm buffer reset from activation changes, and existing tmux reconnect behavior still works after transport disruptions.
- [x] 5.3 Verify a mixed-session restore round trip: create multiple tabs, arrange them, reload, confirm tmux-backed tabs restore in persisted order, the persisted active tab becomes active again when recoverable, and skipped shell tabs produce one summary notification.
- [x] 5.4 Verify the reset-layout action clears persisted workspace state, reopens the workspace without reusing the prior layout, and document desktop-first drag behavior plus any validated mobile limitations for this phase.
