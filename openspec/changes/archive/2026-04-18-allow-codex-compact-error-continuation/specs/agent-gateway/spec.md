## ADDED Requirements

### Requirement: Degraded chat context does not force clean-context prompt control
Gateway prompt control SHALL treat recoverable degraded chat context as compatible with ordinary current-context prompt delivery when the target otherwise satisfies the prompt-ready contract.

For native headless targets, recoverable degraded chat context SHALL NOT by itself force the effective chat-session selector to `chat_session.mode = new`.

For TUI-backed targets, recoverable degraded chat context SHALL NOT by itself trigger the reset-then-send workflow.

Explicit clean-context requests SHALL remain supported. When a caller explicitly requests `chat_session.mode = new`, the gateway SHALL preserve the existing headless fresh-chat selection and TUI reset-then-send behavior for targets that support that selector.

#### Scenario: Ordinary TUI prompt continues degraded current context
- **GIVEN** a TUI-backed gateway target whose tracked state is prompt-ready and whose chat context is recoverably degraded
- **WHEN** a caller submits direct prompt control without a `chat_session` selector
- **THEN** the gateway sends the caller's prompt through the ordinary TUI prompt path
- **AND THEN** the gateway does not first send `/new`, `/clear`, or another context-reset signal solely because degraded context is present

#### Scenario: Explicit TUI new-chat prompt still resets
- **GIVEN** a TUI-backed gateway target whose tracked state is prompt-ready
- **WHEN** a caller submits direct prompt control with `chat_session.mode = new`
- **THEN** the gateway runs the supported TUI reset-then-send workflow
- **AND THEN** the caller's actual prompt is sent only after the reset workflow reaches prompt-ready posture

#### Scenario: Ordinary headless prompt does not force new chat for degraded context
- **GIVEN** a native headless gateway target whose chat context is recoverably degraded
- **WHEN** a caller submits prompt control without an explicit clean-context selector
- **THEN** the gateway resolves the prompt's chat-session selector using the ordinary current-context rules
- **AND THEN** the dispatched request body does not include `chat_session.mode = new` solely because degraded context is present

#### Scenario: Explicit headless new-chat prompt remains supported
- **GIVEN** a native headless gateway target
- **WHEN** a caller submits prompt control with `chat_session.mode = new`
- **THEN** the gateway dispatches the prompt with a fresh provider-chat selection
