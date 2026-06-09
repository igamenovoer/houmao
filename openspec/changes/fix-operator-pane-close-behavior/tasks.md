## 1. Operator Pane Lifecycle

- [x] 1.1 Update workbench startup logic so the operator pane is created for fresh or empty workbench layouts.
- [x] 1.2 Update Dockview panel removal handling so an explicit operator pane close is not immediately auto-respawned when other panes remain.
- [x] 1.3 Preserve existing operator target metadata in storage when the operator visual pane is closed.
- [x] 1.4 Preserve ordinary agent pane and Debug Agent pane close/removal behavior.

## 2. Persistence and Regression Coverage

- [x] 2.1 Add Playwright coverage that opens another pane, closes the operator pane, and verifies the operator pane stays absent.
- [x] 2.2 Extend Playwright coverage to reload after operator close and verify the operator pane remains absent while the other pane is restored.
- [x] 2.3 Verify persisted operator target metadata is retained after operator pane close and reload.
- [x] 2.4 Ensure existing operator/multi-pane/debug-agent E2E coverage still passes.

## 3. Verification

- [x] 3.1 Run the workbench TypeScript typecheck.
- [x] 3.2 Run the workbench production build.
- [x] 3.3 Run the deterministic workbench Playwright E2E suite.
- [x] 3.4 Run `openspec validate fix-operator-pane-close-behavior --strict`.
