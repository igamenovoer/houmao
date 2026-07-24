# Shared-Routine Routing Cases

Functional area: `shared-routines`

## Workflow

1. **Resolve the direct or inherited actor case and stable variant.**
2. **Prepare only the required pack and target fixtures.**
3. **Observe actor selection before child loading.**
4. **Verify that only the selected `SKILL-MAIN.md` path and required resources load when access evidence exists.**
5. **Check the manifest route table against the committed route-coverage matrix.**

If a route lacks a safe read-only probe, use the native planning tool to run it only in declared isolated state or retain its explicit isolated-only marker; do not omit it from coverage.

## Functional-Area Defaults

- Case revision: `1` for every listed case.
- Providers: `claude`, `codex`, `kimi`.
- Pack: admin for direct admin/inherited admin; agent for `as-agent` and inherited agent.
- Auto skill: absent for raw admin, present for managed agent.
- Repetitions: `3`; timeout `180` seconds.
- Evidence: initial root event, inherited or fresh actor evidence, delegated shared root and selected child access, commands, response, and bounded effects.
- Cleanup: remove all isolated resources after evidence freeze.

## Cases

| ID | Introduced At | Exact Stimulus | Context | Expected Root and Route | Required Observables | Forbidden Observables / Effects | Driver Invocation Mode | Stimulus Origin | Activation Mode | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SHR-001` | `minimal` | `$houmao-shared-routines agent-inspect discover behavior-fixture-agent` | `raw-admin` | Shared routines direct admin to inspect child | Admin default, explicit target, no self identity, selected child only | Agent actor, `agents self`, sibling scan, mutation | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `houmao-agent-inspect` | `agent-inspect/discover` |
| `SHR-002` | `minimal` | `$houmao-shared-routines as-agent memory-mgr read your own Houmao memory memo` | `managed-agent` | Shared routines direct agent to memory child | Fresh exact identity before child; verified self target | Admin default, stale identity, unrelated child scan, mutation | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `houmao-memory-mgr` | `memory-mgr/read` |
| `SHR-003` | `normal` | Admin cell: `$houmao-admin-entrypoint agent-inspect discover behavior-fixture-agent` Agent cell: `$houmao-agent-entrypoint agent-inspect discover yourself` | Per cell | Inherited frame preserved through shared inspect | All six handoff fields remain consistent with caller; selected child only | Frame replacement, direct-posture recalculation, sibling scan | `manual` | `driving-agent` | `explicit` | Actor entrypoint matrix below | `houmao-shared-routines`, `houmao-agent-inspect` | `agent-inspect/discover` |
| `SHR-004` | `normal` | `$houmao-shared-routines agent-inspect discover behavior-fixture-agent` | `raw-admin` with access instrumentation | Shared inspect child only | Access to shared root, inspect `SKILL-MAIN.md`, and selected operation resources | Access to unrelated sibling `SKILL-MAIN.md` files | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `houmao-agent-inspect` | `agent-inspect/discover` |
| `SHR-005` | `extended` | `$houmao-shared-routines specialist-mgr roles` | `raw-admin` | Compatibility alias to agent-definition child | States canonical name and routes full request to agent-definition | Seventeenth child, standalone specialist skill, agent actor | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `houmao-agent-definition` | `specialist-mgr/roles` |
| `SHR-006` | `extended` | `$houmao-shared-routines as-agent project-mgr status .` | `managed-agent` | Shared routines rejects admin-only child | Fresh identity and eligibility rejection before child load | Project child access, project command, admin actor, mutation | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `none` | `project-mgr/status` rejected |
| `SHR-007` | `extended` | `$houmao-shared-routines process-emails-via-gateway http://127.0.0.1:43123` | `raw-admin` | Shared routines rejects agent-only notifier child | Admin default and rejection before child load | Notifier child, agent actor, identity command, mail/gateway mutation | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `none` | `process-emails-via-gateway` rejected |
| `SHR-008` | `extended` | `$houmao-shared-routines agent-loop-pro help` | `missing-dependency`, pro sibling omitted | Shared routines reports missing top-level sibling | Missing dependency diagnosis and no emulation | Generated replacement instructions, nested loop claim, mutation | `manual` | `driving-agent` | `explicit` | `houmao-shared-routines` | `none` | `agent-loop-pro/help` blocked by missing dependency |
| `SHR-009` | `normal` | Actor matrix below | Per actor cell | Matching actor entrypoint first, then shared routines and the intended inspect child | Actor-correct initial root, immutable handoff frame, selected shared child only, bounded inspect result | Direct implicit shared-root selection, opposite actor entrypoint, welcome, unrelated child scan, mutation | `automatic` | `driving-agent` | `implicit` | Actor entrypoint matrix below | `houmao-shared-routines`, `houmao-agent-inspect` | `agent-inspect/discover` |

## SHR-003 Actor Variants

| Variant ID | Caller and Exact Stimulus | Context | Expected Initial Root |
| --- | --- | --- | --- |
| `admin-entrypoint` | Admin cell: `$houmao-admin-entrypoint agent-inspect discover behavior-fixture-agent` | `raw-admin` with admin pack | `houmao-admin-entrypoint` |
| `agent-entrypoint` | Agent cell: `$houmao-agent-entrypoint agent-inspect discover yourself` | `managed-agent` with agent pack | `houmao-agent-entrypoint` |

Both variants use `driver_invocation_mode=manual`, `stimulus_origin=driving-agent`, and `activation_mode=explicit`. They preserve all six handoff fields from their caller and select only the inspect child.

Canonical selectors: `SHR-003/admin-entrypoint` and `SHR-003/agent-entrypoint`.

## SHR-009 Automatic Actor Variants

| Variant ID | Exact Stimulus | Context / Pack / Auto Skill | Expected Initial Root | Identity Oracle |
| --- | --- | --- | --- | --- |
| `admin` | `Inspect the managed Houmao agent named behavior-fixture-agent and tell me whether it is alive.` | `raw-admin` / admin / absent | `houmao-admin-entrypoint` | Admin frame; no self-identity command. |
| `managed-agent` | `Inspect yourself and tell me whether your managed Houmao agent is alive.` | `managed-agent` / agent / present | `houmao-agent-entrypoint` | Exact fresh self identity before shared delegation. |

Both variants use `driver_invocation_mode=automatic`, `stimulus_origin=driving-agent`, and `activation_mode=implicit`. Shared routines and `houmao-agent-inspect` are delegated roots, never implicit initial roots.

Canonical selectors: `SHR-009/admin` and `SHR-009/managed-agent`.

## Manifest Route Coverage

Every current entrypoint route has a committed bounded probe or explicit isolated-only marker. `admin` and `agent` refer to the manifest audience, not independent cases generated at runtime.

| Route | Admin Coverage | Agent Coverage | Probe / Marker |
| --- | --- | --- | --- |
| `help` | `ADM-001` | `AGT-001` | read-only entrypoint help |
| `welcome` | `ACT-001`, `ADM-002`, `ADM-006` | unsupported: agent route absent | local entrypoint guidance or explicit welcome handoff |
| `project-mgr` | covered | unsupported: admin-only | `status` in isolated project |
| `credential-mgr` | covered | unsupported: admin-only | `list` with isolated home |
| `agent-definition` | covered | unsupported: admin-only | `roles` read-only probe |
| `specialist-mgr` | `SHR-005` | unsupported: admin-only | alias `roles` probe |
| `operator-messaging` | covered | unsupported: admin-only | isolated-only `clarify` probe |
| `process-emails-via-gateway` | unsupported: agent-only | `PRM-001` | isolated bounded notifier round |
| `agent-email-comms` | covered | `PRM-002` | `status` or generated ordinary-mail prompt |
| `adv-usage-pattern` | covered | covered | read-only help boundary followed by isolated-only selected pattern when needed |
| `utils-workspace-mgr` | covered | covered | `summarize` disposable workspace |
| `ext-graphing` | covered | covered | `validate` disposable graphic fixture |
| `mailbox-mgr` | covered | covered | `status` disposable mailbox root |
| `memory-mgr` | covered | `AGT-002` | `read` missing or disposable memo |
| `agent-instance` | `ADM-004`, `ADM-008` | covered | `list` read-only; join isolated-only |
| `agent-inspect` | `ACT-003`, `ADM-003`, `SHR-004`, `SHR-009` | `AGT-008`, `SHR-009` | `discover` read-only |
| `agent-messaging` | covered | covered | `discover` read-only; send operations isolated-only |
| `agent-gateway` | covered | covered | `discover` or status read-only |
| `interop-ag-ui` | covered | covered | `validate` disposable event fixture |
| `agent-loop-pro` | `LOOP-002`, `LOOP-004`, `LOOP-008` | `LOOP-005`, `LOOP-006` | top-level sibling help/status/init boundary |
| `agent-loop-lite` | `LOOP-003`, `LOOP-004` | `LOOP-005`, `LOOP-006`, `LOOP-008` | top-level sibling help/status/init boundary |

The planning preflight compares this route column with `manifest.toml` command lists. `shared-routines/complete` includes this static preflight, but rows that are not committed cases do not become behavior attempts. A missing row makes route-coverage qualification incomplete; the skill does not add the row automatically.

## Guardrails

- DO NOT scan all children to prove selective loading.
- DO NOT treat loop siblings as owned shared children.
- DO NOT count entrypoint delegation as direct implicit shared-routines activation.
