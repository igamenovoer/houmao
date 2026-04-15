## ADDED Requirements

### Requirement: Easy profile CLI manages memo seeds
`houmao-mgr project easy profile create` SHALL accept at most one memo seed source option:
- `--memo-seed-text <text>`,
- `--memo-seed-file <path>`,
- `--memo-seed-dir <path>`.

`houmao-mgr project easy profile create` SHALL accept `--memo-seed-policy <policy>` when a memo seed source is supplied, where `<policy>` is one of `initialize`, `replace`, or `fail-if-nonempty`. If a source is supplied without a policy, the stored policy SHALL default to `initialize`.

`houmao-mgr project easy profile set` SHALL support the same source and policy options. It SHALL also accept `--clear-memo-seed` to remove the stored memo seed and policy from the easy profile.

`project easy profile set --memo-seed-policy <policy>` without a new source SHALL update the policy for an existing memo seed and SHALL fail clearly when the profile has no memo seed.

`--clear-memo-seed` SHALL NOT be combined with a memo seed source or memo seed policy.

`project easy profile get --name <profile>` SHALL report memo seed presence, source kind, policy, and managed content reference metadata without printing full memo or page contents by default.

`project easy instance launch --profile <profile>` SHALL apply the selected easy profile's memo seed during managed launch when the profile stores one.

#### Scenario: Easy profile create stores memo seed text
- **WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-default --specialist reviewer --memo-seed-text "Read pages/review.md first."`
- **THEN** the easy profile stores the supplied text as a memo seed
- **AND THEN** later profile inspection reports memo seed policy `initialize`

#### Scenario: Easy profile set preserves memo seed when patching workdir
- **WHEN** easy profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --workdir /repos/next`
- **THEN** the profile updates the stored workdir
- **AND THEN** the stored memo seed remains unchanged

#### Scenario: Easy profile launch applies memo seed
- **WHEN** easy profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-default`
- **THEN** Houmao applies the memo seed to the launched managed agent's resolved `houmao-memo.md` and `pages/` before provider startup

#### Scenario: Easy profile set rejects clear combined with source
- **WHEN** an operator runs `houmao-mgr project easy profile set --name reviewer-default --clear-memo-seed --memo-seed-file docs/reviewer.md`
- **THEN** the command fails clearly before mutating the stored profile
