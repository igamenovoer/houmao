# List Credentials

Use this action only when the user wants to list credentials for one supported tool.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family from the current prompt first and recent chat context second when it was stated explicitly.
3. Recover the target:
   - use `project credentials <tool> list` when the request is project-local
   - use `credentials <tool> list --agent-def-dir <path>` when the user explicitly targets a plain agent-definition directory
4. If the tool family or target is still missing, ask the user in Markdown before proceeding.
5. Run the selected command and report the listed credential names.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project credentials <tool> list
<chosen houmao-mgr launcher> credentials <tool> list --agent-def-dir <path>
```

## Guardrails

- Do not ask for a credential name when the task is only to list credentials.
- Do not guess the tool family or target when the prompt and recent chat context do not identify them explicitly.
- Do not route listing through `project easy specialist` or managed-agent lifecycle commands.
- Do not reinterpret the credential list as the set of easy profiles or explicit launch profiles that reference those credentials.
