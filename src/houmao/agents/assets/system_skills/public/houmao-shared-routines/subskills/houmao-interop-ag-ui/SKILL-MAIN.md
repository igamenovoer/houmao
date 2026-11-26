---
name: houmao-interop-ag-ui
description: "Use when standard AG-UI events or already-chosen Houmao implementation payloads must be validated, framed, rendered, published, routed, or interpreted."
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

# Houmao Interop AG-UI

## Overview

Validate, frame, render, and live-publish standard AG-UI event batches and Houmao implementation payloads without hand-writing raw AG-UI event JSON or guessing gateway delivery state.

## Workflow

1. **Answer explicit `help` first** from **Help** without running validation, framing, rendering, or gateway commands.
2. **Enforce the Actor Frame Gate** and resolve the target gateway (explicit `--agent-id`/`--agent-name` in `admin` posture; verified `agents self` by default in `agent` posture).
3. **Select one subcommand** from **Subcommands** while keeping `ag-ui protocol`, `ag-ui impl`, and `ag-ui impl new-component` distinct (see [references/protocol-and-impl.md](references/protocol-and-impl.md)).
4. **Resolve one `houmao-mgr` launcher** (`command -v houmao-mgr`, then `uv tool run --from houmao houmao-mgr`, or repo `pixi run houmao-mgr`, honoring an explicit user launcher) and load the selected command page.
5. **Execute the selected workflow**, validating payloads and rendered event batches before framing or publishing.
6. **Report exact delivery evidence**, honoring live-only gateway fanout (`stored_count: 0`, `delivered_count`, and `default_sink_due_to_no_destination`).

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, [references/protocol-and-impl.md](references/protocol-and-impl.md), and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Keep gateway targets explicit in `admin` posture and default to verified self in `agent` posture. Route built-in Plotly/Vega-Lite chart authoring to `houmao-shared-routines->houmao-ext-graphing`, gateway lifecycle to `houmao-shared-routines->houmao-agent-gateway`, and task/prompt submission to `houmao-shared-routines->houmao-agent-messaging`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `validate` | Validate standard AG-UI event batches or Houmao implementation payloads. | [commands/validate.md](commands/validate.md) |
| `frame` | Frame validated AG-UI event batches as `json`, `jsonl`, or `sse` for streams or third-party endpoints. | [commands/frame.md](commands/frame.md) |
| `render` | Render Houmao implementations (`houmao.table`, `houmao.metric_grid`, `houmao.dashboard`), custom `new-component` contracts, or generic protocol tool calls into standard AG-UI events. | [commands/render.md](commands/render.md) |
| `publish` | Publish validated AG-UI event batches to a live Houmao gateway and interpret fanout counts. | [commands/publish.md](commands/publish.md) |
| `help` | Read-only guidance on protocol vs impl boundaries, durable identity, input permissions, and live-only fanout. | **Help** |

## Help

Summarize the four operations (`validate`, `frame`, `render`, `publish`) and key contracts in [references/protocol-and-impl.md](references/protocol-and-impl.md): `ag-ui protocol` validates/frames standard events, `ag-ui impl` validates/renders Houmao contracts, `agent_id`/`agent_name` (not a transient gateway URL) is the durable workbench target, gateway `ag-ui publish` is live-only fanout (`stored_count: 0`) with no `--endpoint` flag, and AG-UI client input paths separate `agent.request.submit` (`agent-requester` default) from `agent.prompt.direct` (`agent-operator`). Concrete tasks route to the matching subcommand instead of stopping at generic help.

## Guardrails

- DO NOT hand-write raw AG-UI tool-call event arrays when `ag-ui impl render`, `ag-ui impl new-component render`, or `ag-ui protocol tool-call render` can generate them.
- DO NOT publish unrendered implementation payloads directly to a gateway, or claim GUI visibility when `delivered_count` is `0` or `default_sink_due_to_no_destination` is present.
- DO NOT pass `--endpoint` to `gateway ag-ui publish`, guess `--run-id`/`--connection-id` values, treat `last-sent-thread` as automatic routing, or treat a transient gateway URL as durable agent identity.
- DO NOT call prompt commands (`agent.prompt.direct`) to display AG-UI events, or conflate attributed `agent.request.submit` work requests with `agent.prompt.direct` turns.
- DO NOT include credentials, tokens, cookies, private keys, auth files, unrequested private local file contents, raw HTML, scriptable SVG, JavaScript URLs, or iframes in payloads or events.
