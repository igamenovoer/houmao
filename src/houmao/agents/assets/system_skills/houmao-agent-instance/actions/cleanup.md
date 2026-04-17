# Clean Up Agent Instance Artifacts

Use this action only when the user wants to clean stopped-session managed-agent artifacts after stop.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Determine which cleanup kind the user wants:
   - `session` for one stopped managed-session envelope
   - `logs` for session-local log artifacts
3. Recover one supported cleanup selector from the current prompt first and recent chat context second when it was stated explicitly:
   - Prefer `--manifest-path` or `--session-root` from recent stop output when present.
   - Use `--agent-id` or `--agent-name` when no durable path locator is available but the target identity was stated explicitly. These selectors can recover stopped sessions through bounded runtime-root fallback after the live registry record has been removed.
4. If the cleanup kind or selector is still missing, ask the user in Markdown before proceeding. Prefer a compact table that shows the cleanup kind choices and the selectors still needed.
5. Include `--dry-run` only when the user explicitly asks to preview cleanup.
6. Run the selected cleanup command. Session cleanup removes the stopped session envelope and does not remove the managed-agent memory root.
7. Report the resulting `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions`.

## Command Shape

Prefer the durable locators returned by stop output:

```text
<chosen houmao-mgr launcher> agents cleanup session --manifest-path <path>
<chosen houmao-mgr launcher> agents cleanup session --session-root <path>
```

If no path locator is available, use an explicit name or id selector:

```text
<chosen houmao-mgr launcher> agents cleanup session --agent-name <name>
<chosen houmao-mgr launcher> agents cleanup session --agent-id <id>
```

For log cleanup, use:

```text
<chosen houmao-mgr launcher> agents cleanup logs --manifest-path <path>
<chosen houmao-mgr launcher> agents cleanup logs --session-root <path>
<chosen houmao-mgr launcher> agents cleanup logs --agent-name <name>
<chosen houmao-mgr launcher> agents cleanup logs --agent-id <id>
```

## Guardrails

- Do not route cleanup work to `agents cleanup mailbox`; mailbox secret cleanup is out of scope.
- Do not route instance cleanup to `admin cleanup runtime ...`; that broader maintenance surface is out of scope.
- Do not guess the cleanup kind or cleanup selector.
- Do not widen a vague cleanup request into session or logs cleanup without user confirmation.
- Do not assume cleanup is safe for a live session; this skill is for stopped-session cleanup only.
- Do not create or search stopped-session tombstones, stopped-agent indexes, or unsupported registry state.
