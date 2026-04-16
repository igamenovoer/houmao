## MODIFIED Requirements

### Requirement: Explicit launch-profile CLI manages memo seeds
`houmao-mgr project agents launch-profiles add` SHALL accept at most one memo seed source option:
- `--memo-seed-text <text>`,
- `--memo-seed-file <path>`,
- `--memo-seed-dir <path>`.

`houmao-mgr project agents launch-profiles add` SHALL NOT accept a memo seed apply policy option.

`houmao-mgr project agents launch-profiles set` SHALL support the same source options. It SHALL also accept `--clear-memo-seed` to remove the stored memo seed from the profile.

`--clear-memo-seed` SHALL NOT be combined with a memo seed source.

`launch-profiles get --name <profile>` SHALL report memo seed presence, source kind, and managed content reference metadata without printing full memo or page contents by default.

#### Scenario: Add stores memo seed file
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name reviewer --recipe reviewer-codex-default --memo-seed-file docs/reviewer.md`
- **THEN** the command stores `docs/reviewer.md` as a profile-owned memo seed
- **AND THEN** later `launch-profiles get --name reviewer` reports memo seed source kind `memo`
- **AND THEN** later `launch-profiles get --name reviewer` does not report a memo seed policy

#### Scenario: Add rejects multiple memo seed sources
- **WHEN** an operator supplies both `--memo-seed-text` and `--memo-seed-file`
- **THEN** `launch-profiles add` fails clearly before mutating the stored profile

#### Scenario: Set replaces memo seed content
- **WHEN** launch profile `reviewer` already stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name reviewer --memo-seed-file docs/reviewer-next.md`
- **THEN** the command replaces the stored memo seed content
- **AND THEN** the profile still records no memo seed policy

#### Scenario: Memo seed policy option is unsupported
- **WHEN** an operator supplies `--memo-seed-policy replace`
- **THEN** `launch-profiles add` or `launch-profiles set` fails before mutating the stored profile

#### Scenario: Set clears memo seed
- **WHEN** launch profile `reviewer` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name reviewer --clear-memo-seed`
- **THEN** the profile no longer records a memo seed
- **AND THEN** future launches from the profile do not apply seeded memo content

#### Scenario: Directory seed rejects unsupported top-level files
- **WHEN** an operator supplies `--memo-seed-dir seed` and `seed/README.md` exists beside `seed/houmao-memo.md`
- **THEN** the command fails clearly because memo seed directories may contain only `houmao-memo.md` and `pages/` at the top level
