## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports one-off memory-directory controls
`houmao-mgr agents launch` SHALL accept optional `--memory-dir <path>` and `--no-memory-dir` launch-time controls for tmux-backed managed sessions.

`--memory-dir` and `--no-memory-dir` SHALL be mutually exclusive on this surface.

When neither flag is supplied, `agents launch` SHALL resolve memory binding from any selected launch-profile memory configuration and otherwise fall back to the system default behavior for that launch surface.

When `agents launch` resolves the system default behavior in project context, the default memory directory SHALL derive from the selected source overlay rather than from `--workdir`.

#### Scenario: Project-context launch derives default memory from the source overlay instead of `--workdir`
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --workdir /repo-b`
- **AND WHEN** no stored launch-profile memory configuration and no direct memory override are supplied
- **THEN** the resulting managed launch resolves memory under `/repo-a/.houmao/memory/agents/<agent-id>/`
- **AND THEN** it does not derive the default memory directory from `/repo-b`

#### Scenario: Explicit no-memory override suppresses the default memory directory
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --no-memory-dir`
- **THEN** the resulting managed launch resolves memory binding as disabled
- **AND THEN** the launch does not create a default memory directory for that session

#### Scenario: Explicit memory-dir override wins over a profile that disables memory
- **WHEN** launch profile `alice` stores disabled memory binding
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --memory-dir /tmp/alice-memory`
- **THEN** the resulting managed launch resolves memory directory `/tmp/alice-memory`
- **AND THEN** the stored launch profile still records disabled memory binding as its reusable default
