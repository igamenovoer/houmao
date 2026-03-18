## Context

Tailmux already uses Dockview as the browser tab workspace, but the current implementation still behaves like a single-pane tab strip. The frontend explicitly blocks split-producing drops and collapses any extra Dockview groups back into one visible group, even though it already persists Dockview JSON layout state and keeps one stable xterm DOM root per session.

That current shape is important because it gives this change a clean extension path:

- one live terminal session already maps to one Dockview panel
- panels already use Dockview's `always` renderer, which is appropriate for DOM-stateful terminal content
- workspace state already stores `workspace.toJSON()` plus session restore descriptors

The main gap is behavioral, not foundational. The code still assumes that only one browser terminal is visible at a time for drag/drop policy, active-session routing, and resize handling.

## Goals / Non-Goals

**Goals:**

- allow users to drag terminal tabs into multiple visible Dockview groups
- support both horizontal and vertical splits
- allow moving tabs between groups without recreating the underlying terminal session
- keep toolbar, keyboard, dashboard, and tmux actions routed to the currently focused visible pane
- persist and restore split layouts for restorable tmux-backed tabs
- keep the current session continuity model, reconnect behavior, and panel-local terminal DOM roots

**Non-Goals:**

- floating groups or pop-out windows
- duplicate views of the same terminal session in more than one panel
- browser-level 2-view or 4-view presets separate from Dockview drag/drop behavior
- changes to tmux's own internal pane splitting
- full mobile-first split-layout ergonomics

## Decisions

### 1. Dockview groups become the visible pane model

Tailmux will stop normalizing Dockview back into a single visible group. Instead, Dockview groups will be treated as the browser-level pane containers, and a user-created left/right/top/bottom drop will be allowed to create a split.

Rationale:

- Dockview already models groups and split layouts natively.
- The current implementation stores Dockview layout JSON already, so the persisted state format is close to what this feature needs.
- Removing the Tailmux-specific single-group restrictions is lower-risk than layering a second custom split model above Dockview.

Alternatives considered:

- Keep a Tailmux-owned split model outside Dockview: rejected because it duplicates the layout engine Dockview already provides.
- Add fixed presets only: rejected because the user goal is free arrangement, not just predefined 2-view or 4-view layouts.

### 2. One live terminal session remains equal to one Dockview panel

This change keeps the existing invariant that one browser terminal session owns one websocket transport, one xterm instance, and one stable terminal root. Moving a panel between groups changes layout only; it does not create a second view of that session.

Rationale:

- The current frontend stores a single DOM root per session and mounts it into the Dockview panel host.
- Reusing the same session object across layout changes preserves terminal buffer state, reconnect state, and mobile controls with minimal architectural churn.
- Duplicate views of the same live terminal would require a different ownership model for DOM, focus, and resize events.

Alternatives considered:

- Allow cloned views of one session: rejected for this change because it introduces a second rendering and focus model that is separate from split layouts themselves.

### 3. Active-session routing follows focused pane content

With multiple visible panes, `activeSessionId` must mean the session whose panel currently holds focus, not merely the most recently selected tab in some other group. Tailmux will treat Dockview's active/focus events as the primary signal and will also forward direct interaction inside terminal content back to the owning panel so toolbar and keyboard actions follow the pane the user is actually working in.

Rationale:

- In a split layout, multiple panels are visible at once and the old single-visible-tab assumption is no longer valid.
- Dockview exposes active-panel and focus-related events, and panel APIs expose focus and visibility state.
- Explicit focus handoff avoids cases where a toolbar action targets a hidden or merely previously active tab.

Alternatives considered:

- Keep routing by most recently opened or most recently tab-activated session: rejected because it becomes ambiguous once two panes remain visible.

### 4. Resize and fit behavior will target visible panels, not only the active one

The current implementation only does a global fit for `activeSessionId` on window resize. In split layouts, Tailmux will fit every visible panel after workspace layout changes and window resize events, while still using per-panel dimension and visibility hooks for more local resizes.

Rationale:

- Multiple panels can change size together when a split divider moves or when the window changes size.
- xterm must receive updated dimensions for every visible terminal to keep rows and columns correct.
- Dockview panel APIs already surface dimension and visibility changes, so the implementation can limit work to visible panels rather than every session.

Alternatives considered:

- Fit every session unconditionally on each layout change: rejected because hidden panels do not need immediate resize work and the extra traffic is unnecessary.

### 5. Persisted workspace state will move to a split-aware versioned format

Tailmux will bump the workspace state version and treat Dockview layout JSON as the primary representation of arrangement. Session descriptors will remain alongside the layout so restorable tmux-backed tabs can be recreated before the layout is loaded with `fromJSON(..., { reuseExistingPanels: true })`.

The restore flow will:

1. load the stored state
2. recreate restorable sessions from their descriptors
3. filter the Dockview layout tree to restored panel IDs only
4. load the filtered layout
5. restore the previously focused session when possible
6. report skipped non-restorable shell tabs in one summary notification

Rationale:

- Dockview already provides `toJSON()` and `fromJSON()` for full layout state.
- A version bump is simpler than carrying forward the old single-group assumptions.
- The repository explicitly allows forward-moving breaking changes where that keeps the design cleaner.

Alternatives considered:

- Preserve backward compatibility with the old persisted layout version: rejected because the new multi-group design changes the meaning of the stored workspace state enough that reset-on-version-change is cleaner.

### 6. The current global toolbar model stays, but the UI must show focused-pane ownership clearly

The existing external tmux and keyboard controls will remain global controls rather than becoming per-pane embedded toolbars. To keep that usable in a split layout, the focused pane must be visually obvious and the workspace summary should describe the currently targeted session.

Rationale:

- The toolbar relocation from the prior change already decoupled actions from the tab strip.
- Reusing the global toolbar avoids duplicating controls into every pane.
- A strong focused-pane visual treatment is enough to make targeting legible without a larger control-surface redesign.

Alternatives considered:

- Duplicate toolbar controls inside every pane: rejected because it adds UI clutter and increases the chance that per-pane control states diverge.

## Risks / Trade-offs

- [Focus ambiguity between visible panes] -> Forward pointer/focus events from terminal roots into Dockview panel activation and add stronger visual focus styling for the targeted pane.
- [More resize and websocket resize traffic] -> Debounce global layout saves and fit only visible panels after layout-affecting events.
- [Corrupted or stale persisted layout data] -> Use a new workspace state version, filter restored layouts to known session IDs, and fall back to the default empty workspace on invalid state.
- [Mobile drag/drop remains weaker than desktop] -> Treat split layouts as desktop-first in docs and avoid promising touch-optimized pane management in this change.
- [User confusion when shell tabs disappear after reload from a complex layout] -> Keep the existing summary toast behavior and make the message apply to split layouts as well.

## Migration Plan

- Bump the persisted workspace state version for Tailmux's browser storage.
- On version mismatch, discard the previous stored workspace state rather than translating it.
- Rollout is frontend-only inside the Tailmux submodule; no server API migration is required.
- Rollback is a code revert to the previous single-group Dockview implementation, which will also naturally stop reading the newer workspace version.

## Open Questions

- Should the dashboard remain a flat session list in this phase, or should it show which workspace group each session belongs to? Current design assumes a flat list is acceptable.
- Should the UI expose explicit split commands later in addition to drag/drop, or is drag/drop alone sufficient for the first multi-pane release?
