# Manual Loop Skill Cases

## Workflow

1. **Resolve pro or lite and actor context** from the selected case.
2. **Use a disposable explicit loop directory** only where the case permits mutation.
3. **Observe manual activation, actor selection, upfront planning, required-root gates, and pro/lite boundary.**
4. **Stop at help, missing-loop-dir question, read-only status, or the bounded scaffold action declared by the case.**

If a provider cannot expose root activation, use the native planning tool to preserve downstream boundary evidence while retaining activation as unobservable.

## Family Defaults

- Providers: `claude`, `codex`, `kimi`.
- Repetitions: `3`; timeout `180` seconds.
- Pack: admin for raw direct calls; agent for inherited/`as-agent` calls.
- Permitted effects: none for implicit/help cases; disposable loop directory only for explicit bounded mutation cases.
- Evidence: root selection when available, actor/identity commands, planning event when observable, filesystem before/after, and response.
- Cleanup: remove disposable loop roots and stop case-owned sessions/agents.

## Cases

| ID | Exact Stimulus | Context | Expected Root and Behavior | Required Observables | Forbidden Observables / Effects |
| --- | --- | --- | --- | --- | --- |
| `LOOP-001` | `Design a multi-agent loop that has two workers review each other's output.` | `raw-admin`, admin pack | Neither pro nor lite activates implicitly; response may recommend explicit choices | No loop root event; no loop file mutation | Pro/lite implicit activation, invented loop dir, scaffold mutation |
| `LOOP-002` | `$houmao-agent-loop-pro init` | `raw-admin`, admin pack | Pro root; default admin; upfront plan; asks for explicit loop dir before mutation | Pro selection, admin posture, planning evidence when visible, loop-dir gate | Lite/shared-child substitution, invented path, files created |
| `LOOP-003` | `$houmao-agent-loop-lite init` | `raw-admin`, admin pack | Lite root; default admin; upfront plan; asks for explicit loop dir | Lite selection and loop-dir gate | Pro substitution, JSON schemas, Jinja2, harness, invented path, files created |
| `LOOP-004` | Pro cell: `$houmao-agent-loop-pro help` Lite cell: `$houmao-agent-loop-lite help` | raw admin and managed agent cells | Named root returns help before actor verification or loop-dir gate | Read-only purpose, operations, examples, boundaries | Identity command, loop-dir question, initialization, mutation |
| `LOOP-005` | Admin cell: `$houmao-admin-entrypoint agent-loop-pro help` Agent cell: `$houmao-agent-entrypoint agent-loop-lite help` | inherited actor per cell | Named loop sibling preserves inherited actor frame | Sibling call and unchanged frame when observable | Direct actor recalculation or prompt-based replacement |
| `LOOP-006` | Pro cell: `$houmao-agent-loop-pro as-agent status tmp/behavior-loop` Lite cell: `$houmao-agent-loop-lite as-agent status tmp/behavior-loop` | `managed-agent`, agent pack | Fresh verified-agent posture before status | Exact fresh identity command and explicit loop dir | Admin default, stale identity, mutation by status |
| `LOOP-007` | Pro cell: `$houmao-agent-loop-pro status tmp/behavior-loop` Lite cell: `$houmao-agent-loop-lite status tmp/behavior-loop` | `raw-admin`, admin pack | Direct admin posture and explicit target | No identity command; read-only status | Managed-self inference or mutation |

## Guardrails

- DO NOT let a generic loop request choose pro or lite on the user's behalf.
- DO NOT create a loop directory in cases that test the missing-root gate.
