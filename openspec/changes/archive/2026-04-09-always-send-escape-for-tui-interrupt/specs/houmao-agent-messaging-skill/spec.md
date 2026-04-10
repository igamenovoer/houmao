## ADDED Requirements

### Requirement: `houmao-agent-messaging` describes TUI interrupt as best-effort `Escape`
The packaged `houmao-agent-messaging` skill SHALL describe `houmao-mgr agents interrupt` as the default transport-neutral interrupt path for already-running managed agents.

For TUI-backed managed agents, the skill SHALL explain that ordinary interrupt means one best-effort `Escape` delivery and that the caller does not need to switch to raw `send-keys` merely to get that TUI interrupt behavior.

For TUI-backed managed agents, the skill SHALL explain that interrupt MAY still be useful when currently reported TUI state looks idle because tracked TUI state can lag the live visible surface.

For headless managed agents, the skill SHALL explain that ordinary interrupt targets active execution work and MAY return no-op semantics when no headless work is active.

The skill SHALL continue treating `houmao-mgr agents gateway send-keys` as the exact raw control-input path for slash menus, cursor movement, partial typing, or other precise TUI shaping.

#### Scenario: Skill describes ordinary TUI interrupt without redirecting to raw send-keys
- **WHEN** the user asks to interrupt a managed TUI agent
- **THEN** the skill directs the agent to use `houmao-mgr agents interrupt`
- **AND THEN** it explains that the TUI interrupt path delivers best-effort `Escape` rather than redirecting the caller to `houmao-mgr agents gateway send-keys`

#### Scenario: Skill explains delayed TUI tracking honestly
- **WHEN** the user asks why TUI interrupt may still be attempted while reported state looks idle
- **THEN** the skill explains that tracked TUI state can lag the live visible pane
- **AND THEN** it does not describe the idle tracked posture as proof that a TUI interrupt request would be meaningless

#### Scenario: Skill keeps headless interrupt semantics distinct
- **WHEN** the user asks to interrupt a managed headless agent
- **THEN** the skill explains that ordinary interrupt targets active execution work
- **AND THEN** it does not describe headless interrupt as unconditional `Escape` delivery
