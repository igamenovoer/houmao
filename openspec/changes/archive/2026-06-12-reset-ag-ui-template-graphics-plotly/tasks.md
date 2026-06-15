## 1. Python Contract and Capabilities

- [x] 1.1 Update `houmao.graphic.template` constants to schema version `2`, renderer ids `["plotly"]`, default renderer `plotly`, and the five initial `chartType` values `bar`, `line`, `scatter`, `pie`, and `histogram`.
- [x] 1.2 Replace the current row-and-encoding Pydantic model with curated Plotly-aligned models for the five initial chart types, inline arrays, layout, config, dataRefs, trace source bindings, and display metadata.
- [x] 1.3 Add validation that defaults missing renderer metadata to Plotly and rejects non-Plotly renderer ids, legacy fallback semantics, legacy `data.values` plus `encoding` payloads, remote URLs, unsafe text, and raw backend replacement fields.
- [x] 1.4 Add `extra.plotly` validation with an allowlist for non-essential presentation refinements and rejection for raw `data`, `traces`, full `layout`, full `config`, frames, transforms, templates, JavaScript, HTML, iframes, SVG, and remote URLs.
- [x] 1.5 Update component schema discovery, validation output, render-to-events normalization, and examples so generated AG-UI events carry schema version `2` and stable camelCase fields.
- [x] 1.6 Update AG-UI capability metadata to advertise Plotly as the only Layer 1 renderer, include datasource binding support and limits, and report that raw Plotly and raw Vega-Lite DSLs are not Layer 1 template graphics.
- [x] 1.7 Update Python unit tests for valid inline payloads for `bar`, `line`, `scatter`, `pie`, and `histogram`, omitted renderer defaults, invalid non-Plotly renderer ids, unsupported 2D and 3D chart types, legacy payload rejection, safe `extra.plotly`, unsafe `extra.plotly`, capability metadata, and event rendering.
- [x] 1.8 Remove legacy fixed chart components `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` from Python component schema discovery, authoring examples, render-to-events support, CLI docs, and tests; validation for those retired names must fail as unsupported.

## 2. Workbench Plotly Renderer and Recharts Retirement

- [x] 2.1 Select and add a Plotly.js frontend dependency bundle that contains `bar`, `scatter`, `pie`, and `histogram` trace modules, with any required TypeScript types, then remove `recharts` from the workbench dependency manifest and lockfile.
- [x] 2.2 Replace the current `templateGraphics.tsx` multi-renderer registry with a Plotly adapter that validates schema version `2`, compiles Houmao traces/layout/config into Plotly objects, and renders inline charts with `Plotly.react`.
- [x] 2.3 Implement chart-family compilation for `bar`, `line`, `scatter`, `pie`, and `histogram`, including multi-trace Cartesian charts, marker styling, line styling, text, hover templates, axes, legends, margins, and responsive sizing.
- [x] 2.4 Add Plotly lifecycle cleanup with `Plotly.purge` when a template graphic unmounts, rerenders, or is cleared.
- [x] 2.5 Remove fixed `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` from the workbench registered renderer map, dashboard child examples, fake fixtures, debug sender presets, and deterministic tests; older streams using those names must remain visible through the unknown/unsupported component fallback.
- [x] 2.6 Remove all workbench runtime imports from `recharts`, Recharts-specific test selectors, and Recharts-specific CSS or fixture assumptions.
- [x] 2.7 Replace the template renderer picker and stored `templateGraphicBackend` override with no renderer control or a read-only Plotly label, and sanitize any legacy stored values to the Plotly default.
- [x] 2.8 Update workbench renderer diagnostics for malformed payloads, unsupported chart types, unsupported trace shapes, invalid renderer ids, rejected extra fields, and legacy schema payloads.
- [x] 2.9 Update fake AG-UI server fixtures, debug agent fixtures, debug panel examples, and workbench tests to emit Plotly-backed schema version `2` template payloads instead of `houmao.chart.*` payloads.

## 3. Datasource Binding Vocabulary

- [x] 3.1 Add datasource binding fields to Python schema validation, including `dataRefs` and trace `source` channel mappings, while keeping them contract-only.
- [x] 3.2 Update AG-UI capabilities to distinguish datasource binding vocabulary support from datasource materialization support and report materialization as unsupported in this round.
- [x] 3.3 Add browser renderer diagnostics for datasource-bound template payloads received while materialization support is false.
- [x] 3.4 Add tests proving datasource-bound payload shape validates, capabilities do not advertise materialization, and datasource-bound rendering produces a visible diagnostic rather than a blank chart.

## 4. Documentation and Agent Guidance

- [x] 4.1 Update `docs/reference/gateway/ag-ui.md` to describe the Plotly-only Layer 1 schema, renderer metadata, static inline examples, contract-only datasource-bound examples, `extra.plotly`, and the Layer 1 boundary against raw Plotly and Vega-Lite.
- [x] 4.2 Update `houmao-interop-ag-ui` guidance so agents use Plotly-backed `houmao.graphic.template`, stop choosing Layer 1 renderers, treat datasource bindings as reserved vocabulary until materialization is advertised, and validate before publishing.
- [x] 4.3 Update real-agent GUI smoke prompts and deterministic smoke fixtures so they require a visible Plotly-backed `houmao.graphic.template` chart instead of Vega-Lite or Recharts evidence.
- [x] 4.4 Remove or rewrite stale mentions of `renderer.preferred: "vega-lite"`, `renderer.fallback: ["recharts"]`, `extra.vega-lite`, `houmao.chart.bar`, `houmao.chart.line`, `houmao.chart.pie`, Recharts DOM selectors, Recharts dependency guidance, and Layer 1 Vega-Lite/Recharts support from docs, tests, fixtures, and skill text.
- [x] 4.5 Add a migration note explaining that previous experimental schema version `1` template payloads and legacy fixed `houmao.chart.*` payloads must be rewritten to schema version `2` `houmao.graphic.template`.

## 5. Verification

- [x] 5.1 Run `pixi run test` and confirm Python authoring, capability, docs, and command tests pass.
- [x] 5.2 Run `pixi run lint` and `pixi run typecheck`.
- [x] 5.3 Run `bun run typecheck` and `bun run build` in `apps/ag-ui-workbench`.
- [x] 5.4 Run deterministic workbench Playwright coverage for inline `bar`, `line`, `scatter`, `pie`, and `histogram` charts, datasource-bound diagnostic-only payloads, retired fixed-chart fallback behavior, visible diagnostics, and renderer control removal.
- [x] 5.5 Add compile/render unit coverage for every advertised `chartType`, including unsupported 2D chart types, rejected 3D families, and unsupported trace-shape diagnostics.
- [x] 5.6 Verify `rg -n "from \\\"recharts\\\"|from 'recharts'|recharts|Recharts" apps/ag-ui-workbench` has no remaining runtime, dependency, fixture, test-selector, or documentation references except intentional migration notes if any.
- [x] 5.7 Run or update the real-agent GUI graphics smoke only after deterministic coverage passes.
- [x] 5.8 Run `openspec status --change reset-ag-ui-template-graphics-plotly` and any available OpenSpec validation command to confirm the change remains apply-ready.
