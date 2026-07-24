## ADDED Requirements

### Requirement: Cases are owned by functional areas
The behavior-testing catalog SHALL organize every committed case under exactly one of `activation`, `managed-bootstrap`, `admin-entrypoint`, `agent-entrypoint`, `shared-routines`, `agent-loops`, or `generated-prompts`.

`AUTO-*` cases SHALL belong to managed bootstrap. `PRM-004` SHALL belong to agent entrypoint and `PRM-005` SHALL belong to admin entrypoint. This organization MUST preserve all 42 existing case ids, exact stimuli, semantic oracles, and case revisions.

#### Scenario: Maintainer browses one functional area
- **WHEN** the maintainer selects the admin-entrypoint area
- **THEN** the skill loads the admin-entrypoint cases and their shared contracts
- **AND THEN** it does not require unrelated area pages

#### Scenario: Catalog organization changes without case meaning changes
- **WHEN** an existing case moves to its correct functional area
- **THEN** its stable id, exact stimulus, semantic oracle, and case revision remain unchanged

### Requirement: Coverage profiles are cumulative and committed
Every functional area SHALL expose `minimal`, `normal`, `extended`, and `complete` coverage profiles ordered as `minimal < normal < extended < complete`.

Each case SHALL declare the profile where it is introduced. Selecting a profile MUST include every case introduced at that profile or a lower profile in the same area. `complete` SHALL include every committed case and declared matrix variant in the selected area for the frozen catalog version.

The version 2 catalog SHALL resolve `all/minimal`, `all/normal`, `all/extended`, and `all/complete` to 11, 22, 41, and 42 case records respectively before matrix expansion.

#### Scenario: Maintainer selects normal coverage
- **WHEN** the maintainer selects `shared-routines/normal`
- **THEN** the resolved selection includes every minimal and normal shared-routine case
- **AND THEN** it excludes cases introduced at extended or complete

#### Scenario: Maintainer selects complete global coverage
- **WHEN** the maintainer selects `all/complete`
- **THEN** the resolved selection contains all 42 committed case records and all declared variants
- **AND THEN** the run identifies the frozen catalog revision as the boundary of the completeness claim

### Requirement: Suite selectors resolve deterministically
The skill SHALL accept canonical `<functional-area>/<coverage-profile>` selectors, `all/<coverage-profile>`, `tag:<name>`, exact case ids, exact case-variant ids, and composite unions of those selectors.

A bare functional area SHALL alias its `normal` profile. Composite selections SHALL use a stable catalog-order union and SHALL deduplicate repeated cases and variants. Unknown selectors MUST fail before provider launch. An absent selector MUST produce read-only selection help and MUST NOT launch `all/normal` or another implicit suite.

#### Scenario: Composite selection overlaps
- **WHEN** a maintainer selects `admin-entrypoint/normal` together with an exact case already included by that profile
- **THEN** the resolved run contains one copy of the case and records both selection sources

#### Scenario: No suite is named
- **WHEN** `run-suite` or `list-cases` receives no selector
- **THEN** the skill shows areas, profile meanings, cumulative counts, and examples without launching a provider or creating runtime resources

#### Scenario: Selector is invalid
- **WHEN** a requested area, profile, tag, case, or case variant does not exist in the frozen catalog
- **THEN** planning fails with a read-only diagnostic before provider launch

### Requirement: Cross-cutting views remain tags
The version 2 catalog SHALL retain the existing `critical`, `actor-boundaries`, and `route-coverage` memberships as cross-cutting tags. Tags MAY overlap and MUST NOT define or alter cumulative coverage-profile membership.

#### Scenario: Maintainer investigates actor boundaries
- **WHEN** the maintainer selects `tag:actor-boundaries`
- **THEN** the skill resolves the preserved actor-boundary case view across functional areas
- **AND THEN** the selected cases retain their functional ownership and introduced profile

### Requirement: Run manifests freeze resolved coverage
Before execution, the run manifest SHALL freeze requested selectors, catalog version and digest, resolved case ids and revisions, resolved variant ids, functional-area and profile attribution, explicit exclusions, and the planned provider, context, and repetition matrix.

Provider choice and repetition count MUST remain independent of coverage-profile selection. The runtime system-skill manifest MUST NOT generate or rewrite case or profile membership.

#### Scenario: Catalog changes after planning
- **WHEN** a committed catalog changes after a run manifest is frozen
- **THEN** the existing run continues to refer to its frozen selector expansion and digests
- **AND THEN** the skill does not substitute membership from the newer catalog

#### Scenario: Normal coverage uses a provider override
- **WHEN** a maintainer selects `agent-entrypoint/normal` for one provider
- **THEN** the semantic case membership remains the normal agent-entrypoint profile
- **AND THEN** only the provider execution dimension changes

### Requirement: Reports distinguish selection from qualification
Behavior-test reports SHALL identify requested selectors, resolved case and variant counts, planned and completed attempt cells, per-area selected coverage, per-case aggregate outcomes, and unexecuted or incomplete cells.

A report MUST NOT state that a selected profile was qualified when required cells did not receive a qualifying aggregate. It SHALL distinguish full qualification, partial qualification, and selection-only posture.

#### Scenario: Selected cases include incomplete attempts
- **WHEN** `admin-entrypoint/normal` is selected but one required provider or repetition cell remains incomplete
- **THEN** the report states that normal coverage was selected but only partially qualified
- **AND THEN** it links the incomplete cell and preserves its reason

### Requirement: Functional profiles remain development-only skill data
Functional areas and coverage profiles SHALL remain committed Markdown resources of `houmao-dev-behavior-testing`. They SHALL NOT add a runtime dependency, packaged system skill, admin or agent pack member, or managed auto-skill projection.

#### Scenario: Runtime skill manifest is inspected
- **WHEN** the packaged system-skill manifest and actor packs are resolved
- **THEN** behavior-testing functional areas and coverage profiles do not appear as installable runtime skills
