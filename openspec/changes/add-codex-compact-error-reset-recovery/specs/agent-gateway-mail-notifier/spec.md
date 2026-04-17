## ADDED Requirements

### Requirement: Gateway mail notifier begins reset-required prompts with clean context
When open inbox work is present, the gateway mail notifier SHALL distinguish prompt readiness from chat-context state.

For prompt-ready sessions, chat-context state `reset_required` SHALL NOT by itself cause an ordinary notifier busy skip. Instead, notifier work SHALL be normalized to effective `chat_session.mode = new` so it begins with clean context before the notifier prompt is enqueued or delivered.

For native headless sessions with chat-context state `reset_required`, notifier work SHALL carry `chat_session.mode = new` in the prompt request body.

For TUI-backed sessions with chat-context state `reset_required`, notifier work SHALL behave as an implicit TUI `chat_session.mode = new` prompt and run the tool-appropriate context-reset signal workflow before enqueueing or delivering the notifier prompt. The reset workflow SHALL use the same reset signal selection as gateway TUI clean-context prompt control, including Codex `/new` and configured non-Codex reset signals such as `/clear`.

After a successful TUI reset, the notifier SHALL preserve existing queue-admission and notifier prompt rules before creating notifier work. If reset fails or post-reset prompt-ready stabilization does not complete without chat-context state `reset_required`, the notifier SHALL NOT enqueue or deliver the notifier prompt for that poll.

The notifier SHALL record structured audit evidence that distinguishes clean-context notification success from reset failure. Reset failure SHALL NOT mark mailbox messages read, archived, answered, or otherwise closed.

Generic prompt-not-ready, busy, active, queued, overlay-blocked, detached, draft-editing, or unknown TUI states SHALL continue to produce the existing busy-skip or ineligible-skip behavior.

#### Scenario: Reset-required headless notifier prompt uses clean-context request body
- **WHEN** a notifier poll finds open inbox work for a native headless session
- **AND WHEN** the session is eligible for notifier work and chat-context state is `reset_required`
- **THEN** the notifier creates prompt work with `chat_session.mode = new`
- **AND THEN** it records audit evidence that the notifier prompt began with clean context

#### Scenario: Prompt-ready reset-required TUI resets before notifier prompt
- **WHEN** a notifier poll finds open inbox work for a TUI-backed session
- **AND WHEN** the gateway-owned TUI state satisfies the prompt-ready contract and chat-context state is `reset_required`
- **AND WHEN** queue admission and notifier mode checks pass
- **THEN** the notifier treats the prompt as implicit TUI `chat_session.mode = new` and runs the tool-appropriate context-reset signal workflow before enqueueing notifier work
- **AND THEN** after post-reset prompt-ready stabilization clears `reset_required`, it records a clean-context notification audit outcome with the created notifier request identifier

#### Scenario: Codex notifier reset uses slash-new
- **WHEN** a notifier poll resets a prompt-ready Codex TUI-backed session whose chat-context state is `reset_required`
- **THEN** the notifier reset workflow sends `/new`
- **AND THEN** it waits for post-reset prompt-ready stabilization before creating notifier work

#### Scenario: Configured non-Codex notifier reset may use slash-clear
- **WHEN** a notifier poll resets a prompt-ready non-Codex TUI-backed session whose configured context-reset signal is `/clear`
- **THEN** the notifier reset workflow sends `/clear`
- **AND THEN** it waits for post-reset prompt-ready stabilization before creating notifier work

#### Scenario: Reset failure preserves mailbox state
- **WHEN** a notifier poll attempts reset-required TUI context recovery
- **AND WHEN** the reset signal cannot be admitted or the TUI does not stabilize back to prompt-ready posture without `reset_required`
- **THEN** the notifier records a reset-failed audit outcome for that poll
- **AND THEN** it does not enqueue notifier work or mutate mailbox read, answered, archived, or closed state

#### Scenario: Prompt-ready generic error surface not requiring reset receives normal notifier work
- **WHEN** a notifier poll finds open inbox work for a TUI-backed session
- **AND WHEN** the gateway-owned TUI state satisfies the prompt-ready contract while also reporting previous-turn generic error evidence
- **AND WHEN** chat-context state is not `reset_required` and queue admission passes
- **THEN** the notifier enqueues the normal notifier prompt without first resetting context
- **AND THEN** it does not record a busy skip solely because the previous visible turn contains a generic error

#### Scenario: Generic not-ready state remains a busy skip
- **WHEN** a notifier poll finds open inbox work for a TUI-backed session
- **AND WHEN** the session does not satisfy prompt-readiness or queue-admission requirements
- **THEN** the notifier records the existing busy-skip or ineligible-skip decision
- **AND THEN** it does not infer notifier eligibility from `reset_required` diagnostics alone
