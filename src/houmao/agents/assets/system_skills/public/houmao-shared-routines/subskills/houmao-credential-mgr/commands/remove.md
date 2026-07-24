# Remove Credential

Use this action only when the user wants to remove one existing credential.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, credential name, and target from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, credential name, or target is still missing, ask the user before proceeding.
4. Run the direct credential remove command.
6. Report the removed credential name and any diagnostic path returned by the command.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shape

Run the matching direct command:

```bash
<chosen houmao-mgr launcher> project credentials <tool> remove --name <credential>
<chosen houmao-mgr launcher> internals native-agent credentials <tool> remove --native-agent-root <dir> --name <credential>
```

## Guardrails

- Do not guess which tool, target, or credential the user meant.
- Do not remove multiple credentials unless the user explicitly asks for that broader operation.
- Do not present removal as changing specialists, project profiles, launch dossiers, live instances, or mailbox credentials automatically.
- Do not route removal through direct filesystem deletion when the CLI surface already owns the operation.
