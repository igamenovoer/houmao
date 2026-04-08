# Relaunch Agent Instance

Use this action only when the user wants to relaunch one tmux-backed managed-agent surface without rebuilding the managed-agent home.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the relaunch target from the current prompt first and recent chat context second when it was stated explicitly.
3. If the user is clearly asking for current-session relaunch from inside the owning tmux session, allow the current-session `agents relaunch` form without requiring an unnecessary explicit selector.
4. If no explicit target is available and current-session relaunch is not clearly the intended valid path, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need the live managed-agent name or id.
5. Run `agents relaunch`.
6. Report the relaunch result returned by the command.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents relaunch --agent-name <name>
```

or:

```text
<chosen houmao-mgr launcher> agents relaunch --agent-id <id>
```

or, for current-session relaunch from inside the owning tmux session:

```text
<chosen houmao-mgr launcher> agents relaunch
```

## Guardrails

- Do not guess which live managed agent the user meant.
- Do not require an explicit selector when the supported current-session relaunch form is already the intended path.
- Do not reinterpret a relaunch request as `agents launch` or `project easy instance launch`.
- Do not claim that relaunch always recreates a missing tmux session or otherwise acts as a generic fresh-launch recovery path.
- If relaunch is unavailable because the selected session has no relaunch posture or the current-session authority cannot be resolved, report that relaunch is unavailable instead of silently switching to a fresh launch flow.
