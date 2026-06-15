## 1. Harness Setup

- [x] 1.1 Decide the smoke entrypoint location and keep one canonical command for operators.
- [x] 1.2 Add opt-in environment parsing for `HMWB_REAL_AGENT_SMOKE`, passive-server URL, test-agent name or id, timeout, and optional stop-after-smoke cleanup.
- [x] 1.3 Configure the smoke to start or target the AG-UI workbench dev server through the Bun-global Playwright toolchain.
- [x] 1.4 Ensure the smoke is excluded from default unit tests and normal frontend checks unless explicitly enabled.

## 2. Real-Agent Setup and Preflight

- [x] 2.1 Relaunch the selected existing test agent through `pixi run houmao-mgr` before the GUI flow begins.
- [x] 2.2 Wait for passive-server discovery or resolution to report a live gateway for the selected agent.
- [x] 2.3 Fetch AG-UI capabilities and require run/connect, published-event fanout, and local `houmao.graphic.template` authoring support before submitting model work.
- [x] 2.4 Fail or skip with a clear prerequisite diagnostic when the agent selector, passive server, live gateway, capabilities, or Playwright browser is unavailable.

## 3. Workbench GUI Flow

- [x] 3.1 Use Playwright to open the workbench, clear persisted test state, and open the agent picker.
- [x] 3.2 Fill the passive-server URL, refresh discovered agents, and select the configured test agent from the picker.
- [x] 3.3 Connect the selected agent pane and wait for a connected or watched state before sending the prompt.
- [x] 3.4 Read the pane thread id and include it in the validation prompt as an explicit fallback route.
- [x] 3.5 Submit the nonce-labeled validation prompt through the pane prompt composer and run button.

## 4. Assertions and Diagnostics

- [x] 4.1 Request and record whether the transcript contains `AG_UI_TEMPLATE_GRAPHIC_SMOKE_DONE <nonce>`.
- [x] 4.2 Assert that the workbench displays `Real Agent Template Graphic Smoke <nonce>`.
- [x] 4.3 Assert that the Vega-Lite template chart container is visible and contains SVG renderer evidence.
- [x] 4.4 Treat text-only answers, Markdown-only charts, stale charts, wrong component names, and missing chart render output as failures.
- [x] 4.5 Save screenshot, browser console output, visible transcript text, submitted prompt, agent selector, resolved target, thread id, and capabilities JSON on failure.
- [x] 4.6 Preserve raw AG-UI events or reconstructed tool-call diagnostics when the workbench or gateway exposes them.

## 5. Cleanup and Documentation

- [x] 5.1 Close browser resources and detach GUI subscriptions opened by the smoke.
- [x] 5.2 Leave the selected managed agent running by default and stop it only when the explicit cleanup option is enabled.
- [x] 5.3 Document the smoke command, required environment variables, expected prerequisites, and failure artifacts in the AG-UI gateway or workbench smoke documentation.
- [x] 5.4 Document that the smoke is manual or opt-in because it uses live credentials, model behavior, and browser automation.

## 6. Verification

- [x] 6.1 Run existing deterministic AG-UI backend tests.
- [x] 6.2 Run existing deterministic AG-UI browser smoke or workbench renderer tests.
- [x] 6.3 Run the new real-agent GUI smoke against a configured local test agent and record the command plus artifact locations.
- [x] 6.4 Run `pixi run openspec status --change add-ag-ui-real-agent-gui-smoke` and confirm the change remains apply-ready.
