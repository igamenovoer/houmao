## Context

Houmao now exposes AG-UI through two explicit command layers: `houmao-mgr ag-ui protocol` for standard event validation, framing, and schema-agnostic tool-call rendering, and `houmao-mgr ag-ui impl` for Houmao-owned implementation schemas such as `houmao.graphic.template`, `houmao.graphic.vegalite`, `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`. The current `houmao-interop-ag-ui` skill still reads like a single broad skill for protocol mechanics, implementation schema usage, Plotly.js Layer 1 chart authoring, Vega-Lite Layer 2 chart authoring, gateway publishing, and delivery interpretation.

That broad shape makes routing unclear. A user asking to publish an already-rendered AG-UI event batch needs protocol and gateway guidance. A user asking to draw a heatmap or an Altair chart needs graphing guidance first, then standard AG-UI rendering and delivery. The advanced graphing plan already treats graphing as layered authoring capability (`templated-graphics`, `freeform-graphics`, and future custom components), so the skill layout should match that model.

## Goals / Non-Goals

**Goals:**

- Add `houmao-utils-graphing` as the agent-facing utility skill for built-in Houmao graphing authoring.
- Keep `houmao-interop-ag-ui` focused on AG-UI protocol, generic implementation rendering mechanics, Houmao gateway delivery, endpoint boundaries, routing, and publish-result interpretation.
- Preserve the existing `houmao-mgr ag-ui protocol ...`, `houmao-mgr ag-ui impl ...`, and gateway publish command shapes.
- Make the new skill discoverable through the packaged system-skill catalog, default installation sets, `houmao-mgr system-skills list`, docs, and packaged-asset tests.
- Avoid duplicating long graphing rules in both skills; cross-reference the graphing utility from the interop skill.

**Non-Goals:**

- Do not change AG-UI event schemas, gateway routes, publish semantics, or protocol validation.
- Do not change `houmao.graphic.template`, `houmao.graphic.vegalite`, Plotly trace catalog generation, Vega-Lite validation, or workbench rendering behavior.
- Do not add a new graphing backend, D3 implementation, datasource materialization, or frontend component schema.
- Do not preserve duplicate graphing authoring prose in `houmao-interop-ag-ui` for compatibility.

## Decisions

### Split by Authoring Concern, Not by CLI Namespace

`houmao-interop-ag-ui` remains the skill for AG-UI event movement. It should teach agents how to resolve `houmao-mgr`, validate standard AG-UI events, frame events, render generic tool calls, validate/render Houmao implementation payloads when the implementation is already chosen, and publish rendered event batches through the Houmao gateway. It should not teach the detailed rules for choosing Plotly.js versus Vega-Lite or constructing those graphing payloads.

`houmao-utils-graphing` becomes the skill for graphing payload construction. It should teach agents how to list graphing implementation categories, choose `templated-graphics` or `freeform-graphics`, inspect `houmao.graphic.template` and `houmao.graphic.vegalite`, check the Plotly trace catalog, build payload JSON, validate payloads, render events, and then hand off delivery to the interop/gateway workflow.

Alternative considered: keep a single large `houmao-interop-ag-ui` skill and add more headings. That keeps one entrypoint, but it continues to conflate protocol transport with graph authoring and makes future graphing backends harder to place.

### Keep Graphing Under `utils`

The new name is `houmao-utils-graphing` because it is not a managed-agent lifecycle, gateway control, mailbox, memory, project, or loop skill. It is a reusable authoring utility that produces payloads/events consumed by AG-UI delivery workflows.

Alternative considered: name it `houmao-interop-ag-ui-graphing`. That makes the transport relationship visible, but it keeps graph authoring mentally nested under interop and conflicts with the desired split.

### Install the Graphing Utility Wherever AG-UI Interop Is Installed

The default catalog sets should include `houmao-utils-graphing` next to `houmao-interop-ag-ui` so managed agents that receive AG-UI interop guidance can follow its graphing delegation without missing the target skill. Explicit users can still install only one skill by name if they want a smaller external tool home.

Alternative considered: include graphing only in `all`. That would keep `core` smaller, but a managed agent with `houmao-interop-ag-ui` would be told to use a skill that managed launch did not install.

### Preserve Protocol/Impl CLI Shape

The implementation should not add `houmao-mgr graphing ...` commands. Graphing still uses the existing implementation categories:

- `houmao-mgr ag-ui impl templated-graphics list`
- `houmao-mgr ag-ui impl freeform-graphics list`
- `houmao-mgr ag-ui impl schema houmao.graphic.template`
- `houmao-mgr ag-ui impl schema houmao.graphic.vegalite`
- `houmao-mgr ag-ui impl catalog houmao.graphic.template traces`
- `houmao-mgr ag-ui impl validate ...`
- `houmao-mgr ag-ui impl render ...`

This keeps the command surface aligned with the protocol/impl model and avoids creating a second path to the same schemas.

### Use Cross-References Instead of Duplication

`houmao-interop-ag-ui` should keep a short “Graphing handoff” section and examples that show how to publish rendered events, but it should not duplicate the Plotly and Vega-Lite payload examples from `houmao-utils-graphing`. The graphing skill can refer back to interop for gateway publish details and delivery-result interpretation.

Alternative considered: duplicate minimal chart examples in both skills. That would reduce one skill lookup, but duplicated examples would drift as graphing schemas evolve.

## Risks / Trade-offs

- Skill routing ambiguity → Give each skill a tight help section and related-skill boundary: interop for protocol/delivery, graphing for Plotly.js/Vega-Lite authoring.
- Missing delegated skill in managed homes → Add `houmao-utils-graphing` to the same default sets as `houmao-interop-ag-ui` and cover installation/status tests.
- Documentation drift → Update both the getting-started overview and CLI reference in the same implementation pass and test for the new skill in docs.
- Over-splitting small workflows → Keep `houmao-utils-graphing` able to validate and render event batches so a graphing task remains one coherent workflow before gateway handoff.
- Confusion between AG-UI implementation categories and graphing backends → Use the layer names `templated-graphics` and `freeform-graphics` in the skill, and identify their current concrete built-ins as Plotly.js and Vega-Lite.

## Migration Plan

1. Add `src/houmao/agents/assets/system_skills/houmao-utils-graphing/` with a top-level `SKILL.md` and optional agent metadata.
2. Move graphing-specific guidance from `houmao-interop-ag-ui/SKILL.md` into the new skill, then replace it with a concise graphing handoff section.
3. Register `houmao-utils-graphing` in `catalog.toml` and include it in `core` and `all` near `houmao-utils-workspace-mgr` or near `houmao-interop-ag-ui`, choosing one stable order and updating tests.
4. Update docs and tests that enumerate packaged system skills, default resolved skills, installed paths, and skill descriptions.
5. Run focused system-skill tests and docs tests, then run the normal Pixi checks if implementation changes are made.

Rollback is straightforward before archive: remove the new skill from the catalog, restore graphing guidance to `houmao-interop-ag-ui`, and revert docs/tests. After archive, rollback should be a new change because the installed skill inventory and documentation contract will have changed.

## Open Questions

- Should `houmao-utils-graphing` include table/metric/dashboard payload examples, or stay strictly limited to graphics? The current recommendation is to keep it graphing-only and leave non-graph component examples in `houmao-interop-ag-ui`.
- Should future D3 or custom graphing guidance live in `houmao-utils-graphing` when implemented? The current recommendation is yes, but only when capabilities advertise the backend and the implementation contract exists.
