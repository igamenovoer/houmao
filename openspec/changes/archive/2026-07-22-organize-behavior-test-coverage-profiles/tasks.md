## 1. Catalog and Schema

- [x] 1.1 Advance the behavior suite catalog to version 2 and document canonical area/profile, global, tag, exact-case, exact-variant, and composite selectors.
- [x] 1.2 Replace the flat catalog listing with seven functional-area summaries, cumulative counts, profile meanings, concise no-selector guidance, and preserved cross-cutting tag membership.
- [x] 1.3 Extend the case schema with functional area, introduced profile, optional tags, stable matrix variants, and deterministic selector-expansion rules.
- [x] 1.4 Define frozen selection provenance and keep provider/repetition dimensions independent from semantic coverage.

## 2. Functional Area Organization

- [x] 2.1 Split activation and managed bootstrap into separate linked area pages without changing ACT or AUTO case meaning.
- [x] 2.2 Mark every admin-entrypoint case with its introduced profile and move PRM-005 into that functional area unchanged.
- [x] 2.3 Mark every agent-entrypoint case with its introduced profile and move PRM-004 into that functional area unchanged.
- [x] 2.4 Mark every shared-routine, loop, and generated-prompt case with its introduced profile while preserving stimuli and oracles.
- [x] 2.5 Add stable variant ids for every existing root, lifecycle, actor, or loop matrix cell.

## 3. Skill Selection and Reporting

- [x] 3.1 Update SKILL.md to route by functional area and coverage profile and to load only selected area pages and shared contracts.
- [x] 3.2 Update list-cases help behavior so no selector returns a concise read-only suite summary and selected output expands only requested slices.
- [x] 3.3 Update plan-run to validate, union, deduplicate, order, and freeze canonical selector expansion before provider launch.
- [x] 3.4 Update run-suite to accept the new selectors, reject unknown selectors, and preview case, variant, provider, and repetition cost.
- [x] 3.5 Update artifact and reporting contracts to distinguish selected coverage, full qualification, partial qualification, and selection-only posture.

## 4. Structural Coverage

- [x] 4.1 Update behavior-skill tests for the seven area pages, all 42 stable case ids, and unchanged stimuli/oracles relative to the prior revision.
- [x] 4.2 Add tests for unique area ownership, allowed introduced profiles, exact cumulative counts 11/22/41/42, nesting, and complete-catalog equality.
- [x] 4.3 Add tests for canonical selector and stable matrix-variant documentation, preserved tag memberships, and valid local Markdown links.
- [x] 4.4 Retain tests that both development skills remain outside the packaged runtime manifest and that the renamed TUI workflow is unchanged.

## 5. Validation

- [x] 5.1 Run the focused development-testing and system-skill unit tests.
- [x] 5.2 Run the skill validator and record only the established Imsight `skill_invocation_notation` schema exception if it remains.
- [x] 5.3 Run repository formatting and lint checks.
- [x] 5.4 Run `git diff --check` and strict OpenSpec validation for this change.
