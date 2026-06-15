## 1. Protocol and Impl Boundaries

- [x] 1.1 Reconcile the completed Plotly template graphics change state if it is still active so schema version 3 remains the implementation baseline.
- [x] 1.2 Extract or rename shared AG-UI event validation, framing, and tool-call event construction helpers into protocol-oriented functions.
- [x] 1.3 Add a schema-agnostic protocol tool-call renderer that accepts any valid tool name and JSON argument object without consulting Houmao implementation schemas.
- [x] 1.4 Rename the Houmao component registry concepts to implementation registry concepts while preserving existing payload models and validation behavior.
- [x] 1.5 Route Houmao implementation rendering through the shared protocol tool-call event construction path.

## 2. Manager CLI

- [x] 2.1 Add `houmao-mgr ag-ui protocol events validate` for standard AG-UI event batch validation.
- [x] 2.2 Add `houmao-mgr ag-ui protocol events frame` for JSON, JSON Lines, and SSE output from already-standard AG-UI event batches.
- [x] 2.3 Add `houmao-mgr ag-ui protocol tool-call render` and `houmao-mgr ag-ui impl new-component render` for arbitrary frontend-specific implementation tool names and JSON arguments, with shared schema-agnostic event construction.
- [x] 2.4 Add `houmao-mgr ag-ui impl list`, `schema`, `validate`, and `render` for Houmao-known implementation payloads.
- [x] 2.5 Add `houmao-mgr ag-ui impl templated-graphics list` for supported Layer 1 templated graphics schema discovery with explicit Plotly metadata.
- [x] 2.6 Add `houmao-mgr ag-ui impl freeform-graphics list` for supported higher-freedom graphics schema discovery with explicit Vega-Lite metadata.
- [x] 2.7 Add `houmao-mgr ag-ui impl catalog houmao.graphic.template traces` for the Plotly 2D trace catalog.
- [x] 2.8 Decide and implement whether `houmao-mgr internals ag-ui ...` remains as a deprecated alias or is removed directly.

## 3. Capabilities

- [x] 3.1 Add Houmao custom `agUiProtocol` metadata for protocol validation, protocol tool-call rendering, event output formats, and live-only Houmao gateway publish semantics.
- [x] 3.2 Add Houmao custom `agUiImpl` metadata for built-in implementation names, frontend-specific implementation transport policy, and renderer-support caveats.
- [x] 3.3 Move Plotly template metadata under template implementation metadata while preserving trace catalog, renderer, datasource, map, and extra policies.
- [x] 3.4 Move Vega-Lite metadata under Vega-Lite implementation metadata while preserving version, renderer, remote-data, inline-data, and Altair authoring policy.
- [x] 3.5 Keep standard AG-UI tool metadata conservative when generated graphics are disabled.

## 4. Documentation and Skill Guidance

- [x] 4.1 Update `houmao-interop-ag-ui` to teach protocol commands, implementation commands, and the custom frontend implementation path.
- [x] 4.2 Update gateway AG-UI reference docs to describe protocol versus impl and the new manager command shape.
- [x] 4.3 Update examples and migration notes from `internals ag-ui components/events` to `ag-ui protocol` and `ag-ui impl`.
- [x] 4.4 State clearly that protocol validation does not imply GUI render support for an unknown frontend-specific implementation.

## 5. Tests

- [x] 5.1 Add unit tests for protocol event validation and protocol event framing commands.
- [x] 5.2 Add unit tests for protocol tool-call rendering and `impl new-component render` with an unknown custom implementation tool name.
- [x] 5.3 Update implementation registry and CLI tests from components terminology to impl terminology.
- [x] 5.4 Add tests proving `impl templated-graphics list` includes `houmao.graphic.template` with Plotly metadata, excludes `houmao.graphic.vegalite` and non-graphic UI implementation schemas, and does not flatten Plotly trace types into schema names.
- [x] 5.5 Add tests proving `impl freeform-graphics list` includes `houmao.graphic.vegalite` with Vega-Lite metadata and excludes `houmao.graphic.template` and non-graphic UI implementation schemas.
- [x] 5.6 Update capabilities tests for separate `agUiProtocol` and `agUiImpl` metadata.
- [x] 5.7 Update skill and docs tests or snapshots that assert old `internals ag-ui` command wording.
- [x] 5.8 Run focused AG-UI unit tests and the relevant workbench typecheck or browser smoke if renderer-facing metadata changes affect the frontend.
