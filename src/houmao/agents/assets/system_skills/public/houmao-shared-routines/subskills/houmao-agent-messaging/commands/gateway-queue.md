# Use Gateway Prompt Admission Control

Use this action only when the user explicitly wants a nondefault live-gateway prompt-admission policy, gateway-owned TUI inspection, or prompt provenance beyond the ordinary gateway-preferred prompt path.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and the requested gateway action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target, prompt text, or explicit gateway intent, ask the user in Markdown before proceeding.
4. Run `agents single ... gateway status` or `agents self gateway status` first when the current context does not already confirm live gateway availability.
5. Map the caller's intent to one prompt-admission policy:
   - `ready-only`: submit only when the TUI is stably ready and has no provider-native pending prompt; this is the default
   - `if-no-pending`: permit submission while the TUI is busy, but back off when pending input is `yes` or `unknown`
   - `always`: submit regardless of tracked readiness and provider-native pending input
6. Use `agents single ... gateway prompt` or `agents self gateway prompt` with the selected `--admission-policy`. Use the corresponding `gateway interrupt` path for an interrupt.
7. Use `agents single ... gateway tui state|history` or `agents self gateway tui state|history` when the task needs the exact raw gateway-owned TUI tracker surface before or after prompt control.
8. Use `agents single ... gateway tui note-prompt` or `agents self gateway tui note-prompt` when the task needs prompt provenance without submitting a prompt.
9. If the caller is already operating through the pair-managed HTTP API, use the managed-agent gateway routes in `references/managed-agent-http.md`.
10. Report the selected admission policy, gateway result, or TUI inspection outcome.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Command Shapes

Policy-controlled prompt:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway prompt --admission-policy <ready-only|if-no-pending|always> --prompt "<message>"
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

`surface.pending_input` means provider-native submitted input waiting behind an active turn. It is independent from an unsubmitted composer draft, gateway-durable requests, and a Houmao prompt note. Conditional policies fail closed on `unknown`. Admission is observational, so two closely spaced `if-no-pending` calls can both dispatch before the provider surface repaints.

## Guardrails

- Do not silently replace explicit gateway prompt-control work with `agents single ... prompt`, `agents self prompt`, `agents single ... interrupt`, or `agents self interrupt`.
- Do not describe direct gateway prompt control as gateway-durable queued work.
- Do not choose `always` unless the caller explicitly wants submission regardless of readiness and pending input.
- Do not promise atomic queue-slot reservation for `if-no-pending`.
- Do not use this action for exact raw key delivery; use `commands/send-keys.md` instead.
- Do not claim that `tui note-prompt` submits a queued prompt turn.
- Do not proceed when the requested queued action still lacks a target or prompt body.
