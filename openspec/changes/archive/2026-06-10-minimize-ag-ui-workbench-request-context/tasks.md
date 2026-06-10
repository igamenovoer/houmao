## 1. Request Construction

- [x] 1.1 Add a small canvas-size input type and helper that renders `houmao.canvas_size_px.v1` as a compact AG-UI context entry only when `widthPx` and `heightPx` are positive integers.
- [x] 1.2 Update `buildRunInput` so normal workbench runs use `state: {}`, `forwardedProps: {}`, `tools: []`, and only the optional compact canvas context entry.
- [x] 1.3 Update `buildConnectInput` so connect/watch requests use empty `state`, `context`, `tools`, and `forwardedProps`.
- [x] 1.4 Remove Debug Agent connect-time forwarded-prop overrides unless they are needed for a standard AG-UI or gateway-recognized Houmao control.

## 2. Canvas Measurement

- [x] 2.1 Measure the visible graphics/display surface for operator and agent panes using browser layout data available at prompt submission time.
- [x] 2.2 Pass the measured canvas size into `buildRunInput` for operator and agent prompt submissions.
- [x] 2.3 Omit the canvas context when the display surface has no positive measured width or height.

## 3. Verification

- [x] 3.1 Add or update workbench request-builder tests to assert compact canvas context, empty state, empty tools, and empty forwarded props for normal run submissions.
- [x] 3.2 Add or update workbench connect tests to assert connect/watch requests do not include pane/source metadata in state, context, tools, or forwarded props.
- [x] 3.3 Run the relevant workbench checks and the focused Python AG-UI tests needed to confirm gateway prompt conversion remains compatible with empty state and forwarded props.
