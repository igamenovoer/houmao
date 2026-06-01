# Rename Credential

Use this action only when the user wants to rename one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, current credential name, new credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If any of those inputs are still missing, ask the user before proceeding.
4. Render the selected command template: `project.credentials.<tool>.rename` or `credentials.<tool>.rename`.
5. Run the rendered `argv`.
6. Report the renamed credential name, previous name, and any diagnostic metadata returned by the command.

## Command Shape

Use the matching CLI-owned template, then run its rendered `argv`:

```text
<chosen houmao-mgr launcher> --print-json internals command-templates render --id project.credentials.<tool>.rename --intent '<json>'
<chosen houmao-mgr launcher> --print-json internals command-templates render --id credentials.<tool>.rename --intent '<json>'
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not treat rename as env or auth-file mutation; use `set` for content changes.
- Do not present project-backed rename as requiring manual directory moves or launch-profile rewrites.
- Do not present direct-dir rename as metadata-only; it rewrites maintained `presets/*.yaml` and `launch-profiles/*.yaml` auth references for that selected tool.
- Do not imply that any returned auth path is always a user-facing identity surface.
