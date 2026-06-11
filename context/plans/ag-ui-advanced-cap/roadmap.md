# AG-UI Advanced Presentation Capability Roadmap

## Scope

This roadmap covers a future expansion of AG-UI graphics and media beyond the current typed component and SVG compatibility paths. It assumes the existing live per-agent gateway remains the source of truth for AG-UI routing, stream delivery, and lifecycle boundaries. The workbench remains a GUI harness for already-running agents and must not gain managed-agent lifecycle ownership as part of presentation work.

The target capability stack has three user-facing layers:

1. Template graphics: one standardized Houmao chart schema, selectable renderer backends, and optional backend-specific `extra`.
2. Vega DSL graphics: raw Vega-Lite and possibly raw Vega specs, locked to the Vega ecosystem.
3. React components: predefined trusted component catalog first, future sandboxed custom React later.

## Milestone 1: Define the Standard Template Graphics Schema

Goal: replace ad hoc fixed component payloads with one renderer-neutral chart intent schema that can feed Recharts, Vega-Lite, Plotly, and later renderers.

Deliverables:

- A `houmao.graphic.template` payload model with `schemaVersion`, `chartType`, `renderer`, `title`, `data`, `encoding`, `interactions`, style fields, and optional `extra`.
- Renderer ids such as `recharts`, `vega-lite`, and `plotly`.
- A strict rule that top-level standardized fields are sufficient to render the chart.
- A strict rule that `extra` is keyed by renderer id and ignored when unsupported.
- A strict rule that Layer 1 does not accept custom user templates, arbitrary backend specs, JavaScript callbacks, HTML, iframes, remote data URLs, or full trace/spec replacement.
- Capabilities that advertise supported renderer ids and the `extra` policy.

Todo:

- [ ] Define the core chart types for the first release: bar, line, scatter, area, pie or donut, table-like summary if desired.
- [ ] Define common data and encoding shape, including field names, field types, title, aggregate, sort, color, size, tooltip, and series semantics.
- [ ] Define `renderer.preferred` and `renderer.fallback` semantics.
- [ ] Define `extra` as `dict[renderer_id, object]` with per-renderer allowlists.
- [ ] Decide whether unsupported known `extra` fields produce warnings, diagnostics records, or silent no-ops.
- [ ] Add examples for the same payload rendered through Recharts, Vega-Lite, and Plotly.
- [ ] Add test cases proving the same standardized payload renders through every enabled backend without `extra`.
- [ ] Add test cases proving unsupported `extra` is ignored and fallback rendering still works.

Done when:

- Agents can emit one standard template payload without knowing the final renderer.
- The GUI can choose Recharts, Vega-Lite, or Plotly and get a reasonable chart from the same payload.
- Backend-specific tuning exists only as optional `extra`.

## Milestone 2: Implement Renderer Adapters for Template Graphics

Goal: ship multiple Layer 1 backends early so users can compare output and provide feedback before the schema hardens.

Initial renderer adapters:

- Recharts: native React renderer for common dashboard charts.
- Vega-Lite: adapter from the standardized schema to a Vega-Lite spec.
- Plotly: adapter from the standardized schema to Plotly data and layout.

Todo:

- [ ] Add a renderer registry in the workbench keyed by renderer id.
- [ ] Add adapter-level validation for each renderer's supported chart types and `extra` fields.
- [ ] Keep renderer selection deterministic: preferred renderer when available, otherwise first supported fallback, otherwise GUI default.
- [ ] Surface selected renderer and ignored `extra` warnings in diagnostics.
- [ ] Add a visual comparison fixture for several payloads across all enabled renderers.
- [ ] Add browser tests for renderer fallback when the preferred backend is unavailable.
- [ ] Add browser tests for renderer-specific `extra` behavior.

Done when:

- The workbench can render one Layer 1 payload through at least two independent backends.
- Users can choose or compare backends without changing the agent payload.
- Renderer-specific differences are observable without breaking the standardized contract.

## Milestone 3: Add Vega DSL Graphics

Goal: give agents full declarative graphics freedom through the Vega ecosystem without allowing arbitrary React or JavaScript execution.

Recommended libraries:

- Python gateway and tooling: `altair`, `jsonschema`, and optionally `vl-convert-python`.
- TypeScript GUI: `vega`, `vega-lite`, and `vega-embed` or `react-vega`.

Contracts:

- Tool name: `houmao.graphic.vegalite`.
- Tool name: `houmao.graphic.vega`.
- Payload contains `schemaVersion`, `library`, `specVersion`, `title`, optional `description`, the raw `spec`, and optional display metadata.
- Inline data values are allowed with size limits.
- Remote data URLs are disabled by default or restricted by explicit allowlist.
- The GUI renderer owns theme, autosizing defaults, error display, and renderer cleanup.

Todo:

- [ ] Define `HoumaoVegaLiteGraphicPayload` in Python with title, spec version, spec object, and metadata.
- [ ] Define `HoumaoVegaGraphicPayload` only if direct Vega is included in the first release.
- [ ] Add backend validation for payload size, required JSON object shape, and forbidden high-risk fields.
- [ ] Decide whether Python preflight compiles specs with `vl-convert-python` during validation or only validates shape and lets the GUI renderer report compile errors.
- [ ] Add CLI authoring helpers for validating and rendering Vega DSL event batches.
- [ ] Add a workbench renderer that mounts Vega-Lite and optionally Vega specs in a bounded responsive container.
- [ ] Add renderer cleanup so repeated specs do not leak Vega views.
- [ ] Add capability metadata for supported DSL library, supported major version, max payload bytes, max inline rows, and remote data policy.
- [ ] Add deterministic examples for bar chart, layered chart, interactive selection, tooltip, linked view, and one direct Vega example if enabled.
- [ ] Add tests for malformed specs, oversized inline data, disabled remote URLs, and successful interactive render smoke.

Done when:

- A user who wants custom templates can use a raw Vega-Lite or Vega spec rather than extending Layer 1.
- The workbench renders a Vega-Lite chart with interaction and a clear fallback on validation or render failure.
- Capabilities make it clear that this is Vega DSL, not renderer-neutral template graphics and not React code execution.

## Milestone 4: Add Predefined React Component Catalog

Goal: expose trusted GUI components such as PDF viewers, video players, image viewers, galleries, and layout containers to agents through validated JSON props.

Recommended libraries:

- Python gateway and tooling: `pydantic` for component payload models and JSON Schema.
- TypeScript GUI: `zod` or generated validators for browser-side props validation.
- PDF: PDF.js-backed viewer or a React wrapper built on PDF.js.
- Video and audio: native media elements, Vidstack, or Media Chrome depending on desired controls.

Contract:

- Tool name: `houmao.component.catalog`.
- Payload contains `schemaVersion`, `component`, and `props`.
- Component ids are stable names such as `houmao.media.pdf_viewer`, `houmao.media.video_player`, `houmao.media.audio_player`, `houmao.media.image_viewer`, `houmao.media.gallery`, `houmao.ui.tabs`, `houmao.ui.split_panel`, and `houmao.ui.dashboard`.
- Each component id has an owned props schema.
- Prefer gateway artifact ids over arbitrary remote URLs.

Todo:

- [ ] Define the component catalog registry and metadata shape.
- [ ] Add initial components for PDF, video, image, and gallery.
- [ ] Define source reference objects: gateway artifact, data URI where safe, and explicit URL only when allowed by policy.
- [ ] Add per-component payload size, MIME type, and source policy.
- [ ] Add workbench renderers with loading, error, and unsupported fallbacks.
- [ ] Add capabilities listing component ids, schema versions, source policies, and media limits.
- [ ] Add tests for valid PDF/video/image payloads, unsupported source kinds, oversized media references, and unknown component ids.

Done when:

- Agents can present complex media without generating React code.
- The GUI owns the trusted implementation and the agent supplies only JSON props.
- Components render through the same AG-UI tool-call/reducer path as graphics.

## Milestone 5: Plan Custom React Components Without Enabling Them by Default

Goal: define the future custom React contract and sandbox requirements without shipping it as an active default feature.

Recommended libraries:

- Python gateway and tooling: `pydantic` for manifest validation and optional out-of-process Node or Bun preflight.
- TypeScript GUI: `@codesandbox/sandpack-react` for the first prototype, or `esbuild-wasm` plus a custom iframe runtime for stricter control.

Contract:

- Tool name: `houmao.component.react_bundle`.
- Payload contains `schemaVersion`, `componentId`, `entryFile`, `files`, `props`, `propsSchema`, `dependencies`, `permissions`, and display metadata.
- The component must export a default React component or a known named export.
- The component receives only `data`, `width`, `height`, `theme`, and a narrow optional `emit` function.
- Communication with the parent GUI uses `postMessage` or a controlled Sandpack channel.

Security posture:

- Disabled by default in normal capabilities.
- Requires explicit workbench setting or trusted mode.
- Runs in a sandboxed iframe.
- No access to parent DOM, localStorage, cookies, credentials, mailbox content, memory content, or tmux sockets.
- Network disabled or allowlisted by default.
- Dependency list allowlisted and pinned.
- Payload size, file count, compile time, render time, and console output are bounded.

Todo:

- [ ] Decide whether the first prototype uses Sandpack or a custom `esbuild-wasm` iframe.
- [ ] Define the manifest model and minimum source file format.
- [ ] Define dependency policy, starting with `react`, `react-dom`, and a small approved visualization helper set.
- [ ] Add GUI trust controls and visible enabled or disabled state for custom React.
- [ ] Add iframe sandbox flags and a parent-child message protocol.
- [ ] Add compile error, runtime error, timeout, dependency rejection, and permission rejection fallbacks.
- [ ] Add test fixtures for a valid tiny component, a compile error, an attempted parent access, an attempted network access, and an infinite render loop.
- [ ] Decide whether generated React component bundles can be cached client-side, and if so, what metadata is safe to persist.

Done when:

- The custom React contract is documented and capability-gated.
- The workbench can keep reporting the feature as planned or disabled until the sandbox is implemented.
- The predefined component catalog remains the recommended route for complex media.

## Milestone 6: Agent-Facing Authoring Guidance

Goal: teach agents to choose the least powerful layer that satisfies the requested visual output.

Selection rule:

1. Use template graphics for ordinary charts when a standardized schema can express the chart.
2. Add Layer 1 `extra` only for non-essential backend-specific refinements.
3. Use Vega-Lite or Vega DSL when the user needs custom chart structure, custom interaction, or backend-native Vega control.
4. Use predefined React catalog components for PDFs, videos, images, galleries, and trusted GUI widgets.
5. Use custom React only when explicitly enabled and no safer layer can express the requested surface.

Todo:

- [ ] Update `houmao-agent-ag-ui` guidance to explain the three-layer decision tree.
- [ ] Add examples for Layer 1 with and without `extra`.
- [ ] Add examples for raw Vega-Lite specs as the custom-template path.
- [ ] Add examples for predefined media components.
- [ ] Add repair guidance for validation failures per layer.
- [ ] Make publish-result reporting unchanged: never claim a GUI displayed graphics unless delivery and render evidence support that claim.
- [ ] Teach agents not to guess GUI destination routing ids.

Done when:

- Agents default to standardized template graphics.
- Agents understand that Layer 1 `extra` is optional and disposable.
- Agents choose Vega DSL for custom chart specs and predefined components for complex media.
- Agents do not use custom React unless the GUI advertises explicit support.

## Milestone 7: Capability, Compatibility, and Tests

Goal: make the advanced capability set discoverable and regression-resistant.

Deliverables:

- Capabilities report template renderer ids, `extra` policy, Vega DSL support, component catalog ids, custom React support, versions, limits, sandbox policy, and whether explicit enablement is required.
- Workbench renderers show layer-specific fallback details.
- Unit tests cover backend validation for all layers.
- Browser tests cover successful render, fallback render, selected renderer behavior, ignored `extra`, and state isolation for all enabled layers.
- Documentation explains transport-vs-renderer separation clearly: the gateway may carry opaque AG-UI events, but the GUI renders only recognized and enabled contracts.

Suggested test cases:

- `test_capabilities_list_template_renderers_and_extra_policy`.
- `test_template_payload_renders_without_extra`.
- `test_template_extra_is_renderer_scoped`.
- `test_template_unsupported_extra_does_not_block_fallback`.
- `test_template_rejects_full_backend_spec_in_extra`.
- `test_vegalite_payload_rejects_remote_data_when_disabled`.
- `test_vegalite_payload_accepts_inline_interactive_spec`.
- `test_workbench_renders_vegalite_spec`.
- `test_workbench_shows_vegalite_compile_error_fallback`.
- `test_catalog_component_validates_pdf_props`.
- `test_catalog_component_rejects_unknown_component`.
- `test_custom_react_capability_disabled_by_default`.
- `test_custom_react_runs_only_in_sandbox_when_enabled`.
- `test_custom_react_rejects_unapproved_dependency`.

Done when:

- The layers are visible as separate capabilities.
- Each layer has a distinct validation and renderer path.
- Backend-specific Layer 1 tuning does not weaken renderer-neutral fallback.
- Higher freedom does not weaken lower-risk defaults.
