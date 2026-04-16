## MODIFIED Requirements

### Requirement: `houmao-memory-mgr` explains launch-profile memo seed scope
When the packaged `houmao-memory-mgr` skill guides launch-profile or easy-profile memo seed edits, it SHALL explain that memo seed sources define which managed-memory components are replaced.

The skill SHALL guide memo-only seed requests through `--memo-seed-text` or `--memo-seed-file` without suggesting or requiring a memo seed policy.

The skill SHALL distinguish `--clear-memo-seed`, which removes stored profile seed configuration, from an empty memo seed, which stores empty memo content for future profile-backed launches.

#### Scenario: Skill routes empty memo seed without clearing pages
- **WHEN** a user asks an agent to make a launch profile seed an empty memo on future launches
- **THEN** `houmao-memory-mgr` guides the agent to use `--memo-seed-text ''`
- **AND THEN** the skill states that this affects `houmao-memo.md` and leaves pages outside the memo-only seed scope
- **AND THEN** the skill does not tell the agent to use `--memo-seed-policy`

#### Scenario: Skill removes stored seed only when requested
- **WHEN** a user asks an agent to remove a stored launch-profile memo seed
- **THEN** `houmao-memory-mgr` guides the agent to use `--clear-memo-seed`
- **AND THEN** the skill does not present `--clear-memo-seed` as a way to write an empty `houmao-memo.md`
