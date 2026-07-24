# Houmao System-Skill Behavior Suite Catalog

Catalog version: `houmao-dev-behavior-cases.v4`

## Workflow

1. **Resolve selectors** from **Selector Forms**. With no selector, return only the functional-area, invocation-mode, and coverage-profile summary below.
2. **Expand cumulative profiles** in catalog order, filter by driver invocation mode when requested, then union and deduplicate exact cases and variants while retaining every selector that contributed them.
3. **Load only selected functional-area pages** and resolve their defaults plus case-specific records.
4. **Validate resolved records** against [case-schema.md](case-schema.md), including stable variants, invocation provenance, initial-root and delegation oracles, and frozen selection provenance.
5. **Compare route-coverage expectations with the current packaged manifest** and report drift without changing cases or profile membership.
6. **Pass the exact catalog version, digest, selectors, cases, variants, invocation modes, and root oracles to `plan-run`.**

If the requested behavior is not represented, use the native planning tool to draft a new committed case and review its oracle before running it; do not improvise an unversioned qualification.

## Selector Forms

| Form | Meaning | Example |
| --- | --- | --- |
| `<area>/<profile>` | Cumulative profile within one functional area across all invocation modes | `admin-entrypoint/normal` |
| `<area>/<manual\|automatic>/<profile>` | Cumulative functional-area profile filtered to one driver invocation mode | `activation/automatic/normal` |
| `<area>` | Alias for `<area>/normal` across all invocation modes | `agent-loops` |
| `all/<profile>` | Union of that cumulative profile across all areas and invocation modes | `all/minimal` |
| `all/<manual\|automatic>/<profile>` | Global cumulative profile filtered to one driver invocation mode | `all/manual/extended` |
| `tag:<name>` | Preserved cross-cutting diagnostic view | `tag:actor-boundaries` |
| `<case-id>` | One exact case with every declared variant | `AGT-004` |
| `<case-id>/<variant-id>` | One exact stable case variant | `ACT-005/informational` |
| comma-separated selectors | Stable catalog-order union with deduplication | `activation/automatic/normal,AGT-004` |

Mode-aware selectors filter after cumulative functional-profile expansion. They accept only `manual` or `automatic`; generated-prompt and lifecycle cases use `not-applicable` and remain available through unfiltered area, global, tag, or exact-case selectors. Unknown areas, modes, profiles, tags, cases, or variants fail during read-only planning. Coverage selectors do not choose providers or repetition counts. An absent selector never implies `all/normal` and never launches a provider.

The canonical mode-aware forms are `<area>/<manual|automatic>/<profile>` and `all/<manual|automatic>/<profile>`.

## Driver Invocation Modes

| Mode | Contract |
| --- | --- |
| `manual` | The driving agent submits an exact prompt containing the intended top-level `$houmao-*` handle. |
| `automatic` | The driving agent submits natural task context without any `$houmao-*` handle and the oracle evaluates implicit actor-entrypoint selection or intentional non-selection. |
| `not-applicable` | The stimulus originates from maintained generated-prompt or lifecycle machinery rather than a direct driving-agent prompt. |

Automatic selection qualifies an actor entrypoint as the initial root. Delegated shared routines or loop siblings remain explicit-only roots and do not become direct implicit activations. Welcome is manual-only and cannot appear as an automatic initial or delegated root.

## Coverage Profiles

The profile order is `minimal < normal < extended < complete`. A profile includes cases introduced at that profile or any lower profile in the selected area.

| Profile | Contract |
| --- | --- |
| `minimal` | Smallest meaningful smoke selection for the functional area |
| `normal` | Core routes, gates, handoffs, identity failures, automatic delegation, and route boundaries; default for a bare area |
| `extended` | Secondary routes, repeated identity, spoof resistance, aliases, missing dependencies, combined-pack context, and lifecycle reloads |
| `complete` | Every committed case and declared variant in the selected area for this catalog version |

`complete` means complete for `houmao-dev-behavior-cases.v4`; it does not claim coverage of uncommitted product behavior.

## Functional Areas and Cumulative Counts

Counts are committed case records before provider, repetition, invocation-mode filtering, or matrix-variant expansion.

| Functional Area | Minimal | Normal | Extended | Complete | Detail |
| --- | ---: | ---: | ---: | ---: | --- |
| `activation` | 4 | 5 | 6 | 6 | [cases/activation.md](cases/activation.md) |
| `managed-bootstrap` | 1 | 1 | 2 | 2 | [cases/managed-bootstrap.md](cases/managed-bootstrap.md) |
| `admin-entrypoint` | 1 | 3 | 8 | 9 | [cases/admin-routing.md](cases/admin-routing.md) |
| `agent-entrypoint` | 1 | 3 | 9 | 9 | [cases/managed-agent-routing.md](cases/managed-agent-routing.md) |
| `shared-routines` | 2 | 5 | 9 | 9 | [cases/shared-routines.md](cases/shared-routines.md) |
| `agent-loops` | 3 | 6 | 8 | 8 | [cases/loops.md](cases/loops.md) |
| `generated-prompts` | 1 | 2 | 3 | 3 | [cases/generated-prompts.md](cases/generated-prompts.md) |
| `agent-definitions` | 2 | 5 | 7 | 8 | [cases/agent-definitions.md](cases/agent-definitions.md) |
| `all` | 15 | 30 | 52 | 54 | Union of all functional areas |

## Cross-Cutting Tags

Tags retain their version 2 membership and add version 3 cases where the same diagnostic contract applies. They are overlapping views and do not change functional ownership or cumulative profile membership.

- `critical`: `ACT-001`, `ACT-002`, `ACT-003`, `ACT-004`, `ACT-005`, `AUTO-001`, `ADM-003`, `ADM-004`, `ADM-006`, `AGT-002`, `AGT-004`, `AGT-005`, `SHR-001`, `SHR-002`, `SHR-004`, `SHR-009`, `LOOP-001`, `LOOP-002`, `LOOP-003`, `LOOP-008`, `PRM-001`, `PRM-002`, `ADF-001`, `ADF-002`, `ADF-003`, `ADF-004`, and `ADF-006`.
- `actor-boundaries`: `ACT-006`, `ADM-005`, `ADM-007`, `ADM-008`, `AGT-004`, `AGT-005`, `AGT-006`, `AGT-007`, `SHR-002`, `SHR-003`, `SHR-006`, `SHR-007`, `SHR-009`, `LOOP-005`, `LOOP-006`, `LOOP-008`, `ADF-006`, `ADF-007`, and `ADF-008`.
- `route-coverage`: `ACT-003`, `ADM-003`, `AGT-002`, `SHR-003`, `SHR-004`, `SHR-005`, `SHR-006`, `SHR-007`, `SHR-009`, `LOOP-002`, `LOOP-003`, `LOOP-008`, `PRM-001`, `ADF-002`, `ADF-004`, `ADF-006`, `ADF-007`, `ADF-008`, and the static route matrix in [cases/shared-routines.md](cases/shared-routines.md).

## Deterministic Resolution

Resolve composite selectors in the order supplied, expand each selector in the functional-area and case order on this page, apply any invocation-mode filter, and retain the first occurrence of each `(case_id, variant_id)` cell. Record every contributing selector even when deduplication removes a repeated cell. A case selector without a variant expands every declared variant or one `base` cell when the case has no variants.

Freeze requested selectors, resolved cells, catalog digest, case revisions, functional areas, introduced profiles, tags, driver invocation modes, stimulus origins, exact stimulus digests, expected initial roots, expected delegated roots, expected routes, explicit exclusions, providers, contexts, and repetitions before launch. Later catalog edits never change an existing frozen run.

## Guardrails

- DO NOT treat catalog ordering as execution ordering.
- DO NOT generate missing cases or profile membership from the current manifest during a run.
- DO NOT describe a selected profile as qualified until all of its required planned cells receive a qualifying aggregate.
- DO NOT change a stimulus or oracle without incrementing its case revision.
- DO NOT report a generated-prompt or lifecycle case as driver-origin automatic discovery.
