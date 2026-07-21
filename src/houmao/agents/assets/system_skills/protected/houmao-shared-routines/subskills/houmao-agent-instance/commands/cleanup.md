# Clean Up Agent Instance Artifacts

Use this action only when the user wants to clean stopped-session managed-agent artifacts after stop.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine which cleanup kind the user wants:
   - `session` for one stopped managed-session envelope
   - `logs` for session-local log artifacts
3. Recover one supported cleanup selector from the current prompt first and recent chat context second when it was stated explicitly:
   - Prefer `--manifest-path` or `--session-root` from recent stop output when present.
   - Use `--agent-id` or `--agent-name` when no durable path locator is available but the target identity was stated explicitly. These selectors prefer cleanup-capable lifecycle registry records, including stopped records preserved by `agents single ... stop`, and fall back to bounded runtime-root fallback scanning only when no matching lifecycle record exists.
4. If the cleanup kind or selector is still missing, ask the user in Markdown before proceeding. Prefer a compact table that shows the cleanup kind choices and the selectors still needed.
5. Include `--dry-run` only when the user explicitly asks to preview cleanup.
6. Build the direct `agents single ... cleanup session` or `agents single ... cleanup logs` command.
7. Run the direct command. Session cleanup removes the stopped session envelope, retires the stopped lifecycle record by default, and does not remove the managed-agent memory root. Add `--purge-registry` only when the user explicitly wants to delete the lifecycle record entirely.
8. Report the resulting `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions`.

## Command Shape

Run one of the direct cleanup commands:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> cleanup session [--manifest-path <path> | --session-root <path>] [--dry-run]
<chosen houmao-mgr launcher> agents single --agent-name <agent-name> cleanup logs [--manifest-path <path> | --session-root <path>] [--dry-run]
```

## Guardrails

- Do not route cleanup work to an `agents self cleanup` path; destructive cleanup belongs under `agents single ... cleanup`.
- Do not route instance cleanup to `admin cleanup runtime ...`; that broader maintenance surface is out of scope.
- Do not guess the cleanup kind or cleanup selector.
- Do not widen a vague cleanup request into session or logs cleanup without user confirmation.
- Do not assume cleanup is safe for a live session; this skill is for stopped-session cleanup only.
- Do not add `--purge-registry` unless the user explicitly asks to delete the lifecycle record.
- Do not create or search stopped-session tombstones, stopped-agent indexes, or unsupported registry state.
- Do not add `--purge-registry` unless the user explicitly asks to delete the lifecycle record.
