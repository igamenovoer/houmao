## ADDED Requirements

### Requirement: `houmao-agent-messaging` delegates generic managed-agent inspection to `houmao-agent-inspect`
The packaged `houmao-agent-messaging` skill SHALL treat generic requests to inspect managed-agent liveness, transport detail, mailbox posture, runtime artifacts, logs, or direct tmux backing as outside its primary ownership.

For those generic inspection requests, the packaged skill SHALL direct the caller to `houmao-agent-inspect`.

The packaged skill MAY continue using `agents state`, `agents gateway status`, `agents mail resolve-live`, and gateway-owned TUI tracker surfaces when that inspection is inseparable from the currently selected messaging workflow, such as prompt-lane discovery, queue-specific validation, or explicit prompt-provenance work.

#### Scenario: Generic inspection request routes to the inspect skill
- **WHEN** a caller asks the messaging skill to inspect what one managed agent is doing, which pane backs it, or which logs and artifacts should be examined
- **THEN** the skill directs the caller to `houmao-agent-inspect`
- **AND THEN** it does not present generic managed-agent inspection as primary messaging guidance

#### Scenario: Queue-specific tracker inspection stays available inside messaging
- **WHEN** a caller explicitly needs gateway-owned TUI state or history as part of queued prompt, queued interrupt, or prompt-provenance work
- **THEN** the skill may still direct the caller to the supported gateway TUI tracker surfaces inside the messaging workflow
- **AND THEN** it does not claim ownership of generic managed-agent inspection outside that messaging-specific context
