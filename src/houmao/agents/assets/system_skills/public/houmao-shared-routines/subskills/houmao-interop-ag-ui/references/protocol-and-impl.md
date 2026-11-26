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

# AG-UI Protocol, Implementation, Identity, and Gateway Input Reference

## Surface Comparison

| Surface | CLI Prefix | Responsibility |
| --- | --- | --- |
| Standard AG-UI protocol | `houmao-mgr ag-ui protocol ...` | Schema-agnostic event validation (`events validate`), wire framing (`events frame --format json\|jsonl\|sse`), and generic tool-call rendering (`tool-call render`). |
| Houmao implementations | `houmao-mgr ag-ui impl ...` | Schema discovery (`list`, `schema`), payload validation (`validate`), and rendering (`render`) for `houmao.table`, `houmao.metric_grid`, `houmao.dashboard`, and built-in graphics (authored via `houmao-shared-routines->houmao-ext-graphing`). |
| Custom GUI component | `houmao-mgr ag-ui impl new-component render` | Renders standard tool-call events (`--tool-name <name> --args payload.json`) when the user supplies a frontend-specific contract outside `ag-ui impl list`. |
| Houmao gateway publish | `houmao-mgr agents self\|single ... gateway ag-ui publish` | Live-only fanout of validated AG-UI event batches to connected GUI/run subscribers (`stored_count: 0`, no `--endpoint`). |

## Durable Identity vs Transient Gateway Coordinates

`agent_id` (or an unambiguous `agent_name`) is the durable address of a managed agent. Gateway host and port values are transient transport coordinates that can change across gateway detach/attach or agent relaunch; the Houmao AG-UI workbench binds to `agent_id`/`agent_name` and resolves current live coordinates via `houmao-passive-server`.

## Gateway Client Input Permissions (`request` vs `prompt`)

AG-UI event publishing (`gateway ag-ui publish`) is output-only GUI fanout and never submits agent work. When an AG-UI client or workbench submits input back to a target agent's gateway, two distinct permission actions apply:

- **Attributed work request (`agent.request.submit`)**: allowed by the default `agent-requester` built-in group (`houmao-mgr agents single ... request`); delivers attributed task text under the target agent's existing instructions.
- **Direct verbatim prompt (`agent.prompt.direct`)**: requires `agent-operator` (or higher) authority (`houmao-mgr agents single ... prompt`); injects a direct operator-level turn.

Route input submission workflows to `houmao-shared-routines->houmao-agent-messaging` and policy grants to `houmao-shared-routines->houmao-agent-access`.

## End-to-End `houmao.table` Example

```json
{
  "schemaVersion": 1,
  "title": "Top Issues",
  "columns": [
    { "key": "id", "label": "ID" },
    { "key": "count", "label": "Count", "kind": "number", "align": "right" }
  ],
  "rows": [
    { "id": "A", "count": 4 },
    { "id": "B", "count": 2 }
  ]
}
```

```bash
houmao-mgr ag-ui impl validate houmao.table --input payload.json
houmao-mgr ag-ui impl render houmao.table --input payload.json > events.json
houmao-mgr ag-ui protocol events validate --input events.json
houmao-mgr agents self gateway ag-ui publish --input events.json
```

Prefer typed labels, numbers, rows, metrics, and dashboard children; never embed secrets, private files, or unsanitized HTML/SVG/JS.
