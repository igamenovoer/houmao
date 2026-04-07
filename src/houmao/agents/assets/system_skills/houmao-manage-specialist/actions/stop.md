# Stop Specialist-Backed Instance

Use this action only when the user wants to stop one easy instance in the specialist workflow.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the easy-instance name from the current prompt first and recent chat context second when it was stated explicitly.
3. If the easy-instance name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the instance name.
4. Run `project easy instance stop --name <name>`.
5. Report the stop result returned by the command.
6. Tell the user that further agent management should go through `houmao-manage-agent-instance`.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project easy instance stop --name <name>
```

## Guardrails

- Do not guess which easy instance the user meant.
- Do not stop an instance from partial name inference when the prompt and recent chat context do not identify it explicitly.
- Do not route specialist-scoped stop through `agents stop`.
- Do not combine stop with cleanup unless the user explicitly asks for cleanup after stop.
- Do not imply that the specialist skill is the canonical surface for broader live-agent lifecycle management after stop.
