## Context

`houmao-dev-behavior-testing` currently stores 42 stable case records in six family pages and exposes one flat catalog plus the overlapping `critical`, `actor-boundaries`, and `route-coverage` labels. `run-suite` accepts a family or label, but neither form communicates cost or a predictable degree of semantic coverage. The three labels are useful cross-cutting views, not a hierarchy.

The case definitions are already committed, versioned, and separated from execution evidence. This change must preserve every exact stimulus, semantic oracle, case id, and case revision. It changes selection and progressive disclosure only. Provider selection, repetition count, fixture isolation, evidence capture, verdict rules, and packaged system skills remain independent.

## Goals / Non-Goals

**Goals:**

- Let maintainers select behavior cases by functional area and cumulative coverage profile.
- Make small, ordinary, deep, and exhaustive selections predictable through `minimal`, `normal`, `extended`, and `complete`.
- Keep selection static, committed, reviewable, reproducible, and independent of the current runtime manifest.
- Reduce no-argument catalog output while retaining exact-case and cross-cutting diagnostic selection.
- Preserve all existing behavior-test meaning and the Imsight complex-procedure skill shape.

**Non-Goals:**

- Change, merge, remove, or rewrite an existing case stimulus or oracle.
- Make a coverage profile choose providers, models, repetition counts, or credentials.
- Generate cases or profile membership from the runtime system-skill manifest.
- Add a parser, runtime package dependency, or packaged Houmao system skill.
- Claim that `complete` covers behavior not represented by the committed catalog revision.

## Decisions

### 1. Use Functional Area and Coverage Profile as Orthogonal Selection Axes

The canonical suite selector is `<functional-area>/<coverage-profile>`. Functional areas are `activation`, `managed-bootstrap`, `admin-entrypoint`, `agent-entrypoint`, `shared-routines`, `agent-loops`, and `generated-prompts`. `all/<coverage-profile>` resolves the union across all areas.

Split `AUTO-*` from activation because managed auto-prompt lifecycle qualification needs different fixtures and cost. Move `PRM-004` to the agent-entrypoint area and `PRM-005` to the admin-entrypoint area because both test actor eligibility under explicit entrypoint calls rather than generated prompt delivery. Their stable ids remain unchanged.

Keeping the current six families unchanged was rejected because activation mixes raw root selection with managed lifecycle bootstrap, while generated prompts currently owns two explicit cross-actor entrypoint cases.

### 2. Make Coverage Profiles Cumulative

The order is `minimal < normal < extended < complete`. Each case record declares `introduced_at`; selecting a profile includes cases introduced at that tier or any lower tier in the same area. This stores one static membership fact per case instead of duplicating four case lists.

- `minimal` is the smallest meaningful smoke selection for the area.
- `normal` adds core gates, handoffs, identity failures, and route boundaries and is the default when a bare area is supplied.
- `extended` adds secondary routes, repeated identity, spoof resistance, aliases, missing dependencies, lifecycle reloads, and other less common contexts.
- `complete` adds every remaining committed case and declared case variant in the area. It means complete for the frozen catalog version, not exhaustive product behavior.

The initial cumulative case-record counts are 11, 22, 41, and 42 for `all/minimal`, `all/normal`, `all/extended`, and `all/complete`. Matrix cases may expand into more execution cells. The shared-routine route matrix remains a committed drift and probe-coverage obligation; `shared-routines/complete` includes its preflight without manufacturing uncommitted cases.

Independent, non-cumulative profiles were rejected because maintainers could not infer whether `extended` subsumes `normal`. Repeated explicit membership lists were rejected because they can drift.

### 3. Preserve Cross-Cutting Labels as Tags

The current `critical`, `actor-boundaries`, and `route-coverage` memberships remain available through `tag:<name>`. Tags are diagnostic views and do not define coverage progression. A case can have multiple tags without changing its one functional area or one `introduced_at` tier.

Removing the labels was rejected because they preserve useful focused investigations. Keeping them as peer suite names was rejected because that recreates the current ambiguity.

### 4. Resolve Selectors Deterministically and Freeze the Expansion

`run-suite` and `plan-run` accept area/profile selectors, `all/<profile>`, `tag:<name>`, exact case ids, exact case-variant ids, or a composite union. A bare area aliases `<area>/normal`. No selector remains read-only and returns the area/profile summary rather than launching a default global suite. Unknown areas, profiles, tags, cases, and variants fail before provider launch.

Composite selections resolve to a stable catalog-order union and deduplicate cases and variants. The frozen run manifest records requested selectors, catalog version and digest, resolved cases and variants, functional-area/profile attribution, explicit exclusions, and planned provider/repetition expansion. A later catalog edit cannot alter an existing run.

Using model memory or runtime manifest contents to expand selectors was rejected because the same invocation could resolve differently without a catalog-version change.

### 5. Organize Detail by Area without Adding Subskills

Keep the Imsight complex-procedure entrypoint and existing subcommands. Coverage profiles are input data for `list-cases`, `plan-run`, and `run-suite`; they are not new subcommands or parent-scoped subskills. The top-level catalog becomes a concise versioned suite index. Seven linked area pages own defaults, tier membership, case definitions, and stable matrix-variant tables.

`list-cases` with no selector shows areas, cumulative counts, profile meanings, and examples. With selectors, it expands only the requested areas and cases. Ordinary execution loads the suite catalog, shared contracts, and only the selected area pages.

Creating one file per area/profile pair was rejected because 28 files would repeat case ids and increase drift. Keeping a flat 42-row table was rejected because it does not solve progressive disclosure.

### 6. Separate Selected Coverage from Achieved Qualification

Reports record the requested selector, resolved membership, planned and completed cells, aggregate case verdicts, and per-area coverage. A selected profile is not reported as qualified when required cells are unexecuted, incomplete, or otherwise lack a qualifying aggregate. Reports use wording such as `normal selected; partial qualification` instead of collapsing selection and outcome.

Provider and repetition overrides remain separate dimensions. This prevents `normal` from silently changing cost or confidence and keeps existing three-attempt verdict semantics intact.

## Risks / Trade-offs

- [The word `complete` may imply product-wide exhaustiveness] → Define it strictly as every committed case and declared variant in the frozen catalog revision.
- [A case can cover more than one concern] → Give it one functional owner and retain cross-cutting tags for secondary views.
- [Moving two `PRM-*` cases makes prefixes differ from areas] → Preserve stable ids for report continuity and make functional area an explicit field.
- [Matrix rows can hide execution cost] → Assign stable variant ids, report resolved cell counts, and preview the full attempt matrix before launch.
- [Cumulative counts can drift during edits] → Add structural tests for unique ownership, allowed tiers, exact initial membership, nesting, totals, and complete-catalog equality.
- [The generic skill validator rejects Imsight extension frontmatter] → Retain the established notation key and validate its exact value with repository tests as in the existing skill change.

## Migration Plan

1. Advance the suite catalog to version 2 and replace the flat list with area/profile selection guidance and preserved tag views.
2. Split managed bootstrap into its own area page, move the two cross-actor `PRM-*` definitions to their functional owners, and add `Introduced At` membership to all cases.
3. Update the case schema, entrypoint, planning, suite, artifact, and reporting instructions for deterministic selector expansion and coverage provenance.
4. Update focused tests for the seven areas, 42 stable ids, profile counts, tags, local links, route coverage, and unchanged runtime-pack exclusion.
5. Run focused tests, formatting, lint, skill validation with the known Imsight metadata exception, and strict OpenSpec validation.

Rollback restores the version 1 catalog and six family pages. No runtime installation, managed home, or behavior-test evidence migration is required because existing run manifests retain their frozen catalog version.

## Open Questions

None. The initial membership follows the reviewed exploration allocation, and later membership changes require a new catalog version while case revisions change only when case meaning changes.
