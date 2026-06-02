# Get Credential

Use this action only when the user wants to inspect one credential safely through the supported redacted CLI surface.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user in Markdown before proceeding.
4. Render the selected command template: `project.credentials.<tool>.get` or `credentials.<tool>.get`.
5. Run the rendered `argv`.
6. Report the structured credential details returned by the command. If diagnostic `bundle_ref`, projected path, or filesystem path data is returned, keep it secondary to the operator-facing credential name.

## Command Shape

Use the matching CLI-owned template, then run its rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.credentials.<tool>.get --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id credentials.<tool>.get --intent '<json>'
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not bypass `get` by reading raw `env/vars.env` or raw auth files just to expose secrets.
- Do not print raw secret values when the command reports them as present but redacted.
- Do not treat `get` as inspection of a stored project-profile or launch-dossier `--auth` override.
