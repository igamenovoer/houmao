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

# Inspect or Refresh Native Resources

## Workflow

1. Preserve the parent actor frame. Select verified self or an explicit agent with supported execution-owner or gateway authority.
2. Choose home inspection, a read-only freshness check, or a refresh the caller requested. For gateway-managed logical files, hand off to `houmao-shared-routines->houmao-agent-files` with the same target.
3. Use the selected launcher and the matching command from **Command Shapes**.
4. Report the observed scope, state, and native boundary. Use **Reading Results** for incomplete evidence or a restart requirement.

If the task does not fit these steps, use the native planning tool to plan from this command, its constraints, and the user's request, then execute the plan.

## Command Shapes

```bash
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" home
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" refresh --check
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" refresh
```

For verified self, use `agents self home`, `agents self refresh --check`, or `agents self refresh`. The reported path belongs to the selected execution context. Use the target owner's supported native tools for ordinary edits outside a gateway-managed mount.

## Reading Results

`refresh --check` observes without requesting a reload. The common-plugin view covers skills and MCP. Use the body's native facilities for native-special-plugin inspection. A supported refresh may reload those extensions as a side effect.

Report each resource as current, pending, or unknown according to the observed scope. Carry forward health and native settlement when reported. Automatic discovery may report a next-step, next-turn, or next-load boundary. A busy self refresh cannot finish inside the turn that requested it. Qualified local inspection and no-op or automatic results can work with the gateway detached. Mutating reload requires an attached gateway.

After an uncertain response, observe freshness and readiness again. If the runtime reports a restart requirement or the caller needs launch-derived inputs regenerated, explain the result and obtain a separate relaunch decision. Its conversation policy applies.

## Guardrails

- DO NOT treat a reported native home as permission to edit files in another execution context.
- DO NOT use refresh to install resources, edit gateway-managed mounts, or regenerate project launch inputs.
- DO NOT infer freshness or readiness from unknown evidence or repeat an uncertain mutation automatically.
