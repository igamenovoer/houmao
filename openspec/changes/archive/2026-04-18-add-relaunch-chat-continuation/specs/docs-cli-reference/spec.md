## ADDED Requirements

### Requirement: CLI reference documents relaunch chat-session selection
The CLI reference SHALL document the `houmao-mgr agents relaunch` relaunch chat-session selector.

That documentation SHALL include:

- supported modes `new`, `tool_last_or_new`, and `exact`,
- the provider-native id requirement for `exact`,
- default fresh-chat behavior when the selector is omitted,
- examples for current-session relaunch and explicit `--agent-id` or `--agent-name` relaunch,
- a note that native headless relaunch applies the selector on the next managed prompt.

The CLI reference SHALL NOT present relaunch continuation as a build-time `agents launch` option.

#### Scenario: Reader finds latest-chat relaunch example
- **WHEN** a reader looks up `houmao-mgr agents relaunch`
- **THEN** the CLI reference includes an example that relaunches a managed agent with relaunch chat-session mode `tool_last_or_new`
- **AND THEN** the example uses the supported Houmao relaunch command rather than a raw provider CLI command

#### Scenario: Reader sees exact id validation
- **WHEN** a reader looks up relaunch chat-session mode `exact`
- **THEN** the CLI reference states that a provider-native chat-session id is required
- **AND THEN** it does not imply that Houmao can always infer that id for TUI sessions

#### Scenario: Reader understands headless relaunch timing
- **WHEN** a reader looks up relaunch chat-session selection for a native headless managed agent
- **THEN** the CLI reference states that the relaunch command records the selector for the next managed prompt
- **AND THEN** it does not imply that relaunch itself sends a prompt
