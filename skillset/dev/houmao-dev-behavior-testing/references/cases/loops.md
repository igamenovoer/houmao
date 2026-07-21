# Agent Loop Skill Cases

Functional area: `agent-loops`

## Workflow

1. **Resolve pro or lite and actor context** from the selected case and stable variant.
2. **Use a disposable explicit loop directory** only where the case permits mutation.
3. **Observe initial actor entrypoint selection separately from explicit direct loop activation or delegated loop access.**
4. **Check actor selection, upfront planning, required-root gates, and the pro/lite boundary.**
5. **Stop at help, missing-loop-dir question, read-only status, or the bounded scaffold action declared by the case.**

If a provider cannot expose root activation, use the native planning tool to preserve downstream boundary evidence while retaining activation as unobservable.

## Functional-Area Defaults

- Case revision: `2` for `LOOP-001`; `1` for every other listed case.
- Providers: `claude`, `codex`, `kimi`.
- Repetitions: `3`; timeout `180` seconds.
- Pack: admin for raw direct calls; agent for inherited/`as-agent` calls.
- Permitted effects: none for automatic/help cases; disposable loop directory only for explicit bounded mutation cases.
- Evidence: initial root selection when available, delegated root evidence, actor/identity commands, planning event when observable, filesystem before/after, and response.
- Cleanup: remove disposable loop roots and stop case-owned sessions/agents.

## Cases

| ID | Introduced At | Exact Stimulus | Context | Expected Root and Behavior | Required Observables | Forbidden Observables / Effects | Driver Invocation Mode | Stimulus Origin | Activation Mode | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `LOOP-001` | `minimal` | `Design a multi-agent loop that has two workers review each other's output.` | `raw-admin`, admin pack | Admin entrypoint may activate, but neither pro nor lite is selected until the user distinguishes one | Admin entrypoint selection when visible; one concise pro/lite choice when routing is needed; no loop file mutation | Pro/lite selection or delegation, invented loop dir, scaffold mutation, welcome | `automatic` | `driving-agent` | `implicit` | `houmao-admin-entrypoint` | `none` | `none` |
| `LOOP-002` | `minimal` | `$houmao-agent-loop-pro init` | `raw-admin`, admin pack | Pro root; default admin; upfront plan; asks for explicit loop dir before mutation | Pro selection, admin posture, planning evidence when visible, loop-dir gate | Lite/shared-child substitution, invented path, files created | `manual` | `driving-agent` | `explicit` | `houmao-agent-loop-pro` | `none` | `init` |
| `LOOP-003` | `minimal` | `$houmao-agent-loop-lite init` | `raw-admin`, admin pack | Lite root; default admin; upfront plan; asks for explicit loop dir | Lite selection and loop-dir gate | Pro substitution, JSON schemas, Jinja2, harness, invented path, files created | `manual` | `driving-agent` | `explicit` | `houmao-agent-loop-lite` | `none` | `init` |
| `LOOP-004` | `normal` | Pro cell: `$houmao-agent-loop-pro help` Lite cell: `$houmao-agent-loop-lite help` | raw admin and managed agent cells | Named root returns help before actor verification or loop-dir gate | Read-only purpose, operations, examples, boundaries | Identity command, loop-dir question, initialization, mutation | `manual` | `driving-agent` | `explicit` | Loop matrix below | `none` | `help` |
| `LOOP-005` | `normal` | Admin cell: `$houmao-admin-entrypoint agent-loop-pro help` Agent cell: `$houmao-agent-entrypoint agent-loop-lite help` | inherited actor per cell | Named loop sibling preserves inherited actor frame | Sibling call and unchanged frame when observable | Direct actor recalculation or prompt-based replacement | `manual` | `driving-agent` | `explicit` | Actor entrypoint matrix below | Loop matrix below | `help` |
| `LOOP-006` | `extended` | Pro cell: `$houmao-agent-loop-pro as-agent status tmp/behavior-loop` Lite cell: `$houmao-agent-loop-lite as-agent status tmp/behavior-loop` | `managed-agent`, agent pack | Fresh verified-agent posture before status | Exact fresh identity command and explicit loop dir | Admin default, stale identity, mutation by status | `manual` | `driving-agent` | `explicit` | Loop matrix below | `none` | `status` |
| `LOOP-007` | `extended` | Pro cell: `$houmao-agent-loop-pro status tmp/behavior-loop` Lite cell: `$houmao-agent-loop-lite status tmp/behavior-loop` | `raw-admin`, admin pack | Direct admin posture and explicit target | No identity command; read-only status | Managed-self inference or mutation | `manual` | `driving-agent` | `explicit` | Loop matrix below | `none` | `status` |
| `LOOP-008` | `normal` | Actor and loop matrix below | Per actor cell | Matching actor entrypoint first, then the explicitly distinguished top-level loop sibling | Actor-correct initial root, immutable frame, exact loop sibling, explicit loop dir, read-only status | Direct implicit loop selection, other loop, welcome, invented target, mutation | `automatic` | `driving-agent` | `implicit` | Actor matrix below | Loop matrix below | `status` |

## Stable Matrix Variants

| Case | Variant ID | Context | Exact Stimulus | Expected Initial Root | Expected Delegated Roots |
| --- | --- | --- | --- | --- | --- |
| `LOOP-004` | `pro-admin` | raw admin | `$houmao-agent-loop-pro help` | `houmao-agent-loop-pro` | `none` |
| `LOOP-004` | `pro-agent` | managed agent | `$houmao-agent-loop-pro help` | `houmao-agent-loop-pro` | `none` |
| `LOOP-004` | `lite-admin` | raw admin | `$houmao-agent-loop-lite help` | `houmao-agent-loop-lite` | `none` |
| `LOOP-004` | `lite-agent` | managed agent | `$houmao-agent-loop-lite help` | `houmao-agent-loop-lite` | `none` |
| `LOOP-005` | `admin-pro` | inherited admin | `$houmao-admin-entrypoint agent-loop-pro help` | `houmao-admin-entrypoint` | `houmao-agent-loop-pro` |
| `LOOP-005` | `agent-lite` | inherited agent | `$houmao-agent-entrypoint agent-loop-lite help` | `houmao-agent-entrypoint` | `houmao-agent-loop-lite` |
| `LOOP-006` | `pro` | managed agent | `$houmao-agent-loop-pro as-agent status tmp/behavior-loop` | `houmao-agent-loop-pro` | `none` |
| `LOOP-006` | `lite` | managed agent | `$houmao-agent-loop-lite as-agent status tmp/behavior-loop` | `houmao-agent-loop-lite` | `none` |
| `LOOP-007` | `pro` | raw admin | `$houmao-agent-loop-pro status tmp/behavior-loop` | `houmao-agent-loop-pro` | `none` |
| `LOOP-007` | `lite` | raw admin | `$houmao-agent-loop-lite status tmp/behavior-loop` | `houmao-agent-loop-lite` | `none` |

Every existing matrix variant uses `driver_invocation_mode=manual`, `stimulus_origin=driving-agent`, and `activation_mode=explicit`.

Canonical selectors: `LOOP-004/pro-admin`, `LOOP-004/pro-agent`, `LOOP-004/lite-admin`, `LOOP-004/lite-agent`, `LOOP-005/admin-pro`, `LOOP-005/agent-lite`, `LOOP-006/pro`, `LOOP-006/lite`, `LOOP-007/pro`, and `LOOP-007/lite`.

## LOOP-008 Automatic Actor and Loop Variants

| Variant ID | Context / Pack / Auto Skill | Exact Stimulus | Expected Initial Root | Expected Delegated Roots | Identity Oracle |
| --- | --- | --- | --- | --- | --- |
| `admin-pro` | `raw-admin` / admin / absent | `Check the status of the Houmao pro agent loop at tmp/behavior-loop.` | `houmao-admin-entrypoint` | `houmao-agent-loop-pro` | Preserve admin frame; do not run self identity. |
| `agent-lite` | `managed-agent` / agent / present | `Check the status of the Houmao lite agent loop at tmp/behavior-loop.` | `houmao-agent-entrypoint` | `houmao-agent-loop-lite` | Run exact fresh self identity before loop delegation. |

Both variants use `driver_invocation_mode=automatic`, `stimulus_origin=driving-agent`, and `activation_mode=implicit`. The selected loop remains an explicit-only initial root and appears only as a delegated root.

Canonical selectors: `LOOP-008/admin-pro` and `LOOP-008/agent-lite`.

## Guardrails

- DO NOT let a generic loop request choose pro or lite on the user's behalf.
- DO NOT create a loop directory in cases that test the missing-root gate.
- DO NOT treat delegated loop access as direct implicit loop activation.
