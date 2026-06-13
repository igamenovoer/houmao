# AG-UI Advanced Graphing Capability Roadmap

## Scope

This roadmap covers graphing capability beyond the current fixed chart components and SVG compatibility path. It assumes the live per-agent gateway remains the source of truth for AG-UI routing, stream delivery, and lifecycle boundaries. The workbench remains a GUI harness for already-running agents and must not gain managed-agent lifecycle ownership as part of graphing work.

The revised target stack has three graphing layers:

1. Template graphics: one Plotly-aligned standardized Houmao chart schema rendered through Plotly.js, with static inline data and dynamic datasource bindings backed by the GUI presentation server.
2. Vega DSL graphics: raw Vega-Lite and possibly raw Vega specs rendered with `vega-embed`, with Python Altair as the main authoring bridge.
3. D3.js scripted graphics: sandboxed agent-authored JavaScript that uses D3 inside an isolated iframe.

This roadmap intentionally removes Recharts, Apache ECharts, and Vega-Lite from the planned Layer 1 backend set. Vega-Lite moves to Layer 2.

## Milestone 1: Reset the Layer 1 Backend Contract Around Plotly

Goal: keep Layer 1 templated graphics, but make Plotly.js the only Layer 1 renderer and align the standardized schema with Plotly concepts as much as possible without exposing raw unrestricted Plotly figures as the whole contract.

Decisions:

- Layer 1 renderer ids SHALL include only `plotly` for the next design pass.
- Plotly.js SHALL be the only Layer 1 renderer.
- The Layer 1 schema SHALL be Plotly-aligned, using trace-like series, layout-like axes and legends, and config-like interaction options where practical.
- The Layer 1 schema SHALL NOT be the complete raw Plotly.js builtin schema. The raw Plotly schema may inform field names, validation allowlists, examples, and converter behavior, but the public Houmao template schema remains curated.
- Recharts SHALL be removed from the planned Layer 1 backend set.
- Apache ECharts SHALL be removed from the planned Layer 1 backend set.
- Vega-Lite SHALL be removed from the Layer 1 backend set and reserved for Layer 2.
- Layer 1 `extra` SHALL be scoped to `extra.plotly`.
- Layer 1 SHALL support static inline data for immutable snapshots.
- Layer 1 SHALL support dynamic datasource bindings for presentation-server-managed data.
- Dynamic datasource contents SHALL remain in server-owned presentation sessions unless explicitly sent as a bounded render materialization.
- The agent prompt SHALL include compact datasource metadata for presentation-server-managed datasources, including id, scope, kind, column schema, version, row count, update mode, and optional semantic descriptions.
- The agent prompt SHALL NOT include full dynamic datasource rows by default.
- Layer 1 SHALL NOT accept raw Plotly trace/layout/config replacement, Vega-Lite specs, JavaScript callbacks, HTML, iframes, or remote data URLs.

Deliverables:

- Revised `houmao.graphic.template` schema metadata that lists only the `plotly` renderer id.
- Capability metadata with `renderers: ["plotly"]` and `defaultRenderer: "plotly"`.
- Updated docs and agent guidance that remove Recharts, ECharts, and Layer 1 Vega-Lite from the template backend story.
- A migration note for existing experimental workbench code that still advertises or implements Recharts, ECharts, or Vega-Lite as Layer 1 template renderers.

Todo:

- [x] Use a Plotly 2D trace catalog rather than a fixed chart-type list; supported trace types are generated from Plotly.js schema metadata by excluding true 3D scene traces and applying Houmao safety policy.
- [x] Define the exact boundary between curated Plotly-aligned fields and raw Plotly fields through catalog-backed `traces[].data`, `traces[].style`, policy-checked `layout` and `config`, and rejected raw figure replacement fields.
- [x] Define the trace-like data shape around `traces[].type`, optional `name`, `data`, and `style`, including nested fields such as `node`, `link`, `header`, `cells`, financial OHLC fields, polar fields, and table fields where the catalog allows them.
- [x] Define the dynamic trace binding shape with datasource refs and catalog field-path mappings under `source.bindings`, such as `data.x`, `data.y`, `data.open`, `data.node.label`, `data.link.value`, `data.header.values`, and `data.cells.values`.
- [ ] Define the layout-like common shape, including title, axes, legend, margins, annotations, subplot hints, and responsive sizing.
- [ ] Define the config-like interaction shape, including tooltip or hover behavior, mode bar policy, responsiveness, and static-vs-interactive mode.
- [ ] Define `renderer.preferred` semantics when the only supported renderer is `plotly`.
- [ ] Define `extra.plotly` allowlisted fragments such as narrow layout refinements, hover mode, axis formatting, marker refinements, and bar gap.
- [ ] Decide whether unsupported known `extra.plotly` fields produce warnings, diagnostics records, or silent no-ops.
- [ ] Add examples for Plotly-first payloads rendered through Plotly.
- [ ] Add tests proving standardized payloads render through Plotly without `extra`.
- [ ] Add tests proving unsupported `extra.plotly` is ignored or reported without breaking rendering.

Done when:

- Agents can emit one standard template payload without choosing among template renderers.
- Agents can emit either static inline chart data or datasource-bound chart payloads.
- The GUI renders every valid Layer 1 payload through Plotly unless the payload explicitly targets a chart family not supported by the chosen Plotly bundle.
- Backend-specific tuning exists only as optional `extra.plotly`.
- Recharts, ECharts, and Vega-Lite are absent from Layer 1 documentation, capabilities, and renderer selection.

## Milestone 2: Add Layer 1 Datasource Binding and Prompt Metadata

Goal: let agents write Plotly template graphics over presentation-server-managed dynamic data without copying volatile rows into the prompt, chart payload, or browser state.

Decisions:

- Datasources SHALL be separate server-owned presentation-session state objects, not hidden fields inside chart payloads.
- The first datasource kind SHALL be `table`.
- Datasource scope SHALL be explicit, starting with `pane`, `thread`, and `workspace`.
- Datasource updates SHALL support `replace`, `append`, `patchRows`, `deleteRows`, and `clear`.
- Dynamic chart payloads SHALL reference datasources by stable id through `dataRefs`.
- Trace fields SHALL use Houmao-owned field-path source bindings such as `source.dataRef` plus `source.bindings["data.x"].column` and `source.bindings["data.link.value"].column`, not Plotly Cloud `xsrc` or `ysrc` semantics.
- The GUI backend SHALL resolve source bindings into bounded Plotly trace arrays or materializations before the browser calls Plotly.
- Prompt metadata SHALL describe datasource shape and freshness, but it SHALL NOT be treated as the render-time source of truth.
- Missing datasource ids, missing columns, incompatible column types, and stale versions SHALL produce visible renderer diagnostics instead of silent blank charts.

Example datasource metadata shown to the agent:

```json
{
  "id": "gui.selection.metrics",
  "scope": "pane",
  "kind": "table",
  "version": 18,
  "rowCount": 240,
  "updateMode": "replace",
  "columns": [
    { "name": "timestamp", "type": "datetime" },
    { "name": "component", "type": "string" },
    { "name": "latency_ms", "type": "number" }
  ]
}
```

Example dynamic chart binding:

```json
{
  "schemaVersion": 3,
  "figureType": "plotly2d",
  "renderer": { "preferred": "plotly" },
  "title": "Latency Over Time",
  "dataRefs": [
    { "id": "gui.selection.metrics", "required": true }
  ],
  "traces": [
    {
      "type": "scatter",
      "name": "Latency",
      "style": { "mode": "lines+markers" },
      "source": {
        "dataRef": "gui.selection.metrics",
        "bindings": {
          "data.x": { "column": "timestamp" },
          "data.y": { "column": "latency_ms" },
          "data.text": { "column": "component" }
        }
      }
    }
  ]
}
```

Todo:

- [ ] Define `HoumaoDatasourceMetadata` with id, scope, kind, version, row count, update mode, columns, optional descriptions, and optional freshness.
- [ ] Define `HoumaoDatasourceUpdatePayload` for table rows and update operations.
- [ ] Define `HoumaoGraphicDataRef` and trace source binding models.
- [ ] Decide whether datasource ids are chosen by GUI, agent, or gateway for each scope.
- [ ] Add capability metadata for datasource support, supported scopes, supported update modes, max rows, max bytes, and whether prompt metadata includes rows.
- [ ] Add prompt assembly that includes datasource metadata for active presentation-server-managed datasources.
- [ ] Keep prompt datasource metadata separate from removed canvas-size and volatile AG-UI context entries.
- [ ] Add presentation-session datasource registry keyed by scope and id.
- [ ] Add server-side binding resolution that compiles datasource columns into bounded Plotly trace arrays or materializations.
- [ ] Add renderer diagnostics for missing datasource, missing column, type mismatch, empty datasource, and stale version warnings.
- [ ] Add tests for static inline payloads, datasource-bound payloads, datasource replacement, append updates, missing refs, and stale metadata.

Done when:

- Agents can see datasource metadata in the prompt and write valid Plotly template bindings against it.
- The GUI backend can update a datasource and refresh every bound Plotly chart without asking the agent to resend the chart.
- Static inline charts and dynamic datasource-bound charts share one Layer 1 schema.
- Prompt metadata helps authoring but does not become the render-time data source.

## Milestone 3: Implement the Layer 1 Plotly Adapter

Goal: ship Plotly.js as the single Layer 1 renderer and remove the old multi-backend template renderer assumption.

Initial renderer adapter:

- Plotly.js: default and only Layer 1 renderer, and the schema alignment target.

Migration from current implementation:

- Remove Recharts template rendering code and dependencies when no longer used by compatibility components.
- Remove Vega-Lite template rendering code from Layer 1.
- Do not add ECharts template rendering code.
- Keep `vega`, `vega-lite`, and `vega-embed` only for Layer 2 when that milestone lands.
- Replace the workbench template renderer dropdown with either no control or a fixed `plotly` display, unless future non-template layers need a separate selector.
- Update capability metadata, test fixtures, docs, and agent-facing examples.

Todo:

- [ ] Add or revise the renderer registry so Layer 1 resolves to `plotly`.
- [ ] Resolve dynamic datasource bindings through the presentation server before constructing Plotly trace data.
- [ ] Use `Plotly.react` as the default refresh path when bound datasource versions change.
- [ ] Consider `Plotly.extendTraces` only as an internal optimization for append-only datasource updates.
- [ ] Add adapter-level validation for supported chart types and allowed `extra.plotly` fields.
- [ ] Keep renderer selection deterministic: forced GUI override is unnecessary while only Plotly exists; payload `renderer.preferred` may be accepted only when it is `plotly`.
- [ ] Surface selected renderer and ignored `extra.plotly` warnings in diagnostics.
- [ ] Add visual fixtures for Plotly-first payloads across common chart families.
- [ ] Add browser tests for renderer-specific `extra.plotly` behavior.
- [ ] Add browser tests for pie or donut charts, line charts, scatter charts, grouped bars, and multi-trace layouts.

Done when:

- The workbench renders Layer 1 payloads through Plotly by default.
- The workbench renders both inline static charts and datasource-bound dynamic charts through Plotly.
- The GUI no longer presents ECharts, Recharts, or Vega-Lite as Layer 1 choices.
- Renderer-specific differences no longer complicate the standardized contract.

## Milestone 4: Add Vega DSL Graphics and Altair Authoring

Goal: give agents full declarative graphics freedom through the Vega ecosystem without allowing arbitrary React or JavaScript execution.

Recommended libraries:

- Python gateway and tooling: `altair`, `jsonschema`, and optionally `vl-convert-python`.
- TypeScript GUI: `vega`, `vega-lite`, and `vega-embed`.

Contracts:

- Tool name: `houmao.graphic.vegalite`.
- Tool name: `houmao.graphic.vega`.
- Payload contains `schemaVersion`, `library`, `specVersion`, `title`, optional `description`, the raw `spec`, and optional display metadata.
- Inline data values are allowed with size limits.
- Remote data URLs are disabled by default or restricted by explicit allowlist.
- The GUI renderer owns theme, autosizing defaults, error display, and renderer cleanup.

Altair path:

```python
import altair as alt
import pandas as pd

df = pd.DataFrame({"status": ["ready", "queued"], "count": [58, 23]})
chart = alt.Chart(df).mark_arc().encode(
    theta="count:Q",
    color="status:N",
    tooltip=["status:N", "count:Q"],
)
spec = chart.to_dict()
```

The agent sends `spec` as a Layer 2 Vega-Lite payload. If raw Vega is needed, an optional helper can compile with `vl-convert-python` before publishing.

Todo:

- [ ] Define `HoumaoVegaLiteGraphicPayload` in Python with title, spec version, spec object, and metadata.
- [ ] Define `HoumaoVegaGraphicPayload` only if direct Vega is included in the first release.
- [ ] Add backend validation for payload size, required JSON object shape, and forbidden high-risk fields.
- [ ] Decide whether Python preflight compiles specs with `vl-convert-python` during validation or only validates shape and lets the GUI renderer report compile errors.
- [ ] Add CLI authoring helpers for validating and rendering Vega DSL event batches.
- [ ] Add a workbench renderer that mounts Vega-Lite and optionally Vega specs in a bounded responsive container.
- [ ] Add renderer cleanup so repeated specs do not leak Vega views.
- [ ] Add capability metadata for supported DSL library, supported major version, max payload bytes, max inline rows, and remote data policy.
- [ ] Add deterministic examples for bar chart, pie chart, layered chart, interactive selection, tooltip, linked view, and one direct Vega example if enabled.
- [ ] Add tests for malformed specs, oversized inline data, disabled remote URLs, and successful interactive render smoke.

Done when:

- A user who wants custom templates can use a raw Vega-Lite or Vega spec rather than extending Layer 1.
- Altair-generated Vega-Lite JSON can be validated, sent through AG-UI, and rendered by the workbench.
- Capabilities make it clear that this is Vega DSL, not template graphics and not JavaScript code execution.

## Milestone 5: Plan D3.js Scripted Graphics

Goal: define the future custom scripted graphics contract and sandbox requirements before enabling it by default.

Recommended libraries:

- Python gateway and tooling: `pydantic` for manifest validation and optional out-of-process Node or Bun preflight.
- TypeScript GUI: `d3`, sandboxed iframe runtime, and optional `esbuild-wasm` only if TypeScript or bundling becomes necessary.

Contract:

- Tool name: `houmao.graphic.d3_script`.
- Payload contains `schemaVersion`, `title`, optional `description`, `scriptKind`, `code`, `data`, optional `style`, optional `propsSchema`, `permissions`, and display metadata.
- The script exports `render(context)` and may return a cleanup function.
- The context provides `d3`, `container`, `data`, `width`, `height`, `theme`, and a narrow optional `emit` function.
- The script runs only inside a sandboxed iframe and communicates with the workbench through `postMessage`.

Security posture:

- Disabled by default in normal capabilities.
- Requires explicit workbench setting or trusted mode.
- Runs in a sandboxed iframe.
- No access to parent DOM, localStorage, cookies, credentials, mailbox content, memory content, or tmux sockets.
- Network disabled or allowlisted by default.
- Dependency list starts with D3 only; additional dependencies require explicit allowlisting and version pinning.
- Payload size, file count, compile time, render time, and console output are bounded.

Todo:

- [ ] Decide whether the first prototype accepts plain JavaScript modules only, or also TypeScript through `esbuild-wasm`.
- [ ] Define the script payload model and minimum source format.
- [ ] Define the iframe sandbox flags and parent-child message protocol.
- [ ] Define the D3 render context interface and cleanup lifecycle.
- [ ] Define dependency policy, starting with `d3` only.
- [ ] Add GUI trust controls and visible enabled or disabled state for D3 scripts.
- [ ] Add compile error, runtime error, timeout, dependency rejection, and permission rejection fallbacks.
- [ ] Add test fixtures for a valid tiny D3 chart, a compile error, attempted parent access, attempted network access, excessive CPU loop, and cleanup after pane clear.
- [ ] Decide whether D3 script payloads can be cached client-side, and if so, what metadata is safe to persist.

Done when:

- The D3 script contract is documented and capability-gated.
- The workbench can keep reporting the feature as planned or disabled until the sandbox is implemented.
- Layer 1 and Layer 2 remain the recommended routes unless the user explicitly needs scripted D3 behavior.

## Milestone 6: Agent-Facing Authoring Guidance

Goal: teach agents to choose the least powerful graphing layer that satisfies the requested visual output.

Selection rule:

1. Use Layer 1 template graphics with static inline data for ordinary snapshot charts.
2. Use Layer 1 template graphics with datasource bindings when the GUI owns or updates the data.
3. Add Layer 1 `extra.plotly` only for non-essential Plotly refinements.
4. Use Layer 2 Vega-Lite when the user needs a backend-native declarative grammar, Altair output, custom chart structure, or custom interaction.
5. Use Layer 2 direct Vega only when Vega-Lite cannot express the needed behavior.
6. Use Layer 3 D3.js only when the GUI advertises explicit support and the requested graphic needs scripted DOM/SVG/canvas behavior.

Todo:

- [ ] Update `houmao-interop-ag-ui` guidance to explain the three graphing layers.
- [ ] Add examples for Plotly-only Layer 1 payloads.
- [ ] Add examples for datasource-bound Layer 1 payloads that reference prompt datasource metadata.
- [ ] Teach agents to request datasource metadata when they need dynamic GUI data, and to avoid copying volatile GUI rows into ordinary prompt context.
- [ ] Add examples for raw Vega-Lite specs generated by Altair.
- [ ] Add examples for D3.js scripted graphics, clearly marked as sandboxed and disabled by default until implemented.
- [ ] Add repair guidance for validation failures per layer.
- [ ] Make publish-result reporting unchanged: never claim a GUI displayed graphics unless delivery and render evidence support that claim.
- [ ] Teach agents not to guess GUI destination routing ids.

Done when:

- Agents default to standardized template graphics.
- Agents use datasource bindings when charts should follow GUI-updated data.
- Agents understand that Layer 1 `extra.plotly` is optional and disposable.
- Agents choose Vega DSL for custom declarative specs and D3 only for custom scripted graphics.
- Agents do not use D3 scripts unless the GUI advertises explicit support.

## Milestone 7: Capability, Compatibility, and Tests

Goal: make the advanced graphing capability set discoverable and regression-resistant.

Deliverables:

- Capabilities report Plotly template support, static inline data support, datasource binding support, datasource prompt metadata policy, `extra.plotly` policy, Vega DSL support, D3 script support, versions, limits, sandbox policy, and whether explicit enablement is required.
- Workbench renderers show layer-specific fallback details.
- Unit tests cover backend validation for all enabled layers.
- Browser tests cover successful render, selected renderer behavior where applicable, ignored `extra.plotly`, state isolation, and sandbox failures.
- Documentation explains transport-vs-renderer separation clearly: the gateway may carry opaque AG-UI events, but the GUI renders only recognized and enabled graphing contracts.

Suggested test cases:

- `test_capabilities_list_plotly_template_renderer_and_extra_policy`.
- `test_template_payload_renders_without_extra_plotly`.
- `test_template_payload_renders_with_static_inline_data`.
- `test_template_payload_renders_with_datasource_binding`.
- `test_datasource_metadata_is_included_in_agent_prompt_without_rows`.
- `test_datasource_update_refreshes_bound_plotly_chart`.
- `test_datasource_bound_chart_reports_missing_column`.
- `test_template_extra_plotly_is_allowlisted`.
- `test_template_rejects_full_plotly_figure_replacement`.
- `test_vegalite_payload_rejects_remote_data_when_disabled`.
- `test_vegalite_payload_accepts_altair_generated_inline_spec`.
- `test_workbench_renders_vegalite_spec`.
- `test_workbench_shows_vegalite_compile_error_fallback`.
- `test_d3_script_capability_disabled_by_default`.
- `test_d3_script_runs_only_in_sandbox_when_enabled`.
- `test_d3_script_rejects_unapproved_dependency`.
- `test_d3_script_cannot_access_parent_dom_or_local_storage`.
- `test_d3_script_timeout_unloads_iframe`.

Done when:

- The layers are visible as separate capabilities.
- Datasource binding is visible as a Layer 1 capability rather than a hidden GUI behavior.
- Each layer has a distinct validation and renderer path.
- Backend-specific Layer 1 tuning does not weaken the curated Plotly-aligned contract.
- Higher freedom does not weaken lower-risk defaults.
