## MODIFIED Requirements

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
- **THEN** the launch completion payload reports the memo seed application result
- **AND THEN** the launch completion payload does not report a memo seed policy

### Requirement: Explicit launch-profile memo seed application is component-scoped
`houmao-mgr agents launch --launch-profile <name>` SHALL apply the selected explicit launch profile's memo seed using source-scoped replacement semantics from managed launch runtime.

Direct launch-time overrides for other launch fields, such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir`, SHALL remain one-shot overrides and SHALL NOT rewrite the stored memo seed or its component scope.

#### Scenario: Explicit memo-only launch preserves pages
- **WHEN** explicit launch profile `reviewer-default` stores memo-only seed text
- **AND WHEN** managed agent `reviewer-default` already has pages
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's `houmao-memo.md`
- **AND THEN** it leaves the launched agent's pages unchanged
- **AND THEN** the launch completion payload reports the memo seed application result

#### Scenario: Explicit pages-only launch preserves memo
- **WHEN** explicit launch profile `reviewer-default` stores a directory memo seed containing `pages/notes/start.md` and no `houmao-memo.md`
- **AND WHEN** managed agent `reviewer-default` already has a memo
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's contained pages
- **AND THEN** it leaves the launched agent's `houmao-memo.md` unchanged
