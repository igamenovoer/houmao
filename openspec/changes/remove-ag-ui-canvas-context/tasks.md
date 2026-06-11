## 1. Request Path

- [x] 1.1 Remove `canvasSize` from the `agUi/runRequested` runtime action type and all dispatch/effect call sites.
- [x] 1.2 Stop measuring the agent pane display surface during prompt submission.
- [x] 1.3 Update `buildRunInput` so normal prompt runs always set `context: []`.
- [x] 1.4 Remove the canvas context helper and related types when no longer used.

## 2. Documentation and Guidance

- [x] 2.1 Update workbench or gateway documentation that describes GUI-sent canvas-size context.
- [x] 2.2 Search for `houmao.canvas_size_px.v1`, `houmao.canvas.v1`, and AG-UI context guidance, then remove or revise workbench-owned references.

## 3. Tests

- [x] 3.1 Update runtime tests for `agUi/runRequested` to use the new action shape.
- [x] 3.2 Update Playwright request-body assertions so prompt runs require empty `context`.
- [x] 3.3 Add or revise a regression check proving available or changed pane dimensions do not produce GUI layout context.
- [x] 3.4 Run targeted workbench tests and TypeScript checks for the changed request path.
