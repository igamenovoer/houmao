# Use Gateway Queue Control

Use this action only when the user explicitly wants live-gateway queue semantics instead of the default synchronous prompt or interrupt path.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the target selector and the requested gateway action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target, prompt text, or explicit gateway intent, ask the user in Markdown before proceeding.
4. Run `agents gateway status` first when the current context does not already confirm live gateway availability.
5. Use `agents gateway prompt` for queued prompt submission or `agents gateway interrupt` for queued interrupt submission.
6. Use `agents gateway tui state|history` when the task needs the exact raw gateway-owned TUI tracker surface before or after queued work.
7. Use `agents gateway tui note-prompt` when the task needs prompt provenance without submitting a queued request.
8. If the caller is already operating through the pair-managed HTTP API, use the managed-agent gateway routes in `references/managed-agent-http.md`.
9. Report the gateway request result or the selected TUI inspection outcome.

## Command Shapes

Queued prompt:

```text
<resolved houmao-mgr launcher> agents gateway prompt --agent-name <name> --prompt "<message>"
```

Queued interrupt:

```text
<resolved houmao-mgr launcher> agents gateway interrupt --agent-name <name>
```

Related gateway-owned TUI inspection:

```text
<resolved houmao-mgr launcher> agents gateway tui state --agent-name <name>
<resolved houmao-mgr launcher> agents gateway tui history --agent-name <name>
<resolved houmao-mgr launcher> agents gateway tui note-prompt --agent-name <name> --prompt "<note>"
```

The gateway prompt path also accepts `--force` when the user explicitly wants to bypass prompt-readiness checks.

## Guardrails

- Do not silently replace explicit gateway queue work with `agents prompt` or `agents interrupt`.
- Do not describe queued gateway requests as the same guarantee as direct prompt control.
- Do not use this action for exact raw key delivery; use `actions/send-keys.md` instead.
- Do not claim that `tui note-prompt` submits a queued prompt turn.
- Do not proceed when the requested queued action still lacks a target or prompt body.
