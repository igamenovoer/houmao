---
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Templated Graphics (`houmao.graphic.template`)

## Workflow

1. **Inspect the Layer 1 schema and trace catalog** using [../references/schema-and-render.md](../references/schema-and-render.md) (`houmao-mgr ag-ui impl templated-graphics list`, `schema houmao.graphic.template`, and `catalog houmao.graphic.template traces`).
2. **Author or repair the Layer 1 JSON payload** with `schemaVersion: 3`, `figureType: "plotly2d"`, inline `traces[].data`, and supported 2D `traces[].type` values.
3. **Validate the payload** via `houmao-mgr ag-ui impl validate houmao.graphic.template --input payload.json`, fixing any rejected trace or field before proceeding.
4. **Render and verify AG-UI events** via `houmao-mgr ag-ui impl render houmao.graphic.template --input payload.json > events.json` followed by `houmao-mgr ag-ui protocol events validate --input events.json`.
5. **Return or hand off** the validated `events.json` batch to `houmao-shared-routines->houmao-interop-ag-ui` if gateway framing or live publication is requested.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/schema-and-render.md](../references/schema-and-render.md), the Layer 1 envelope rules below, and the user request, then execute the plan.

## Layer 1 Envelope Rules

- **Renderer field**: omit `renderer` or set `"renderer": { "preferred": "plotly" }`; `renderer.fallback` is retired and non-Plotly renderer IDs fail validation.
- **Inline data default**: populate `traces[].data` inline whenever a visible chart is needed now. Datasource `dataRefs` and `source.bindings` (`data.x`, `data.y`, `data.open`, `data.high`, `data.low`, `data.close`, `data.node.label`, `data.link.value`, `data.header.values`, `data.cells.values`) are reserved vocabulary and render a diagnostic until target capabilities advertise materialization support.
- **Curated `extra.plotly`**: restrict `extra.plotly` to small allowlisted `layout`, `config`, `style`, and `display` refinements.
- **Schema vs trace names**: Plotly trace names (`bar`, `heatmap`, `sankey`, etc.) live inside `traces[].type` under `houmao.graphic.template`, never as standalone schema names.

## Guardrails

- DO NOT ask the user to choose a Layer 1 renderer or emit `chartType` or retired `houmao.chart.*` schemas.
- DO NOT place raw replacement `data`/`traces`, `frames`, `transforms`, `templates`, Vega/Vega-Lite specs, HTML/SVG/JS, remote URLs, credentialed map settings, or 3D scene traces (`scatter3d`, `surface`, `mesh3d`) inside `houmao.graphic.template`.
