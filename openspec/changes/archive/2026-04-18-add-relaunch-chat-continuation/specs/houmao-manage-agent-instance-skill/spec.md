## ADDED Requirements

### Requirement: `houmao-agent-instance` explains relaunch chat continuation
The packaged `houmao-agent-instance` skill SHALL explain that `houmao-mgr agents relaunch` can restart a relaunchable tmux-backed managed agent as either a fresh provider chat or a provider-native continuation when the implementation supports relaunch chat-session selection.

The skill SHALL route user requests to continue the previous provider chat during relaunch through `houmao-mgr agents relaunch` with the supported relaunch chat-session selector rather than through `agents launch` or ad hoc provider CLI commands.

The skill SHALL distinguish relaunch continuation from TUI prompt control: relaunch continuation happens at provider process startup, while TUI prompt control against an already-running surface remains a separate messaging/gateway concern.

The skill SHALL ask for a provider session id before selecting exact relaunch mode when the user has not supplied one.

#### Scenario: Skill routes latest-chat relaunch to agents relaunch
- **WHEN** the user asks to relaunch managed agent `reviewer` and continue the previous provider chat
- **THEN** the skill directs the agent to use `houmao-mgr agents relaunch --agent-name reviewer` with the latest-chat relaunch selector
- **AND THEN** it does not direct the agent to run `codex resume`, `claude --continue`, or `gemini --resume` outside Houmao control

#### Scenario: Skill asks before exact relaunch without id
- **WHEN** the user asks to relaunch into an exact provider chat
- **AND WHEN** no provider session id is present in the prompt or recent context
- **THEN** the skill tells the agent to ask for the missing provider session id
- **AND THEN** it does not guess an id from unrelated history

#### Scenario: Skill keeps fresh relaunch distinct from continuation
- **WHEN** the user asks for a normal relaunch and does not mention provider chat continuation
- **THEN** the skill keeps the default fresh relaunch behavior
- **AND THEN** it does not add continuation flags unprompted
