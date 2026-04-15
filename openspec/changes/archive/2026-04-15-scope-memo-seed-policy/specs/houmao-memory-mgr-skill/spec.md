## ADDED Requirements

### Requirement: `houmao-memory-mgr` explains launch-profile memo seed scope
When the packaged `houmao-memory-mgr` skill guides launch-profile or easy-profile memo seed edits, it SHALL explain that memo seed policies apply only to the managed-memory components represented by the seed source.

The skill SHALL guide memo-only seed requests through `--memo-seed-text` or `--memo-seed-file` without suggesting that policy `replace` clears pages.

The skill SHALL distinguish `--clear-memo-seed`, which removes stored profile seed configuration, from an empty memo seed, which stores empty memo content for future profile-backed launches.

#### Scenario: Skill routes empty memo seed without clearing pages
- **WHEN** a user asks an agent to make a launch profile seed an empty memo on future launches
- **THEN** `houmao-memory-mgr` guides the agent to use `--memo-seed-text '' --memo-seed-policy replace`
- **AND THEN** the skill states that this affects `houmao-memo.md` and leaves pages outside the memo-only seed scope

#### Scenario: Skill removes stored seed only when requested
- **WHEN** a user asks an agent to remove a stored launch-profile memo seed
- **THEN** `houmao-memory-mgr` guides the agent to use `--clear-memo-seed`
- **AND THEN** the skill does not present `--clear-memo-seed` as a way to write an empty `houmao-memo.md`
