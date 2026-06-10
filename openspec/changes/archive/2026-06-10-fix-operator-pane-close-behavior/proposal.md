## Why

Closing the operator pane currently removes it for only a moment because the workbench immediately re-creates it from `onDidRemovePanel`. This makes the close control feel broken and prevents users from keeping an agent-only or debug-only workspace layout.

## What Changes

- Treat operator pane close as an explicit user action that the workbench respects while other panes remain open.
- Keep the operator pane available as the default pane for a fresh or empty workbench.
- Preserve existing operator target configuration and ordinary agent/debug pane behavior.
- Add deterministic browser coverage for closing the operator pane with other panes open and verifying that it stays closed across layout persistence.
- No breaking API changes.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `ag-ui-workbench-app`: clarify and test operator pane lifecycle behavior so the operator pane is default/restorable but not auto-respawned after an explicit close.

## Impact

- Affected app code: `apps/ag-ui-workbench/src/App.tsx` for Dockview remove/startup behavior.
- Affected tests: `apps/ag-ui-workbench/tests/workbench.spec.ts` for operator close and persistence coverage.
- Affected specs: `openspec/specs/ag-ui-workbench-app/spec.md` through a delta spec.
- No changes to AG-UI protocol routes, managed-agent lifecycle, passive-server discovery, debug relay behavior, or Python package distribution.
