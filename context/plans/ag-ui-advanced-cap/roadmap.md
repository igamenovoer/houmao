# AG-UI Advanced Graphing Capability Roadmap

## Scope

This roadmap covers graphing capability beyond the current fixed chart components and SVG compatibility path. It assumes the live per-agent gateway remains the source of truth for AG-UI routing, stream delivery, and lifecycle boundaries. The workbench remains a GUI harness for already-running agents and must not gain managed-agent lifecycle ownership as part of graphing work.

The revised target stack has three graphing layers:

1. Template graphics: one Plotly-aligned standardized Houmao chart schema rendered through Plotly.js.
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
- Layer 1 SHALL NOT accept raw Plotly trace/layout/config replacement, Vega-Lite specs, JavaScript callbacks, HTML, iframes, or remote data URLs.

Deliverables:

- Revised `houmao.graphic.template` schema metadata that lists only the `plotly` renderer id.
- Capability metadata with `renderers: ["plotly"]` and `defaultRenderer: "plotly"`.
- Updated docs and agent guidance that remove Recharts, ECharts, and Layer 1 Vega-Lite from the template backend story.
- A migration note for existing experimental workbench code that still advertises or implements Recharts, ECharts, or Vega-Lite as Layer 1 template renderers.

Todo:

- [ ] Confirm whether the standardized chart types remain bar, line, scatter, area, pie or donut.
- [ ] Decide the exact boundary between curated Plotly-aligned fields and raw Plotly fields.
- [ ] Define the trace-like common data shape, including `type`, `name`, `x`, `y`, `z`, `labels`, `values`, marker style, line style, color, size, text, hover, and series semantics.
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
- The GUI renders every valid Layer 1 payload through Plotly unless the payload explicitly targets a chart family not supported by the chosen Plotly bundle.
- Backend-specific tuning exists only as optional `extra.plotly`.
- Recharts, ECharts, and Vega-Lite are absent from Layer 1 documentation, capabilities, and renderer selection.

## Milestone 2: Implement the Layer 1 Plotly Adapter

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
- [ ] Add adapter-level validation for supported chart types and allowed `extra.plotly` fields.
- [ ] Keep renderer selection deterministic: forced GUI override is unnecessary while only Plotly exists; payload `renderer.preferred` may be accepted only when it is `plotly`.
- [ ] Surface selected renderer and ignored `extra.plotly` warnings in diagnostics.
- [ ] Add visual fixtures for Plotly-first payloads across common chart families.
- [ ] Add browser tests for renderer-specific `extra.plotly` behavior.
- [ ] Add browser tests for pie or donut charts, line charts, scatter charts, grouped bars, and multi-trace layouts.

Done when:

- The workbench renders Layer 1 payloads through Plotly by default.
- The GUI no longer presents ECharts, Recharts, or Vega-Lite as Layer 1 choices.
- Renderer-specific differences no longer complicate the standardized contract.

## Milestone 3: Add Vega DSL Graphics and Altair Authoring

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

## Milestone 4: Plan D3.js Scripted Graphics

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

## Milestone 5: Agent-Facing Authoring Guidance

Goal: teach agents to choose the least powerful graphing layer that satisfies the requested visual output.

Selection rule:

1. Use Layer 1 template graphics for ordinary charts when the Plotly-aligned standardized schema can express the chart.
2. Add Layer 1 `extra.plotly` only for non-essential Plotly refinements.
3. Use Layer 2 Vega-Lite when the user needs a backend-native declarative grammar, Altair output, custom chart structure, or custom interaction.
4. Use Layer 2 direct Vega only when Vega-Lite cannot express the needed behavior.
5. Use Layer 3 D3.js only when the GUI advertises explicit support and the requested graphic needs scripted DOM/SVG/canvas behavior.

Todo:

- [ ] Update `houmao-interop-ag-ui` guidance to explain the three graphing layers.
- [ ] Add examples for Plotly-only Layer 1 payloads.
- [ ] Add examples for raw Vega-Lite specs generated by Altair.
- [ ] Add examples for D3.js scripted graphics, clearly marked as sandboxed and disabled by default until implemented.
- [ ] Add repair guidance for validation failures per layer.
- [ ] Make publish-result reporting unchanged: never claim a GUI displayed graphics unless delivery and render evidence support that claim.
- [ ] Teach agents not to guess GUI destination routing ids.

Done when:

- Agents default to standardized template graphics.
- Agents understand that Layer 1 `extra.plotly` is optional and disposable.
- Agents choose Vega DSL for custom declarative specs and D3 only for custom scripted graphics.
- Agents do not use D3 scripts unless the GUI advertises explicit support.

## Milestone 6: Capability, Compatibility, and Tests

Goal: make the advanced graphing capability set discoverable and regression-resistant.

Deliverables:

- Capabilities report Plotly template support, `extra.plotly` policy, Vega DSL support, D3 script support, versions, limits, sandbox policy, and whether explicit enablement is required.
- Workbench renderers show layer-specific fallback details.
- Unit tests cover backend validation for all enabled layers.
- Browser tests cover successful render, selected renderer behavior where applicable, ignored `extra.plotly`, state isolation, and sandbox failures.
- Documentation explains transport-vs-renderer separation clearly: the gateway may carry opaque AG-UI events, but the GUI renders only recognized and enabled graphing contracts.

Suggested test cases:

- `test_capabilities_list_plotly_template_renderer_and_extra_policy`.
- `test_template_payload_renders_without_extra_plotly`.
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
- Each layer has a distinct validation and renderer path.
- Backend-specific Layer 1 tuning does not weaken the curated Plotly-aligned contract.
- Higher freedom does not weaken lower-risk defaults.
