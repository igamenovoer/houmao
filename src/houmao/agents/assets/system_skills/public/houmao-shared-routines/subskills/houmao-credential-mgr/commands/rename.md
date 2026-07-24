# Rename Credential

Use this action only when the user wants to rename one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, current credential name, new credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If any of those inputs are still missing, ask the user before proceeding.
4. Run the direct credential rename command.
6. Report the renamed credential name, previous name, and any diagnostic metadata returned by the command.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> rename --name <credential> --to <new-credential>
<chosen houmao-mgr launcher> internals native-agent credentials <tool> rename --native-agent-root <dir> --name <credential> --to <new-credential>
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not treat rename as env or auth-file mutation; use `set` for content changes.
- Do not present project-backed rename as requiring manual directory moves or launch-profile rewrites.
- Do not present direct-dir rename as metadata-only; it rewrites maintained `presets/*.yaml` and `launch-profiles/*.yaml` auth references for that selected tool.
- Do not imply that any returned auth path is always a user-facing identity surface.
