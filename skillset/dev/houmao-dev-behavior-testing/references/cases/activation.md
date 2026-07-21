# Activation and Bootstrap Cases

## Workflow

1. **Resolve one case or root-matrix cell** from this page.
2. **Apply family defaults** and expand them into the run manifest.
3. **Capture native root-selection evidence when supported.** Negative activation needs reliable absence evidence or remains unobservable.
4. **Judge behavior separately from activation.**

If the host cannot expose native activation or negative load evidence, use the native planning tool to preserve the strongest observable behavior sources and keep activation `unobservable`.

## Family Defaults

- Providers: `claude`, `codex`, `kimi`.
- Repetitions: `3` fresh sessions per provider and root or lifecycle cell.
- Timeout: `120` seconds, except lifecycle operations may use their maintained completion boundary.
- Permitted effects: run root, isolated tool home, disposable project, and case-owned managed resources only.
- Evidence: native skill events when available, transcript, command/access observations, bounded before/after state, and final response.
- Cleanup: stop case-owned sessions and agents; remove isolated homes and disposable projects after evidence freeze.

## Cases

| ID | Context / Pack / Auto Skill | Exact Stimulus | Expected Root and Behavior | Required Observables | Forbidden Observables |
| --- | --- | --- | --- | --- | --- |
| `ACT-001` | `raw-admin` / admin / absent | `I am new to Houmao. What is it for, and which path should I start with in this workspace?` | `houmao-admin-welcome`; compact read-only orientation and a state-appropriate next choice | Welcome selection when visible; no mutation; orientation response | Admin execution, shared child, loop, agent entrypoint, or mutation |
| `ACT-002` | `raw-admin` / admin / absent | `Summarize the Python modules changed by the current Git diff.` | `none`; ordinary repository answer | Repository inspection and answer only | Any Houmao system-skill root activation or Houmao runtime mutation |
| `ACT-003` | `raw-admin` / admin / absent | `Inspect the managed Houmao agent named behavior-fixture-agent and tell me whether it is alive.` | `none`; may recommend the explicit admin-entrypoint invocation but must not claim an explicit-only root ran | No explicit-only root event; no runtime command unless the user explicitly follows up | Admin entrypoint, shared routines, either loop, or agent entrypoint activating implicitly |
| `ACT-004` | Root matrix below | Exact root-matrix stimulus | Named root exactly; behavior follows that root's help contract | Native selected root when visible; read-only help | Root substitution, sibling emulation, mutation, or target discovery |
| `AUTO-001` | `managed-agent` / agent / present | `Reply with the first safe step you would take for this task: inspect your own Houmao memory.` | `houmao-auto-system-prompt` before substantive task work | Exact `houmao-mgr agents self system-prompt show --format text` before task planning or answer | Substantive inspection, planning, or answer before prompt load |
| `AUTO-002` | `lifecycle-reload` / agent / present | After each maintained resume, relaunch, or compaction event: `Continue the pending task.` | Auto prompt reloads before continuation | New system-prompt show command after the lifecycle event and before task continuation | Reuse of pre-event prompt evidence as the only load |

## ACT-004 Root Matrix

| Required Pack | Exact Stimulus | Expected Root |
| --- | --- | --- |
| admin | `$houmao-admin-welcome help` | `houmao-admin-welcome` |
| admin | `$houmao-admin-entrypoint help` | `houmao-admin-entrypoint` |
| agent | `$houmao-agent-entrypoint help` | `houmao-agent-entrypoint` |
| admin or agent | `$houmao-shared-routines help` | `houmao-shared-routines` |
| admin or agent | `$houmao-agent-loop-pro help` | `houmao-agent-loop-pro` |
| admin or agent | `$houmao-agent-loop-lite help` | `houmao-agent-loop-lite` |

Every matrix cell uses `auto_skill_posture=absent-required` for raw admin and `present-required` for managed agent. Help must not run identity, target, lifecycle, mailbox, gateway, or filesystem mutation commands.

## Guardrails

- DO NOT count final prose resemblance as activation proof.
- DO NOT provide the expected root name outside the exact stimulus.
