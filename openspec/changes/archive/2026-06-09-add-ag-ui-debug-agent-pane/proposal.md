## Why

The AG-UI workbench can render typed graphics when it receives valid AG-UI SSE frames, but live-agent testing currently makes it hard to separate GUI rendering bugs from gateway subscription and routing bugs. Operators need a first-class debug surface that can receive externally posted AG-UI messages, display them through the same workbench renderer path, and provide repeatable curl-based proof without launching a real managed agent.

## What Changes

- Add a Debug Agent pane to the AG-UI workbench, opened explicitly from the toolbar.
- Provide a host-side debug-agent relay endpoint that exposes an AG-UI-compatible route family for the debug pane.
- Make the debug pane a two-sided playground: a white-box sender/control side and an AG-UI display side.
- Allow external callers to post AG-UI event batches with `curl` and have those batches delivered to the debug pane display.
- Reuse the existing AG-UI client, reducer, diagnostics, and typed component renderers for the display side.
- Support bounded debug replay so curl-before-connect and live-only behavior can both be tested intentionally.
- Add documentation and Playwright evidence that the debug pane receives AG-UI messages and renders graphical components.

## Capabilities

### New Capabilities
- `ag-ui-workbench-debug-agent`: Defines the workbench debug-agent playground, host-side debug relay routes, external curl publish behavior, replay controls, and graphical rendering proof.

### Modified Capabilities
- None.

## Impact

- Affected app code: `apps/ag-ui-workbench/src/`, especially toolbar/pane registration, storage models, and pane components.
- Affected dev-server code: `apps/ag-ui-workbench/scripts/` for a host-side debug-agent relay middleware alongside the existing AG-UI proxy.
- Affected tests: `apps/ag-ui-workbench/tests/` Playwright coverage for opening the debug pane, posting events through the relay, and verifying rendered graphics.
- Affected docs: `apps/ag-ui-workbench/README.md` and AG-UI route/debug guidance.
- No managed-agent lifecycle, passive-server registry, or real Houmao gateway behavior changes are required.
