# Remove Credential

Use this action only when the user wants to remove one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user before proceeding.
4. Render the selected command template: `project.credentials.<tool>.remove` or `credentials.<tool>.remove`.
5. Run the rendered `argv`.
6. Report the removed credential name and any diagnostic path returned by the command.

## Command Shape

Use the matching CLI-owned template, then run its rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.credentials.<tool>.remove --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id credentials.<tool>.remove --intent '<json>'
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not remove multiple credentials unless the user explicitly asks for that broader operation.
- Do not present removal as changing specialists, project profiles, launch dossiers, live instances, or mailbox credentials automatically.
- Do not route removal through direct filesystem deletion when the CLI surface already owns the operation.
