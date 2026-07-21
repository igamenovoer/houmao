# Houmao System-Skill Behavior Case Catalog

Catalog version: `houmao-dev-behavior-cases.v1`

## Workflow

1. **Select a case id or family** from the tables below.
2. **Load the linked family page** and resolve its family defaults plus case-specific record.
3. **Validate the resolved case** against [case-schema.md](case-schema.md).
4. **Compare route-coverage expectations with the current packaged manifest** and report drift without changing this catalog.
5. **Pass the exact selected revision to `plan-run`.**

If the requested behavior is not represented, use the native planning tool to draft a new committed case and review its oracle before running it; do not improvise an unversioned qualification.

## Families

| Family | Scope | Detail |
| --- | --- | --- |
| `activation` | Implicit, explicit, non-activation, and managed auto-prompt bootstrap | [cases/activation.md](cases/activation.md) |
| `admin-routing` | Admin help, targets, welcome, shared delegation, eligibility, and join transition | [cases/admin-routing.md](cases/admin-routing.md) |
| `managed-agent-routing` | Fresh identity, self/peer targets, agent eligibility, and spoof resistance | [cases/managed-agent-routing.md](cases/managed-agent-routing.md) |
| `shared-routines` | Direct posture, inherited frames, selective child loading, aliases, eligibility, and route coverage | [cases/shared-routines.md](cases/shared-routines.md) |
| `loops` | Manual-only pro/lite activation, actor selection, help, and loop boundary | [cases/loops.md](cases/loops.md) |
| `generated-prompts` | Notifier rounds, ordinary mailbox prompts, missing dependencies, and pack mismatch | [cases/generated-prompts.md](cases/generated-prompts.md) |

## Cases

| Case ID | Revision | Family | Context | Activation | Repetitions |
| --- | ---: | --- | --- | --- | ---: |
| `ACT-001` | 1 | activation | raw-admin | implicit | 3 |
| `ACT-002` | 1 | activation | raw-admin | implicit | 3 |
| `ACT-003` | 1 | activation | raw-admin | implicit | 3 |
| `ACT-004` | 1 | activation | raw-admin or managed-agent | explicit | 3 per root |
| `AUTO-001` | 1 | activation | managed-agent | lifecycle | 3 |
| `AUTO-002` | 1 | activation | lifecycle-reload | lifecycle | 3 per lifecycle event |
| `ADM-001` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-002` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-003` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-004` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-005` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-006` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-007` | 1 | admin-routing | raw-admin | explicit | 3 |
| `ADM-008` | 1 | admin-routing | joined-session | lifecycle | 3 |
| `AGT-001` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `AGT-002` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `AGT-003` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `AGT-004` | 1 | managed-agent-routing | managed-identity-failure | explicit | 3 |
| `AGT-005` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `AGT-006` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `AGT-007` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `AGT-008` | 1 | managed-agent-routing | managed-agent | explicit | 3 |
| `SHR-001` | 1 | shared-routines | raw-admin | explicit | 3 |
| `SHR-002` | 1 | shared-routines | managed-agent | explicit | 3 |
| `SHR-003` | 1 | shared-routines | raw-admin or managed-agent | explicit | 3 per actor |
| `SHR-004` | 1 | shared-routines | raw-admin | explicit | 3 |
| `SHR-005` | 1 | shared-routines | raw-admin | explicit | 3 |
| `SHR-006` | 1 | shared-routines | managed-agent | explicit | 3 |
| `SHR-007` | 1 | shared-routines | raw-admin | explicit | 3 |
| `SHR-008` | 1 | shared-routines | missing-dependency | explicit | 3 |
| `LOOP-001` | 1 | loops | raw-admin | implicit | 3 |
| `LOOP-002` | 1 | loops | raw-admin | explicit | 3 |
| `LOOP-003` | 1 | loops | raw-admin | explicit | 3 |
| `LOOP-004` | 1 | loops | raw-admin or managed-agent | explicit | 3 per root |
| `LOOP-005` | 1 | loops | raw-admin or managed-agent | explicit | 3 per actor |
| `LOOP-006` | 1 | loops | managed-agent | explicit | 3 per root |
| `LOOP-007` | 1 | loops | raw-admin | explicit | 3 per root |
| `PRM-001` | 1 | generated-prompts | managed-agent | generated-prompt | 3 |
| `PRM-002` | 1 | generated-prompts | managed-agent | generated-prompt | 3 |
| `PRM-003` | 1 | generated-prompts | missing-dependency | generated-prompt | 3 |
| `PRM-004` | 1 | generated-prompts | managed-agent | explicit | 3 |
| `PRM-005` | 1 | generated-prompts | raw-admin | explicit | 3 |

## Suite Labels

- `critical`: `ACT-001`, `ACT-002`, `ACT-003`, `ACT-004`, `AUTO-001`, `ADM-003`, `ADM-004`, `ADM-006`, `AGT-002`, `AGT-004`, `AGT-005`, `SHR-001`, `SHR-002`, `SHR-004`, `LOOP-001`, `LOOP-002`, `LOOP-003`, `PRM-001`, and `PRM-002`.
- `actor-boundaries`: `ADM-005`, `ADM-007`, `ADM-008`, `AGT-004`, `AGT-005`, `AGT-006`, `AGT-007`, `SHR-002`, `SHR-003`, `SHR-006`, `SHR-007`, `LOOP-005`, and `LOOP-006`.
- `route-coverage`: `ADM-003`, `AGT-002`, `SHR-003`, `SHR-004`, `SHR-005`, `SHR-006`, `SHR-007`, `LOOP-002`, `LOOP-003`, `PRM-001`, and the route matrix in `cases/shared-routines.md`.

## Guardrails

- DO NOT treat catalog ordering as execution ordering.
- DO NOT generate missing cases from the current manifest during a run.
- DO NOT change a stimulus or oracle without incrementing its revision.
