# Behavior Case and Suite Selection Schema

## Workflow

1. **Resolve suite selectors.** Apply [case-catalog.md](case-catalog.md) to area/profile, mode-aware area/profile, global profile, mode-aware global profile, tag, exact-case, exact-variant, and composite forms.
2. **Resolve functional-area defaults.** Treat the selected area page plus each case row and variant table as one case definition.
3. **Validate every required field** from **Resolved Case Fields** and **Frozen Selection Fields** before planning an attempt.
4. **Expand inherited defaults and variants** into the frozen run manifest so execution never depends on mutable implicit values.
5. **Bind invocation provenance, the semantic oracle, and exact stimulus** by digest before provider launch.
6. **Reject unknown selectors, areas, profiles, invocation modes, stimulus origins, tags, activation modes, verdict requirements, or effect boundaries.**

If a new case needs a field the schema cannot represent, use the native planning tool to revise this schema and catalog explicitly before executing the case; do not hide the value in evaluator prose.

## Resolved Case Fields

| Field | Contract |
| --- | --- |
| `case_id` | Stable uppercase prefix and three digits, such as `ADM-003`; the prefix does not determine functional ownership |
| `case_revision` | Positive integer incremented when stimulus or semantic oracle changes |
| `title` | Short human-readable scenario name |
| `function_area` | `activation`, `managed-bootstrap`, `admin-entrypoint`, `agent-entrypoint`, `shared-routines`, `agent-loops`, `generated-prompts`, or `agent-definitions` |
| `introduced_at` | `minimal`, `normal`, `extended`, or `complete`; higher profiles include lower tiers |
| `tags` | Zero or more committed cross-cutting views; current names are `critical`, `actor-boundaries`, and `route-coverage` |
| `providers` | Explicit subset of `claude`, `codex`, and `kimi`, or a recorded unsupported reason |
| `context_type` | One named fixture context from `fixture-contexts.md` |
| `required_pack` | `admin`, `agent`, `admin+agent`, or `none` |
| `auto_skill_posture` | `present-required`, `absent-required`, or `not-applicable` |
| `driver_invocation_mode` | `manual`, `automatic`, or `not-applicable` under the catalog contract |
| `stimulus_origin` | `driving-agent`, `generated-prompt`, or `lifecycle`; `not-applicable` driver mode is valid only for the latter two origins |
| `activation_mode` | `implicit`, `explicit`, `generated-prompt`, or `lifecycle` |
| `stimulus` | Exact prompt or ordered multi-turn stimulus; placeholders resolve before freeze |
| `expected_initial_root` | Expected host-selected top-level root, `none`, or a parameterized root matrix |
| `expected_delegated_roots` | Ordered sibling and parent-scoped roots expected after initial selection, or `none` |
| `expected_route` | Expected child or operation path, `none`, a blocked/rejected path, or an explicitly unobservable route |
| `required_observables` | Concrete events, commands, phases, gates, response meanings, or state transitions required to pass |
| `forbidden_observables` | Roots, routes, commands, actor transitions, mutations, or claims that fail the case |
| `permitted_effects` | Bounded paths and runtime resources the attempt may change |
| `evidence_requirements` | Minimum evidence kinds needed for each required verdict dimension |
| `repetitions` | Positive count; default `3`; independent of coverage profile |
| `timeout_seconds` | Positive observation limit or an explicit lifecycle boundary |
| `stop_condition` | Terminal response, clarification, bounded effect, generated round completion, or lifecycle event |
| `cleanup` | Sessions, temporary homes, agents, gateways, mailboxes, and files to restore or remove |

`expected_initial_root` records host selection. Entry-point delegation to `houmao-shared-routines`, a parent-scoped child, or a loop sibling belongs only in `expected_delegated_roots` and `expected_route`. Automatic cases cannot name welcome as an initial or delegated root. Shared routines and both loop roots can be automatic delegated roots but cannot be automatic initial roots.

## Driver Invocation Integrity

A `manual` resolved cell must contain its intended top-level `$houmao-*` handle in the driving stimulus. An `automatic` resolved cell must contain no `$houmao-*` handle and must use `stimulus_origin=driving-agent`. A `not-applicable` cell must use `stimulus_origin=generated-prompt` or `lifecycle` and must not be counted as natural-context automatic discovery.

Generated prompt text may itself contain an explicit skill handle because the generator, not a driving agent, owns that stimulus. The frozen origin prevents that case from being mislabeled as either manual driver invocation or automatic discovery.

## Stable Variants

A case with a root, lifecycle, actor, dependency, phase, or loop matrix declares one stable lowercase variant id per existing matrix cell. The canonical exact selector is `<case-id>/<variant-id>`, such as `ACT-005/informational`. A case without a matrix resolves to one implicit `base` cell.

Variant records inherit the case id, revision, functional area, introduced profile, tags, and shared oracle. They declare any cell-specific pack, context, driver invocation mode, stimulus origin, stimulus, initial root, delegated roots, route, stop condition, or repetition multiplier. Adding, removing, or semantically changing a variant increments the case revision.

## Frozen Selection Fields

| Field | Contract |
| --- | --- |
| `requested_selectors` | Exact ordered selector strings supplied by the maintainer |
| `catalog_version` | `houmao-dev-behavior-cases.v4` |
| `catalog_digest` | Digest of the committed catalog and selected area resources |
| `resolved_cells` | Stable catalog-order records containing case id, revision, variant id, area, introduced profile, driver invocation mode, stimulus origin, exact stimulus digest, initial-root oracle, delegated-root oracle, route oracle, and contributing selectors |
| `explicit_exclusions` | Any requested exclusions with a reason; absence is explicit |
| `provider_matrix` | Providers selected independently from semantic coverage |
| `context_matrix` | Expanded supported and unsupported context cells |
| `repetition_matrix` | Per-cell planned attempts from case defaults or explicit overrides, never inferred from profile name |

Composite selectors form a union. Retain the first catalog-order occurrence of each `(case_id, variant_id)` and record every contributing selector. A bare area resolves its `normal` profile across every invocation mode. No selector is a read-only help posture and does not resolve an implicit suite.

## Inheritance

A functional-area page may declare common providers, context, pack, auto-skill posture, driver invocation mode, stimulus origin, activation mode, repetitions, timeout, evidence requirements, permitted root, and cleanup. A case table cell may say `area default`, but the planned `run-manifest.json` must contain the expanded value. Stimulus, expected initial root, expected delegated roots, expected route, required behavior, and forbidden behavior are never inherited from another case.

## Revision Rules

Increment `case_revision` when the exact stimulus, expected initial root, delegated roots, route, required or forbidden behavior, permitted effects, stop condition, evidence minimum, or stable variants change. Provider additions, clarified prose, and timeout changes also increment revision when they can affect results. Functional-area movement, introduced-profile assignment, invocation-mode classification of an otherwise unchanged stimulus, tags, and catalog ordering alone do not increment a case revision when the stimulus and semantic oracle remain identical; they do increment the catalog version.

Version 3 intentionally advances `ACT-001`, `ACT-003`, `ADM-002`, and `LOOP-001` to revision 2. It adds `ACT-005`, `ACT-006`, `SHR-009`, and `LOOP-008` at revision 1. Every other version 2 case retains its exact stimulus and semantic oracle.

Version 4 adds the `agent-definitions` functional area and `ADF-001` through `ADF-008` at revision 1. Every version 3 case retains its exact stimulus and semantic oracle.

## Guardrails

- DO NOT execute a case with unresolved selectors or placeholders.
- DO NOT let area defaults, profile expansion, invocation provenance, or variants remain implicit in a frozen run manifest.
- DO NOT use a profile or invocation mode to choose providers or repetitions.
- DO NOT change an oracle without incrementing the case revision.
- DO NOT call delegated sibling access direct implicit activation.
