## ADDED Requirements

### Requirement: Layered managed system-skill coverage
Managed system-skill policy tests SHALL be organized so each test layer owns a distinct behavioral contract and does not repeatedly assert behavior owned by a cheaper lower layer.

#### Scenario: Pure policy layer owns mode and selector semantics
- **WHEN** managed system-skill policy parsing, selector validation, source/profile mode resolution, deduplication, disabled policy, replacement policy, managed-home sync cleanup, retired path cleanup, or user-skill preservation behavior is changed
- **THEN** the authoritative unit coverage SHALL live in direct policy/helper tests rather than repeated CLI flow tests

#### Scenario: Storage and parser layers stay focused
- **WHEN** recipe parsing or launch-profile catalog projection for managed system-skill policy is tested
- **THEN** the tests SHALL prove acceptance, rejection of lane-invalid modes, persistence, and projected payload shape without repeating the full policy mode matrix

### Requirement: Runtime integration coverage remains representative
Brain-builder and launch-resolution tests SHALL keep representative integration coverage for managed system-skill policy wiring without duplicating all low-level sync assertions.

#### Scenario: Build integration keeps behavior boundaries covered
- **WHEN** managed system-skill policy is passed through source recipes, launch profiles, or managed launch resolution into brain construction
- **THEN** tests SHALL verify representative source additive behavior, profile override or disable behavior, collision rejection, tool-specific projection roots, and secret-free provenance

#### Scenario: Filesystem sync details stay in sync helper tests
- **WHEN** a brain-builder test exercises reused-home cleanup
- **THEN** it SHALL assert the integration outcome and provenance, while exact removal ordering and path preservation details SHALL be covered by managed-home sync helper tests

### Requirement: CLI coverage is smoke-oriented and non-duplicative
CLI tests for managed system-skill policy SHALL verify user-facing wiring for each command lane while avoiding repeated copies of shared validation and policy semantics.

#### Scenario: Each user-facing lane has a compact smoke test
- **WHEN** testing `project easy specialist`, `project easy profile`, or `project agents launch-profiles` managed system-skill policy options
- **THEN** each lane SHALL have a compact test proving the command accepts policy options and emits or persists the expected user-visible payload shape

#### Scenario: Shared validation is tested once
- **WHEN** testing conflicts such as `--no-system-skills` combined with selectors, invalid system-skill names, or empty replacement selections
- **THEN** the shared validation behavior SHALL be covered by pure option/policy tests or one representative CLI error-rendering test, not duplicated across all command lanes

### Requirement: Refactor preserves verification confidence
Managed system-skill test deduplication SHALL preserve full-suite correctness and keep focused verification commands available for the changed modules.

#### Scenario: Focused and full verification pass
- **WHEN** the test deduplication refactor is complete
- **THEN** focused unit tests for the touched managed system-skill modules SHALL pass
- **AND** `pixi run test` SHALL pass

#### Scenario: Removed tests map to retained coverage
- **WHEN** a duplicate managed system-skill assertion is removed from a higher-level test
- **THEN** the implementation notes or task completion evidence SHALL identify the retained lower-level or representative test that still covers the behavior
