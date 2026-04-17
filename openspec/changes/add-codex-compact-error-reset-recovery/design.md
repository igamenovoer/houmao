## Context

Issue 19 describes a Codex TUI surface where a remote compact task error appears, the composer returns, and the user can type another prompt such as "continue". That means the TUI input surface is prompt-ready. The repeated failure is a separate chat-context problem: the next semantic prompt should begin with clean context rather than reuse the current broken conversation.

Houmao currently treats the visible error as a readiness blocker by reducing the surface to unknown readiness. The gateway then refuses prompt-control delivery and the mail notifier records busy skips even though the user could submit text manually. This loses the distinction between "the terminal can accept input" and "the next prompt must start with clean context".

Existing gateway prompt control already has a headless request-body selector for fresh provider chat (`chat_session.mode = new`). TUI targets cannot set provider chat state through a structured request body; the gateway must send a tool-appropriate clear/reset signal before the real prompt. Local Codex source distinguishes `/new` from `/clear`: `/new` starts a new chat during a conversation, while `/clear` additionally clears terminal UI. For Codex fresh-chat recovery, `/new` is the precise reset signal; other TUI profiles may use `/clear` or another configured context-reset signal.

## Goals / Non-Goals

**Goals:**

- Make Codex prompt readiness reflect whether the composer can accept a new prompt.
- Keep current error evidence from being misreported as successful completion.
- Introduce a `reset_required` chat-context state that can coexist with prompt-ready input posture.
- Ensure the next accepted semantic prompt begins with clean context when chat context is `reset_required`.
- Use headless request-body chat-session selection for clean context, including `chat_session.mode = new`.
- Use tool-appropriate TUI clear/reset signals before prompt submission, including Codex `/new` and configured reset prompts such as `/clear`.
- Let the mail notifier recover prompt-ready `reset_required` sessions through the same clean-context prompt path.

**Non-Goals:**

- Treating `reset_required` as proof that the TUI input surface is not prompt-ready.
- Automatically resetting every prompt-ready Codex surface that has any historical error in scrollback.
- Treating a compact/server error as a successful turn.
- Guessing whether an upstream Codex/server bug has been fixed after the tracker has emitted `reset_required`.
- Adding a new external dependency or mailbox storage format.

## Decisions

### Separate input readiness from reset-required chat context

The Codex TUI profile will derive prompt readiness from current input-surface facts: stable composer, accepting input, no draft editing, no active turn, and no blocking overlay. A visible red error cell from the current latest turn can still block success settlement, but it must not by itself force `ready_posture` or `turn.phase` to unknown when the composer facts establish readiness.

The profile will also expose a chat-context state. When a prompt-adjacent compact/server-error surface matches the narrow reset-required signature, the chat-context state becomes `reset_required`. That state means the next accepted semantic prompt must start from clean context. It does not mean the input surface cannot accept the reset signal or a subsequent prompt.

Alternative considered: keep using a weaker "degraded context" diagnostic while allowing ordinary current-context prompts. That preserves continuity when continuation might work, but it does not satisfy the requirement that `reset_required` means the next prompt begins with clean context.

### Restrict error and reset detection to the prompt-adjacent live edge

Current error evidence and `reset_required` must be derived from the live edge of the current latest-turn surface near the prompt/composer, not arbitrary visible scrollback. A long Codex transcript can keep old error cells on screen; those historical cells must not become current error or reset-required state after the conversation has moved on.

Alternative considered: scan all visible text for compact/server-error strings. That is simpler, but it will misclassify long-history panes and cause unnecessary resets.

### Gateway consumes reset_required on the next accepted prompt

Gateway prompt readiness will continue to require the existing prompt-ready fields and parsed-surface idle/freeform checks. A prompt-ready target with chat context `reset_required` is eligible for prompt work, but the gateway must transform that prompt into clean-context execution.

The implementation should model this as effective selector normalization: when `reset_required` is present, the next accepted semantic prompt behaves as if `chat_session.mode = new` had been selected.

For native headless targets, the gateway consumes `reset_required` by forcing the effective chat-session selector for the accepted prompt to fresh context. The downstream request body must carry the clean-context selector `chat_session.mode = new`, even when the public request omitted `chat_session` or asked for an otherwise reusable context. Malformed selectors remain validation errors, but reset-required state takes precedence over ordinary continuity selection for accepted prompts.

For TUI targets, the gateway consumes `reset_required` by treating the prompt as an implicit TUI `chat_session.mode = new` request. That means the gateway sends the tool-appropriate clear/reset signal first, waits until the tracked TUI stabilizes back to prompt-ready posture without `reset_required`, and then sends the caller's actual prompt. If the reset signal cannot be admitted or post-reset stabilization fails, the caller's prompt is not sent.

Alternative considered: reject ordinary prompt control while `reset_required` and require the caller to explicitly set `chat_session.mode = new`. That makes the state visible but does not satisfy the "next prompt begins with clean context" behavior and would leave notifier-driven workflows stuck behind an extra control step.

### Tool profiles choose the TUI reset signal

Gateway TUI reset selection becomes tool-aware. Codex fresh-chat reset uses `/new`; other TUI targets may use their configured reset command, commonly `/clear`, when that is the correct context reset for the tool.

The reset workflow always waits for post-reset prompt-ready stabilization before sending the caller's actual prompt. If reset cannot be admitted or stabilization fails, the request fails explicitly and the caller's prompt is not sent.

Alternative considered: hard-code `/new` for every TUI target. That matches Codex but would be wrong for tools whose context reset command is `/clear` or another signal.

### Mail notifier uses the same clean-context path

When open inbox work exists and the target is prompt-ready but chat context is `reset_required`, the mail notifier should not record an ordinary busy skip and should not deliver the notifier prompt into the stale context. It should normalize notifier prompt work to effective `chat_session.mode = new`: for headless targets, enqueue or dispatch notifier work with that clean-context request-body selector; for TUI targets, run the reset-signal workflow first, wait for prompt-ready stabilization, then preserve existing queue-admission and notifier prompt rules.

The notifier records structured audit outcomes for clean-context notification success and reset failure. Reset failure does not mark mail read, archived, answered, or otherwise closed.

Alternative considered: require a human or external caller to explicitly reset before notifier progress. That leaves unattended mail-driven workflows stuck even though the system has a first-class state saying the next prompt must begin with clean context.

## Risks / Trade-offs

- Reset-required classification may be too broad -> Restrict matching to prompt-adjacent compact/server-error surfaces and keep generic red errors out of `reset_required`.
- Reset-required classification may miss future wording -> The session remains prompt-ready but the gateway will not know to force clean context until the signature is extended with test evidence.
- Resetting loses in-chat context -> The reset is only automatic for workflows that must proceed while the tracker says the current context needs reset; ordinary historical errors must not trigger it.
- Historical scrollback error text may be mistaken for the current turn -> Restrict error matching to the prompt-adjacent live-edge region and add regression coverage with long transcript history.
- Reset command behavior differs by tool -> Route reset signal selection through tool/profile configuration and test Codex `/new` separately from generic `/clear` behavior.

## Migration Plan

No persisted user data migration is required. Implementation changes state reduction, effective chat-session selection, TUI reset signal selection, and notifier recovery/audit behavior. Rollback is direct: remove the `reset_required` state handling and return to generic error diagnostics, though that reintroduces issue 19's stuck notifier behavior.

## Open Questions

- What exact tracked-state field should carry `reset_required`? The implementation should choose the least invasive stable shape that can be asserted in tests and consumed by gateway prompt-control and notifier policy.
