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

# Freeform Graphics (`houmao.graphic.vegalite`)

## Workflow

1. **Confirm Layer 2 is warranted**: use `houmao.graphic.vegalite` only when custom Vega-Lite encodings, layering, transforms, selections, or linked views do not fit `houmao.graphic.template`.
2. **Inspect the Layer 2 schema** via `houmao-mgr ag-ui impl freeform-graphics list` and `houmao-mgr ag-ui impl schema houmao.graphic.vegalite` (see [../references/schema-and-render.md](../references/schema-and-render.md)).
3. **Author or repair the Layer 2 JSON envelope** (`schemaVersion: 1`, `library: "vega-lite"`, `specVersion: "6"`, inline `spec.data.values`, optional `title` and `display`); if using Python Altair locally as a helper, serialize `chart.to_dict()` into declarative JSON under `spec`.
4. **Validate and render** via `houmao-mgr ag-ui impl validate houmao.graphic.vegalite --input payload.json`, `houmao-mgr ag-ui impl render houmao.graphic.vegalite --input payload.json > events.json`, and `houmao-mgr ag-ui protocol events validate --input events.json`.
5. **Return or hand off** the validated `events.json` batch to `houmao-shared-routines->houmao-interop-ag-ui` when gateway framing or publication is requested.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/schema-and-render.md](../references/schema-and-render.md), the Layer 2 envelope rules below, and the user request, then execute the plan.

## Layer 2 Envelope and Authoring Rules

- **Declarative JSON only**: the gateway and workbench never execute Python; Altair (`alt.Chart(...).to_dict()`) is strictly a local authoring convenience whose JSON output goes into `spec`.
- **Inline data requirement**: embed records directly in `spec.data.values` unless a target capability explicitly advertises a safe reference mechanism.
- **Schema marker**: use the Vega-Lite v6 `$schema` URL (`https://vega.github.io/schema/vega-lite/v6.4.1.json`) inside `spec`.

## Guardrails

- DO NOT send Python source code, Altair objects, pandas DataFrames, notebook state, or local filesystem paths in payloads.
- DO NOT use remote `data.url`, local file URLs, remote images, or arbitrary HTTP(S) URLs outside the Vega-Lite v6 `$schema` marker.
- DO NOT embed credentials, unrequested private local file contents, raw HTML, script tags, iframes, JavaScript URLs, or scriptable SVG.
