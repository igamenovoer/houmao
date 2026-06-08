## MODIFIED Requirements

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
- Kimi Code `tool_last_or_new`: `kimi --continue`
- Kimi Code `exact`: `kimi --session <session_id>`

For Kimi Code local interactive relaunch, runtime SHALL NOT use bare `kimi --session` because that opens Kimi's interactive picker rather than selecting a deterministic provider session.

For Kimi Code local interactive relaunch that resumes a provider chat through `--continue` or `--session <session_id>`, runtime SHALL reject final launch arguments that also contain `--yolo`, `--auto`, or `--plan`.

Kimi Code local interactive relaunch SHALL allow launch-owned `--model <alias>` to remain in the final command when resuming a provider chat.

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
- **WHEN** an operator relaunches a Codex, Claude Code, Gemini CLI, or Kimi Code local interactive managed session with relaunch chat-session mode `tool_last_or_new`
- **THEN** the runtime respawns the provider TUI on tmux window `0` using that provider's native latest-chat continuation startup args
- **AND THEN** it does not route through build-time `houmao-mgr agents launch`

#### Scenario: TUI relaunch resumes an exact provider session
- **WHEN** an operator relaunches a local interactive managed session with relaunch chat-session mode `exact` and provider session id `abc123`
- **THEN** the runtime respawns the provider TUI on tmux window `0` using that provider's native exact-session resume startup args for `abc123`
- **AND THEN** it rejects the request if the exact selector has no session id

#### Scenario: Kimi TUI relaunch rejects native resume conflicts
- **WHEN** an operator relaunches a Kimi Code local interactive managed session with relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** the final provider startup arguments would contain both `--continue` and `--yolo`
- **THEN** runtime rejects the relaunch before respawning the Kimi process
- **AND THEN** the error names the unsupported Kimi resume conflict

#### Scenario: Kimi TUI relaunch keeps model alias with resume
- **WHEN** an operator relaunches a Kimi Code local interactive managed session with relaunch chat-session mode `exact` and provider session id `abc123`
- **AND WHEN** launch-owned model selection resolved to `kimi-code/kimi-for-coding`
- **THEN** runtime includes `--model kimi-code/kimi-for-coding --session abc123` in the Kimi startup args
- **AND THEN** runtime does not reject the relaunch solely because the model alias is present

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
