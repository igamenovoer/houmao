## MODIFIED Requirements

### Requirement: Layered managed system-skill coverage
Managed system-skill tests SHALL assign distinct contracts to v4 manifest and schema parsing, pure pack and policy resolution, static source content validation, filesystem staging, receipt ownership transactions, CLI rendering, and runtime integration.

Pure tests SHALL own exact public inventory, pack membership, shared-owner deduplication, child actor eligibility, dependency closure, policy modes, and selector rejection. Filesystem tests SHALL own byte-identical copy, direct symlink targets, atomic commit and rollback, receipt persistence, mode changes, v3 drift classification, conflict preservation, and last-owner removal.

#### Scenario: Shared pack membership changes
- **WHEN** a standalone skill's owning pack set changes
- **THEN** authoritative membership and deduplication coverage lives in pure manifest tests
- **AND THEN** integration tests keep only representative installed-path assertions

#### Scenario: Last-owner removal changes
- **WHEN** receipt owner-set cleanup behavior changes
- **THEN** detailed ordering and restoration assertions live in filesystem transaction tests
- **AND THEN** CLI tests assert one representative user-visible outcome

#### Scenario: Pure policy layer owns mode and selector semantics
- **WHEN** managed system-skill policy parsing, selector validation, source/profile mode resolution, deduplication, disabled policy, replacement policy, managed-home sync cleanup, retired path cleanup, or user-skill preservation behavior is changed
- **THEN** the authoritative unit coverage SHALL live in direct policy/helper tests rather than repeated CLI flow tests

#### Scenario: Storage and parser layers stay focused
- **WHEN** recipe parsing or launch-profile catalog projection for managed system-skill policy is tested
- **THEN** the tests SHALL prove acceptance, rejection of lane-invalid modes, persistence, and projected payload shape without repeating the full policy mode matrix

#### Scenario: Audience route behavior changes
- **WHEN** a routine's eligible audiences or dependency closure changes
- **THEN** authoritative matrix coverage lives in pure manifest and route-policy tests
- **AND THEN** higher-level CLI and brain-builder tests keep only representative wiring assertions


#### Scenario: Receipt rollback behavior changes
- **WHEN** pack transaction rollback or ownership cleanup changes
- **THEN** detailed ordering and restoration assertions live in filesystem transaction tests
- **AND THEN** integration tests assert the resulting healthy or failed outcome



### Requirement: Runtime integration coverage remains representative
Brain-builder, launch, rebuild, relaunch, and join tests SHALL prove that managed defaults install the complete four-member static agent pack in copy mode and do not install admin public skills by default.

Representative integration coverage SHALL include policy override or disable behavior, reused-home synchronization, tool-native top-level siblings, shared child completeness, generated prompt route availability, auto-skill separation, collision rejection, and secret-free provenance without duplicating the low-level transaction matrix.

#### Scenario: Managed launch builds an agent home
- **WHEN** managed launch uses default system-skill policy
- **THEN** integration coverage verifies the agent entrypoint, shared routines, pro loop, and lite loop as top-level siblings
- **AND THEN** it verifies that no composed tree exists below the entrypoint

#### Scenario: Join opts out of system skills
- **WHEN** joined-session adoption uses explicit opt-out
- **THEN** integration coverage verifies that all four agent-pack members are absent
- **AND THEN** generated prompts use their fallback posture

#### Scenario: Build integration keeps behavior boundaries covered
- **WHEN** managed system-skill policy is passed through source recipes, launch profiles, or managed launch resolution into brain construction
- **THEN** tests SHALL verify representative source additive behavior, profile override or disable behavior, collision rejection, tool-specific projection roots, and secret-free provenance

#### Scenario: Filesystem sync details stay in sync helper tests
- **WHEN** a brain-builder test exercises reused-home cleanup
- **THEN** it SHALL assert the integration outcome and provenance, while exact removal ordering and path preservation details SHALL be covered by managed-home sync helper tests


### Requirement: CLI coverage is smoke-oriented and non-duplicative
CLI tests SHALL provide compact smoke coverage for static `list`, default and explicit `install`, `status`, v3-to-v4 `upgrade`, and overlapping-owner `uninstall` in plain and structured output.

Shared validation such as unknown packs, obsolete composition selectors, untracked collisions, incomplete sibling sets, drifted receipts, and modified conflicts SHALL be tested authoritatively in lower layers plus one representative CLI diagnostic.

#### Scenario: Each lifecycle command has one static smoke path
- **WHEN** CLI coverage is reviewed
- **THEN** every pack lifecycle command has a concise current success or status example
- **AND THEN** the full static source and receipt matrices are not duplicated across Click tests

#### Scenario: Obsolete mount selector is rendered once
- **WHEN** testing an old protected-mount selector
- **THEN** one CLI test verifies the static-pack migration diagnostic
- **AND THEN** rejection semantics remain owned by manifest or option tests

#### Scenario: Each user-facing lane has a compact smoke test
- **WHEN** testing `project specialist`, `project profile`, or `internals native-agent launch-dossiers` managed system-skill policy options
- **THEN** each lane SHALL have a compact test proving the command accepts policy options and emits or persists the expected user-visible payload shape

#### Scenario: Shared validation is tested once
- **WHEN** testing conflicts such as `--no-system-skills` combined with selectors, invalid system-skill names, or empty replacement selections
- **THEN** the shared validation behavior SHALL be covered by pure option/policy tests or one representative CLI error-rendering test, not duplicated across all command lanes

#### Scenario: Each lifecycle command has one public smoke path
- **WHEN** CLI coverage is reviewed
- **THEN** every pack lifecycle command has a concise success or status example
- **AND THEN** the full manifest and transaction matrices are not duplicated across Click tests


#### Scenario: Removed skill selector is rendered once
- **WHEN** testing obsolete `--skill` input
- **THEN** one representative CLI test verifies the migration diagnostic
- **AND THEN** selector rejection semantics remain owned by pure option or policy tests



### Requirement: Refactor preserves verification confidence
The refactor SHALL add content and behavior tests for all six standalone skills, sixteen shared children, both actor route indexes, direct shared and loop posture, welcome mutation boundaries, Imsight format rules, source-derived semantic preservation, exact Skills CLI discovery, static pack lifecycle, supported tool roots, generated prompt sibling checks, documentation examples, and safe v3 migration.

Focused tests for changed modules and content SHALL pass, followed by `pixi run lint`, `pixi run typecheck`, `pixi run test`, relevant runtime-focused suites, package build, and strict OpenSpec validation. Any removed composer test SHALL map to retained static staging, identity, or receipt coverage.

#### Scenario: Static refactor verification is complete
- **WHEN** implementation tasks are ready to close
- **THEN** focused manifest, static asset, actor, lifecycle, CLI, managed-home, prompt, and semantic-parity tests pass
- **AND THEN** repository verification and distribution checks pass or report only independently confirmed baseline failures

#### Scenario: Composer test is removed
- **WHEN** a test for dynamic protected mounting is deleted
- **THEN** implementation evidence identifies the static source, byte-identity, route, or receipt test that replaces its confidence

#### Scenario: Focused and full verification pass
- **WHEN** the test deduplication refactor is complete
- **THEN** focused unit tests for the touched managed system-skill modules SHALL pass
- **AND** `pixi run test` SHALL pass

#### Scenario: Removed tests map to retained coverage
- **WHEN** a duplicate managed system-skill assertion is removed from a higher-level test
- **THEN** the implementation notes or task completion evidence SHALL identify the retained lower-level or representative test that still covers the behavior

#### Scenario: Refactor verification is complete
- **WHEN** implementation tasks are ready to close
- **THEN** focused pack, actor, composer, CLI, managed-home, and content tests pass
- **AND THEN** lint, strict type checking, and the full unit suite pass


#### Scenario: Higher-level duplicate is removed
- **WHEN** a redundant old flat-skill assertion is deleted
- **THEN** implementation evidence identifies the retained pack-aware test that covers the behavior
