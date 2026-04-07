# Remove Credential

Use this action only when the user wants to remove one existing project-local auth bundle.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the tool family and bundle name from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family or bundle name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
4. Run `project agents tools <tool> auth remove --name <name>`.
5. Report the removed auth bundle name and path returned by the command.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project agents tools <tool> auth remove --name <name>
```

## Guardrails

- Do not guess which tool or auth bundle the user meant.
- Do not remove multiple auth bundles unless the user explicitly asks for that broader operation.
- Do not present removal as changing specialists, easy profiles, explicit launch profiles, live instances, or mailbox credentials automatically.
- Do not route removal through direct filesystem deletion when the CLI surface already owns the operation.
