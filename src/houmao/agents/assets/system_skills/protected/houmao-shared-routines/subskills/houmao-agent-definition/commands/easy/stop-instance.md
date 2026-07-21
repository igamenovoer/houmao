# Stop Project Managed Agent

Use this subskill only when the user wants to stop one project managed agent through `project agents stop`.

## Preconditions

- Read [../../references/common/launcher.md](../../references/common/launcher.md).
- Read [../../references/common/missing-inputs.md](../../references/common/missing-inputs.md).
- Use this subskill for the project stop entry point. General live-agent stop belongs to `<public-entrypoint>->houmao-shared-routines->agent-instance`.

## Workflow

1. Recover the project managed-agent name from the prompt or explicit recent context.
2. Ask for the name if it is still missing.
3. Run `project agents stop --name <name>`.
4. Report the stop result.
5. Tell the user that broader live-agent lifecycle management belongs to `<public-entrypoint>->houmao-shared-routines->agent-instance`.

## Command Shape

```text
<chosen houmao-mgr launcher> project agents stop --name <name>
```

## Guardrails

- Do not guess which project managed agent the user meant.
- Do not stop from partial name inference.
- Do not route project stop through generic selected-agent lifecycle unless the user asks for broader live-agent control; use `agents single --agent-name <name> stop` only for the canonical shared-registry lifecycle surface.
- Do not combine stop with cleanup unless the user explicitly asks for cleanup after stop.
