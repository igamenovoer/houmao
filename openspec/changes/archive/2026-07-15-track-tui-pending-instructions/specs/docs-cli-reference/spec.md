## ADDED Requirements

### Requirement: CLI reference documents gateway prompt admission policies

The maintained `houmao-mgr` CLI reference SHALL document `--admission-policy ready-only|if-no-pending|always` for scoped `agents single ... gateway prompt` and `agents self gateway prompt` commands.

The reference SHALL explain the readiness and pending-input condition for each value, the conservative treatment of `pending_input=unknown`, the observational behavior when multiple submissions occur before a TUI repaint, and the TUI-only scope of non-default policies.

The reference SHALL remove `--force` from current syntax, option tables, and examples and SHALL NOT present it as an alias or migration shim.

#### Scenario: Reader can choose the policy from the CLI reference

- **WHEN** a reader opens the scoped gateway prompt command reference
- **THEN** the option table defines ready-only, if-no-pending, and always in terms of tracked readiness and provider-native pending input
- **AND THEN** the examples show the current `--admission-policy` syntax

#### Scenario: Reference explains observational concurrency

- **WHEN** a reader looks up whether if-no-pending reserves an empty queue slot
- **THEN** the CLI reference states that each call evaluates the latest observation independently
- **AND THEN** it explains that two calls may both submit before the provider TUI repaints

#### Scenario: Removed force option is absent from current docs

- **WHEN** a reader reviews gateway prompt syntax after the breaking change
- **THEN** current command tables and examples do not include `--force`
- **AND THEN** no documentation claims that a compatibility alias remains
