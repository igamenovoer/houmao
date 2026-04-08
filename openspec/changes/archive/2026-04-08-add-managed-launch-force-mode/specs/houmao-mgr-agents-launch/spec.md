## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports launch-owned managed force takeover

`houmao-mgr agents launch` SHALL accept optional `--force` for replacing an existing fresh live owner of the resolved managed identity on the current launch.

`--force` MAY be supplied bare or with an explicit mode value.

Bare `--force` SHALL default to mode `keep-stale`.

The only supported explicit force mode values SHALL be `keep-stale` and `clean`.

The selected force mode SHALL remain launch-owned only and SHALL NOT be persisted into reusable launch profiles.

When no force mode is supplied and a fresh live session already owns the resolved managed identity, the command SHALL fail rather than replacing that live owner.

When `--force` is supplied and a fresh live session already owns the resolved managed identity, the command SHALL delegate to the managed runtime takeover flow for that identity.

The command SHALL target takeover by the resolved managed identity rather than by tmux session name alone.

#### Scenario: Bare `--force` defaults to `keep-stale`
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a --force`
- **AND WHEN** a fresh live session already owns managed identity `worker-a`
- **THEN** the launch requests managed takeover in mode `keep-stale`
- **AND THEN** the command does not require the operator to spell `keep-stale` explicitly

#### Scenario: Explicit `clean` selects destructive takeover for the current launch only
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a --force clean`
- **AND WHEN** a fresh live session already owns managed identity `worker-a`
- **THEN** the launch requests managed takeover in mode `clean`
- **AND THEN** that `clean` selection applies only to the current launch invocation

#### Scenario: Force mode does not rewrite launch profile defaults
- **WHEN** launch profile `alice` exists
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --force clean`
- **THEN** the current launch uses managed takeover mode `clean`
- **AND THEN** stored launch profile `alice` remains unchanged and does not gain a persisted force mode

#### Scenario: Missing `--force` preserves the existing ownership conflict failure
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a`
- **AND WHEN** a fresh live session already owns managed identity `worker-a`
- **THEN** the command fails rather than replacing that existing live owner

#### Scenario: Tmux session-name collision alone does not authorize takeover
- **WHEN** an unrelated live session already uses tmux session name `my-agent`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a --session-name my-agent --force`
- **AND WHEN** that unrelated live session does not own managed identity `worker-a`
- **THEN** the command does not treat `--force` as permission to replace that unrelated session
- **AND THEN** the launch still fails on the tmux session-name collision
