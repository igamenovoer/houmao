# Spec Delta

## MODIFIED Requirements

### Requirement: Agents single scope owns explicitly selected one-agent operations
`agents single` SHALL use one group-level agent ID or name. Local gateway commands also accept a unique fresh tmux alias. Nested commands SHALL use the selected target without inferring it from the caller's session.

#### Scenario: Acceptance criteria

- **WHEN** a caller selects an agent for `state`, `prompt`, `interrupt`, `stop`, `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, `turn`, or `cleanup`
- **THEN** the command uses the group-level selection
- **AND THEN** current-session membership operations such as `join` belong to `agents self`

#### Scenario: Single prompt uses group-level selector
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 prompt --prompt ping`
- **THEN** the command targets managed agent `agent-123`
- **AND THEN** the `prompt` leaf does not require another `--agent-id` option

#### Scenario: Single stop uses explicit selected-agent authority
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 stop`
- **THEN** the command targets managed agent `agent-123` through the explicit selected-agent selector
- **AND THEN** the command does not infer or target the caller's current tmux session

#### Scenario: Single mail read uses group-level selector
- **WHEN** an operator runs `houmao-mgr agents single --agent-name worker-a mail read --message-ref msg-1`
- **THEN** the command reads message `msg-1` for managed agent `worker-a`
- **AND THEN** it does not resolve the target from the caller's current tmux session

#### Scenario: Single scope does not expose current-session join
- **WHEN** an operator runs `houmao-mgr agents single --agent-id agent-123 join`
- **THEN** the command is not a maintained public path
- **AND THEN** the diagnostic or help output points current-session adoption to `houmao-mgr agents self join`

#### Scenario: Single command rejects missing selector inside tmux
- **WHEN** an operator runs `houmao-mgr agents single gateway prompt --prompt ping` inside a managed tmux session without a group-level selector
- **THEN** the command fails clearly because `agents single` requires an explicit selected agent
- **AND THEN** the diagnostic points the operator to either supply a single-agent selector or use `houmao-mgr agents self gateway prompt`

### Requirement: Current-session gateway and mail behavior moves to agents self
Current-session gateway, mail, mailbox, memory, and turn operations SHALL be represented through `houmao-mgr agents self ...` command paths.

Explicit one-agent gateway, mail, mailbox, memory, and turn operations SHALL be represented through `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`. Local gateway commands may also use the group-level tmux session alias.

#### Scenario: Self gateway prompt replaces implicit selected-agent prompt
- **WHEN** an agent wants to prompt its own managed session from inside the owning tmux session
- **THEN** the maintained command path is `houmao-mgr agents self gateway prompt`
- **AND THEN** `houmao-mgr agents single gateway prompt` requires an explicit group-level selector

#### Scenario: Self mail read replaces implicit agents mail read
- **WHEN** an agent wants to read its own mailbox message from inside the owning tmux session
- **THEN** the maintained command path is `houmao-mgr agents self mail read --message-ref <ref>`
- **AND THEN** no `--agent-id`, `--agent-name`, or `--current-session` option is required
