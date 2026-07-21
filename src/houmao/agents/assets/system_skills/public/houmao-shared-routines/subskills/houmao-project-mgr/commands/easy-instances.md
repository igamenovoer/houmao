---
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

# Inspect Or Stop Project Managed Agents Through The Selected Overlay

Use this action only when the user wants to list, inspect, or stop project-managed agents through the selected project overlay.

## Workflow

1. Determine whether the user wants to `list`, `get`, or `stop` one project-managed agent.
2. Recover the instance name from the prompt or recent chat context when it was stated explicitly.
3. If the action or required instance name is still missing, ask before proceeding.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching project managed-agent command.
6. Report the selected overlay details and the instance result from the command output.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project agents list
<chosen houmao-mgr launcher> project agents get --name <name>
<chosen houmao-mgr launcher> project agents stop --name <name>
```

## Behavior Notes

- These commands use non-creating selected-overlay resolution and therefore require an already-existing selected project overlay.
- `get` and `stop` verify that the managed agent belongs to the selected overlay.
- Specialist-backed or profile-backed project launch remains on `houmao-shared-routines->houmao-agent-definition`.

## Guardrails

- Do not guess an instance name for `get` or `stop`.
- Do not route project managed-agent `launch` through this action.
- Do not present these commands as the canonical generic lifecycle surface after the user leaves the project-scoped inspection or stop task; broader live-agent lifecycle belongs to `houmao-shared-routines->houmao-agent-instance`.
