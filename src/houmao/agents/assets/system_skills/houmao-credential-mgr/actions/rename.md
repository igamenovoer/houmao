# Rename Credential

Use this action only when the user wants to rename one existing project-local auth bundle without changing its underlying stored auth identity.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the tool family, current auth display name, and new auth display name from the current prompt first and recent chat context second when they were stated explicitly.
3. If the tool family, current name, or new name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
4. Run `project agents tools <tool> auth rename --name <old> --to <new>`.
5. Report the renamed auth display name, previous display name, and any diagnostic metadata returned by the command.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> project agents tools <tool> auth rename --name <old> --to <new>
```

## Guardrails

- Do not guess which tool or auth bundle the user meant.
- Do not treat rename as env or auth-file mutation; use `auth set` for content changes.
- Do not present auth rename as requiring manual directory moves or launch-profile rewrites.
- Do not imply that any returned auth path is a user-facing identity surface; projected auth directory basenames are opaque implementation detail.
