## 1. Python Authoring Contract

- [x] 1.1 Add `houmao.graphic.template` to the Houmao AG-UI component registry with schema summary, JSON Schema export, and example payload.
- [x] 1.2 Add Pydantic models for template graphic chart type, renderer selection, inline data rows, encoding channels, interactions, style, and renderer-scoped `extra`.
- [x] 1.3 Enforce Layer 1 safety rules, including rejection of raw backend specs, remote data replacement, scriptable content, and disallowed `extra.vega-lite` keys.
- [x] 1.4 Add unit tests for schema discovery, valid payload validation, safe `extra.vega-lite`, rejected raw Vega-Lite spec fragments, and rendered AG-UI events.

## 2. Gateway Capabilities and Documentation

- [x] 2.1 Add template graphics metadata to AG-UI capabilities with tool name, schema version, chart types, renderer ids, default renderer, and `extra` policy.
- [x] 2.2 Update gateway AG-UI reference docs to describe `houmao.graphic.template`, renderer selection, Vega-Lite Layer 1 behavior, and the Layer 1 versus Layer 2 boundary.
- [x] 2.3 Update docs tests or capability tests that assert AG-UI graphics metadata.

## 3. Workbench Rendering

- [x] 3.1 Add workbench dependencies for `vega`, `vega-lite`, and `vega-embed`.
- [x] 3.2 Add template graphic payload validation and a renderer registry in the workbench.
- [x] 3.3 Implement the Recharts template renderer for supported chart types.
- [x] 3.4 Implement the Vega-Lite template renderer and cleanup behavior.
- [x] 3.5 Wire `houmao.graphic.template` into `ToolCallRenderer` and dashboard nested rendering where applicable.
- [x] 3.6 Add workbench tests or fixtures proving Vega-Lite rendering, fallback rendering, and invalid payload fallback.

## 4. Agent Guidance and Debug Fixtures

- [x] 4.1 Update `houmao-agent-ag-ui` guidance to prefer `houmao.graphic.template` for ordinary Layer 1 charts and keep raw Vega-Lite out of Layer 1 `extra`.
- [x] 4.2 Update Debug Agent component lists and templates so developers can send a template graphic payload from the workbench.
- [x] 4.3 Update system-skill docs tests if they assert specific AG-UI component guidance.

## 5. Verification

- [x] 5.1 Run targeted Python unit tests for AG-UI authoring, capabilities, docs, and AG-UI CLI commands.
- [x] 5.2 Run workbench typecheck and targeted Playwright coverage for template graphics.
- [x] 5.3 Run OpenSpec status to confirm all implementation tasks are complete.
