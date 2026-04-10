# Get Credential

Use this action only when the user wants to inspect one credential safely through the supported redacted CLI surface.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user in Markdown before proceeding.
4. Run the selected command.
5. Report the structured credential details returned by the command. If diagnostic `bundle_ref`, projected path, or filesystem path data is returned, keep it secondary to the operator-facing credential name.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project credentials <tool> get --name <name>
<chosen houmao-mgr launcher> credentials <tool> get --agent-def-dir <path> --name <name>
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not bypass `get` by reading raw `env/vars.env` or raw auth files just to expose secrets.
- Do not print raw secret values when the command reports them as present but redacted.
- Do not treat `get` as inspection of a stored easy-profile or explicit launch-profile `--auth` override.
