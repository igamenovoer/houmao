## Context

Houmao currently exposes AG-UI authoring commands under `houmao-mgr internals ag-ui`. That group mixes two different concerns:

- Standard AG-UI protocol work: validate AG-UI event batches, render event batches in JSON/JSONL/SSE forms, and publish already-standard events through a Houmao gateway.
- Houmao implementation work: discover, validate, and render payload contracts such as `houmao.graphic.template`, `houmao.graphic.vegalite`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`.

The advanced graphics plan already separates graphing layers by renderer contract: Plotly template graphics, Vega-Lite DSL graphics, and future sandboxed D3 graphics. The manager surface needs a higher-level split. AG-UI itself is the protocol. Plotly, Vega-Lite, Houmao tables, and custom frontend drawing contracts are implementation contracts carried inside AG-UI tool-call events. Within the `impl` surface, graphics discovery should use the generic layer category names `templated-graphics`, `freeform-graphics`, and `new-component` so future graphing backends can fit the same vocabulary without hiding the concrete backend metadata.

The important user case is a project-specific frontend renderer. A user might have `myapp.graphic.timeline` implemented in their GUI. Houmao should still help that user produce valid AG-UI `TOOL_CALL_*` events and publish them to a Houmao gateway, even when Houmao cannot validate the custom timeline payload semantics.

## Goals / Non-Goals

**Goals:**

- Make `protocol` and `impl` the canonical manager and documentation terms.
- Let users validate, frame, and publish standard AG-UI events without using a Houmao implementation schema.
- Let users render a generic AG-UI tool-call sequence for an arbitrary tool name and JSON arguments.
- Keep Houmao built-ins discoverable and validated as implementation contracts.
- Keep Plotly and Vega-Lite capability metadata under implementation metadata, not protocol metadata.
- Preserve the Houmao gateway publish helper as a live-only Houmao gateway operation over already-standard AG-UI event batches.
- Provide clear migration from `houmao-mgr internals ag-ui components ...` and `houmao-mgr internals ag-ui events ...`.

**Non-Goals:**

- Do not add a plugin loader for third-party implementation schemas in this change.
- Do not require Houmao to validate project-specific renderer payload semantics.
- Do not change the AG-UI wire protocol or gateway `/v1/ag-ui/*` routes.
- Do not implement new graphics renderers beyond the existing Houmao implementations.
- Do not make the Houmao gateway an arbitrary third-party AG-UI endpoint client.

## Decisions

### Split Manager Surfaces Into Protocol and Impl

Add a normal user-facing command group:

```bash
houmao-mgr ag-ui protocol ...
houmao-mgr ag-ui impl ...
```

`protocol` owns standard AG-UI operations:

```bash
houmao-mgr ag-ui protocol events validate --input events.json
houmao-mgr ag-ui protocol events frame --input events.json --format json
houmao-mgr ag-ui protocol events frame --input events.json --format jsonl
houmao-mgr ag-ui protocol events frame --input events.json --format sse
houmao-mgr ag-ui protocol tool-call render --tool-name myapp.graphic.timeline --args payload.json
```

`impl` owns Houmao-known payload contracts:

```bash
houmao-mgr ag-ui impl list
houmao-mgr ag-ui impl templated-graphics list
houmao-mgr ag-ui impl freeform-graphics list
houmao-mgr ag-ui impl new-component render --tool-name myapp.graphic.timeline --args payload.json
houmao-mgr ag-ui impl schema houmao.graphic.template
houmao-mgr ag-ui impl validate houmao.graphic.template --input payload.json
houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json
houmao-mgr ag-ui impl catalog houmao.graphic.template traces
```

`impl list` lists all Houmao-known implementation schemas, including non-graphic UI implementation schemas such as tables and dashboards. `impl templated-graphics list` lists Layer 1 templated graphics schemas only. It should include `houmao.graphic.template` with explicit Plotly metadata, and it should not include Vega-Lite because Vega-Lite belongs to the freeform graphics category. `impl freeform-graphics list` lists supported higher-freedom graphics schemas such as `houmao.graphic.vegalite`, and later `houmao.graphic.vega` or sandboxed D3 script schemas when they are implemented. `impl new-component render` is the schema-agnostic custom frontend component lane: it accepts a caller-provided tool name and JSON args, builds standard AG-UI tool-call events, and does not imply Houmao schema validation or GUI render support.

The JSON output for `impl templated-graphics list` should be shaped for agent discovery:

```json
{
  "category": "templated-graphics",
  "schemas": [
    {
      "name": "houmao.graphic.template",
      "layer": 1,
      "schemaVersion": 3,
      "kind": "plotly2d-template",
      "backend": "plotly",
      "renderer": "plotly.js",
      "catalogs": ["traces"]
    }
  ]
}
```

The JSON output for `impl freeform-graphics list` should keep the concrete freeform backend visible:

```json
{
  "category": "freeform-graphics",
  "schemas": [
    {
      "name": "houmao.graphic.vegalite",
      "layer": 2,
      "schemaVersion": 1,
      "kind": "vega-lite-dsl",
      "backend": "vega-lite",
      "renderer": "vega-embed",
      "catalogs": []
    }
  ]
}
```

Plotly trace types are not schema names in either category. Trace types such as `bar`, `heatmap`, and `sankey` remain catalog entries under `houmao.graphic.template` and are discovered through `houmao-mgr ag-ui impl catalog houmao.graphic.template traces`.

The existing `internals ag-ui` commands can be removed directly or kept as compatibility aliases with deprecation text. The repository allows breaking changes, so the implementation should prefer the clearer surface unless retaining aliases is low cost and does not obscure docs.

### Model Houmao Components as Implementation Specs

Internally, replace the overloaded component registry concept with an implementation registry. A registry entry should describe a tool-call payload contract:

```json
{
  "toolName": "houmao.graphic.template",
  "owner": "houmao",
  "schemaVersion": 3,
  "description": "Display standardized Layer 1 Plotly 2D template graphics.",
  "protocolBinding": "tool-call-json-args",
  "schema": {},
  "example": {},
  "catalogs": {
    "traces": {}
  },
  "security": {
    "remoteData": "disabled",
    "scriptExecution": false
  }
}
```

The first registry still contains only Houmao built-ins. Project-specific renderer contracts do not have to be registered in Houmao to use the protocol tool-call renderer. That keeps the implementation registry useful without turning it into a mandatory global source of truth for all frontends.

### Keep Generic Protocol Rendering Schema-Agnostic

The generic protocol renderer should accept:

- `--tool-name <name>`
- `--args <json-file-or-stdin>`
- optional `--message-id`
- optional `--tool-call-id`
- output format selection through the protocol framing command or a direct format option if that matches local CLI style.

It should validate only protocol-safe properties:

- tool name is a non-empty safe tool-call name string
- arguments are valid JSON and encoded as AG-UI tool-call args
- generated event sequence obeys AG-UI tool-call ordering
- batch size and byte limits are enforced by the standard event validator

It should not reject unknown tool names merely because Houmao lacks an implementation schema.

`houmao-mgr ag-ui impl new-component render` should compose with the same protocol tool-call renderer. It exists so agent-facing guidance can name the custom component layer explicitly while still keeping the implementation protocol-valid and schema-agnostic.

### Implementation Rendering Composes Validation Plus Protocol Rendering

`houmao-mgr ag-ui impl render <tool-name>` should:

1. Resolve the implementation spec.
2. Validate and normalize the payload with the implementation model.
3. Call the same protocol tool-call event builder used by the generic protocol path.
4. Emit standard AG-UI events.

This keeps one AG-UI event construction path and prevents drift between custom and Houmao-known tool-call output.

### Capabilities Expose Protocol and Impl Separately

Houmao custom capability metadata should distinguish protocol support from implementation support:

```json
{
  "custom": {
    "houmao": {
      "agUiProtocol": {
        "eventValidation": true,
        "toolCallRendering": true,
        "eventFormats": ["json", "jsonl", "sse"],
        "gatewayPublish": "houmao_live_only_fanout"
      },
      "agUiImpl": {
        "builtins": [
          "houmao_render_graphic",
          "houmao.graphic.template",
          "houmao.graphic.vegalite",
          "houmao.table",
          "houmao.metric_grid",
          "houmao.dashboard"
        ],
        "frontendSpecificImplAllowedViaProtocol": true,
        "renderingRequiresFrontendSupport": true,
        "categories": {
          "templated-graphics": ["houmao.graphic.template"],
          "freeform-graphics": ["houmao.graphic.vegalite"],
          "new-component": {
            "schemaAgnosticToolCallRendering": true,
            "validation": "ag-ui-protocol-only"
          }
        },
        "metadata": {
          "houmao.graphic.template": {
            "schemaVersion": 3,
            "category": "templated-graphics",
            "figureType": "plotly2d"
          },
          "houmao.graphic.vegalite": {
            "schemaVersion": 1,
            "category": "freeform-graphics",
            "library": "vega-lite"
          }
        }
      }
    }
  }
}
```

The standard AG-UI `tools.items` list can still include Houmao-supported tools when generated graphics are enabled. The Houmao custom metadata should make clear that unsupported frontend-specific tool names may still be transported as AG-UI protocol events, but only a frontend that implements the matching contract can render them.

### Documentation and Skill Guidance Use Protocol and Impl

Docs and `houmao-interop-ag-ui` should teach this rule:

```text
Use protocol commands when you already have AG-UI events or a frontend-specific tool-call payload.
Use impl commands when you want Houmao to validate a known Houmao payload contract before producing AG-UI events.
```

The skill should stop saying that users must always inspect a Houmao component schema before rendering AG-UI tool-call events. That remains correct for Houmao implementation contracts, but custom frontend implementations can use the schema-agnostic protocol renderer.

## Risks / Trade-offs

- Existing scripts may call `internals ag-ui components ...` -> Mitigate with direct migration docs and, if cheap, temporary aliases.
- The word `impl` could imply Houmao can load arbitrary implementation schemas -> Mitigate by documenting that this change introduces Houmao built-in implementation discovery plus schema-agnostic protocol rendering, not a third-party implementation loader.
- Generic protocol rendering can produce tool calls that no frontend understands -> Mitigate by making docs and output state that protocol validity does not imply GUI render support.
- Capability metadata may become verbose -> Mitigate by keeping protocol metadata compact and nesting renderer-specific details under per-implementation metadata.
- Tests may overfit old command names -> Mitigate by moving tests to protocol and impl command groups and adding one compatibility test only if aliases are retained.

## Migration Plan

1. Add internal protocol helpers for event validation, event framing, and schema-agnostic tool-call rendering.
2. Rename the component registry to an implementation registry while preserving existing Houmao payload models.
3. Add `houmao-mgr ag-ui protocol` commands.
4. Add `houmao-mgr ag-ui impl` commands, including `templated-graphics`, `freeform-graphics`, and `new-component` category commands.
5. Replace docs and skill workflows with the protocol/impl vocabulary.
6. Revise capabilities metadata to report `agUiProtocol` and `agUiImpl` separately while preserving existing standard AG-UI capability fields.
7. Update tests and examples from `internals ag-ui components/events` to the new command shape.
8. Decide during implementation whether `internals ag-ui` remains as a deprecated alias or is removed.

Rollback is straightforward before archive: keep the existing `internals ag-ui` command group and registry names. After archive, rollback would require a new change because the user-facing CLI contract will have changed.

## Open Questions

- Should `internals ag-ui` remain as a deprecated alias for one release, or should the breaking rename be immediate?
- Should `protocol tool-call render` embed JSON arguments in one `TOOL_CALL_ARGS` event only, or support chunking for large payloads under the existing byte limits?
- Should the implementation registry expose a machine-readable `owner` field for all built-ins now, or wait until third-party schema registration exists?
