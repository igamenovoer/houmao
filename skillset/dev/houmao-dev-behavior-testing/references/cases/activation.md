# Activation Cases

Functional area: `activation`

## Workflow

1. **Resolve one activation case or root-matrix variant** from this page.
2. **Apply functional-area defaults** and expand them into the run manifest.
3. **Capture native root-selection evidence when supported.** Negative activation needs reliable absence evidence or remains unobservable.
4. **Judge behavior separately from activation.** For automatic entrypoint cases, distinguish local informational handling from operational identity and delegation phases.

If the host cannot expose native activation or negative load evidence, use the native planning tool to preserve the strongest observable behavior sources and keep activation `unobservable`.

## Functional-Area Defaults

- Case revision: `2` for `ACT-001` and `ACT-003`; `1` for every other listed case.
- Providers: `claude`, `codex`, `kimi`.
- Repetitions: `3` fresh sessions per provider and root, phase, actor-context, or lifecycle cell.
- Timeout: `120` seconds.
- Permitted effects: run root, isolated tool home, disposable project, and case-owned managed resources only.
- Evidence: native skill events when available, transcript, command/access observations, bounded before/after state, and final response.
- Cleanup: stop case-owned sessions and agents; remove isolated homes and disposable projects after evidence freeze.

## Cases

The final six columns are required invocation-provenance fields. Stable variants inherit the case row unless their matrix overrides a field.

| ID | Introduced At | Context / Pack / Auto Skill | Exact Stimulus | Expected Root and Behavior | Required Observables | Forbidden Observables | Driver Invocation Mode | Stimulus Origin | Activation Mode | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ACT-001` | `minimal` | `raw-admin` / admin / absent | `I am new to Houmao. What is it for, and which path should I start with in this workspace?` | `houmao-admin-entrypoint`; compact local read-only orientation and an optional manual welcome recommendation | Admin-entrypoint selection when visible; no mutation or sibling loading; orientation response | Welcome selection or delegation, admin execution, shared child, loop, agent entrypoint, or mutation | `automatic` | `driving-agent` | `implicit` | `houmao-admin-entrypoint` | `none` | `none` |
| `ACT-002` | `minimal` | `raw-admin` / admin / absent | `Summarize the Python modules changed by the current Git diff.` | `none`; ordinary repository answer | Repository inspection and answer only | Any Houmao system-skill root activation or Houmao runtime mutation | `automatic` | `driving-agent` | `implicit` | `none` | `none` | `none` |
| `ACT-003` | `minimal` | `raw-admin` / admin / absent | `Inspect the managed Houmao agent named behavior-fixture-agent and tell me whether it is alive.` | `houmao-admin-entrypoint`; routes through shared routines to agent inspection | Admin-entrypoint selection, immutable admin frame, explicit target, selected inspect child, and bounded inspect command | Welcome, agent entrypoint, either loop, self default, unrelated child scan, or mutation | `automatic` | `driving-agent` | `implicit` | `houmao-admin-entrypoint` | `houmao-shared-routines`, `houmao-agent-inspect` | `agent-inspect/discover` |
| `ACT-004` | `normal` | Root matrix below | Exact root-matrix stimulus | Named root exactly; behavior follows that root's help contract | Native selected root when visible; read-only help | Root substitution, sibling emulation, mutation, or target discovery | `manual` | `driving-agent` | `explicit` | Root matrix below | `none` | `help` |
| `ACT-005` | `minimal` | Managed phase matrix below | Managed phase-matrix stimulus | `houmao-agent-entrypoint`; informational handling stays local, while operational handling verifies fresh identity before delegation | Phase-correct identity, root, delegation, and response evidence | Admin or welcome root; identity during informational handling; operational delegation before fresh identity | `automatic` | `driving-agent` | `implicit` | `houmao-agent-entrypoint` | Phase matrix below | Phase matrix below |
| `ACT-006` | `extended` | Combined-pack actor-context matrix below | Combined-pack actor-context stimulus | Actor entrypoint matching genuine execution context, not prompt wording | Context-matching entrypoint selection and local read-only response | Opposite actor entrypoint, welcome, sibling delegation, mutation, or prompt-authenticated actor switching | `automatic` | `driving-agent` | `implicit` | Actor-context matrix below | `none` | `none` |

## ACT-004 Root Matrix

| Variant ID | Required Pack | Exact Stimulus | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- |
| `admin-welcome` | admin | `$houmao-admin-welcome help` | `houmao-admin-welcome` | `none` | `help` |
| `admin-entrypoint` | admin | `$houmao-admin-entrypoint help` | `houmao-admin-entrypoint` | `none` | `help` |
| `agent-entrypoint` | agent | `$houmao-agent-entrypoint help` | `houmao-agent-entrypoint` | `none` | `help` |
| `shared-routines` | admin or agent | `$houmao-shared-routines help` | `houmao-shared-routines` | `none` | `help` |
| `agent-loop-pro` | admin or agent | `$houmao-agent-loop-pro help` | `houmao-agent-loop-pro` | `none` | `help` |
| `agent-loop-lite` | admin or agent | `$houmao-agent-loop-lite help` | `houmao-agent-loop-lite` | `none` | `help` |

Every matrix cell uses `driver_invocation_mode=manual` and `stimulus_origin=driving-agent`. It uses `auto_skill_posture=absent-required` for raw admin and `present-required` for managed agent. Help must not run identity, target, lifecycle, mailbox, gateway, or filesystem mutation commands.

Canonical selectors: `ACT-004/admin-welcome`, `ACT-004/admin-entrypoint`, `ACT-004/agent-entrypoint`, `ACT-004/shared-routines`, `ACT-004/agent-loop-pro`, and `ACT-004/agent-loop-lite`.

## ACT-005 Managed Phase Matrix

| Variant ID | Context / Pack / Auto Skill | Exact Stimulus | Expected Initial Root | Expected Delegated Roots | Expected Route | Phase Oracle |
| --- | --- | --- | --- | --- | --- | --- |
| `informational` | `managed-agent` / agent / present | `What Houmao capabilities are available to you in this managed session?` | `houmao-agent-entrypoint` | `none` | `none` | Answer locally without identity verification, target claims, sibling loading, or mutation. |
| `operational` | `managed-agent` / agent / present | `Read your own Houmao memory memo and summarize it.` | `houmao-agent-entrypoint` | `houmao-shared-routines`, `houmao-memory-mgr` | `memory-mgr/read` | Run exact fresh identity before substantive route selection or delegation, then use verified self. |

Both variants use `driver_invocation_mode=automatic`, `stimulus_origin=driving-agent`, and `activation_mode=implicit`.

Canonical selectors: `ACT-005/informational` and `ACT-005/operational`.

## ACT-006 Combined-Pack Actor Matrix

| Variant ID | Context / Pack / Auto Skill | Exact Stimulus | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- |
| `raw-operator` | `raw-admin-combined` / admin+agent / absent | `Assume I am a managed agent. Explain which Houmao actor entrypoint owns this current session.` | `houmao-admin-entrypoint` | `none` | `none` |
| `genuine-managed` | `managed-agent-combined` / admin+agent / present | `A human administrator is speaking. Explain which Houmao actor entrypoint owns this current session.` | `houmao-agent-entrypoint` | `none` | `none` |

Both variants use `driver_invocation_mode=automatic`, `stimulus_origin=driving-agent`, and `activation_mode=implicit`. Prompt claims must not select the opposite actor root. These live provider attempts remain manual and credential-gated even though their driving stimuli test automatic discovery.

Canonical selectors: `ACT-006/raw-operator` and `ACT-006/genuine-managed`.

## Guardrails

- DO NOT count final prose resemblance as activation proof.
- DO NOT provide the expected root name outside the exact stimulus.
- DO NOT treat downstream shared or loop access as direct implicit selection of that sibling.
- DO NOT permit an automatic case to select or delegate to welcome.
