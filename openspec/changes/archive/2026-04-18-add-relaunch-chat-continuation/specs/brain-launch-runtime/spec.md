## ADDED Requirements

### Requirement: Tmux-backed relaunch can select provider-native chat continuation
For tmux-backed managed sessions, runtime relaunch SHALL accept an optional relaunch chat-session selector with modes `new`, `tool_last_or_new`, and `exact`.

When the selector is omitted, runtime relaunch SHALL behave as `new` and preserve the existing fresh-chat relaunch behavior.

When the selector mode is `exact`, the selector SHALL include a non-empty provider-native session id.

For local interactive TUI sessions, runtime relaunch SHALL translate the selector into provider-native startup args before respawning the provider process on tmux window `0`.

The provider-native TUI translation SHALL be:

- Codex `tool_last_or_new`: `codex resume --last`
- Codex `exact`: `codex resume <session_id>`
- Claude Code `tool_last_or_new`: `claude --continue`
- Claude Code `exact`: `claude --resume <session_id>`
- Gemini CLI `tool_last_or_new`: `gemini --resume latest`
- Gemini CLI `exact`: `gemini --resume <session_id>`

For native headless sessions, runtime relaunch SHALL record the selector as the startup/default chat-session selection for the next managed headless prompt rather than starting a provider turn during the relaunch command itself.

The provider-native headless translation on the next prompt SHALL be:

- Codex `tool_last_or_new`: `codex exec resume --last <prompt>`
- Codex `exact`: `codex exec resume <session_id> <prompt>`
- Claude Code `tool_last_or_new`: `claude -p --continue <prompt>`
- Claude Code `exact`: `claude -p --resume <session_id> <prompt>`
- Gemini CLI `tool_last_or_new`: `gemini --resume latest -p <prompt>`
- Gemini CLI `exact`: `gemini --resume <session_id> -p <prompt>`

When local interactive relaunch resumes an existing provider chat, runtime SHALL NOT submit a bootstrap-message role injection as a chat turn during relaunch.

#### Scenario: TUI relaunch resumes the provider latest chat
- **WHEN** an operator relaunches a Codex, Claude Code, or Gemini CLI local interactive managed session with relaunch chat-session mode `tool_last_or_new`
- **THEN** the runtime respawns the provider TUI on tmux window `0` using that provider's native latest-chat continuation startup args
- **AND THEN** it does not route through build-time `houmao-mgr agents launch`

#### Scenario: TUI relaunch resumes an exact provider session
- **WHEN** an operator relaunches a local interactive managed session with relaunch chat-session mode `exact` and provider session id `abc123`
- **THEN** the runtime respawns the provider TUI on tmux window `0` using that provider's native exact-session resume startup args for `abc123`
- **AND THEN** it rejects the request if the exact selector has no session id

#### Scenario: Headless relaunch applies continuation on the next prompt
- **WHEN** an operator relaunches a native headless managed session with relaunch chat-session mode `tool_last_or_new`
- **THEN** the relaunch command refreshes the stable headless authority without starting a provider turn immediately
- **AND THEN** the next managed headless prompt uses the provider's native latest-chat continuation form

#### Scenario: Default relaunch remains fresh
- **WHEN** an operator relaunches a tmux-backed managed session without a relaunch chat-session selector
- **THEN** the runtime uses fresh-chat relaunch behavior
- **AND THEN** existing sessions and manifests without relaunch chat-session metadata continue to relaunch successfully

#### Scenario: Bootstrap message is not replayed into resumed TUI chat
- **WHEN** a local interactive relaunch resumes an existing provider chat
- **AND WHEN** the launch plan uses bootstrap-message role injection
- **THEN** runtime does not submit the bootstrap message into the resumed provider chat as a user turn
- **AND THEN** the resumed provider conversation is not polluted with a duplicate launch bootstrap prompt
