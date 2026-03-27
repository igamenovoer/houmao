## MODIFIED Requirements

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

After a successful TUI join, later local `houmao-mgr agents state` commands SHALL continue to use the adopted tmux window identity for that joined session rather than falling back to the native-launch default window name `agent`.

#### Scenario: Successful TUI join auto-detects the provider from the primary pane
- **WHEN** an operator runs `houmao-mgr agents join --agent-name coder` from tmux window `1` of a session whose window `0`, pane `0` already hosts a live Codex TUI
- **THEN** the command auto-detects `codex` from the primary pane process tree
- **AND THEN** it adopts that tmux session into managed-agent control as a `local_interactive` session without restarting the live Codex process
- **AND THEN** later `houmao-mgr agents state --agent-name coder` resolves that adopted managed agent through the normal local discovery path

#### Scenario: Joined TUI remains inspectable through later local state commands
- **WHEN** an operator joins a live Claude TUI whose adopted window `0` is still named `claude`
- **AND WHEN** the operator later runs `houmao-mgr agents state --agent-name tester`
- **THEN** that local managed-agent command probes the adopted TUI surface using the persisted joined window identity
- **AND THEN** it does not fail only because the joined session was not running in a window named `agent`
