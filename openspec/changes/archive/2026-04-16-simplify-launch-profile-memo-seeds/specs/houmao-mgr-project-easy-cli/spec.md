## MODIFIED Requirements

### Requirement: Easy profile CLI manages memo seeds
`houmao-mgr project easy profile create` SHALL accept at most one memo seed source option:
- `--memo-seed-text <text>`,
- `--memo-seed-file <path>`,
- `--memo-seed-dir <path>`.

`houmao-mgr project easy profile create` SHALL NOT accept a memo seed apply policy option.

`houmao-mgr project easy profile set` SHALL support the same source options. It SHALL also accept `--clear-memo-seed` to remove the stored memo seed from the easy profile.

`--clear-memo-seed` SHALL NOT be combined with a memo seed source.

`project easy profile get --name <profile>` SHALL report memo seed presence, source kind, and managed content reference metadata without printing full memo or page contents by default.

`project easy instance launch --profile <profile>` SHALL apply the selected easy profile's memo seed during managed launch when the profile stores one, using source-scoped replacement semantics from managed launch runtime.

#### Scenario: Easy profile create stores memo seed text
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-default --specialist reviewer --memo-seed-text "Read pages/review.md first."`
- **THEN** the easy profile stores the supplied text as a memo seed
- **AND THEN** later profile inspection reports memo seed source kind `memo`
- **AND THEN** later profile inspection does not report a memo seed policy

#### Scenario: Easy profile set preserves memo seed when patching workdir
- **WHEN** easy profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --workdir /repos/next`
- **THEN** the profile updates the stored workdir
- **AND THEN** the stored memo seed remains unchanged

#### Scenario: Easy profile set replaces memo seed content
- **WHEN** easy profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --memo-seed-file docs/reviewer-next.md`
- **THEN** the command replaces the stored memo seed content
- **AND THEN** the profile still records no memo seed policy

#### Scenario: Easy memo-only seed preserves pages
- **WHEN** easy profile `reviewer-default` stores memo-only seed text
- **AND WHEN** managed agent `reviewer-default` already has pages
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's `houmao-memo.md`
- **AND THEN** it leaves the launched agent's pages unchanged

#### Scenario: Memo seed policy option is unsupported
- **WHEN** an operator supplies `--memo-seed-policy replace`
- **THEN** `project easy profile create` or `project easy profile set` fails before mutating the stored profile

#### Scenario: Easy profile set rejects clear combined with source
- **WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --clear-memo-seed --memo-seed-file docs/reviewer.md`
- **THEN** the command fails clearly before mutating the easy profile
