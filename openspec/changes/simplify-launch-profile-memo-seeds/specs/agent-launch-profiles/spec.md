## MODIFIED Requirements

### Requirement: Launch profiles may store memo seeds
The shared launch-profile object family SHALL support one optional memo seed as reusable birth-time launch configuration.

A memo seed SHALL support these source forms:
- inline memo text,
- one Markdown file whose content becomes `houmao-memo.md`,
- one directory shaped like the managed memo tree with optional `houmao-memo.md` and optional `pages/`.

A memo seed directory SHALL reject unsupported top-level entries outside `houmao-memo.md` and `pages/`.

The launch-profile catalog SHALL store memo seed payloads as managed content references rather than as absolute source paths.

A stored memo seed SHALL NOT store or expose an apply policy. Its launch-time behavior SHALL be source-scoped replacement of represented managed-memory components.

Launch-profile inspection SHALL report whether a memo seed is present, the seed source kind, and managed content reference metadata without printing full memo or page contents by default.

Patch mutation SHALL preserve an existing memo seed when no memo seed field is supplied. Replacement mutation SHALL clear an existing memo seed unless the replacement request supplies a new memo seed. Removing a launch profile SHALL remove the profile's catalog relationship to its memo seed.

#### Scenario: Profile stores inline memo seed text
- **WHEN** an operator creates launch profile `researcher` with inline memo seed text
- **THEN** the shared launch-profile object records a memo seed with source kind `memo`
- **AND THEN** the catalog stores the memo seed as managed content rather than as an absolute caller path
- **AND THEN** profile inspection does not report a memo seed policy

#### Scenario: Profile stores a memo-shaped seed directory
- **WHEN** an operator creates easy profile `writer` with a seed directory containing `houmao-memo.md` and `pages/style.md`
- **THEN** the shared launch-profile object records a memo seed with source kind `tree`
- **AND THEN** later profile inspection reports that a memo seed is present without printing the full contents of `pages/style.md`
- **AND THEN** profile inspection does not report a memo seed policy

#### Scenario: Patch preserves stored memo seed
- **WHEN** launch profile `reviewer` stores a memo seed and workdir `/repos/a`
- **AND WHEN** an operator patches only the workdir to `/repos/b`
- **THEN** the stored launch profile records workdir `/repos/b`
- **AND THEN** the stored memo seed remains associated with the profile

#### Scenario: Replacement clears omitted memo seed
- **WHEN** launch profile `reviewer` stores a memo seed
- **AND WHEN** an operator replaces `reviewer` in the same profile lane without supplying a memo seed
- **THEN** the replacement profile no longer records a memo seed

#### Scenario: Cross-lane replacement cannot replace memo seed owner
- **WHEN** easy profile `alice` stores a memo seed
- **AND WHEN** an operator attempts to replace `alice` through the explicit launch-profile lane
- **THEN** the replacement fails because the profile lane does not match
- **AND THEN** the easy profile and its memo seed relationship remain unchanged
