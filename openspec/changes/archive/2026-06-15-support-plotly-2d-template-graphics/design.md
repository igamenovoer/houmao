## Context

Layer 1 template graphics are already Plotly-only, but the implemented contract is narrow: schema version 2 accepts `chartType` values `bar`, `line`, `scatter`, `pie`, and `histogram`, while the workbench imports `plotly.js-cartesian-dist-min`. The current main spec also says deferred 2D chart families such as heatmap and box are outside this round's scope.

The advanced graphing plan now wants Layer 1 to cover Plotly.js 2D graphics while staying templated. That changes the hard problem from choosing a renderer to defining a durable Houmao contract around Plotly's large trace surface. The local Plotly source checkout includes `extern/orphan/plotly.js/dist/plot-schema.json`, which is the best primary reference for trace names, attributes, and trace categories.

## Goals / Non-Goals

**Goals:**

- Let agents use `houmao.graphic.template` for ordinary Plotly.js 2D graphics beyond the initial five chart types.
- Keep Layer 1 as a curated Houmao schema rather than raw unrestricted Plotly figure JSON.
- Make supported trace coverage discoverable through schema output and AG-UI capabilities.
- Share one trace catalog across Python validation, TypeScript workbench validation, examples, capability metadata, and tests.
- Support both inline arrays and datasource-bound trace fields with a binding vocabulary that works for cartesian, financial, domain, table, network, polar, ternary, carpet, map, and matrix-style traces.
- Render allowed traces through Plotly.js in the workbench with deterministic invalid-payload diagnostics.

**Non-Goals:**

- Do not support true 3D scene traces in Layer 1.
- Do not turn `houmao.graphic.template` into a raw Plotly DSL that accepts arbitrary `data`, `layout`, `config`, `frames`, `template`, or callback content.
- Do not add a second Layer 1 renderer.
- Do not move Vega-Lite, Vega, D3, React, HTML, or arbitrary JavaScript into Layer 1.
- Do not implement full datasource materialization semantics beyond the binding vocabulary unless a separate datasource milestone is active.

## Decisions

### Use Schema Version 3 With Trace-First Semantics

Schema version 3 should replace the `chartType`-first model with a Plotly 2D figure envelope. The payload should identify the component through `houmao.graphic.template`, carry `schemaVersion: 3`, keep `renderer.preferred: "plotly"` as the only renderer, and define chart content through `traces[].type`.

The proposed envelope is:

```json
{
  "schemaVersion": 3,
  "figureType": "plotly2d",
  "renderer": { "preferred": "plotly" },
  "title": "Latency Distribution",
  "traces": [
    {
      "type": "violin",
      "name": "api",
      "data": { "y": [21, 33, 37, 44] },
      "style": { "box": { "visible": true } }
    }
  ],
  "layout": { "yaxis": { "title": "ms" } },
  "config": { "responsive": true }
}
```

Version 2 payloads should fail validation with a migration diagnostic. The repository allows breaking changes, and preserving both versions would keep the old chart-type assumptions in every validator, fixture, and agent guidance path.

### Define Plotly 2D by Trace Categories, Then Apply Houmao Policy

The catalog source should start from Plotly's schema and include every trace whose categories do not include `gl3d`. The initial excluded true 3D set is `scatter3d`, `surface`, `mesh3d`, `cone`, `streamtube`, `volume`, and `isosurface`.

This definition intentionally includes non-cartesian but still 2D trace families: polar, ternary, smith, carpet, geo, map, mapbox, domain traces, table, sankey, parcoords, parcats, splom, financial traces, heatmaps, contours, treemaps, sunbursts, icicles, funnelarea, and indicator. Houmao policy then narrows unsafe or environment-dependent fields. For map and geo traces, Layer 1 should use an offline-first policy: no remote URLs, no credential-bearing tokens, and no user-provided tile/style URLs.

### Generate a Houmao Trace Catalog

Do not hand-maintain large trace lists separately in Python and TypeScript. Add a repo-owned catalog artifact generated from `extern/orphan/plotly.js/dist/plot-schema.json`, then check in the generated Houmao catalog used at runtime.

The catalog should describe:

- allowed trace types
- disallowed trace types and reasons
- required or minimal data fields for each trace family
- allowed inline data field paths
- allowed style field paths
- allowed layout fragments associated with coordinate systems
- allowed datasource binding paths
- unsafe paths rejected globally, including `*src`, `stream`, `frames`, `template`, `transforms`, arbitrary URLs, HTML, and executable content
- minimal example traces for tests and docs

The Python authoring path and TypeScript workbench path should consume generated code or a shared checked-in JSON catalog, not duplicate the source schema manually.

### Keep the Public Payload Curated

The public v3 schema should map Plotly concepts into explicit Houmao sections:

- `traces[].type`: required Plotly trace type from the catalog.
- `traces[].data`: trace data arrays and nested data objects, such as `x`, `y`, `z`, `open`, `high`, `low`, `close`, `labels`, `values`, `node`, `link`, `dimensions`, `header`, and `cells`.
- `traces[].style`: safe trace presentation fields such as marker, line, fill, colorscale, contours, box, meanline, text, hover template, and opacity where allowed by the catalog.
- `layout`: safe figure layout fields, including axes, polar, ternary, smith, geo/map layout fragments, legend, margins, domain, grid, hover mode, barmode, and responsive sizing.
- `config`: safe Plotly config fields such as responsive mode, mode bar display policy, scroll zoom, and static plot.
- `extra.plotly`: optional non-essential renderer refinements only, still not a raw figure replacement.

The workbench compiler can convert this envelope into Plotly's `{ data, layout, config }` shape immediately before `Plotly.react`.

### Generalize Datasource Bindings to Field Paths

The current `source.x.column` vocabulary does not scale to `sankey.link.value`, `candlestick.open`, `table.cells.values`, or `parcoords.dimensions[].values`. Version 3 should use field-path bindings:

```json
{
  "type": "candlestick",
  "source": {
    "dataRef": "prices",
    "bindings": {
      "data.x": { "column": "date" },
      "data.open": { "column": "open" },
      "data.high": { "column": "high" },
      "data.low": { "column": "low" },
      "data.close": { "column": "close" }
    }
  }
}
```

Nested trace families use the same shape:

```json
{
  "type": "sankey",
  "source": {
    "dataRef": "flows",
    "bindings": {
      "data.node.label": { "column": "node_label" },
      "data.link.source": { "column": "source_index" },
      "data.link.target": { "column": "target_index" },
      "data.link.value": { "column": "value" }
    }
  }
}
```

Validation should reject any field path not in the trace catalog, reject inline data and source bindings for the same path, and keep datasource materialization status explicit in capabilities.

### Use a Plotly Bundle That Matches the Catalog

The current `plotly.js-cartesian-dist-min` dependency cannot satisfy all allowed 2D trace families. The preferred implementation is a custom Plotly bundle built from `plotly.js/lib/core` plus registered allowed trace modules. A full `plotly.js-dist-min` dependency is acceptable as a first implementation shortcut only if validation still rejects 3D traces and unsafe fields.

The capability metadata should advertise the actual bundle id and trace types registered in the browser. Renderer validation should fail visibly when a payload uses a catalog-allowed trace that is absent from the loaded bundle, because a blank chart is worse than an explicit unsupported-bundle diagnostic.

### Catalog-Driven Tests

Tests should use the catalog rather than one-off hand lists. Python tests should validate the schema, normalized payloads, unsafe field rejection, and capability metadata for every allowed trace type. Browser tests should render a representative fixture matrix across trace families, with a smaller full-catalog smoke option when runtime cost is acceptable.

Useful browser groups are cartesian SVG, GL 2D, statistical, matrix, financial, polar/ternary/smith, carpet, domain hierarchy, table/indicator, network/parallel, and geo/map. Each group needs visible Plotly evidence and invalid-payload fallback coverage.

## Risks / Trade-offs

- Large Plotly bundle size -> Prefer a custom 2D bundle; accept the full bundle only as a short-lived implementation shortcut and measure workbench load impact.
- Plotly schema drift -> Pin catalog generation to the installed Plotly version and commit generated catalog output so changes are reviewed.
- Raw Plotly creep -> Keep `data`, `layout`, `config`, and `extra.plotly` allowlisted, and reject backend replacement fields early in Python validation.
- Geospatial rendering ambiguity -> Require offline-safe defaults and reject remote map tile/style URLs or credential-bearing map settings.
- Validator complexity -> Generate Python and TypeScript artifacts from the same catalog rather than hand-coding equivalent logic twice.
- Test runtime growth -> Split tests into fast catalog validation, representative browser groups, and optional full-catalog browser smoke.

## Migration Plan

1. Add the trace catalog generator and checked-in catalog output.
2. Replace Python authoring models with schema version 3 trace-first validation and clear migration diagnostics for schema version 2 payloads.
3. Replace workbench validation and compilation with catalog-backed v3 support.
4. Replace the cartesian Plotly dependency with a bundle that covers the allowed 2D catalog.
5. Update capabilities, docs, debug-agent examples, dashboard examples, and the AG-UI interop skill.
6. Remove or rewrite tests and fixtures that assert the old five-chart-type contract.

Rollback is simple before archive: restore the previous v2 contract and cartesian Plotly bundle. After archive, rollback would require a new breaking-change proposal because the public schema version would already have advanced.

## Open Questions

- Whether the first implementation should use a full Plotly bundle for speed of delivery or invest immediately in a custom 2D bundle.
- Whether mapbox trace aliases should be accepted initially or deferred behind the same map/geo offline policy as newer map traces.
- Whether v2 payloads should be rejected everywhere or accepted only in the workbench as a temporary local compatibility path. The recommended path is rejection with migration diagnostics.
