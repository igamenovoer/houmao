## 1. Plotly 2D Trace Catalog

- [x] 1.1 Add a catalog-generation script that reads `extern/orphan/plotly.js/dist/plot-schema.json` and identifies allowed trace types by excluding traces with the `gl3d` category.
- [x] 1.2 Define Houmao safety policy in the catalog generator for globally rejected fields such as `*src`, `stream`, `frames`, `template`, `transforms`, remote URLs, executable content, and credential-bearing map settings.
- [x] 1.3 Add a checked-in generated catalog artifact with allowed trace types, excluded trace types and reasons, allowed data paths, allowed style paths, allowed datasource binding paths, and minimal example fixtures.
- [x] 1.4 Add a generator verification test that fails when the checked-in catalog is stale against the local Plotly schema source.

## 2. Python Authoring and Capabilities

- [x] 2.1 Replace the schema version 2 `chartType` Pydantic model with a schema version 3 `figureType: "plotly2d"` trace-first model.
- [x] 2.2 Validate `traces[].type`, `traces[].data`, `traces[].style`, `layout`, `config`, and `extra.plotly` against the generated trace catalog and existing unsafe-content rules.
- [x] 2.3 Reject schema version 2 `chartType` payloads with a migration diagnostic that points authors to schema version 3, `figureType`, and `traces[].type`.
- [x] 2.4 Replace fixed datasource binding validation with catalog-backed `source.bindings` field-path validation.
- [x] 2.5 Update component schema discovery output and example payloads for `houmao.graphic.template` schema version 3.
- [x] 2.6 Update AG-UI capability metadata to advertise schema version 3, `figureType`, supported trace types, excluded true 3D traces, bundle identity, geo/map offline policy, and datasource binding vocabulary.

## 3. Workbench Plotly Renderer

- [x] 3.1 Replace `plotly.js-cartesian-dist-min` with a Plotly bundle strategy that can render every trace type advertised by the Layer 1 trace catalog.
- [x] 3.2 Add a workbench-side catalog module or generated TypeScript artifact that matches the Python catalog.
- [x] 3.3 Rewrite `houmao.graphic.template` browser validation to accept schema version 3 trace-first payloads and reject schema version 2 chart-type payloads.
- [x] 3.4 Rewrite the template compiler to translate Houmao `traces[].data`, `traces[].style`, `layout`, and `config` into Plotly `data`, `layout`, and `config` objects.
- [x] 3.5 Add visible workbench diagnostics for unsupported trace types, unsupported trace fields, unsupported bundle coverage, unsafe content, and datasource-bound payloads when materialization is unavailable.
- [x] 3.6 Update the debug agent and dashboard fixture payloads to use schema version 3 examples.

## 4. Docs and Agent Guidance

- [x] 4.1 Update `docs/reference/gateway/ag-ui.md` to document schema version 3, `figureType: "plotly2d"`, trace-catalog discovery, datasource field-path bindings, true 3D exclusions, and the Plotly-only renderer policy.
- [x] 4.2 Update `context/plans/ag-ui-advanced-cap` so Layer 1 scope says Plotly 2D trace catalog rather than the previous five chart types.
- [x] 4.3 Update the maintained `houmao-interop-ag-ui` skill to teach agents to prefer `houmao.graphic.template` for supported Plotly 2D charts and to inspect capabilities for uncommon trace families.
- [x] 4.4 Update inline examples and smoke prompts that currently emit schema version 2 `chartType` payloads.

## 5. Verification

- [x] 5.1 Add Python tests for schema version 3 validation, all catalog-allowed trace types, true 3D trace rejection, unsafe field rejection, schema version 2 migration diagnostics, and datasource binding field-path validation.
- [x] 5.2 Add capability metadata tests proving supported trace types, excluded trace types, bundle identity, offline geo/map policy, and datasource materialization status are advertised.
- [x] 5.3 Add workbench unit or component tests for schema version 3 payload compilation and invalid-payload fallbacks.
- [x] 5.4 Add Playwright coverage for representative Plotly 2D trace families across cartesian, statistical, matrix, financial, polar or ternary, domain hierarchy, table or indicator, and network or parallel groups.
- [x] 5.5 Run focused checks: `pixi run test`, relevant AG-UI authoring tests, workbench typecheck, and targeted Playwright template-graphics tests.
