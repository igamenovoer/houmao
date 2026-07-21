# Behavior Case and Suite Selection Schema

## Workflow

1. **Resolve suite selectors.** Apply [case-catalog.md](case-catalog.md) to area/profile, global, tag, exact-case, exact-variant, and composite forms.
2. **Resolve functional-area defaults.** Treat the selected area page plus each case row and variant table as one case definition.
3. **Validate every required field** from **Resolved Case Fields** and **Frozen Selection Fields** before planning an attempt.
4. **Expand inherited defaults and variants** into the frozen run manifest so execution never depends on mutable implicit values.
5. **Bind the semantic oracle and exact stimulus** by digest before provider launch.
6. **Reject unknown selectors, areas, profiles, tags, activation modes, verdict requirements, or effect boundaries.**

If a new case needs a field the schema cannot represent, use the native planning tool to revise this schema and catalog explicitly before executing the case; do not hide the value in evaluator prose.

## Resolved Case Fields

| Field | Contract |
| --- | --- |
| `case_id` | Stable uppercase prefix and three digits, such as `ADM-003`; the prefix does not determine functional ownership |
| `case_revision` | Positive integer incremented when stimulus or semantic oracle changes |
| `title` | Short human-readable scenario name |
| `function_area` | `activation`, `managed-bootstrap`, `admin-entrypoint`, `agent-entrypoint`, `shared-routines`, `agent-loops`, or `generated-prompts` |
| `introduced_at` | `minimal`, `normal`, `extended`, or `complete`; higher profiles include lower tiers |
| `tags` | Zero or more committed cross-cutting views; initial names are `critical`, `actor-boundaries`, and `route-coverage` |
| `providers` | Explicit subset of `claude`, `codex`, and `kimi`, or a recorded unsupported reason |
| `context_type` | One named fixture context from `fixture-contexts.md` |
| `required_pack` | `admin`, `agent`, `admin+agent`, or `none` |
| `auto_skill_posture` | `present-required`, `absent-required`, or `not-applicable` |
| `activation_mode` | `implicit`, `explicit`, `generated-prompt`, or `lifecycle` |
| `stimulus` | Exact prompt or ordered multi-turn stimulus; placeholders resolve before freeze |
| `expected_root` | Expected top-level skill, `none`, or a parameterized root matrix |
| `expected_route` | Expected sibling/child/operation path, `none`, or an explicitly unobservable route |
| `required_observables` | Concrete events, commands, gates, response meanings, or state transitions required to pass |
| `forbidden_observables` | Roots, routes, commands, actor transitions, mutations, or claims that fail the case |
| `permitted_effects` | Bounded paths and runtime resources the attempt may change |
| `evidence_requirements` | Minimum evidence kinds needed for each required verdict dimension |
| `repetitions` | Positive count; default `3`; independent of coverage profile |
| `timeout_seconds` | Positive observation limit or an explicit lifecycle boundary |
| `stop_condition` | Terminal response, clarification, bounded effect, generated round completion, or lifecycle event |
| `cleanup` | Sessions, temporary homes, agents, gateways, mailboxes, and files to restore or remove |

## Stable Variants

A case with a root, lifecycle, actor, dependency, or loop matrix declares one stable lowercase variant id per existing matrix cell. The canonical exact selector is `<case-id>/<variant-id>`, such as `ACT-004/admin-welcome`. A case without a matrix resolves to one implicit `base` cell.

Variant records inherit the case id, revision, functional area, introduced profile, tags, and shared oracle. They declare any cell-specific pack, context, stimulus, expected root or route, stop condition, or repetition multiplier. Adding, removing, or semantically changing a variant increments the case revision.

## Frozen Selection Fields

| Field | Contract |
| --- | --- |
| `requested_selectors` | Exact ordered selector strings supplied by the maintainer |
| `catalog_version` | `houmao-dev-behavior-cases.v2` for the initial profile catalog |
| `catalog_digest` | Digest of the committed catalog and selected area resources |
| `resolved_cells` | Stable catalog-order records containing case id, revision, variant id, area, introduced profile, and contributing selectors |
| `explicit_exclusions` | Any requested exclusions with a reason; absence is explicit |
| `provider_matrix` | Providers selected independently from semantic coverage |
| `context_matrix` | Expanded supported and unsupported context cells |
| `repetition_matrix` | Per-cell planned attempts from case defaults or explicit overrides, never inferred from profile name |

Composite selectors form a union. Retain the first catalog-order occurrence of each `(case_id, variant_id)` and record every contributing selector. A bare area resolves its `normal` profile. No selector is a read-only help posture and does not resolve an implicit suite.

## Inheritance

A functional-area page may declare common providers, context, pack, auto-skill posture, repetitions, timeout, evidence requirements, permitted root, and cleanup. A case table cell may say `area default`, but the planned `run-manifest.json` must contain the expanded value. Stimulus, expected root, required behavior, and forbidden behavior are never inherited from another case.

## Revision Rules

Increment `case_revision` when the exact stimulus, expected root or route, required or forbidden behavior, permitted effects, stop condition, evidence minimum, or stable variants change. Provider additions, clarified prose, and timeout changes also increment revision when they can affect results. Functional-area movement, introduced-profile assignment, tags, and catalog ordering alone do not increment a case revision when the stimulus and oracle remain identical; they do increment the catalog version.

## Guardrails

- DO NOT execute a case with unresolved selectors or placeholders.
- DO NOT let area defaults, profile expansion, or variants remain implicit in a frozen run manifest.
- DO NOT use a profile to choose providers or repetitions.
- DO NOT change an oracle without incrementing the case revision.
