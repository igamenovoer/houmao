## ADDED Requirements

### Requirement: System-skills list reports the static collection and pack membership
`houmao-mgr system-skills list` SHALL report the six standalone skill names, the sixteen shared child logical ids, admin and agent pack member lists, default lanes, and activation posture.

Plain and structured output SHALL distinguish standalone install units from parent-scoped routines. It SHALL NOT describe shared routines as a protected mount or either loop as a shared child.

#### Scenario: Operator lists current system skills
- **WHEN** an operator runs `houmao-mgr system-skills list`
- **THEN** the output reports six standalone skills
- **AND THEN** it reports five admin members and four agent members
- **AND THEN** it identifies the three overlapping members and sixteen shared children

### Requirement: System-skills install manages complete static packs
`houmao-mgr system-skills install` SHALL accept repeatable `--pack admin|agent` selection plus supported tool, home, and copy or symlink options. Omitted external selection SHALL resolve admin.

The result SHALL report selected packs, deduplicated standalone members, top-level destination paths, projection mode, and receipt path. It SHALL NOT report a composed mount path or materialization root.

#### Scenario: Operator installs both packs
- **WHEN** an operator selects both admin and agent
- **THEN** the command installs six unique top-level roots transactionally
- **AND THEN** output reports shared ownership for shared routines, pro loop, and lite loop

### Requirement: System-skills status reports static integrity and owner sets
`houmao-mgr system-skills status` SHALL classify each installed pack and each receipt-owned standalone member as absent, complete, incomplete, drifted, or conflicting. It SHALL report owner pack ids, content digest posture, projection mode, and v3 migration evidence.

Status SHALL validate shared child completeness inside `houmao-shared-routines` without treating child paths as independent projections.

#### Scenario: Shared routines is missing from an agent installation
- **WHEN** the receipt owns agent but the shared-routines path is absent
- **THEN** status reports the agent pack as incomplete
- **AND THEN** it identifies the missing shared dependency

### Requirement: System-skills upgrade migrates composed packs to static packs
`houmao-mgr system-skills upgrade` SHALL migrate receipt-owned v3 actor packs to the v4 static collection through staged validation and transactional commit.

Output SHALL name added sibling roots, replaced actor entrypoints, removed obsolete composition material, preserved conflicts, and the resulting owner sets.

#### Scenario: Operator upgrades a V3 admin pack
- **WHEN** an operator upgrades a healthy receipt-owned v3 admin installation
- **THEN** the command installs all five static admin members
- **AND THEN** it replaces the composed admin entrypoint with the static entrypoint
- **AND THEN** it records a v4 receipt only after successful validation

### Requirement: System-skills uninstall honors overlapping ownership
`houmao-mgr system-skills uninstall` SHALL remove selected pack ownership transactionally and SHALL remove a standalone projection only after its last owner is removed.

Plain and structured output SHALL distinguish removed exclusive members, retained shared members, absent members, and preserved conflicts.

#### Scenario: Operator uninstalls agent while admin remains
- **WHEN** both packs are installed and the operator uninstalls agent
- **THEN** the command removes only the agent entrypoint
- **AND THEN** it retains shared routines and both loop skills for admin

### Requirement: System-skills CLI rejects dynamic-composition terminology and selectors
Current help and diagnostics SHALL describe static standalone members and shared parent-scoped routines. Protected mount ids, protected logical install selectors, materialized composition paths, and old set selectors SHALL NOT appear as supported current inputs.

#### Scenario: Operator requests a protected mount id
- **WHEN** an operator attempts to install `houmao-shared-routines` as a protected mount selector
- **THEN** the command rejects that obsolete selector form
- **AND THEN** it explains that shared routines is a standalone member installed through an actor pack
