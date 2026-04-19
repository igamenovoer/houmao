## ADDED Requirements

### Requirement: `houmao-mgr agents relaunch` exposes relaunch chat-session selection
`houmao-mgr agents relaunch` SHALL expose optional relaunch chat-session selection for tmux-backed managed agents.

The command SHALL accept a relaunch chat-session mode with values `new`, `tool_last_or_new`, and `exact`.

The command SHALL accept a provider-native chat-session id only when the mode is `exact`.

When relaunch chat-session mode is omitted, the command SHALL default to `new`.

The command SHALL preserve both existing target forms:

- explicit targeting by `--agent-id` or `--agent-name`,
- current-session targeting when invoked from inside the owning managed tmux session.

The command SHALL fail clearly when a selector is invalid, the target is not relaunchable, or the selected provider/backend does not support the requested relaunch chat-session mode.

#### Scenario: Current-session relaunch continues latest provider chat
- **WHEN** an operator runs `houmao-mgr agents relaunch --chat-session-mode tool_last_or_new` from inside a supported tmux-backed managed session
- **THEN** the command resolves the current session through tmux-local manifest discovery
- **AND THEN** it passes the latest-chat relaunch selector into the runtime relaunch primitive

#### Scenario: Explicit relaunch resumes exact provider chat
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-name reviewer --chat-session-mode exact --chat-session-id abc123`
- **THEN** the command resolves managed agent `reviewer`
- **AND THEN** it passes exact provider session id `abc123` into the runtime relaunch primitive

#### Scenario: Exact relaunch requires an id
- **WHEN** an operator runs `houmao-mgr agents relaunch --chat-session-mode exact` without `--chat-session-id`
- **THEN** the command fails validation before relaunching the managed session
- **AND THEN** it does not silently fall back to latest-chat or fresh-chat relaunch

#### Scenario: Fresh relaunch remains the default
- **WHEN** an operator runs `houmao-mgr agents relaunch --agent-id abc123` without relaunch chat-session flags
- **THEN** the command uses relaunch chat-session mode `new`
- **AND THEN** existing relaunch scripts keep their prior behavior
