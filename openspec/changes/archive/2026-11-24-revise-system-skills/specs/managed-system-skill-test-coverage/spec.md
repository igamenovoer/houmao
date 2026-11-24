## MODIFIED Requirements

### Requirement: Layered managed system-skill coverage
Unit tests of shipped skill assets SHALL verify the existence and layout of declared roots, child entrypoints, and resource files. Executable product tests SHALL cover manifest and schema parsing, pack and policy resolution, filesystem staging, ownership transactions, release validation, CLI output, and managed-runtime integration.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Pure product tests SHALL cover the declared inventory, pack membership, shared-owner deduplication, child actor eligibility, dependency closure, policy modes, and selector rejection. Filesystem tests SHALL cover byte-identical copy, direct symlink targets, atomic commit and rollback, config persistence, mode changes, old-installation drift, conflict preservation, and last-owner removal.

#### Scenario: Maintainer revises instruction prose
- **WHEN** the wording, examples, guardrails, or workflow steps change without changing declared paths
- **THEN** asset unit tests still verify path existence and layout
- **AND THEN** unit tests do not assert instruction text, simulate authored workflow behavior, or run a semantic inventory against the Markdown

#### Scenario: Shared pack membership changes
- **WHEN** a standalone skill's owning pack set changes
- **THEN** authoritative membership and deduplication coverage lives in pure manifest tests
- **AND THEN** integration tests keep only representative installed-path assertions

#### Scenario: Last-owner removal changes
- **WHEN** config owner-set cleanup behavior changes
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

### Requirement: Refactor preserves verification confidence
Structural tests SHALL cover the six standalone entrypoints and declared shared children. Product checks SHALL retain coverage for discovery, static pack lifecycle, supported tool roots, manifests, doctor, generated prompts, release validation, and safe handling of older installations. Maintainers SHALL review instruction conformance and examples editorially.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Focused product and structure tests SHALL pass, followed by `pixi run lint`, `pixi run typecheck`, `pixi run test`, relevant runtime-focused suites, package build, and strict OpenSpec validation. Instruction prose and semantic fixtures SHALL stay outside unit-test acceptance.

#### Scenario: Static refactor verification is complete
- **WHEN** implementation tasks are ready to close
- **THEN** focused manifest, static asset structure, lifecycle, CLI, managed-home, and generated-prompt tests pass
- **AND THEN** repository verification and distribution checks pass or report only independently confirmed baseline failures

#### Scenario: Composer test is removed
- **WHEN** a test for dynamic protected mounting is deleted
- **THEN** implementation evidence identifies the retained test of static layout, staging, or ownership that covers the corresponding product behavior

#### Scenario: Focused and full verification pass
- **WHEN** the test deduplication refactor is complete
- **THEN** focused unit tests for the touched managed system-skill modules SHALL pass
- **AND THEN** `pixi run test` SHALL pass

#### Scenario: Removed tests map to retained coverage
- **WHEN** a duplicate product assertion is removed from a higher-level managed system-skill test
- **THEN** the implementation evidence identifies the retained lower-level or representative test that covers the executable behavior

#### Scenario: Refactor verification is complete
- **WHEN** implementation tasks are ready to close
- **THEN** focused pack, actor inventory, CLI, managed-home, and asset structure tests pass
- **AND THEN** lint, strict type checking, and the full unit suite pass

#### Scenario: Higher-level duplicate is removed
- **WHEN** a redundant old flat-skill assertion is deleted
- **THEN** implementation evidence identifies the retained pack-aware test that covers the corresponding product behavior

#### Scenario: A prose-only assertion or fixture is removed
- **WHEN** a test locks instruction wording, body format, procedural semantics, command examples, or guardrail text
- **THEN** the test or assertion is removed together with any fixture used solely for it
- **AND THEN** no new automated prose assertion or semantic fixture replaces it
