## ADDED Requirements

### Requirement: Gateway headless prompt surfaces accept request-scoped execution overrides
For native headless gateway targets, both semantic gateway prompt surfaces SHALL accept an optional request-scoped `execution.model` object:

- `POST /v1/control/prompt`
- `POST /v1/requests` with `kind = submit_prompt`

That `execution.model` object SHALL use the same normalized unified model-selection shape as Houmao launch-owned model configuration.

For native headless targets, the gateway SHALL treat `execution` and `chat_session` as orthogonal controls:

- `chat_session` selects conversation continuity
- `execution.model` selects model and reasoning for the accepted prompt

When both fields are present, the gateway SHALL preserve both through prompt admission and headless execution.

The request-scoped execution override SHALL apply only to the accepted prompt being dispatched or dequeued.

The gateway SHALL NOT store execution state inside `chat_session.current`, `chat_session.startup_default`, or `chat_session.next_prompt_override`.

For TUI-backed targets, any supplied `execution` override on either semantic prompt surface SHALL be rejected with validation semantics rather than ignored.

#### Scenario: Headless direct prompt control accepts execution and chat-session together
- **WHEN** a caller submits `POST /v1/control/prompt` for a native headless gateway target
- **AND WHEN** the request includes `chat_session.mode = current` and `execution.model.reasoning.level = 4`
- **THEN** the gateway preserves the explicit current-session selector for conversation continuity
- **AND THEN** the gateway applies reasoning level `4` only to that accepted prompt execution

#### Scenario: Headless queued prompt submission accepts the same execution override contract
- **WHEN** a caller submits `POST /v1/requests` with `kind = submit_prompt` for a native headless gateway target
- **AND WHEN** the request payload includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** the gateway accepts that queued semantic prompt request using the same execution-override contract as direct prompt control
- **AND THEN** the later dequeued headless prompt uses `gpt-5.4-mini` only for that queued request

#### Scenario: TUI direct prompt control rejects execution override
- **WHEN** a caller submits `POST /v1/control/prompt` for a TUI-backed gateway target
- **AND WHEN** the request includes `execution.model.name = "gpt-5.4-mini"`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not silently ignore the execution override and pretend that prompt control succeeded

#### Scenario: TUI queued prompt submission rejects execution override
- **WHEN** a caller submits `POST /v1/requests` with `kind = submit_prompt` for a TUI-backed gateway target
- **AND WHEN** the request payload includes `execution.model.reasoning.level = 2`
- **THEN** the gateway rejects that request with validation semantics
- **AND THEN** it does not silently queue a TUI prompt while dropping the requested execution override
