## Why

The current `houmao-interop-ag-ui` system skill mixes AG-UI protocol/gateway interop with detailed Plotly.js and Vega-Lite graph authoring guidance. Now that Houmao separates AG-UI protocol from Houmao implementation layers, agents need a clearer skill boundary: one skill for moving standard AG-UI events through the gateway, and one utility skill for authoring built-in graphing payloads.

## What Changes

- Add a new packaged system skill named `houmao-utils-graphing` for built-in Houmao graphing authoring.
- Move graphing-specific guidance for `templated-graphics`, `freeform-graphics`, Plotly.js `houmao.graphic.template`, Vega-Lite `houmao.graphic.vegalite`, trace-catalog discovery, graphing safety limits, and graphing repair examples out of `houmao-interop-ag-ui`.
- Narrow `houmao-interop-ag-ui` so it focuses on AG-UI protocol event validation/framing, generic implementation rendering mechanics, custom `new-component` tool-call rendering, Houmao gateway publishing, routing, endpoint boundaries, and delivery-result interpretation.
- Keep the existing `houmao-mgr ag-ui protocol ...` and `houmao-mgr ag-ui impl ...` CLI shape unchanged; this change reorganizes agent-facing skill guidance and catalog/docs coverage.
- Add `houmao-utils-graphing` to the packaged system-skill catalog and default installed sets when graphing guidance must be available wherever `houmao-interop-ag-ui` can delegate to it.
- Update system-skill documentation and tests so operators can list, install, status-check, and discover the new graphing utility skill.

## Capabilities

### New Capabilities

- `houmao-utils-graphing-skill`: Defines the new `houmao-utils-graphing` system skill for built-in Plotly.js and Vega-Lite graphing payload authoring over Houmao AG-UI implementations.

### Modified Capabilities

- `houmao-interop-ag-ui-skill`: Narrow the existing AG-UI interop skill to protocol/gateway/generic implementation workflows and delegate built-in graphing authoring to `houmao-utils-graphing`.
- `houmao-mgr-system-skills-cli`: Add `houmao-utils-graphing` to the current installable system-skill inventory, list/install/status/uninstall behavior, and resolved set expectations.
- `houmao-system-skill-families`: Treat `houmao-utils-graphing` as a utility skill while preserving flat tool-native projection and current named-set behavior.
- `docs-system-skills-overview-guide`: Document `houmao-utils-graphing` and update the `houmao-interop-ag-ui` row so the overview reflects the new boundary.

## Impact

- System skill assets under `src/houmao/agents/assets/system_skills/`, including a new `houmao-utils-graphing` directory and a narrower `houmao-interop-ag-ui` skill.
- System skill catalog metadata in `src/houmao/agents/assets/system_skills/catalog.toml`.
- System skill installation/list/status tests and packaged-asset contract tests.
- Documentation under `docs/getting-started/system-skills-overview.md` and `docs/reference/cli/system-skills.md`.
- No changes to AG-UI protocol event schemas, Houmao implementation payload schemas, Plotly trace catalog generation, Vega-Lite validation, or gateway publish APIs.
