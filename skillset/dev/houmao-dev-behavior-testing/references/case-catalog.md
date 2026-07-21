# Houmao System-Skill Behavior Suite Catalog

Catalog version: `houmao-dev-behavior-cases.v2`

## Workflow

1. **Resolve selectors** from **Selector Forms**. With no selector, return only the functional-area and coverage-profile summary below.
2. **Expand cumulative profiles** in catalog order, then union and deduplicate exact cases and variants while retaining every selector that contributed them.
3. **Load only selected functional-area pages** and resolve their defaults plus case-specific records.
4. **Validate resolved records** against [case-schema.md](case-schema.md), including stable variants and the frozen selection provenance.
5. **Compare route-coverage expectations with the current packaged manifest** and report drift without changing cases or profile membership.
6. **Pass the exact catalog version, digest, selectors, cases, and variants to `plan-run`.**

If the requested behavior is not represented, use the native planning tool to draft a new committed case and review its oracle before running it; do not improvise an unversioned qualification.

## Selector Forms

| Form | Meaning | Example |
| --- | --- | --- |
| `<area>/<profile>` | Cumulative profile within one functional area | `admin-entrypoint/normal` |
| `<area>` | Alias for `<area>/normal` | `agent-loops` |
| `all/<profile>` | Union of that cumulative profile across all areas | `all/minimal` |
| `tag:<name>` | Preserved cross-cutting diagnostic view | `tag:actor-boundaries` |
| `<case-id>` | One exact case with every declared variant | `AGT-004` |
| `<case-id>/<variant-id>` | One exact stable case variant | `ACT-004/admin-welcome` |
| comma-separated selectors | Stable catalog-order union with deduplication | `admin-entrypoint/normal,AGT-004` |

Unknown areas, profiles, tags, cases, or variants fail during read-only planning. Coverage selectors do not choose providers or repetition counts. An absent selector never implies `all/normal` and never launches a provider.

## Coverage Profiles

The profile order is `minimal < normal < extended < complete`. A profile includes cases introduced at that profile or any lower profile in the selected area.

| Profile | Contract |
| --- | --- |
| `minimal` | Smallest meaningful smoke selection for the functional area |
| `normal` | Core routes, gates, handoffs, identity failures, and route boundaries; default for a bare area |
| `extended` | Secondary routes, repeated identity, spoof resistance, aliases, missing dependencies, and lifecycle reloads |
| `complete` | Every committed case and declared variant in the selected area for this catalog version |

`complete` means complete for `houmao-dev-behavior-cases.v2`; it does not claim coverage of uncommitted product behavior.

## Functional Areas and Cumulative Counts

Counts are committed case records before provider, repetition, or matrix-variant expansion.

| Functional Area | Minimal | Normal | Extended | Complete | Detail |
| --- | ---: | ---: | ---: | ---: | --- |
| `activation` | 2 | 4 | 4 | 4 | [cases/activation.md](cases/activation.md) |
| `managed-bootstrap` | 1 | 1 | 2 | 2 | [cases/managed-bootstrap.md](cases/managed-bootstrap.md) |
| `admin-entrypoint` | 1 | 3 | 8 | 9 | [cases/admin-routing.md](cases/admin-routing.md) |
| `agent-entrypoint` | 1 | 3 | 9 | 9 | [cases/managed-agent-routing.md](cases/managed-agent-routing.md) |
| `shared-routines` | 2 | 4 | 8 | 8 | [cases/shared-routines.md](cases/shared-routines.md) |
| `agent-loops` | 3 | 5 | 7 | 7 | [cases/loops.md](cases/loops.md) |
| `generated-prompts` | 1 | 2 | 3 | 3 | [cases/generated-prompts.md](cases/generated-prompts.md) |
| `all` | 11 | 22 | 41 | 42 | Union of all functional areas |

## Cross-Cutting Tags

Tags preserve the version 1 suite-label membership. They are overlapping diagnostic views and do not change functional ownership or cumulative profile membership.

- `critical`: `ACT-001`, `ACT-002`, `ACT-003`, `ACT-004`, `AUTO-001`, `ADM-003`, `ADM-004`, `ADM-006`, `AGT-002`, `AGT-004`, `AGT-005`, `SHR-001`, `SHR-002`, `SHR-004`, `LOOP-001`, `LOOP-002`, `LOOP-003`, `PRM-001`, and `PRM-002`.
- `actor-boundaries`: `ADM-005`, `ADM-007`, `ADM-008`, `AGT-004`, `AGT-005`, `AGT-006`, `AGT-007`, `SHR-002`, `SHR-003`, `SHR-006`, `SHR-007`, `LOOP-005`, and `LOOP-006`.
- `route-coverage`: `ADM-003`, `AGT-002`, `SHR-003`, `SHR-004`, `SHR-005`, `SHR-006`, `SHR-007`, `LOOP-002`, `LOOP-003`, `PRM-001`, and the static route matrix in [cases/shared-routines.md](cases/shared-routines.md).

## Deterministic Resolution

Resolve composite selectors in the order supplied, expand each selector in the functional-area and case order on this page, and retain the first occurrence of each `(case_id, variant_id)` cell. Record every contributing selector even when deduplication removes a repeated cell. A case selector without a variant expands every declared variant or one `base` cell when the case has no variants.

Freeze requested selectors, resolved cells, catalog digest, case revisions, functional areas, introduced profiles, tags, explicit exclusions, providers, contexts, and repetitions before launch. Later catalog edits never change an existing frozen run.

## Guardrails

- DO NOT treat catalog ordering as execution ordering.
- DO NOT generate missing cases or profile membership from the current manifest during a run.
- DO NOT describe a selected profile as qualified until all of its required planned cells receive a qualifying aggregate.
- DO NOT change a stimulus or oracle without incrementing its case revision.
