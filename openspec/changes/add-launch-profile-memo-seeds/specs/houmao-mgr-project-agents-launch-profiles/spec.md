## ADDED Requirements

### Requirement: Explicit launch-profile CLI manages memo seeds
`houmao-mgr project agents launch-profiles add` SHALL accept at most one memo seed source option:
- `--memo-seed-text <text>`,
- `--memo-seed-file <path>`,
- `--memo-seed-dir <path>`.

`houmao-mgr project agents launch-profiles add` SHALL accept `--memo-seed-policy <policy>` when a memo seed source is supplied, where `<policy>` is one of `initialize`, `replace`, or `fail-if-nonempty`. If a source is supplied without a policy, the stored policy SHALL default to `initialize`.

`houmao-mgr project agents launch-profiles set` SHALL support the same source and policy options. It SHALL also accept `--clear-memo-seed` to remove the stored memo seed and policy from the profile.

`launch-profiles set --memo-seed-policy <policy>` without a new source SHALL update the policy for an existing memo seed and SHALL fail clearly when the profile has no memo seed.

`--clear-memo-seed` SHALL NOT be combined with a memo seed source or memo seed policy.

`launch-profiles get --name <profile>` SHALL report memo seed presence, source kind, policy, and managed content reference metadata without printing full memo or page contents by default.

#### Scenario: Add stores memo seed file
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name reviewer --recipe reviewer-codex-default --memo-seed-file docs/reviewer.md`
- **THEN** the command stores `docs/reviewer.md` as a profile-owned memo seed
- **AND THEN** later `launch-profiles get --name reviewer` reports memo seed policy `initialize`

#### Scenario: Add rejects multiple memo seed sources
- **WHEN** an operator supplies both `--memo-seed-text` and `--memo-seed-file`
- **THEN** `launch-profiles add` fails clearly before mutating the stored profile

#### Scenario: Set updates memo seed policy only
- **WHEN** launch profile `reviewer` already stores a memo seed with policy `initialize`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name reviewer --memo-seed-policy fail-if-nonempty`
- **THEN** the command updates the stored memo seed policy
- **AND THEN** the memo seed content remains unchanged

#### Scenario: Set clears memo seed
- **WHEN** launch profile `reviewer` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name reviewer --clear-memo-seed`
- **THEN** the profile no longer records a memo seed
- **AND THEN** future launches from the profile do not apply seeded memo content

#### Scenario: Directory seed rejects unsupported top-level files
- **WHEN** an operator supplies `--memo-seed-dir seed` and `seed/README.md` exists beside `seed/houmao-memo.md`
- **THEN** the command fails clearly because memo seed directories may contain only `houmao-memo.md` and `pages/` at the top level
