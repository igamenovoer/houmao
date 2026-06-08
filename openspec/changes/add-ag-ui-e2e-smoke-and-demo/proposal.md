## Why

Milestone 2 made `/v1/ag-ui/runs` stream Houmao output as AG-UI SSE, including typed `houmao_render_graphic` events, but the path is still covered mostly by unit-level and fake-runtime tests. Before stage 1 becomes the target for passive-server proxying, Houmao needs repeatable end-to-end evidence that the live per-agent gateway, durable request queue, canonical headless artifacts, AG-UI SSE stream, and CopilotKit-style graphics reconstruction work together without giving the GUI lifecycle control.

## What Changes

- Add deterministic AG-UI end-to-end smoke coverage for `/v1/ag-ui/runs` against a live per-agent gateway surface.
- Add a controlled graphics smoke path that proves `houmao_render_graphic` reconstruction without depending on a live model choosing to call a graphics tool.
- Add a live managed-agent smoke path that proves queue admission, stream lifecycle, and terminal completion through a real headless gateway target.
- Add a small browser or client fixture using Bun-global Playwright and AG-UI/CopilotKit-style reconstruction to validate rendered graphics.
- Add AG-UI diagnostics for connect, disconnect, run admission, completion, active stream counts, and stream errors.
- Document the per-agent AG-UI endpoint setup, CopilotKit `HttpAgent` wiring, lifecycle boundary, known limits, and manual smoke workflow.
- Add passive-server readiness checks that define what stage 2 proxying must preserve without implementing the proxy in this change.

## Capabilities

### New Capabilities

- `per-agent-ag-ui-e2e-smoke`: Defines repeatable end-to-end smoke coverage and demo fixtures for AG-UI runs, generated graphics, browser rendering, and passive-server readiness.

### Modified Capabilities

- `per-agent-ag-ui-attachment`: Adds live gateway hardening requirements for AG-UI diagnostics, active connection/run counts, and explicit stream-error behavior while preserving GUI-detach lifecycle semantics.

## Impact

- Affected code: `src/houmao/ag_ui/*`, `src/houmao/agents/realm_controller/gateway_service.py`, gateway diagnostics helpers, and any small demo/test helpers needed to drive AG-UI streams.
- Affected tests: new integration or manual smoke tests under `tests/integration/` or `tests/manual/`, focused AG-UI unit tests, route/docs drift tests, and optional Playwright browser checks driven through Bun.
- Affected docs and examples: `context/plans/ag-ui-integration/roadmap.md`, `docs/reference/gateway/*`, and CopilotKit/AG-UI demo fixtures.
- Dependencies: no new Python runtime dependency is expected; browser checks should use the existing Bun-global Playwright toolchain documented in `AGENTS.md`.
