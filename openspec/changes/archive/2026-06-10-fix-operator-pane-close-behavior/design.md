## Context

The workbench always creates an `operator` Dockview panel during startup and currently re-creates it in `onDidRemovePanel` whenever the operator panel is removed. This made sense as a defensive guard for a pinned/default panel, but it conflicts with the close affordance that Dockview exposes. If a user closes the operator pane while agent or debug panes remain, the workbench immediately adds the operator pane back in a queued microtask.

The existing `ag-ui-workbench-app` spec calls the operator pane "pinned", but it does not state that user-initiated close must be undone. The desired behavior is a user-respecting layout: operator remains the default starting pane, but an explicit close should persist like other layout changes when the workspace still has other useful panes.

## Goals / Non-Goals

**Goals:**
- Make explicit operator-pane close persist while other panes remain open.
- Preserve the operator pane as the default pane for a fresh or otherwise empty workbench.
- Keep operator pane target metadata in storage so closing the visual pane does not erase the configured operator target.
- Preserve ordinary agent pane and Debug Agent pane close behavior.
- Add deterministic Playwright coverage for operator close and reload persistence.

**Non-Goals:**
- Do not remove the operator pane concept.
- Do not add operator lifecycle controls or managed-agent lifecycle behavior.
- Do not change AG-UI request, connect, run, detach, proxy, or debug relay semantics.
- Do not add a separate operator restore toolbar unless implementation reveals that restoring operator from an empty layout needs an explicit UI affordance.

## Decisions

### Decision: Stop auto-respawning operator on panel removal

`onDidRemovePanel` should not call `ensureOperatorPanel()` for every `operator` removal. Removal is an explicit user action when the close control is used, so the workbench should allow the remaining panes to occupy the layout.

Rejected alternative: hide or disable the operator close affordance. That would make "pinned" literal, but Dockview close affordance customization is less direct, and the user report asks for the close action to work rather than disappear.

### Decision: Ensure operator only when the workbench has no usable panel

The startup path should still add the operator pane when there is no saved layout or when the restored layout contains no panels. This keeps a fresh workbench useful and avoids an empty first screen.

The implementation can derive this from the Dockview API after `fromJSON()` and before initial render completes. If the restored layout still has agent or debug panels, the workbench should not force the operator pane back in.

### Decision: Keep operator storage metadata when its panel closes

`removePaneRecord()` already ignores the `operator` pane ID. That behavior should stay. Closing the operator visual pane should not erase operator target configuration because a future default restore or explicit retarget flow may reuse it.

### Decision: Cover behavior through Playwright

The regression should be tested in the existing workbench Playwright suite. A test can open another pane, close the operator tab through Dockview's close control or a test-accessible close path, assert that the operator panel does not reappear, reload, and assert the operator panel remains absent while the other pane remains.

## Risks / Trade-offs

- Dockview may leave no panels if the user closes every pane. Mitigation: keep default operator creation for empty layouts.
- Closing the operator pane may make it less obvious how to restore operator input. Mitigation: preserve operator target metadata and consider a follow-up toolbar restore action if users need it.
- The term "pinned" in the existing spec is ambiguous. Mitigation: update the spec to define default/restorable behavior instead of immortal panel behavior.
- Browser tests may need a stable way to click Dockview's tab close affordance. Mitigation: use accessible tab controls if available, or add a test-friendly UI path only if necessary.
