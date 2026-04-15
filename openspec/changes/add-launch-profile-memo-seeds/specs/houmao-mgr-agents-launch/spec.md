## ADDED Requirements

### Requirement: Explicit launch-profile-backed launch applies stored memo seeds
`houmao-mgr agents launch --launch-profile <name>` SHALL apply the selected explicit launch profile's memo seed as part of the managed launch when that profile stores a memo seed.

The memo seed SHALL be applied after explicit launch-profile resolution and direct override resolution for managed-agent identity, so the seed targets the same authoritative agent id used by the launched runtime.

Direct launch-time overrides for other launch fields, such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir`, SHALL remain one-shot overrides and SHALL NOT rewrite the stored memo seed.

#### Scenario: Explicit launch profile seeds memo for overridden agent name
- **WHEN** explicit launch profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default --agent-name reviewer-a`
- **THEN** Houmao applies the memo seed to the memo paths for managed agent `reviewer-a`
- **AND THEN** the stored launch profile remains unchanged

#### Scenario: Explicit launch profile launch reports memo seed result
- **WHEN** explicit launch profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** the launch completion payload reports whether the memo seed was applied, skipped, or failed
