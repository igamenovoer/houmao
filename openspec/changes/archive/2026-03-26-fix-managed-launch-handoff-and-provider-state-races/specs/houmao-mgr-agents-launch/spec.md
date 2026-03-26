## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes
`houmao-mgr agents launch` SHALL support both headless (detached) and interactive (tmux-backed TUI) modes.

When `--headless` is specified, the agent SHALL run as a detached headless process.

When `--headless` is not specified, the agent SHALL start the selected provider's interactive terminal UI in a tmux session.

When `--headless` is not specified and the caller provides a usable interactive terminal, the CLI SHALL perform the operator handoff to that tmux session through the repo-owned tmux integration boundary rather than through an ad hoc raw tmux subprocess call.

When `--headless` is not specified and the caller does not provide a usable interactive terminal, the command SHALL still be considered successful once the runtime session is live and the provider reaches the required ready posture, SHALL NOT attempt a terminal attach that can fail solely because the caller is non-interactive, and SHALL surface enough tmux identity for a later manual attach.

Interactive or non-interactive launch SHALL still fail if the session falls back to an idle shell before the provider reaches its interactive ready posture.

#### Scenario: Headless launch runs detached
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **THEN** the agent starts in a tmux-backed headless session without attaching the operator's terminal
- **AND THEN** the command prints the agent identity and manifest path, then exits

#### Scenario: Interactive launch attaches to a live provider TUI when the caller is interactive
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the caller has a usable interactive terminal
- **THEN** the agent starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the CLI attaches the operator's terminal to that tmux session through the repo-owned tmux integration path
- **AND THEN** the launch is not considered successful if the session falls back to an idle shell before the provider reaches its interactive ready posture

#### Scenario: Non-interactive caller does not turn a successful launch into a false attach failure
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the caller has no usable interactive terminal
- **THEN** the agent still starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the command reports launch success without attempting a tmux attach that would fail only because the caller is non-interactive
- **AND THEN** the output still surfaces the tmux session identity needed for a later manual attach
