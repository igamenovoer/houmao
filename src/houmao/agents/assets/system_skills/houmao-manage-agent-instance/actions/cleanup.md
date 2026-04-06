# Clean Up Agent Instance Artifacts

Use this action only when the user wants to clean stopped-session managed-agent artifacts after stop.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Determine which cleanup kind the user wants:
   - `session` for one stopped managed-session envelope
   - `logs` for session-local log artifacts
3. Recover one supported cleanup selector from the current prompt first and recent chat context second when it was stated explicitly:
   - `--agent-id`
   - `--agent-name`
   - `--manifest-path`
   - `--session-root`
4. If the cleanup kind or selector is still missing, ask the user in Markdown before proceeding. Prefer a compact table that shows the cleanup kind choices and the selectors still needed.
5. Include `--dry-run` only when the user explicitly asks to preview cleanup.
6. For `cleanup session`, include `--include-job-dir` only when the user explicitly wants the persisted job dir removed together with the stopped session envelope.
7. Run the selected cleanup command.
8. Report the resulting `planned_actions`, `applied_actions`, `blocked_actions`, and `preserved_actions`.

## Command Shape

Use one of:

```text
<resolved houmao-mgr launcher> agents cleanup session --agent-name <name>
<resolved houmao-mgr launcher> agents cleanup session --agent-id <id>
<resolved houmao-mgr launcher> agents cleanup session --manifest-path <path>
<resolved houmao-mgr launcher> agents cleanup session --session-root <path>
```

or:

```text
<resolved houmao-mgr launcher> agents cleanup logs --agent-name <name>
<resolved houmao-mgr launcher> agents cleanup logs --agent-id <id>
<resolved houmao-mgr launcher> agents cleanup logs --manifest-path <path>
<resolved houmao-mgr launcher> agents cleanup logs --session-root <path>
```

## Guardrails

- Do not route cleanup work to `agents cleanup mailbox`; mailbox secret cleanup is out of scope.
- Do not route instance cleanup to `admin cleanup runtime ...`; that broader maintenance surface is out of scope.
- Do not guess the cleanup kind or cleanup selector.
- Do not widen a vague cleanup request into session or logs cleanup without user confirmation.
- Do not assume cleanup is safe for a live session; this skill is for stopped-session cleanup only.
