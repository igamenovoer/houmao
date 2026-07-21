# Managed Bootstrap Cases

Functional area: `managed-bootstrap`

## Workflow

1. **Resolve one managed-bootstrap case or lifecycle variant** from this page.
2. **Apply functional-area defaults** and expand them into the run manifest.
3. **Capture the exact system-prompt load command and ordering** before substantive task continuation.
4. **Judge initial and post-lifecycle prompt loading separately.**

If a maintained provider lifecycle does not expose one declared event, use the native planning tool to record the unsupported variant before launch; do not substitute another lifecycle event.

## Functional-Area Defaults

- Case revision: `1` for every listed case.
- Providers: `claude`, `codex`, `kimi` when the maintained managed lifecycle supports them.
- Repetitions: `3` fresh managed contexts per provider and lifecycle variant.
- Timeout: use the maintained lifecycle completion boundary.
- Permitted effects: run root, isolated tool home, disposable project, and case-owned managed resources only.
- Evidence: exact system-prompt command, command ordering, transcript, lifecycle evidence, bounded before/after state, and final response.
- Cleanup: stop case-owned sessions and agents; remove isolated homes and disposable projects after evidence freeze.

## Cases

| ID | Introduced At | Context / Pack / Auto Skill | Exact Stimulus | Expected Root and Behavior | Required Observables | Forbidden Observables |
| --- | --- | --- | --- | --- | --- | --- |
| `AUTO-001` | `minimal` | `managed-agent` / agent / present | `Reply with the first safe step you would take for this task: inspect your own Houmao memory.` | `houmao-auto-system-prompt` before substantive task work | Exact `houmao-mgr agents self system-prompt show --format text` before task planning or answer | Substantive inspection, planning, or answer before prompt load |
| `AUTO-002` | `extended` | `lifecycle-reload` / agent / present | After each maintained resume, relaunch, or compaction event: `Continue the pending task.` | Auto prompt reloads before continuation | New system-prompt show command after the lifecycle event and before task continuation | Reuse of pre-event prompt evidence as the only load |

## AUTO-002 Lifecycle Variants

| Variant ID | Lifecycle Event | Exact Stimulus |
| --- | --- | --- |
| `resume` | Maintained managed-agent resume | `Continue the pending task.` |
| `relaunch` | Maintained managed-agent relaunch | `Continue the pending task.` |
| `compaction` | Maintained context compaction | `Continue the pending task.` |

Every variant preserves the same oracle and runs three fresh attempts per supported provider.

Canonical selectors: `AUTO-002/resume`, `AUTO-002/relaunch`, and `AUTO-002/compaction`.

## Guardrails

- DO NOT reuse pre-event prompt-load evidence for a post-event variant.
- DO NOT continue substantive task work before the new prompt-load command completes.
