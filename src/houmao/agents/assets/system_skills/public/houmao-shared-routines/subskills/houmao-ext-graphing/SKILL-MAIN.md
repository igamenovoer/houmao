---
name: houmao-ext-graphing
description: "Use when Houmao Plotly.js templated graphics or Vega-Lite freeform graphics must be created, repaired, schema-validated, rendered as AG-UI events, or prepared for later gateway publishing."
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

# Houmao Ext Graphing

## Overview

Author, repair, schema-validate, and render built-in Houmao graphing payloads into standard AG-UI event batches without hand-writing raw AG-UI event JSON.

## Workflow

1. **Answer explicit `help` first** from **Help** without running schema, validation, rendering, or publishing commands.
2. **Enforce the Actor Frame Gate** and preserve the caller's actor frame and any downstream gateway target.
3. **Select the least powerful graphing layer** from **Subcommands** (`templated-graphics` before `freeform-graphics`; never `new-component` for built-in charts, and never retired `houmao.chart.bar|line|pie`).
4. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and load the selected command page plus [references/schema-and-render.md](references/schema-and-render.md).
5. **Run the full pipeline**: validate the graphing payload (`ag-ui impl validate`), render standard AG-UI events (`ag-ui impl render`), and validate the rendered event batch (`ag-ui protocol events validate`).
6. **Return the validated output** or hand the rendered event batch to `houmao-shared-routines->houmao-interop-ag-ui` for framing or live gateway publication.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, [references/schema-and-render.md](references/schema-and-render.md), and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Authoring and validation behave identically for both actors, while any subsequent gateway publish preserves the inherited actor and target through `houmao-shared-routines->houmao-interop-ag-ui`. Route gateway attachment and status to `houmao-shared-routines->houmao-agent-gateway`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `templated-graphics` | Layer 1 Plotly.js 2D charts via `houmao.graphic.template` (`schemaVersion: 3`, `figureType: "plotly2d"`). | [commands/templated-graphics.md](commands/templated-graphics.md) |
| `freeform-graphics` | Layer 2 Vega-Lite v6 charts via `houmao.graphic.vegalite` (`schemaVersion: 1`) when custom grammar, layering, transforms, or selections exceed Layer 1. | [commands/freeform-graphics.md](commands/freeform-graphics.md) |
| `help` | Read-only overview of graphing layers, schema discovery, validation, rendering, and `interop-ag-ui` handoff. | **Help** |

## Help

Explain the two built-in layers (`templated-graphics` for `houmao.graphic.template` v3 `plotly2d`, `freeform-graphics` for `houmao.graphic.vegalite` v1), schema/catalog discovery via `houmao-mgr ag-ui impl`, the `validate -> render -> protocol events validate` sequence, and handoff to `houmao-shared-routines->houmao-interop-ag-ui` for publishing or custom frontend `new-component` tool calls. Concrete chart requests (such as "help me draw a Plotly heatmap") execute the matching subcommand instead of stopping at generic help.

## Guardrails

- DO NOT generate retired `houmao.chart.bar`, `houmao.chart.line`, or `houmao.chart.pie` payloads, or use `ag-ui impl new-component` for built-in Plotly or Vega-Lite charts.
- DO NOT publish unrendered graphing payloads directly to a gateway or skip `ag-ui impl validate` and `ag-ui protocol events validate`.
- DO NOT include credentials, tokens, cookies, private keys, auth files, or unrequested private local file contents in payloads.
- DO NOT emit Python source, Altair or pandas objects, notebook state, raw HTML, scriptable SVG, JavaScript URLs, iframes, or event-handler attributes.
- DO NOT place raw Plotly `data`/`traces`, frames, transforms, templates, remote URLs, Vega/Vega-Lite fields, or 3D scene traces (`scatter3d`, `surface`, `mesh3d`) in Layer 1 payloads.
- DO NOT use non-inline Vega-Lite `data.url`, local file URLs, remote images, or arbitrary HTTP(S) strings outside the allowed Vega-Lite v6 `$schema` marker in Layer 2 payloads.
