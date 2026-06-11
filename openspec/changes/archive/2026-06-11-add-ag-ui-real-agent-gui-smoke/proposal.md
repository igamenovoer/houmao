## Why

Houmao now has deterministic AG-UI gateway and browser rendering coverage, but it does not have an opt-in smoke that proves the real workbench can prompt a real managed agent and display a GUI message the agent publishes back. This matters for template graphics because the end-to-end product path depends on GUI run submission, agent routing, gateway fanout, and React rendering all working together.

## What Changes

- Add an opt-in real-agent Playwright smoke for `apps/ag-ui-workbench` that restarts an existing test agent, selects it through passive-server discovery, connects the GUI, submits a prompt through the GUI, and waits for a published `houmao.graphic.template` chart.
- Require the smoke to preflight live agent AG-UI run/connect capability, published-event fanout, and local `houmao.graphic.template` authoring support before submitting the prompt.
- Require nonce-based assertions for visible chart rendering, with Vega-Lite SVG rendering as the required evidence. Record the optional text completion marker when the agent emits it.
- Require failure artifacts that make live-agent failures diagnosable without rerunning immediately.
- Keep the smoke outside default unit tests and regular CI unless an operator explicitly enables real-agent credentials and environment variables.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `per-agent-ag-ui-e2e-smoke`: Add an opt-in real-agent GUI smoke that exercises workbench prompt submission to a real Houmao agent and validates rendered template graphics in the GUI.

## Impact

- `apps/ag-ui-workbench` Playwright or browser-smoke test harness.
- Demo or smoke scripts that coordinate passive-server, workbench, and an existing managed test agent.
- `houmao-mgr` lifecycle usage for restarting and inspecting the selected test agent.
- AG-UI gateway capabilities, local component authoring discovery, and event publish paths used by `houmao.graphic.template`.
- Gateway reference documentation and operator smoke-test instructions.
