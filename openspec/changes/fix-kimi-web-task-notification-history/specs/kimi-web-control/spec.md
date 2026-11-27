# Kimi Web Control Delta

## MODIFIED Requirements

### Requirement: Observation and interruption address exact native work

Kimi Web inspection SHALL retain native origin, session, prompt identity, and actual queue or terminal state. It SHALL preserve each provider-issued prompt ID exactly as recorded, including IDs issued for native task notifications. Passive reads SHALL avoid cold activation. Interruption SHALL target the exact verified prompt. Managed attribution SHALL require an exact match to the bound request.

#### Scenario: The browser starts a turn

- **WHEN** the owner observes a native prompt outside its managed correlation
- **THEN** the observation remains external or of unknown origin and cannot settle an unrelated managed request

#### Scenario: The submission response is lost

- **WHEN** Kimi may have accepted the original POST
- **THEN** the owner reconciles that prompt identity or reports uncertainty without replay

#### Scenario: A native notification follows a managed turn

- **GIVEN** a verified session in which a managed turn has ended
- **WHEN** Kimi records a task notification with its own prompt ID, such as `task:bash-example:completed`, and runs another turn for it
- **THEN** passive state and incremental history remain available throughout the active and completed notification turn while native evidence remains current
- **AND** the start and settlement records expose the same native prompt ID and preserve the journal order
- **AND** the notification cannot complete, supply output for, or trigger replay of the earlier managed request

#### Scenario: Queued input becomes eligible after native activity finishes

- **GIVEN** an authorized plugin has an ordinary input queued for the verified session during a native task notification
- **WHEN** Kimi finishes the turn and the owner verifies idle state, an empty native prompt queue, and current dispatch permission
- **THEN** the existing binding can hand off the pending input once to the same session, with the notification still present in history
- **AND** while Kimi reports active work or a pending interaction the input stays subject to ordinary admission

#### Scenario: An operator interrupts a prompt with a provider-issued ID

- **WHEN** the operator requests interruption of a captured, still-active native turn whose prompt ID contains reserved URL characters
- **THEN** Kimi receives the exact original target ID within the verified session and the owner reports the native outcome
- **AND** a stale turn, changed binding, or mismatched managed operation causes a refusal before the owner sends an abort
