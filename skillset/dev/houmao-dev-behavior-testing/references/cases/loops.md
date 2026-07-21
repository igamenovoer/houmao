# Manual Loop Skill Cases

Functional area: `agent-loops`

## Workflow

1. **Resolve pro or lite and actor context** from the selected case and stable variant.
2. **Use a disposable explicit loop directory** only where the case permits mutation.
3. **Observe manual activation, actor selection, upfront planning, required-root gates, and pro/lite boundary.**
4. **Stop at help, missing-loop-dir question, read-only status, or the bounded scaffold action declared by the case.**

If a provider cannot expose root activation, use the native planning tool to preserve downstream boundary evidence while retaining activation as unobservable.

## Functional-Area Defaults

- Case revision: `1` for every listed case.
- Providers: `claude`, `codex`, `kimi`.
- Repetitions: `3`; timeout `180` seconds.
- Pack: admin for raw direct calls; agent for inherited/`as-agent` calls.
- Permitted effects: none for implicit/help cases; disposable loop directory only for explicit bounded mutation cases.
- Evidence: root selection when available, actor/identity commands, planning event when observable, filesystem before/after, and response.
- Cleanup: remove disposable loop roots and stop case-owned sessions/agents.

## Cases

| ID | Introduced At | Exact Stimulus | Context | Expected Root and Behavior | Required Observables | Forbidden Observables / Effects |
| --- | --- | --- | --- | --- | --- | --- |
| `LOOP-001` | `minimal` | `Design a multi-agent loop that has two workers review each other's output.` | `raw-admin`, admin pack | Neither pro nor lite activates implicitly; response may recommend explicit choices | No loop root event; no loop file mutation | Pro/lite implicit activation, invented loop dir, scaffold mutation |
| `LOOP-002` | `minimal` | `$houmao-agent-loop-pro init` | `raw-admin`, admin pack | Pro root; default admin; upfront plan; asks for explicit loop dir before mutation | Pro selection, admin posture, planning evidence when visible, loop-dir gate | Lite/shared-child substitution, invented path, files created |
| `LOOP-003` | `minimal` | `$houmao-agent-loop-lite init` | `raw-admin`, admin pack | Lite root; default admin; upfront plan; asks for explicit loop dir | Lite selection and loop-dir gate | Pro substitution, JSON schemas, Jinja2, harness, invented path, files created |
| `LOOP-004` | `normal` | Pro cell: `$houmao-agent-loop-pro help` Lite cell: `$houmao-agent-loop-lite help` | raw admin and managed agent cells | Named root returns help before actor verification or loop-dir gate | Read-only purpose, operations, examples, boundaries | Identity command, loop-dir question, initialization, mutation |
| `LOOP-005` | `normal` | Admin cell: `$houmao-admin-entrypoint agent-loop-pro help` Agent cell: `$houmao-agent-entrypoint agent-loop-lite help` | inherited actor per cell | Named loop sibling preserves inherited actor frame | Sibling call and unchanged frame when observable | Direct actor recalculation or prompt-based replacement |
| `LOOP-006` | `extended` | Pro cell: `$houmao-agent-loop-pro as-agent status tmp/behavior-loop` Lite cell: `$houmao-agent-loop-lite as-agent status tmp/behavior-loop` | `managed-agent`, agent pack | Fresh verified-agent posture before status | Exact fresh identity command and explicit loop dir | Admin default, stale identity, mutation by status |
| `LOOP-007` | `extended` | Pro cell: `$houmao-agent-loop-pro status tmp/behavior-loop` Lite cell: `$houmao-agent-loop-lite status tmp/behavior-loop` | `raw-admin`, admin pack | Direct admin posture and explicit target | No identity command; read-only status | Managed-self inference or mutation |

## Stable Matrix Variants

| Case | Variant ID | Context | Exact Stimulus |
| --- | --- | --- | --- |
| `LOOP-004` | `pro-admin` | raw admin | `$houmao-agent-loop-pro help` |
| `LOOP-004` | `pro-agent` | managed agent | `$houmao-agent-loop-pro help` |
| `LOOP-004` | `lite-admin` | raw admin | `$houmao-agent-loop-lite help` |
| `LOOP-004` | `lite-agent` | managed agent | `$houmao-agent-loop-lite help` |
| `LOOP-005` | `admin-pro` | inherited admin | `$houmao-admin-entrypoint agent-loop-pro help` |
| `LOOP-005` | `agent-lite` | inherited agent | `$houmao-agent-entrypoint agent-loop-lite help` |
| `LOOP-006` | `pro` | managed agent | `$houmao-agent-loop-pro as-agent status tmp/behavior-loop` |
| `LOOP-006` | `lite` | managed agent | `$houmao-agent-loop-lite as-agent status tmp/behavior-loop` |
| `LOOP-007` | `pro` | raw admin | `$houmao-agent-loop-pro status tmp/behavior-loop` |
| `LOOP-007` | `lite` | raw admin | `$houmao-agent-loop-lite status tmp/behavior-loop` |

Canonical selectors: `LOOP-004/pro-admin`, `LOOP-004/pro-agent`, `LOOP-004/lite-admin`, `LOOP-004/lite-agent`, `LOOP-005/admin-pro`, `LOOP-005/agent-lite`, `LOOP-006/pro`, `LOOP-006/lite`, `LOOP-007/pro`, and `LOOP-007/lite`.

## Guardrails

- DO NOT let a generic loop request choose pro or lite on the user's behalf.
- DO NOT create a loop directory in cases that test the missing-root gate.
