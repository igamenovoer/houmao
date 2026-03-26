## ADDED Requirements

### Requirement: `houmao-mgr agents join` adopts an existing supported TUI from the current tmux session
`houmao-mgr agents join` SHALL provide a local adoption path for a supported provider TUI that is already running inside the caller's current tmux session.

The command SHALL require `--agent-name <name>` and MAY accept `--agent-id <id>`, `--provider <provider>`, repeatable `--launch-args <arg>`, repeatable `--launch-env <env-spec>`, and `--working-directory <path>`.

The command SHALL resolve its adoption target from the caller's current tmux session and SHALL treat tmux window `0`, pane `0` as the canonical adopted agent surface in v1.

When `--provider` is omitted, the command SHALL inspect the process tree rooted at that pane and SHALL auto-detect exactly one supported provider (`claude_code`, `codex`, or `gemini_cli`) before continuing.

When `--provider` is supplied, the command SHALL validate that the detected live provider process in window `0`, pane `0` matches the requested provider.

When present, `--launch-env` SHALL follow Docker `--env` style:

- `NAME=value` persists a literal env binding for later relaunch,
- `NAME` means the later relaunch resolves `NAME` from the adopted tmux session environment.

When `--working-directory` is omitted, the command SHALL derive it from the target pane's current path. If no usable pane current path is available, the command SHALL fail explicitly rather than guessing another directory.

A successful TUI join SHALL materialize the managed-agent identity and runtime artifacts through the join runtime path without restarting the current TUI process.

#### Scenario: Successful TUI join auto-detects the provider from the primary pane
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` from tmux window `1` of a session whose window `0`, pane `0` already hosts a live Codex TUI
- **THEN** the command auto-detects `codex` from the primary pane process tree
- **AND THEN** it adopts that tmux session into managed-agent control as a `local_interactive` session without restarting the live Codex process
- **AND THEN** later `houmao-mgr agents state --agent-name coder` resolves that adopted managed agent through the normal local discovery path

### Requirement: `houmao-mgr agents join --headless` adopts a tmux-backed native headless logical session
`houmao-mgr agents join --headless` SHALL adopt a tmux-backed native headless logical session between turns rather than a live provider TUI surface.

The headless join form SHALL require `--headless`, `--agent-name <name>`, `--provider <claude_code|codex|gemini_cli>`, and at least one `--launch-args <arg>`. It MAY accept `--agent-id <id>`, repeatable `--launch-env <env-spec>`, optional `--resume-id <provider-resume-selector>`, and `--working-directory <path>`.

For headless join, `--resume-id` SHALL use the following semantics:

- omitted means later runtime-controlled headless work does not resume a known provider chat and instead starts from a fresh provider session,
- `last` means later runtime-controlled headless work resumes the most current known provider chat for that provider,
- any other non-empty value means later runtime-controlled headless work resumes that exact provider chat or session id.

The command SHALL run inside the target tmux session and SHALL treat tmux window `0`, pane `0` as the canonical headless console surface for the adopted session.

When `--working-directory` is omitted, the command SHALL derive it from the primary pane current path and SHALL fail explicitly if that path is unavailable.

A successful headless join SHALL adopt the logical session using the provider-specific native headless backend (`claude_headless`, `codex_headless`, or `gemini_headless`) and SHALL persist the supplied launch args, launch env specs, and resume-selection metadata for later runtime-controlled turns.

#### Scenario: Successful headless join adopts the logical session between turns with an explicit resume id
- **WHEN** an operator runs `houmao-mgr agents join --headless --agent-name reviewer --provider codex --launch-args exec --launch-args --json --launch-env CODEX_HOME --resume-id thread_123` from a tmux session whose window `0`, pane `0` is the headless console surface between turns
- **THEN** the command adopts that tmux session into managed-agent control as a `codex_headless` session
- **AND THEN** it persists the supplied launch args, launch env specs, and explicit resume-selection metadata for later runtime-controlled turns
- **AND THEN** later `houmao-mgr agents turn submit --agent-name reviewer --prompt "..."` can resume the same logical headless session without rebuilding a brain home

#### Scenario: Headless join without `--resume-id` starts from no known chat
- **WHEN** an operator runs `houmao-mgr agents join --headless --agent-name reviewer --provider codex --launch-args exec --launch-args --json` from a tmux session whose window `0`, pane `0` is the headless console surface between turns
- **THEN** the command adopts that tmux session into managed-agent control as a `codex_headless` session
- **AND THEN** it persists that no known provider chat should be resumed for later runtime-controlled turns
- **AND THEN** later headless work starts from a fresh provider session rather than resuming one exact or latest known chat

#### Scenario: Headless join with `--resume-id last` resumes the latest known chat
- **WHEN** an operator runs `houmao-mgr agents join --headless --agent-name reviewer --provider codex --launch-args exec --launch-args --json --resume-id last`
- **THEN** the command adopts that tmux session into managed-agent control as a `codex_headless` session
- **AND THEN** it persists that later runtime-controlled turns should resume the most current known Codex chat
- **AND THEN** the command does not require the operator to supply one exact provider thread id

### Requirement: `houmao-mgr agents join` fails closed when adoption authority is incomplete or inconsistent
When required adoption authority is missing or inconsistent, `houmao-mgr agents join` SHALL fail before publishing a shared-registry record or stable tmux-session discovery pointers.

This failure-closed posture SHALL cover at minimum:

- the caller is not inside tmux,
- tmux window `0`, pane `0` is missing or unusable,
- TUI provider detection returns zero or multiple supported providers and the caller did not provide a usable `--provider`,
- the caller supplies `--provider` that conflicts with the detected live TUI process,
- headless join omits required `--launch-args`,
- the working directory cannot be resolved from `--working-directory` or tmux pane metadata.

The command SHALL return an explicit operator-facing error that identifies the missing or inconsistent input instead of fabricating placeholder values or publishing partially usable runtime metadata.

#### Scenario: TUI join fails outside tmux
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` outside any tmux session
- **THEN** the command fails with an explicit tmux-session-required error
- **AND THEN** it does not publish a shared-registry record or session manifest for that attempted join

#### Scenario: TUI join fails when the requested provider disagrees with the live process
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder --provider claude_code` inside a tmux session whose window `0`, pane `0` currently hosts a live Codex TUI
- **THEN** the command fails with an explicit provider-mismatch error
- **AND THEN** it does not publish joined-session metadata for the mismatched target

#### Scenario: Headless join rejects a blank resume selector
- **WHEN** an operator runs `houmao-mgr agents join --headless --agent-name reviewer --provider codex --launch-args exec --launch-args --json --resume-id ""`
- **THEN** the command fails with an explicit invalid-resume-selector error
- **AND THEN** it does not publish a shared-registry record or stable tmux discovery pointers for that attempted headless join
