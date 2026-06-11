## Why

The AG-UI workbench currently measures the visible graphics surface and sends that size to the agent as a `houmao.canvas_size_px.v1` context entry on prompt runs. That measurement is volatile: pane layout, transcript expansion, renderer changes, scroll state, and later interaction can all change the usable canvas after the prompt is sent.

Agents are treating this GUI-provided context as an authoring constraint, which can produce undersized or otherwise distorted graphics. The workbench should not expose transient GUI layout measurements as agent-visible prompt context.

## What Changes

- Remove GUI-authored canvas-size context from normal agent pane AG-UI run requests.
- Keep normal prompt submissions metadata-minimal: standard AG-UI routing fields, one user message, empty `state`, empty `tools`, empty `context`, and empty `forwardedProps`.
- Stop measuring the agent pane display surface during prompt submission.
- Update tests and documentation that currently expect `houmao.canvas_size_px.v1` or other GUI layout context in workbench prompt runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ag-ui-workbench-app`: normal AG-UI prompt run requests no longer include canvas-size context entries or any other GUI-derived layout measurements.

## Impact

- Affects the AG-UI workbench frontend request path under `apps/ag-ui-workbench/src/`.
- Affects Playwright/runtime tests that assert run request bodies.
- Affects any documentation or examples that say the workbench appends canvas size into `RunAgentInput.context`.
- Agents that relied on `houmao.canvas_size_px.v1` from the workbench must instead produce responsive graphics or use explicit user-provided sizing in the graphic payload.
