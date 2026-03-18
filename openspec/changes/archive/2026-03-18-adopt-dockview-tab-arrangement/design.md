## Context

Tailmux currently renders its own browser tab strip in `public/index.html`, stores tab/session/view state together in the `tabs` map in `public/app.js`, and uses `activeTabId` to decide which terminal wrapper is visible and which session receives header, dashboard, and mobile actions. That design makes drag-and-drop rearrangement awkward because session transport state, xterm DOM state, and tab-strip DOM state are all coupled.

This change introduces Dockview as a browser workspace manager for terminal tabs. The goal is not to add multi-view layouts yet; it is to replace the hand-crafted tab manager with a Dockview-backed workspace that allows users to reorder and activate tabs freely while keeping terminal sessions stable.

Constraints:
- Tailmux should remain a Bun-first / Node-runtime project without a framework migration.
- Existing HTTP and WebSocket backend contracts should remain unchanged.
- tmux pane splitting inside an attached terminal is unaffected by this change.
- The first phase should preserve a single visible workspace group and defer split layouts, floating groups, and popouts.
- The current frontend is still a zero-build CDN page, so the Dockview migration must first establish a coherent bundled frontend asset path.

## Goals / Non-Goals

**Goals:**
- Decouple browser workspace state from terminal session transport state.
- Replace the custom tab strip with a Dockview-managed workspace.
- Allow drag-and-drop tab rearrangement without reconnecting or recreating terminal sessions.
- Route header actions, dashboard actions, and mobile controls through the Dockview active panel/session.
- Persist workspace order and active-tab state, and restore restorable tmux-backed tabs after reload.

**Non-Goals:**
- Supporting 2-view / 4-view split layouts in this change.
- Supporting floating groups, popout windows, or VS Code-style full panel docking.
- Changing Tailmux backend APIs or tmux protocol behavior.
- Reopening ephemeral shell tabs as brand-new shell sessions after reload.

## Decisions

### 1. Use Dockview core in a Bun-driven vanilla frontend build

Tailmux should adopt Dockview through its vanilla/core integration rather than migrating the frontend to React or continuing with a custom drag-and-drop implementation.

The project should introduce a Bun-driven ESM frontend entry point and emit bundled browser assets under `public/build/` so the existing Express static-file serving model remains intact. Dockview, xterm, and the xterm fit addon should all move into that same bundled frontend dependency graph.

Rationale:
- Dockview already provides tab/group primitives, drag-and-drop movement, active panel events, custom tab rendering, and layout serialization.
- A framework migration would add scope unrelated to the user-visible goal.
- Re-implementing drag-and-drop ordering on top of the current custom tab bar would preserve the existing coupling that we are trying to remove.
- Emitting the bundle into `public/` preserves the current runtime serving pattern while making the ESM dependency graph explicit.

Alternatives considered:
- Build custom drag-reorder on the existing tab strip: rejected because it keeps transport and DOM ownership tangled.
- Migrate to React + Dockview React: rejected for this phase because it expands the change far beyond tab management.
- Import maps plus CDN-hosted Dockview ESM: rejected because it would keep the frontend in a mixed CDN-global / package-import state and would not resolve the longer-term asset ownership problem.

### 2. Split current `tabs` state into a terminal session registry and a workspace controller

The current `tabs` map should be replaced conceptually by two cooperating layers:

- `TerminalSessionRegistry`: owns session identity, session mode, session name, WebSocket lifecycle, reconnect policy, xterm instance, fit addon, scroll state helpers, and restore eligibility.
- `WorkspaceController`: owns Dockview setup, panel creation/removal/activation, tab title/status updates, and layout persistence.

Rationale:
- Session transport should not depend on where a tab appears visually.
- Workspace moves must not close sockets or recreate xterm instances.
- Dashboard and action routing become simpler when they query session state directly instead of tab DOM.

Alternatives considered:
- Keep one enriched `tabs` object and bolt Dockview references onto it: rejected because the state boundary remains unclear and fragile.

### 3. Keep terminal DOM and xterm instances stable across tab moves

Each terminal session should own one stable terminal host/root element plus one xterm instance. Dockview panel content should attach that stable session-owned root instead of constructing terminal transport on panel mount.

The required invariant is session-owned terminal DOM stability, not a hard dependency on one Dockview renderer flag. If the pinned Dockview version supports persistent rendering cleanly, Tailmux should use it. If not, the panel shell must still preserve the same session-owned terminal root without recreating the terminal.

Rationale:
- xterm scrollback, focus behavior, sizing, and browser-side buffer state are DOM-sensitive.
- Users should not lose terminal continuity when reordering tabs or switching tabs.

Alternatives considered:
- Let Dockview create/destroy terminal DOM on visibility changes: rejected because it risks buffer/focus churn and unnecessary reconnect work.

### 4. Restrict the first phase to a single visible workspace group

Dockview is being introduced first as a tab workspace, not as a full layout manager. The UI should allow tab reorder and activation but should not create or persist split groups, floating groups, or multi-panel arrangements in this phase.

Implementation guidance:
- Accept drag/drop operations that reorder tabs within the current workspace group.
- Use a single explicit enforcement strategy: block split-creating drops when the pinned Dockview version exposes a reliable pre-drop interception path, otherwise normalize immediately after drop back to one visible group.
- Persist only single-group workspace state in this phase.

Rationale:
- This gives users the main win immediately: freely arranged tabs.
- It keeps the migration small enough to stabilize the session/workspace boundary before enabling more layout freedom.

Alternatives considered:
- Enable full Dockview splitting immediately: rejected because it adds new UI semantics, action-targeting complexity, and mobile behavior questions before the tab foundation is stable.

### 5. Derive active session state from Dockview active-panel events

The current `activeTabId` global should be replaced conceptually by `activeSessionId`, sourced from Dockview active-panel changes.

All tab-sensitive actions should target that active session:
- tmux new-window / rename buttons in a persistent external toolbar
- mobile keyboard and tmux controls
- dashboard switch/close actions
- terminal fit/focus behavior on activation and panel-dimension changes

Rationale:
- After the tab strip is removed, Dockview is the canonical workspace state.
- This avoids stale assumptions tied to hand-managed `.active` classes.

Alternatives considered:
- Keep `activeTabId` and manually synchronize it with Dockview: rejected because it duplicates state and invites drift.

### 6. Persist layout separately from restorable session descriptors

Workspace restoration requires two kinds of state:

- Dockview layout JSON: tab ordering and active panel/group metadata.
- Restorable session descriptors: enough metadata to recreate tabs after reload.

Tailmux should persist that state in a versioned localStorage payload so future layout revisions can reject or migrate stale state intentionally instead of inferring schema from shape alone.

The versioned payload should define:
- stable storage key names,
- a schema version field,
- layout JSON,
- restorable session descriptors, and
- behavior for stale panel references or missing session descriptors during restore.

Session restore behavior should be transport-aware:
- `tmux` and `attach` tabs are restorable by session name and mode.
- plain `new` shell tabs are not restorable because the server terminates them on disconnect.

On startup, Tailmux should rebuild restorable sessions first, then apply the stored Dockview layout. Non-restorable shell tabs should be skipped with one summary notification rather than silently blocking workspace restore.

Rationale:
- Layout-only persistence is insufficient because the old browser tab objects disappear on reload.
- Reopening ephemeral shells automatically would change semantics and surprise users.

Alternatives considered:
- Persist layout only for the current page lifetime: rejected because it provides little value once a reload occurs.
- Reopen shell tabs as fresh shells: rejected because it does not preserve the prior session.

### 7. Keep the existing external action strip and dashboard in phase 1

The header, dashboard modal, and mobile control surfaces should remain external to Dockview in this phase, but their targeting logic should move to the active session resolved from the workspace controller.

The tmux new-window and rename controls should be relocated out of the removed tab strip and into a persistent header/workspace toolbar that always exists independently of Dockview tab chrome.

Rationale:
- It minimizes UI churn while still replacing the core tab-management system.
- The user request is about tab arrangement, not a full UI redesign.

Alternatives considered:
- Move all controls into Dockview group headers immediately: rejected because it makes the first migration larger without being necessary for reorder support.

### 8. Include a user-visible reset-layout action in phase 1

Because this change introduces persisted workspace state for the first time, Tailmux should expose a reset-layout control in the dashboard actions area. That control should clear the versioned workspace persistence payload and reload the workspace.

Rationale:
- It gives users an escape hatch if stored layout state becomes stale or confusing.
- The current dashboard already has an actions area and is the least disruptive place to surface recovery controls.

Alternatives considered:
- Defer reset-layout to a later layout-management pass: rejected because it would force users into browser devtools for first-generation persistence failures.

## Risks / Trade-offs

- [Dockview adds frontend dependency and build complexity] → Mitigation: keep the frontend integration minimal and Bun-first, and avoid a framework migration.
- [Terminal DOM can become inconsistent when hidden or moved] → Mitigation: keep session-owned terminal hosts stable and use persistent rendering for terminal panels.
- [Stored layout can reference stale tmux sessions] → Mitigation: restore only sessions that still resolve successfully and surface skipped-session notifications.
- [Versioned restore payload can drift over time] → Mitigation: define explicit schema versioning and ignore or reset incompatible stored state.
- [Single-group restrictions may feel artificial once Dockview is present] → Mitigation: document this phase boundary clearly and keep the internal architecture ready for later split support.
- [Mobile drag-and-drop ergonomics may be weaker than desktop] → Mitigation: preserve existing mobile keyboard/tmux control flows, validate touch behavior explicitly, and document desktop-first drag behavior as a known first-phase limitation rather than adding a second reorder mechanism now.

## Migration Plan

1. Add a Bun-driven frontend bundle that emits browser assets under `public/build/`, and move Dockview, xterm, and the fit addon into that bundle.
2. Refactor frontend state into a session registry and workspace controller boundary with stable session-owned terminal roots.
3. Replace the hand-crafted tab strip with a Dockview container, relocate tmux tab actions into a persistent external toolbar, and wire fit/focus to Dockview lifecycle events.
4. Add single-group enforcement, versioned workspace persistence, reset-layout recovery, and one summary notification for skipped non-restorable shell tabs.
5. Validate drag reorder, tab close, session continuity, mobile behavior, reset behavior, and restore behavior; if necessary, rollback by reverting the frontend-only change set.

## Open Questions

- None for this revision.
