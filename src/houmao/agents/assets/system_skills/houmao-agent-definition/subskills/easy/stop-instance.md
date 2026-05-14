# Stop Easy Instance

Use this subskill only when the user wants to stop one project-easy managed agent through `project easy instance stop`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Use this subskill for the project-easy stop entry point. General live-agent stop belongs to `houmao-agent-instance`.

## Workflow

1. Recover the easy-instance name from the prompt or explicit recent context.
2. Ask for the name if it is still missing.
3. Run `project easy instance stop --name <name>`.
4. Report the stop result.
5. Tell the user that broader live-agent lifecycle management belongs to `houmao-agent-instance`.

## Command Shape

```text
<chosen houmao-mgr launcher> project easy instance stop --name <name>
```

## Guardrails

- Do not guess which easy instance the user meant.
- Do not stop from partial name inference.
- Do not route easy-workflow stop through `agents stop`.
- Do not combine stop with cleanup unless the user explicitly asks for cleanup after stop.
