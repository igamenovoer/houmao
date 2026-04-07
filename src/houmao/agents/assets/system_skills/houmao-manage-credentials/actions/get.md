# Get Credential

Use this action only when the user wants to inspect one project-local auth bundle safely through the supported redacted CLI surface.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the tool family and bundle name from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family or bundle name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
4. Run `project agents tools <tool> auth get --name <name>`.
5. Report the structured bundle details returned by the command.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project agents tools <tool> auth get --name <name>
```

## Guardrails

- Do not guess which tool or auth bundle the user meant.
- Do not bypass `auth get` by reading raw `env/vars.env` or raw auth files just to expose secrets.
- Do not print raw secret values when the command reports them as present but redacted.
- Do not treat `auth get` as inspection of a stored easy-profile or explicit launch-profile `--auth` override.
- Do not enter specialist-authoring flow or credential-discovery flow for this action.
