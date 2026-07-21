# Get Credential

Use this action only when the user wants to inspect one credential safely through the supported redacted CLI surface.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user in Markdown before proceeding.
4. Run the direct credential get command.
6. Report the structured credential details returned by the command. If diagnostic `bundle_ref`, projected path, or filesystem path data is returned, keep it secondary to the operator-facing credential name.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> get --name <credential>
<chosen houmao-mgr launcher> internals native-agent credentials <tool> get --native-agent-root <dir> --name <credential>
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not bypass `get` by reading raw `env/vars.env` or raw auth files just to expose secrets.
- Do not print raw secret values when the command reports them as present but redacted.
- Do not treat `get` as inspection of a stored project-profile or launch-dossier `--auth` override.
