## Context

The completed `configure-managed-system-skills` change added broad coverage for managed system-skill policy. The coverage is valuable, but the same behavior is now asserted at several layers:

- pure policy parsing/resolution/sync helpers in `tests/unit/agents/test_system_skills.py`
- recipe parsing and catalog storage/projection tests
- brain-builder integration tests that exercise managed home projection, cleanup, collision rejection, and provenance
- CLI flows in `tests/unit/srv_ctrl/test_project_commands.py` for easy specialists, easy profiles, and explicit launch profiles

This creates a maintenance problem: a wording or payload-shape change can require edits in many tests even when only one layer owns that behavior. The unit suite also becomes slower and harder to read because large CLI tests repeat validation already covered by cheaper helper tests.

## Goals / Non-Goals

**Goals:**

- Preserve behavioral confidence for managed system-skill policy while reducing duplicate assertions.
- Make each test layer responsible for one kind of contract.
- Keep CLI tests focused on command wiring and user-visible payload smoke coverage.
- Keep pure helper tests exhaustive because they are cheap, direct, and stable.
- Keep full `pixi run test` green after refactoring.

**Non-Goals:**

- Do not change managed system-skill runtime behavior.
- Do not change CLI flags, payload formats, catalog schema, recipe YAML, provenance, or docs.
- Do not remove coverage for any policy mode or safety guard.
- Do not perform broad suite-wide cleanup outside managed system-skill policy tests.

## Decisions

### Decision: Treat pure policy tests as the authoritative matrix

`tests/unit/agents/test_system_skills.py` should own exhaustive policy behavior: parser normalization, serializer output, allowed source/profile modes, invalid selectors, source/profile resolution order, deduplication, exact replacement, disabled selection, managed-home sync cleanup, retired path cleanup, and user-skill preservation.

Alternative considered: keep mode/error coverage in each CLI lane. This is more expensive and makes CLI tests fail for policy details they do not own.

### Decision: Keep storage and parser tests narrow

Recipe parser tests should prove `launch.system_skills` is accepted and source-invalid modes are rejected. Catalog tests should prove launch-profile payloads persist and project to compatibility YAML. They should not repeat the full parser or mode matrix.

Alternative considered: remove storage/parser tests and rely on CLI flows. This would make failures harder to localize and overcouple storage behavior to command rendering.

### Decision: Compress brain-builder tests to integration boundaries

Brain-builder coverage should prove that resolved policies reach managed home construction and provenance. Keep representative tests for:

- source additive policy
- profile replacement or disabled policy overriding source policy
- reused-home cleanup at a high level
- project/private skill name collision rejection
- Gemini projection root
- manifest provenance

Detailed filesystem cleanup expectations should live in `sync_system_skills_for_home` tests.

Alternative considered: rely only on helper tests. This would miss wiring regressions from launch/build inputs into actual managed homes.

### Decision: Turn CLI coverage into thin lane smoke tests

The three user-facing lanes still need tests:

- `project easy specialist create/set/get`
- `project easy profile create/set`
- `project agents launch-profiles add/set`

Each lane should keep a compact happy-path smoke that proves the options are accepted and the stored/rendered payload appears in the right user-visible shape. Shared conflict/error semantics should be covered once through the common option resolver or a single representative CLI command, rather than repeated across all lanes.

Alternative considered: parameterize one large CLI matrix across all lanes. This reduces lines but still preserves too many layer-crossing assertions and can become difficult to debug.

### Decision: Prefer reusable test helpers only when they clarify ownership

Add or reuse fixtures/helpers for common project bootstrap and system-skill policy assertions where this removes repetition. Avoid clever abstractions that hide the command under test or make assertion failures opaque.

Alternative considered: leave tests verbose but delete cases. This would reduce count but not improve readability.

## Risks / Trade-offs

- Removing a duplicate test can accidentally remove unique coverage -> Build a coverage inventory before deletion and map each removed assertion to a retained lower-layer or representative test.
- CLI smoke tests may become too thin -> Keep at least one JSON/user-visible payload assertion per lane and one conflict/error-rendering assertion overall.
- Test helper extraction can obscure behavior -> Keep helpers small, named after setup or assertion intent, and leave command invocation visible in tests that validate CLI wiring.
- Full-suite time may not drop dramatically -> The primary goal is maintainability; runtime reduction is a secondary benefit.

## Migration Plan

1. Inventory current managed system-skill tests and group assertions by owned behavior.
2. Refactor or parameterize pure helper tests first so they retain the full mode and validation matrix.
3. Trim storage/parser tests to one or two focused assertions per contract.
4. Compress brain-builder tests to integration-level assertions and remove duplicated low-level filesystem expectations.
5. Replace repeated CLI flows with thin lane smoke tests plus one shared conflict/error test.
6. Run focused tests for the touched modules, then `pixi run test`.
7. Rollback strategy is straightforward: restore removed tests from git if a unique behavioral guarantee was lost.

## Open Questions

- Should the common CLI option resolver get direct unit tests if it is sufficiently separable, or should one representative CLI conflict test remain the only user-facing validation check?
- Should test-count reduction be measured only for the newly added managed system-skill tests, or should this establish a repeatable standard for future CLI-heavy changes?
