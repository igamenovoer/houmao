## Why

`houmao-mgr internals ag-ui` currently mixes standard AG-UI event operations with Houmao-owned renderer payload contracts. This makes Plotly, Vega-Lite, and future frontend-specific drawing contracts look like AG-UI protocol features, when they are optional application-layer implementation contracts carried by standard AG-UI tool-call events.

Users who build their own frontend drawing capability should be able to rely on Houmao for standard AG-UI protocol validation, framing, and Houmao gateway publishing without registering every frontend-specific renderer schema in Houmao.

## What Changes

- **BREAKING**: Split the AG-UI authoring CLI vocabulary into `protocol` and `impl` surfaces.
- Move standard AG-UI event operations under `houmao-mgr ag-ui protocol`, covering event validation, deterministic event framing, and generic tool-call event rendering for any tool name.
- Move Houmao-owned payload schema discovery, payload validation, implementation rendering, and implementation catalogs under `houmao-mgr ag-ui impl`.
- Add category-specific implementation discovery under `houmao-mgr ag-ui impl` using `templated-graphics`, `freeform-graphics`, and `new-component` so the CLI mirrors the AG-UI advanced graphing layer model.
- Treat `houmao.graphic.template`, `houmao.graphic.vegalite`, `houmao.table`, `houmao.metric_grid`, `houmao.dashboard`, and future frontend-specific renderer contracts as AG-UI implementation contracts, not AG-UI protocol features.
- Add a generic protocol tool-call render path and an implementation-layer `new-component` render path so users can produce standard AG-UI `TOOL_CALL_*` events for custom frontend tool names without adding Houmao implementation support.
- Revise AG-UI capabilities to expose protocol support separately from implementation support and to keep Plotly/Vega metadata under implementation metadata.
- Update the `houmao-interop-ag-ui` skill and gateway docs to teach the protocol/impl split and to avoid describing renderer payload semantics as AG-UI protocol behavior.
- Keep the Houmao gateway publish helper scoped to already-standard AG-UI event batches and Houmao gateway routing semantics.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-ag-ui-message-authoring`: split manager commands and authoring semantics into AG-UI protocol utilities and AG-UI implementation utilities.
- `houmao-interop-ag-ui-skill`: teach agents the protocol/impl split and the `new-component` path for custom frontend renderer contracts.
- `per-agent-ag-ui-attachment`: revise capabilities metadata so protocol support and implementation metadata are reported separately.
- `ag-ui-template-graphics`: classify Plotly template graphics as a Houmao AG-UI implementation.
- `ag-ui-vegalite-graphics`: classify Vega-Lite graphics as a Houmao AG-UI implementation.

## Impact

- Affected Python modules include `src/houmao/srv_ctrl/commands/ag_ui_authoring.py`, `src/houmao/ag_ui/authoring.py`, and `src/houmao/ag_ui/capabilities.py`.
- Affected documentation includes `docs/reference/gateway/ag-ui.md` and the packaged `houmao-interop-ag-ui` system skill.
- Existing tests for `internals ag-ui components ...` and `internals ag-ui events ...` need to move to the new command shape or assert explicit compatibility behavior.
- No new third-party dependency is required.
