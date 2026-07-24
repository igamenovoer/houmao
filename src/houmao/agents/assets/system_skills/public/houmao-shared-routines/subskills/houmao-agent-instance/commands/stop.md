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

# Stop Agent Instance

Use this action only when the user wants to stop one live managed agent. This remains the canonical general lifecycle stop action even though `houmao-shared-routines->houmao-agent-definition` also owns specialist-scoped easy-instance stop requests.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the managed-agent target from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the live managed-agent name or id.
4. Run `agents single --agent-id <id> stop` or `agents single --agent-name <name> stop` against that target.
5. Report the stop result returned by the command, including `manifest_path` and `session_root` when present because those are the preferred durable locators for any explicit post-stop cleanup request. For tmux-backed relaunchable local sessions, stop now preserves a stopped lifecycle record so later relaunch or cleanup keeps the same managed-agent identity instead of behaving like a fresh launch.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> stop
```

or:

```text
<chosen houmao-mgr launcher> agents single --agent-id <id> stop
```

## Guardrails

- Do not guess which live managed agent the user meant.
- Do not stop an agent from partial name inference when the prompt and recent chat context do not identify it explicitly.
- Do not route stop requests through `project agents stop` unless the user specifically wants the selected-project facade; use the canonical `agents single ... stop` lifecycle surface for general selected-agent stop.
- Do not combine stop with cleanup unless the user explicitly asks for cleanup after stop.
