## MODIFIED Requirements

### Requirement: Layered managed system-skill coverage
Managed system-skill tests SHALL assign distinct contracts to manifest/schema parsing, pure pack and policy resolution, actor-route content validation, filesystem composition, receipt transactions, CLI rendering, and runtime integration.

Pure tests SHALL own pack-role cardinality, audience eligibility, dependency closure, policy modes, deduplication, public-name collision rules, and protected-selector rejection. Filesystem tests SHALL own staging, recursive validation, commit, rollback, receipt persistence, symlink materialization, legacy classification, drift, and preservation of unrelated skills.

#### Scenario: Audience route behavior changes
- **WHEN** a routine's eligible audiences or dependency closure changes
- **THEN** authoritative matrix coverage lives in pure manifest and route-policy tests
- **AND THEN** higher-level CLI and brain-builder tests keep only representative wiring assertions

#### Scenario: Receipt rollback behavior changes
- **WHEN** pack transaction rollback or ownership cleanup changes
- **THEN** detailed ordering and restoration assertions live in filesystem transaction tests
- **AND THEN** integration tests assert the resulting healthy or failed outcome

### Requirement: Runtime integration coverage remains representative
Brain-builder, launch, rebuild, relaunch, and join tests SHALL prove that managed defaults install the complete agent pack with copy projection and do not install admin public skills by default.

Representative integration coverage SHALL include policy override or disable behavior, reused-home receipt sync, tool-native public roots, protected agent composition, auto-skill separation, collision rejection, and secret-free provenance without duplicating the complete low-level transaction matrix.

#### Scenario: Managed launch builds an agent home
- **WHEN** managed launch uses default system-skill policy
- **THEN** integration coverage verifies top-level `houmao-agent-entrypoint`, its protected agent composition, and the absence of admin public skills
- **AND THEN** detailed file-copy ordering remains in composer tests

#### Scenario: Join opts out of system skills
- **WHEN** joined-session adoption uses the explicit opt-out
- **THEN** integration coverage verifies that the agent pack is absent and later prompt assumptions are disabled
- **AND THEN** auto system-prompt ownership remains separately tested

### Requirement: CLI coverage is smoke-oriented and non-duplicative
CLI tests SHALL provide compact smoke coverage for `list`, default and explicit `install`, `status`, `upgrade`, and `uninstall` in plain and structured output.

Shared validation such as unknown packs, removed selectors, untracked collisions, incomplete receipts, and modified legacy conflicts SHALL be tested authoritatively in lower layers plus one representative CLI diagnostic.

#### Scenario: Each lifecycle command has one public smoke path
- **WHEN** CLI coverage is reviewed
- **THEN** every pack lifecycle command has a concise success or status example
- **AND THEN** the full manifest and transaction matrices are not duplicated across Click tests

#### Scenario: Removed skill selector is rendered once
- **WHEN** testing obsolete `--skill` input
- **THEN** one representative CLI test verifies the migration diagnostic
- **AND THEN** selector rejection semantics remain owned by pure option or policy tests

### Requirement: Refactor preserves verification confidence
The refactor SHALL add content and behavior tests for all three public skills, both audience compositions, every protected logical routine, actor guard markers, welcome mutation boundaries, entrypoint identity rules, command and subskill layout, pack lifecycle transactions, supported tool roots, documentation examples, and safe legacy migration.

Focused tests for changed modules and content SHALL pass, followed by `pixi run lint`, `pixi run typecheck`, and `pixi run test`. Any removed duplicate test SHALL map to retained lower-level or representative coverage.

#### Scenario: Refactor verification is complete
- **WHEN** implementation tasks are ready to close
- **THEN** focused pack, actor, composer, CLI, managed-home, and content tests pass
- **AND THEN** lint, strict type checking, and the full unit suite pass

#### Scenario: Higher-level duplicate is removed
- **WHEN** a redundant old flat-skill assertion is deleted
- **THEN** implementation evidence identifies the retained pack-aware test that covers the behavior

