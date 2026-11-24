# Use Gateway Prompt Admission Control

Use this action when the user explicitly requests live-gateway prompt admission, gateway-owned TUI inspection, or prompt provenance.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and the requested gateway action from the current prompt first and recent chat context second when they were stated explicitly.
3. If the task still lacks a required target, prompt text, or explicit gateway intent, ask the user in Markdown before proceeding.
4. Run `agents single ... gateway status` or `agents self gateway status` first when the current context does not already confirm live gateway availability.
5. Map the caller's intent to one prompt-admission policy:
   - `ready-only`: submit only when the TUI is stably ready and has no provider-native pending prompt; this is the default
   - `if-no-pending`: permit submission while the TUI is busy, but back off when pending input is `yes` or `unknown`
   - `always`: submit regardless of tracked readiness and provider-native pending input
6. Submit once with `agents single ... gateway prompt` or `agents self gateway prompt` and the selected `--admission-policy`. Use the corresponding `gateway interrupt` path for an interrupt.
7. Use `agents single ... gateway tui state|history` or `agents self gateway tui state|history` when the task needs the exact raw gateway-owned TUI tracker surface before or after prompt control.
8. Use `agents single ... gateway tui note-prompt` or `agents self gateway tui note-prompt` when the task needs prompt provenance without submitting a prompt.
9. If the caller is already operating through the pair-managed HTTP API, use the managed-agent gateway routes in `references/managed-agent-http.md`.
10. Report the selected admission policy and the evidence from the first receipt. Use read-only inspection for additional details.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Command Shapes

Policy-controlled prompt:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway prompt --admission-policy <ready-only|if-no-pending|always> --prompt "<message>"
```

## Read the Receipt

The receipt shows `status`, `action`, `admission_policy`, `sent`, and `detail` in every output mode. Retain `operation_id` and `native_prompt_id` when returned. Report `outcome: queued` with `sent: false` as accepted queueing. A `sent: true` receipt confirms handoff. Observe provider completion separately when the evidence supports it.

- For a saved headless turn, use `agents single ... turn status <turn-id>` or `turn events <turn-id>`. The matching `agents self turn ...` reads the current agent.
- For a service request, use the existing authorized `GET /v1/control/service/requests/{operation_id}` route to inspect the exact request.
- For Web, use the authorized native state or bounded history routes `GET /v1/control/web/state` and `GET /v1/control/web/history`. Correlate the available operation or native prompt ID where the observation supplies matching evidence.
- For TUI, use `gateway tui state` or `history` to inspect terminal activity. Preserve uncertainty when Web or TUI observation cannot establish the exact outcome.

## Related Gateway Controls

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

- DO NOT silently replace explicit gateway prompt-control work with `agents single ... prompt`, `agents self prompt`, `agents single ... interrupt`, or `agents self interrupt`.
- DO NOT describe direct gateway prompt control as gateway-durable queued work.
- DO NOT choose `always` unless the caller explicitly wants submission regardless of readiness and pending input.
- DO NOT promise atomic queue-slot reservation for `if-no-pending`.
- DO NOT use this action for exact raw key delivery; use `commands/send-keys.md` instead.
- DO NOT claim that `tui note-prompt` submits a queued prompt turn.
- DO NOT proceed when the requested queued action still lacks a target or prompt body.
