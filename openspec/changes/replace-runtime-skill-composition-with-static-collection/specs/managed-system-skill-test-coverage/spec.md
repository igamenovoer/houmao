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
