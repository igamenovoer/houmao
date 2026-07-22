## Why

`houmao-dev-behavior-testing` exposes 42 committed case records through one flat catalog plus three overlapping suite labels. Maintainers must inspect case ids and ad hoc label membership before they can choose a focused qualification run, which makes ordinary functional-area testing unnecessarily expensive and error-prone.

## What Changes

- Replace broad case-family and overlapping suite-label selection with seven explicit functional areas: activation, managed bootstrap, admin entrypoint, agent entrypoint, shared routines, agent loops, and generated prompts.
- Add cumulative `minimal`, `normal`, `extended`, and `complete` coverage profiles within every functional area, plus equivalent `all/<profile>` unions.
- Add canonical `<functional-area>/<coverage-profile>` suite selectors, composite selector unions, exact-case compatibility, deterministic deduplication, and stable matrix-cell selection.
- Make no-selector listing concise: show functional areas, profile counts, and selector examples before expanding individual cases.
- Freeze requested selectors and resolved case and matrix-cell membership in every run manifest, and distinguish selected coverage from successfully qualified coverage in reports.
- Advance the committed suite catalog to version 2 while preserving all existing case ids, stimuli, semantic oracles, and case revisions.
- Retain `critical`, `actor-boundaries`, and `route-coverage` as cross-cutting tags rather than competing suite definitions.

## Capabilities

### New Capabilities

- `houmao-dev-behavior-testing-coverage-profiles`: Defines functional-area organization, cumulative coverage profiles, deterministic suite selectors, frozen selection provenance, and coverage-aware reporting for the development behavior-testing skill.

### Modified Capabilities

None. The existing behavior-testing skill specification remains in its completed but unarchived change; this follow-up adds a separately reviewable selection capability without changing runtime Houmao system skills.

## Impact

- Updates `skillset/dev/houmao-dev-behavior-testing` routing, catalog/schema references, area pages, suite planning, and reporting instructions.
- Updates focused structural tests for functional-area ownership, tier nesting, selector counts, stable case preservation, and development-skill packaging exclusion.
- Adds no runtime dependency, packaged system skill, installation behavior, provider automation, or change to the behavior being tested.
