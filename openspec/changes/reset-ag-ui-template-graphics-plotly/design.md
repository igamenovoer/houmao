## Context

The repository currently has an experimental Layer 1 `houmao.graphic.template` contract that validates a renderer-neutral `data.values` plus `encoding` payload and renders it in the workbench through Vega-Lite or Recharts. The advanced AG-UI graphing plan changes the direction: Layer 1 is now a Plotly.js-backed template layer, while raw Vega-Lite moves to a future Layer 2 DSL path and scripted D3 remains a future Layer 3 path.

The existing implementation spans Python authoring helpers, AG-UI capability metadata, the workbench browser renderer, the workbench Fastify server, fake and debug agent fixtures, docs, tests, and system skill guidance. The browser also uses Recharts for older fixed `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` component renderers. The repository is under active development and permits breaking changes, so this design favors a clean contract reset, full Recharts retirement, and removal of those legacy fixed chart APIs over compatibility shims for experimental payloads.

## Goals / Non-Goals

**Goals:**

- Make Plotly.js the only Layer 1 template renderer and the default advertised backend.
- Replace the current encoding-based template payload with a curated Plotly-aligned schema based on traces, layout, config, datasource references, and optional `extra.plotly`.
- Keep Layer 1 smaller than raw Plotly by validating an allowlisted subset of chart, trace, layout, config, and extra fields.
- Support static inline charts through `houmao.graphic.template` for the five initial 2D chart types: `bar`, `line`, `scatter`, `pie`, and `histogram`.
- Define datasource binding vocabulary in the schema and capabilities for a future runtime without implementing datasource registry, row storage, materialization, or refresh in this round.
- Surface deterministic renderer diagnostics for invalid renderer ids, unsupported chart families, malformed payloads, datasource-bound payloads that cannot be materialized yet, and rejected `extra.plotly`.
- Remove Recharts completely from the AG-UI workbench runtime, tests, fixture assumptions, and dependency graph.
- Retire the legacy fixed chart component APIs `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` from schema discovery, authoring guidance, workbench registered renderers, debug fixtures, docs, and tests.
- Expose the replacement chart set through `houmao.graphic.template` with `chartType` values and curated Plotly-aligned traces instead of preserving the legacy schema version `1` fixed chart payloads.
- Update docs, capability metadata, system skill guidance, fixtures, and tests so agents no longer choose among Layer 1 renderers.

**Non-Goals:**

- Do not implement raw Vega-Lite, raw Vega, Altair authoring, or `houmao.graphic.vegalite`; those belong to the later Layer 2 change.
- Do not implement sandboxed D3 or arbitrary scripted graphics.
- Do not expose the full Plotly figure schema as the public Houmao template contract.
- Do not support remote data URLs, JavaScript callbacks, HTML, iframes, scriptable SVG, React components, or arbitrary Plotly templates in Layer 1.
- Do not preserve compatibility for experimental Layer 1 payloads that depend on `renderer.preferred: "vega-lite"`, `renderer.fallback: ["recharts"]`, `data.values`, `encoding`, or `extra.vega-lite`.
- Do not preserve `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie` as compatibility aliases, registered renderers, schema discovery entries, or hidden Plotly adapters.
- Do not add new per-chart component names such as `houmao.plotly.bar` or a raw-ish `houmao.graphic.plotly` figure component in this round.
- Do not implement every 2D Plotly.js trace family in this round; broader 2D coverage is deferred.
- Do not implement presentation datasource registry, datasource row updates, server-side Plotly materialization, datasource prompt metadata assembly, or datasource-driven chart refresh in this round.

## Decisions

### Use `schemaVersion: 2` for the Plotly reset

The new payload keeps the `houmao.graphic.template` component name but uses `schemaVersion: 2`. The current schema is materially different: it models rows plus encodings, while the new schema models Plotly-like traces plus layout and config. A version bump makes validation errors clear and lets docs distinguish the archived experiment from the new contract.

Alternative considered: keep `schemaVersion: 1` and change the required fields in place. That would make existing examples appear close enough to be reused even though they are not compatible, so the design rejects it.

### Make Plotly the only Layer 1 renderer id

Capabilities SHALL advertise `renderers: ["plotly"]` and `defaultRenderer: "plotly"`. Authoring validation defaults missing `renderer.preferred` to `plotly`; any non-Plotly renderer id is rejected for authored payloads. The workbench may show a diagnostic for streamed non-Plotly renderer ids, but it must not silently fall back to Vega-Lite or Recharts.

Alternative considered: keep a fallback array for future renderers. The graphing plan intentionally removes renderer choice from Layer 1, and a fallback array would keep agent prompts focused on backend selection rather than chart intent.

### Define a curated Plotly-aligned schema, not raw Plotly

The public Layer 1 schema uses Plotly-compatible names where practical: `traces`, trace `type`, trace `mode`, `x`, `y`, `labels`, `values`, `marker`, `line`, `text`, `hovertemplate`, `layout`, `config`, and `extra.plotly`. The schema validates an allowlisted subset for each covered 2D chart family instead of exposing the full Plotly attribute tree. The five initial `chartType` values are `bar`, `line`, `scatter`, `pie`, and `histogram`. `line` compiles to Plotly scatter-family traces with line mode. The renderer adapter compiles this Houmao payload into a real Plotly figure before calling Plotly.js.

Alternative considered: accept raw Plotly `{data, layout, config}` figures directly. That would be powerful, but it would turn Layer 1 into an unrestricted Plotly DSL, complicate security checks, block stable datasource binding semantics, and blur the boundary with future advanced graphics layers.

### Expose the new chart set through `houmao.graphic.template`

The replacement chart surface SHALL stay inside `houmao.graphic.template`. Agents select chart families with `chartType` and describe series with curated trace fields. This round implements only the five most common 2D chart types: `bar`, `line`, `scatter`, `pie`, and `histogram`. The selected set maps to the local Plotly source reference under `extern/orphan/plotly.js/src/traces/bar`, `extern/orphan/plotly.js/src/traces/scatter`, `extern/orphan/plotly.js/src/traces/pie`, and `extern/orphan/plotly.js/src/traces/histogram`.

Broader 2D Plotly coverage is explicitly deferred. Deferred chart families include `area`, `bubble`, `donut`, `heatmap`, `box`, `violin`, `candlestick`, `ohlc`, `contour`, `histogram2d`, `histogram2dcontour`, `barpolar`, `scatterpolar`, `scatterternary`, geo/map chart families, `sankey`, `funnel`, `funnelarea`, `treemap`, `sunburst`, `icicle`, `image`, `indicator`, `table`, `parcoords`, `parcats`, `splom`, carpet charts, and WebGL variants such as `scattergl`. Unsupported 2D and 3D `chartType` values SHALL produce deterministic validation errors or visible renderer diagnostics.

Alternative considered: create new per-chart component names such as `houmao.plotly.bar` and `houmao.plotly.line`. That would make simple cases explicit, but it would multiply schema discovery entries and recreate the fixed chart API shape being retired.

Alternative considered: create `houmao.graphic.plotly` with an allowlisted Plotly-like figure shape. That would be more flexible, but it would pull Layer 1 closer to raw Plotly and weaken the template contract boundary.

### Use a Plotly bundle that contains the five initial chart types

The workbench dependency SHALL include the Plotly trace modules needed for `bar`, `line`, `scatter`, `pie`, and `histogram`. The implementation may use a small Plotly bundle if it renders those five chart types reliably, but capability metadata and tests must not advertise a chart family that the browser bundle cannot render.

Alternative considered: cover every 2D Plotly trace family now. That would expand schema modeling, renderer compilation, bundle choice, examples, and test matrices beyond this round.

### Define datasource bindings as contract-only fields

Each trace SHALL use either inline arrays or a `source` binding, not both for the same channel. Inline traces carry bounded arrays directly in the payload and render in this round. Datasource-bound traces reference a `dataRef` and map columns to trace channels such as `x`, `y`, `z`, `labels`, `values`, `text`, `marker.color`, and `marker.size`, but this round treats those bindings as schema vocabulary only. If a datasource-bound payload reaches the workbench before materialization exists, the workbench shows a deterministic visible diagnostic instead of a blank chart.

Alternative considered: use Plotly Cloud-style `xsrc` and `ysrc` fields. Houmao needs local presentation-session state, prompt metadata, and deterministic diagnostics, so source bindings remain Houmao-owned instead of adopting Plotly Cloud semantics.

### Advertise datasource binding as unsupported at runtime

Capabilities SHALL describe datasource binding vocabulary separately from runtime materialization. This round advertises the contract shape but reports materialization support as false. Agents and tests can see that `dataRefs` and `source` are reserved schema fields, but they must not infer that the workbench can resolve datasource rows yet.

Alternative considered: reject datasource-bound payloads until materialization ships. The user chose to keep the contract visible now, so validation accepts the shape while runtime rendering remains diagnostic-only.

### Defer datasource registry and materialization

The existing Fastify workbench server already owns presentation sessions, but this round does not extend them with row-bearing datasource registries, update operations, prompt metadata, or server-side Plotly materialization. Those features belong to a follow-up change. The only runtime behavior for datasource-bound template payloads in this round is a visible diagnostic stating that datasource materialization is not supported yet.

Alternative considered: implement datasource materialization now. That would combine the renderer migration with a separate server-state feature and expand the risk beyond the agreed round scope.

### Keep `extra.plotly` small and non-essential

The standardized fields must be enough to render a chart without `extra`. `extra.plotly` supports allowlisted refinements such as margins, axis formatting, legend placement, hover mode, bar gap, marker refinements, line interpolation, and responsive sizing hints. It cannot replace traces, raw data, full layout, full config, frames, transforms, templates, JavaScript callbacks, HTML, iframes, or remote URLs.

Alternative considered: pass `extra.plotly` through to Plotly unchanged. That would recreate the raw Plotly DSL through a side door and make validation misleading.

### Remove the template renderer picker from the workbench

The current pane presentation setting stores `auto`, `vega-lite`, or `recharts`. With only Plotly, the UI should remove the selector or replace it with a read-only renderer label. Stored legacy values should sanitize to the new default and not affect rendering.

Alternative considered: keep the selector with one option. A one-option control suggests a user choice that no longer exists.

### Retire Recharts and legacy fixed chart APIs

The workbench currently uses Recharts in both the template renderer experiment and the older fixed component renderer registry. This change retires Recharts completely and removes the fixed chart component APIs instead of migrating them to a hidden Plotly implementation. `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` SHALL be removed from Python schema discovery, authoring examples, workbench registered renderers, debug sender presets, fake fixtures, docs, and tests. If an older stream still sends one of those tool-call names, the workbench treats it as an unknown or unsupported component and keeps the raw event inspectable.

Alternative considered: preserve `houmao.chart.*` by compiling the legacy payloads into Plotly figures. The user chose to retire those APIs completely, so preserving their names would keep stale guidance and tests alive while the new chart set moves into `houmao.graphic.template`.

## Risks / Trade-offs

- Existing experimental fixtures and demos break because the payload shape changes -> Update fake server, debug agent, smoke prompts, docs, and tests in the same change.
- Legacy fixed chart examples and callers break -> Remove them from supported schema discovery and replace fixtures, docs, and smoke prompts with Plotly-backed `houmao.graphic.template` payloads.
- Plotly bundle size may grow the workbench frontend -> Prefer a small Plotly bundle if it covers the five advertised chart types; otherwise keep the dependency explicit and avoid advertising unsupported chart families.
- A curated schema may lag behind useful Plotly features -> Keep `extra.plotly` narrowly extensible and route complex graphics to Layer 2 or Layer 3 instead of expanding Layer 1 into raw Plotly.
- Datasource binding vocabulary can look usable before runtime support exists -> Capability metadata must state `materializationSupported: false`, and datasource-bound payloads must show visible diagnostics.
- Removing renderer fallback may reduce resilience in the short term -> Use visible diagnostics and a single well-tested Plotly adapter instead of hiding incompatibility behind alternate renderers.

## Migration Plan

1. Update the Python `houmao.graphic.template` model to `schemaVersion: 2`, Plotly-only renderer metadata, curated traces, layout, config, dataRefs, source bindings, and `extra.plotly` validation.
2. Update capability metadata to advertise only Plotly for Layer 1 and to report datasource binding support and limits.
3. Add the workbench Plotly adapter for static inline payloads, including lifecycle cleanup and visible diagnostics.
4. Remove fixed `houmao.chart.bar`, `houmao.chart.line`, and `houmao.chart.pie` component schemas, registered renderers, debug presets, fixtures, docs, smoke prompts, and tests.
5. Remove the Layer 1 Vega-Lite and Recharts template renderer paths, renderer picker UI, legacy stored presentation override semantics, and Recharts dependency.
6. Add datasource binding fields to schema and capability metadata while marking materialization as unsupported in this round.
7. Render datasource-bound template payloads as deterministic visible diagnostics.
8. Update docs, `houmao-interop-ag-ui`, fake/debug agent examples, deterministic workbench tests, real-agent smoke guidance, and dependency manifests.

Rollback is source-control rollback while this feature remains experimental. If partial rollback is needed, revert the implementation to the previous archived `ag-ui-template-graphics` behavior and remove Plotly-only capability metadata so agents do not emit unsupported payloads.

## Open Questions

- Which small Plotly bundle should the workbench use for `bar`, `line`, `scatter`, `pie`, and `histogram`?
- What exact row and byte limits should datasource materialization enforce in the follow-up datasource runtime change?
- Should the follow-up datasource runtime start with `replace` and `append` before adding row patch and delete operations?
