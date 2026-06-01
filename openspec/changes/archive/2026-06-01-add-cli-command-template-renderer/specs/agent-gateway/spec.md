## ADDED Requirements

### Requirement: Gateway CLI surfaces provide command-template entries
The CLI-owned command-template registry SHALL provide entries for maintained `houmao-mgr agents gateway ...` command surfaces that system skills author directly.

At minimum, the registry SHALL cover:

- gateway status, attach, detach, prompt, interrupt, and send-keys
- gateway TUI state, history, watch, and note-prompt
- gateway mail-notifier status, enable, and disable
- gateway reminders list, get, create, set, and remove

Each gateway template SHALL describe selector fields, command-specific payload fields, scheduling fields where applicable, conflicts, and omitted-field behavior.

#### Scenario: Gateway prompt renders direct control command
- **WHEN** an agent renders `agents.gateway.prompt` with an agent selector and prompt text
- **THEN** the rendered argv maps to `houmao-mgr agents gateway prompt`
- **AND THEN** unrelated gateway options remain absent

#### Scenario: Reminder create reports scheduling conflicts
- **WHEN** an agent renders `agents.gateway.reminders.create` with conflicting schedule fields
- **THEN** the renderer reports a blocker
- **AND THEN** it does not return executable argv
