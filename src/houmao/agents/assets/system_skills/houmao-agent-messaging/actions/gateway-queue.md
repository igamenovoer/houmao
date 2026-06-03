# Use Gateway Queue Control

Use this action only when the user explicitly wants live-gateway queue semantics, gateway-owned TUI inspection, or prompt provenance beyond the ordinary gateway-preferred prompt path.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and the requested gateway action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target, prompt text, or explicit gateway intent, ask the user in Markdown before proceeding.
4. Run `agents single ... gateway status` or `agents self gateway status` first when the current context does not already confirm live gateway availability.
5. Use `agents single ... gateway prompt` or `agents self gateway prompt` for queued prompt submission, and the corresponding `gateway interrupt` path for queued interrupt submission.
6. Use `agents single ... gateway tui state|history` or `agents self gateway tui state|history` when the task needs the exact raw gateway-owned TUI tracker surface before or after queued work.
7. Use `agents single ... gateway tui note-prompt` or `agents self gateway tui note-prompt` when the task needs prompt provenance without submitting a queued request.
8. If the caller is already operating through the pair-managed HTTP API, use the managed-agent gateway routes in `references/managed-agent-http.md`.
9. Report the gateway request result or the selected TUI inspection outcome.

## Command Shapes

Queued prompt:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway prompt --prompt "<message>"
```

Queued interrupt:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway interrupt
```

Related gateway-owned TUI inspection:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway tui state
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway tui history
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway tui note-prompt --prompt "<note>"
```

The gateway prompt path also accepts `--force` when the user explicitly wants to bypass prompt-readiness checks.

## Guardrails

- Do not silently replace explicit gateway queue work with `agents single ... prompt`, `agents self prompt`, `agents single ... interrupt`, or `agents self interrupt`.
- Do not describe queued gateway requests as the same guarantee as direct prompt control.
- Do not use this action for exact raw key delivery; use `actions/send-keys.md` instead.
- Do not claim that `tui note-prompt` submits a queued prompt turn.
- Do not proceed when the requested queued action still lacks a target or prompt body.
