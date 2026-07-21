# Shared-Routine Routing Cases

## Workflow

1. **Resolve the direct or inherited actor case.**
2. **Prepare only the required pack and target fixtures.**
3. **Observe actor selection before child loading.**
4. **Verify that only the selected `SKILL-MAIN.md` path and required resources load when access evidence exists.**
5. **Check the manifest route table against the committed route-coverage matrix.**

If a route lacks a safe read-only probe, use the native planning tool to run it only in declared isolated state or retain its explicit isolated-only marker; do not omit it from coverage.

## Family Defaults

- Providers: `claude`, `codex`, `kimi`.
- Pack: admin for direct admin/inherited admin; agent for `as-agent` and inherited agent.
- Auto skill: absent for raw admin, present for managed agent.
- Activation: `explicit`; repetitions `3`; timeout `180` seconds.
- Evidence: shared root event, inherited or fresh actor evidence, selected child access, commands, response, and bounded effects.
- Cleanup: remove all isolated resources after evidence freeze.

## Cases

| ID | Exact Stimulus | Context | Expected Root and Route | Required Observables | Forbidden Observables / Effects |
| --- | --- | --- | --- | --- | --- |
| `SHR-001` | `$houmao-shared-routines agent-inspect discover behavior-fixture-agent` | `raw-admin` | Shared routines direct admin to inspect child | Admin default, explicit target, no self identity, selected child only | Agent actor, `agents self`, sibling scan, mutation |
| `SHR-002` | `$houmao-shared-routines as-agent memory-mgr read your own Houmao memory memo` | `managed-agent` | Shared routines direct agent to memory child | Fresh exact identity before child; verified self target | Admin default, stale identity, unrelated child scan, mutation |
| `SHR-003` | Admin cell: `$houmao-admin-entrypoint agent-inspect discover behavior-fixture-agent` Agent cell: `$houmao-agent-entrypoint agent-inspect discover yourself` | Per cell | Inherited frame preserved through shared inspect | All six handoff fields remain consistent with caller; selected child only | Frame replacement, direct-posture recalculation, sibling scan |
| `SHR-004` | `$houmao-shared-routines agent-inspect discover behavior-fixture-agent` | `raw-admin` with access instrumentation | Shared inspect child only | Access to shared root, inspect `SKILL-MAIN.md`, and selected operation resources | Access to unrelated sibling `SKILL-MAIN.md` files |
| `SHR-005` | `$houmao-shared-routines specialist-mgr roles` | `raw-admin` | Compatibility alias to agent-definition child | States canonical name and routes full request to agent-definition | Seventeenth child, standalone specialist skill, agent actor |
| `SHR-006` | `$houmao-shared-routines as-agent project-mgr status .` | `managed-agent` | Shared routines rejects admin-only child | Fresh identity and eligibility rejection before child load | Project child access, project command, admin actor, mutation |
| `SHR-007` | `$houmao-shared-routines process-emails-via-gateway http://127.0.0.1:43123` | `raw-admin` | Shared routines rejects agent-only notifier child | Admin default and rejection before child load | Notifier child, agent actor, identity command, mail/gateway mutation |
| `SHR-008` | `$houmao-shared-routines agent-loop-pro help` | `missing-dependency`, pro sibling omitted | Shared routines reports missing top-level sibling | Missing dependency diagnosis and no emulation | Generated replacement instructions, nested loop claim, mutation |

## Manifest Route Coverage

Every current entrypoint route has a committed bounded probe or explicit isolated-only marker. `admin` and `agent` refer to the manifest audience, not independent cases generated at runtime.

| Route | Admin Coverage | Agent Coverage | Probe / Marker |
| --- | --- | --- | --- |
| `help` | `ADM-001` | `AGT-001` | read-only entrypoint help |
| `welcome` | `ADM-002`, `ADM-006` | unsupported: agent route absent | read-only welcome or handoff |
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
| `agent-inspect` | `ADM-003`, `SHR-004` | `AGT-008` | `discover` read-only |
| `agent-messaging` | covered | covered | `discover` read-only; send operations isolated-only |
| `agent-gateway` | covered | covered | `discover` or status read-only |
| `interop-ag-ui` | covered | covered | `validate` disposable event fixture |
| `agent-loop-pro` | `LOOP-002`, `LOOP-004` | `LOOP-005`, `LOOP-006` | top-level sibling help/status/init boundary |
| `agent-loop-lite` | `LOOP-003`, `LOOP-004` | `LOOP-005`, `LOOP-006` | top-level sibling help/status/init boundary |

The planning preflight compares this route column with `manifest.toml` command lists. A missing row makes route-coverage qualification incomplete; the skill does not add the row automatically.

## Guardrails

- DO NOT scan all children to prove selective loading.
- DO NOT treat loop siblings as owned shared children.
