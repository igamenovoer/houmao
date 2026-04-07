# Stop Agent Instance

Use this action only when the user wants to stop one live managed agent. This remains the canonical general lifecycle stop action even though `houmao-manage-specialist` may also front specialist-scoped easy-instance stop requests.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the managed-agent target from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the live managed-agent name or id.
4. Run `agents stop` against that target.
5. Report the stop result returned by the command.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> agents stop --agent-name <name>
```

or:

```text
<resolved houmao-mgr launcher> agents stop --agent-id <id>
```

## Guardrails

- Do not guess which live managed agent the user meant.
- Do not stop an agent from partial name inference when the prompt and recent chat context do not identify it explicitly.
- Do not route stop requests through `project easy instance stop`; use the canonical `agents stop` lifecycle surface.
- Do not combine stop with cleanup unless the user explicitly asks for cleanup after stop.
