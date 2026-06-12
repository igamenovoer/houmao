## 1. Backend Component Contract

- [x] 1.1 Add `houmao.graphic.vegalite` constants, supported Vega-Lite major-version metadata, and payload limits in `src/houmao/ag_ui/authoring.py`.
- [x] 1.2 Add Pydantic models for the Layer 2 Vega-Lite envelope, display metadata, and raw JSON `spec` object.
- [x] 1.3 Add Vega-Lite-aware safety validation that permits known Vega-Lite v6 `$schema` URLs while rejecting remote data URLs, unsafe inline content, scriptable SVG, iframe content, JavaScript URLs, and oversized payloads.
- [x] 1.4 Register `houmao.graphic.vegalite` in the component spec registry with a valid inline example and JSON Schema output.
- [x] 1.5 Allow `houmao.dashboard` children to reference `houmao.graphic.vegalite` when child props validate.
- [x] 1.6 Extend AG-UI capability metadata and generated-graphics tool metadata with a separate `presentation.vegaDsl` block and a `houmao.graphic.vegalite` tool item.

## 2. Backend Tests

- [x] 2.1 Add unit tests proving component list/schema discovery includes `houmao.graphic.vegalite`.
- [x] 2.2 Add unit tests proving valid hand-authored Vega-Lite payloads validate and render into standard AG-UI tool-call events.
- [x] 2.3 Add unit tests using real Altair `chart.to_dict()` output to prove Altair-shaped Vega-Lite v6 JSON validates without pandas, `vl-convert-python`, or Python runtime execution by the gateway.
- [x] 2.4 Add unit tests proving remote `data.url`, unsafe inline content, Python-source `spec` values, unsupported `specVersion`, and oversized payloads are rejected with safe diagnostics.
- [x] 2.5 Add unit tests proving dashboard payloads can include a valid `houmao.graphic.vegalite` child.
- [x] 2.6 Add capability tests proving `presentation.vegaDsl` is advertised separately and `templateGraphics.rawVegaLiteDsl` remains false.

## 3. Workbench Renderer

- [x] 3.1 Add `vega`, `vega-lite`, and `vega-embed` frontend dependencies and update the Bun lockfile.
- [x] 3.2 Add a `vegaDslGraphics` renderer module that validates the Layer 2 envelope in the browser, rejects obvious unsafe remote-loading shapes, and renders with `vega-embed`.
- [x] 3.3 Ensure the Vega-Lite renderer disables external loading and action controls by default, applies bounded responsive sizing, and finalizes mounted Vega views on rerender, unmount, pane clear, or target clear.
- [x] 3.4 Register `houmao.graphic.vegalite` in the workbench typed component renderer registry while keeping `houmao.graphic.template` on the Plotly renderer path.
- [x] 3.5 Add invalid-component fallback handling for malformed specs, unsupported versions, remote data attempts, and Vega compile/runtime errors.

## 4. Debug Agent and Browser Coverage

- [x] 4.1 Add Debug Agent sender templates for a valid `houmao.graphic.vegalite` payload and at least one invalid remote-data payload.
- [x] 4.2 Update fake/debug AG-UI server fixtures to include Vega-Lite events where graphical proof needs deterministic data.
- [x] 4.3 Add Playwright coverage proving a posted `houmao.graphic.vegalite` event batch renders visibly in a Debug Agent or normal AG-UI pane.
- [x] 4.4 Add Playwright coverage proving a malformed or remote-data Vega-Lite payload shows a visible invalid-component fallback and does not block later valid events.
- [x] 4.5 Add cleanup-oriented browser coverage proving pane clear or rerender removes the prior Vega view without controlling the managed agent lifecycle.

## 5. Docs and System Skill

- [x] 5.1 Update `docs/reference/gateway/ag-ui.md` to document `houmao.graphic.vegalite`, optional Altair authoring, Layer 2 capability metadata, and the remote-data policy.
- [x] 5.2 Update `src/houmao/agents/assets/system_skills/houmao-interop-ag-ui/SKILL.md` to teach Layer 1 versus Layer 2 selection, Altair `chart.to_dict()` authoring, validation/render commands, and Vega-Lite safety limits.
- [x] 5.3 Update `houmao-interop-ag-ui/agents/openai.yaml` if the default prompt or short description becomes stale after the skill guidance changes.
- [x] 5.4 Update real-agent smoke prompts and debug examples so custom declarative chart requests use `houmao.graphic.vegalite` while ordinary charts still use `houmao.graphic.template`.

## 6. Verification

- [x] 6.1 Run focused Python tests for AG-UI authoring, capabilities, and `houmao-mgr internals ag-ui` command behavior.
- [x] 6.2 Run workbench typecheck and build after adding Vega dependencies.
- [x] 6.3 Run focused Playwright workbench tests that cover Vega-Lite rendering, fallback, and cleanup.
- [x] 6.4 Run documentation/system-skill tests that cover AG-UI docs and packaged skill guidance.
