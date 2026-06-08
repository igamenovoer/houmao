# Houmao AG-UI Workbench

The AG-UI workbench is a standalone Bun/Vite application for testing Houmao AG-UI protocol behavior against already-running agents. It is intentionally outside the PyPI package and lives under `apps/ag-ui-workbench/`.

## Commands

Run from this directory:

```bash
bun install
bun run dev
bun run typecheck
bun run build
bun run e2e
```

The E2E script uses Playwright from the Bun toolchain through `bunx playwright`.

## Targets

Each pane accepts either a direct gateway base URL or a concrete AG-UI route URL. These examples normalize to the same route family:

```text
http://127.0.0.1:8765
http://127.0.0.1:8765/v1/ag-ui
http://127.0.0.1:8765/v1/ag-ui/runs
http://127.0.0.1:8765/v1/ag-ui/connect
```

Future passive-server agent URLs are also accepted when they already include the agent-scoped AG-UI path:

```text
http://127.0.0.1:8080/houmao/agents/<agent_ref>/ag-ui
http://127.0.0.1:8080/houmao/agents/<agent_ref>/ag-ui/runs
```

Browser requests go through the app-local development proxy at `/__houmao_ag_ui_proxy`. The proxy allows loopback HTTP or HTTPS targets by default and rejects other hosts unless `HOUMAO_AG_UI_WORKBENCH_ALLOWED_HOSTS` lists an exact hostname or host:port value.

## Lifecycle Boundary

The GUI does not start, stop, restart, shut down, or interrupt Houmao agents. Connect attaches the pane to an existing AG-UI stream, run submits one AG-UI `RunAgentInput`, and disconnect or close means GUI stream detach. If a connection ID is known, the workbench calls AG-UI detach; otherwise it only aborts its browser stream.

The workbench persists Dockview layout, pane labels, target URLs, and thread IDs. It does not persist prompt text, raw events, stream payloads, state snapshots, activity records, or rendered graphics by default.

## Live Kimi Code Headless Check

For live/manual validation of this change, use a Kimi Code headless Houmao agent through an already-running per-agent gateway. When fixture credentials are present, prefer `tests/fixtures/auth-bundles/kimi/personal-a-default/`.

Start or discover the Kimi headless agent with the existing Houmao workflow, then point an operator or agent pane at the gateway URL, for example `http://127.0.0.1:<gateway_port>/v1/ag-ui`. The workbench should attach through AG-UI connect or submit one run through AG-UI runs without managing the Kimi headless process lifecycle.

The deterministic Playwright fake-server smoke remains the required automated test path. The Kimi Code headless run is opt-in evidence for local real-agent validation.

## Known Limits

The first workbench version is a protocol harness, not an operator scheduler. It does not execute frontend tools, send multimodal input, manage credentials, export event logs, or use CopilotKit as its runtime path. Generated graphics render through complete `houmao_render_graphic` tool-call sequences, with SVG supported in the deterministic browser smoke and unsupported formats shown as explicit fallback records.
