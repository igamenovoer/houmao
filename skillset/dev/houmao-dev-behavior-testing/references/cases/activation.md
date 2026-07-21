# Activation Cases

Functional area: `activation`

## Workflow

1. **Resolve one activation case or root-matrix variant** from this page.
2. **Apply functional-area defaults** and expand them into the run manifest.
3. **Capture native root-selection evidence when supported.** Negative activation needs reliable absence evidence or remains unobservable.
4. **Judge behavior separately from activation.**

If the host cannot expose native activation or negative load evidence, use the native planning tool to preserve the strongest observable behavior sources and keep activation `unobservable`.

## Functional-Area Defaults

- Case revision: `1` for every listed case.
- Providers: `claude`, `codex`, `kimi`.
- Repetitions: `3` fresh sessions per provider and root or lifecycle cell.
- Timeout: `120` seconds.
- Permitted effects: run root, isolated tool home, disposable project, and case-owned managed resources only.
- Evidence: native skill events when available, transcript, command/access observations, bounded before/after state, and final response.
- Cleanup: stop case-owned sessions and agents; remove isolated homes and disposable projects after evidence freeze.

## Cases

| ID | Introduced At | Context / Pack / Auto Skill | Exact Stimulus | Expected Root and Behavior | Required Observables | Forbidden Observables |
| --- | --- | --- | --- | --- | --- | --- |
| `ACT-001` | `minimal` | `raw-admin` / admin / absent | `I am new to Houmao. What is it for, and which path should I start with in this workspace?` | `houmao-admin-welcome`; compact read-only orientation and a state-appropriate next choice | Welcome selection when visible; no mutation; orientation response | Admin execution, shared child, loop, agent entrypoint, or mutation |
| `ACT-002` | `minimal` | `raw-admin` / admin / absent | `Summarize the Python modules changed by the current Git diff.` | `none`; ordinary repository answer | Repository inspection and answer only | Any Houmao system-skill root activation or Houmao runtime mutation |
| `ACT-003` | `normal` | `raw-admin` / admin / absent | `Inspect the managed Houmao agent named behavior-fixture-agent and tell me whether it is alive.` | `none`; may recommend the explicit admin-entrypoint invocation but must not claim an explicit-only root ran | No explicit-only root event; no runtime command unless the user explicitly follows up | Admin entrypoint, shared routines, either loop, or agent entrypoint activating implicitly |
| `ACT-004` | `normal` | Root matrix below | Exact root-matrix stimulus | Named root exactly; behavior follows that root's help contract | Native selected root when visible; read-only help | Root substitution, sibling emulation, mutation, or target discovery |

## ACT-004 Root Matrix

| Variant ID | Required Pack | Exact Stimulus | Expected Root |
| --- | --- | --- | --- |
| `admin-welcome` | admin | `$houmao-admin-welcome help` | `houmao-admin-welcome` |
| `admin-entrypoint` | admin | `$houmao-admin-entrypoint help` | `houmao-admin-entrypoint` |
| `agent-entrypoint` | agent | `$houmao-agent-entrypoint help` | `houmao-agent-entrypoint` |
| `shared-routines` | admin or agent | `$houmao-shared-routines help` | `houmao-shared-routines` |
| `agent-loop-pro` | admin or agent | `$houmao-agent-loop-pro help` | `houmao-agent-loop-pro` |
| `agent-loop-lite` | admin or agent | `$houmao-agent-loop-lite help` | `houmao-agent-loop-lite` |

Every matrix cell uses `auto_skill_posture=absent-required` for raw admin and `present-required` for managed agent. Help must not run identity, target, lifecycle, mailbox, gateway, or filesystem mutation commands.

Canonical selectors: `ACT-004/admin-welcome`, `ACT-004/admin-entrypoint`, `ACT-004/agent-entrypoint`, `ACT-004/shared-routines`, `ACT-004/agent-loop-pro`, and `ACT-004/agent-loop-lite`.

## Guardrails

- DO NOT count final prose resemblance as activation proof.
- DO NOT provide the expected root name outside the exact stimulus.
