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

# Render Implementation Payloads or Custom Tool Calls into AG-UI Events

## Workflow

1. **Choose the right render lane** (route built-in Plotly/Vega-Lite chart authoring to `houmao-shared-routines->houmao-ext-graphing`; see [../references/protocol-and-impl.md](../references/protocol-and-impl.md)):
   - Houmao-known implementation (`houmao.table`, `houmao.metric_grid`, `houmao.dashboard`, etc.): inspect via `houmao-mgr ag-ui impl schema <name>`, validate via `houmao-mgr ag-ui impl validate <name> --input payload.json`, then run `houmao-mgr ag-ui impl render <name> --input payload.json [--format json|jsonl|sse] > events.json`.
   - User-supplied custom GUI component contract: run `houmao-mgr ag-ui impl new-component render --tool-name <tool-name> --args payload.json > events.json`.
   - Schema-agnostic protocol tool call: run `houmao-mgr ag-ui protocol tool-call render --tool-name <tool-name> --args payload.json > events.json`.
2. **Validate the generated event batch** via `houmao-mgr ag-ui protocol events validate --input events.json`.
3. **Return the rendered output** or continue to [publish.md](publish.md) when live Houmao gateway delivery is requested.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/protocol-and-impl.md](../references/protocol-and-impl.md) and the user request, then execute the plan.

## Guardrails

- DO NOT hand-write `TOOL_CALL_START` / `TOOL_CALL_ARGS` / `TOOL_CALL_END` JSON arrays manually.
- DO NOT use `new-component render` unless the user supplied or confirmed the frontend component contract, and do not expect custom tool names in `ag-ui impl list`.
