## Why

Houmao now exposes enough per-agent AG-UI protocol surface to justify a real GUI harness, but the current coverage is split between backend tests, documentation examples, and a deterministic browser fixture. A minimal workbench under `apps/` will let developers attach to running Houmao agents, submit AG-UI runs, inspect raw protocol events, and verify rendered graphics without shipping GUI assets in the PyPI package.

## What Changes

- Add a standalone `apps/ag-ui-workbench/` React application for testing Houmao AG-UI protocol behavior outside the Python package distribution.
- Provide a pinned operator input panel that connects to a configured Houmao operator agent and submits prompts through AG-UI run semantics.
- Provide a Dockview-based multi-pane workspace where each pane can be configured independently to connect to one running Houmao agent.
- Add direct AG-UI client code for `/connect`, `/runs`, `/capabilities`, SSE parsing, abort/detach handling, event reduction, raw event inspection, state snapshot display, transcript rendering, and `houmao_render_graphic` rendering.
- Add a local development proxy that forwards only approved AG-UI targets by default, preserves `text/event-stream` behavior, and avoids coupling browser tests to permissive gateway CORS settings.
- Add deterministic Playwright coverage with a fake AG-UI server to verify operator input, multiple panes, connection lifecycle, event rendering, graphics rendering, and layout persistence.
- Document how to run the workbench with Bun, configure direct gateway URLs or future passive-server URLs, and use the harness without managing Houmao agent lifecycle from the GUI.

## Capabilities

### New Capabilities

- `ag-ui-workbench-app`: Defines the standalone AG-UI workbench application, including operator input, docked multi-agent panes, direct AG-UI client behavior, diagnostics views, local proxy behavior, graphics rendering, and browser E2E coverage.

### Modified Capabilities

- None.

## Impact

- New files under `apps/ag-ui-workbench/` and optional shared app documentation under `apps/README.md`.
- New JavaScript/TypeScript dependencies scoped to the workbench app, expected to include React, Vite, Dockview React bindings, AG-UI TypeScript types or compatible local client code, and Playwright test scripts.
- No PyPI package contents should include the GUI app or its node dependencies.
- No change to Houmao agent lifecycle ownership: the GUI attaches to, detaches from, and submits runs to already-running Houmao agents only.
- No change to the existing backend AG-UI protocol requirements except where tests reveal a backend conformance bug that must be fixed separately.
