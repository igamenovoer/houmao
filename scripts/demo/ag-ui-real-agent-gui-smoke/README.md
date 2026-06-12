# AG-UI Real-Agent GUI Smoke

This opt-in smoke validates the full GUI-to-agent AG-UI path with a real Houmao managed agent:

```text
AG-UI workbench prompt -> /v1/ag-ui/runs -> real Houmao agent -> houmao.graphic.template publish -> workbench render
```

The requested chart is intentionally an ordinary Layer 1 Plotly-backed bar chart, so the prompt uses `houmao.graphic.template`. Custom declarative Vega-Lite chart requests should use the Layer 2 `houmao.graphic.vegalite` component; the Debug Agent sender and workbench E2E tests include those deterministic examples.

It uses live credentials, model behavior, passive-server discovery, a managed agent relaunch, and Playwright browser automation. It is intentionally not part of the default Python test suite or the default workbench E2E suite.

## Command

Run from the repository root:

```bash
HMWB_REAL_AGENT_SMOKE=1 \
HMWB_PASSIVE_SERVER_URL=http://127.0.0.1:9891 \
HMWB_TEST_AGENT_NAME=<existing-test-agent-name> \
scripts/demo/ag-ui-real-agent-gui-smoke/run_smoke.sh
```

Use `HMWB_TEST_AGENT_ID=<agent-id>` instead of `HMWB_TEST_AGENT_NAME` when the name is ambiguous.

## Environment

- `HMWB_REAL_AGENT_SMOKE=1`: required opt-in guard.
- `HMWB_PASSIVE_SERVER_URL`: passive-server base URL used by the workbench agent picker.
- `HMWB_TEST_AGENT_NAME` or `HMWB_TEST_AGENT_ID`: existing managed test agent to relaunch and select.
- `HMWB_REAL_AGENT_TIMEOUT_MS`: optional model/render wait timeout, default `180000`.
- `HMWB_AGENT_COMMAND_TIMEOUT_MS`: optional relaunch/resolve/stop command timeout, default `180000`.
- `HMWB_REAL_AGENT_STOP_AFTER=1`: optional cleanup switch to stop the selected agent after the smoke.
- `HMWB_REAL_AGENT_EVIDENCE_DIR`: optional evidence directory. Relative paths resolve from the repository root.

## Assertions

The smoke fails unless the workbench:

- selects the configured agent through passive-server discovery,
- connects the pane before prompting,
- submits the prompt through the GUI composer and run button,
- renders `Real Agent Template Graphic Smoke <nonce>`, and
- shows visible SVG output inside the Plotly template chart container.

The prompt asks for `AG_UI_TEMPLATE_GRAPHIC_SMOKE_DONE <nonce>` and the smoke records whether it appears, but that text marker is diagnostic. Some TUI-backed agents publish the GUI event correctly without mapping a final text reply into the AG-UI transcript before the smoke timeout.

Text-only answers, Markdown-only charts, stale charts, wrong component names, and missing chart output are failures.

## Failure Evidence

On failure the Playwright output directory, or `HMWB_REAL_AGENT_EVIDENCE_DIR` when set, receives:

- `summary.json` with agent selector, resolved target, thread id, capabilities, prompt, command output, and console errors,
- `transcript.txt`,
- `errors.txt`,
- `raw-events.txt` when message diagnostics are available, and
- `screenshot.png`.
