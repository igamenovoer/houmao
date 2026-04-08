# List Credentials

Use this action only when the user wants to list project-local auth bundles for one supported tool.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family from the current prompt first and recent chat context second when it was stated explicitly.
3. If the tool family is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the tool.
4. Run `project agents tools <tool> auth list`.
5. Report the listed auth bundles from the command output.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> project agents tools <tool> auth list
```

## Guardrails

- Do not ask for a bundle name when the task is only to list credentials.
- Do not guess the tool family when the prompt and recent chat context do not identify it explicitly.
- Do not route listing through `project easy specialist` or managed-agent lifecycle commands.
- Do not reinterpret the auth-bundle list as the set of easy profiles or explicit launch profiles that reference those bundles.
- Do not filter or reinterpret the list unless the user explicitly asks for additional selection after listing.
