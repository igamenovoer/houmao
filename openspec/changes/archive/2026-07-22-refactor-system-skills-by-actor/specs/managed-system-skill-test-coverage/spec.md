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

#### Scenario: Pure policy layer owns mode and selector semantics
- **WHEN** managed system-skill policy parsing, selector validation, source/profile mode resolution, deduplication, disabled policy, replacement policy, managed-home sync cleanup, retired path cleanup, or user-skill preservation behavior is changed
- **THEN** the authoritative unit coverage SHALL live in direct policy/helper tests rather than repeated CLI flow tests

#### Scenario: Storage and parser layers stay focused
- **WHEN** recipe parsing or launch-profile catalog projection for managed system-skill policy is tested
- **THEN** the tests SHALL prove acceptance, rejection of lane-invalid modes, persistence, and projected payload shape without repeating the full policy mode matrix


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

#### Scenario: Build integration keeps behavior boundaries covered
- **WHEN** managed system-skill policy is passed through source recipes, launch profiles, or managed launch resolution into brain construction
- **THEN** tests SHALL verify representative source additive behavior, profile override or disable behavior, collision rejection, tool-specific projection roots, and secret-free provenance

#### Scenario: Filesystem sync details stay in sync helper tests
- **WHEN** a brain-builder test exercises reused-home cleanup
- **THEN** it SHALL assert the integration outcome and provenance, while exact removal ordering and path preservation details SHALL be covered by managed-home sync helper tests


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

#### Scenario: Each user-facing lane has a compact smoke test
- **WHEN** testing `project specialist`, `project profile`, or `internals native-agent launch-dossiers` managed system-skill policy options
- **THEN** each lane SHALL have a compact test proving the command accepts policy options and emits or persists the expected user-visible payload shape

#### Scenario: Shared validation is tested once
- **WHEN** testing conflicts such as `--no-system-skills` combined with selectors, invalid system-skill names, or empty replacement selections
- **THEN** the shared validation behavior SHALL be covered by pure option/policy tests or one representative CLI error-rendering test, not duplicated across all command lanes


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

#### Scenario: Focused and full verification pass
- **WHEN** the test deduplication refactor is complete
- **THEN** focused unit tests for the touched managed system-skill modules SHALL pass
- **AND** `pixi run test` SHALL pass

#### Scenario: Removed tests map to retained coverage
- **WHEN** a duplicate managed system-skill assertion is removed from a higher-level test
- **THEN** the implementation notes or task completion evidence SHALL identify the retained lower-level or representative test that still covers the behavior
