# Generated Runtime Prompt Cases

Functional area: `generated-prompts`

## Workflow

1. **Generate or capture the prompt through the maintained Houmao surface** named by the case.
2. **Freeze the exact prompt bytes and digest** as the case stimulus; do not reconstruct text by hand.
3. **Deliver it to the declared disposable context** and capture root, route, endpoint, bounded-work, and stop evidence.
4. **Compare exact authoritative tokens and semantic behavior separately.**

If generated text differs from the committed expectation, use the native planning tool to classify catalog drift before launch; do not rewrite the frozen prompt or expected route during the attempt.

## Functional-Area Defaults

- Case revision: `1` for every listed case.
- Providers: `claude`, `codex`, `kimi` when the maintained generator supports the selected tool.
- Driver invocation: `not-applicable`; stimulus origin `generated-prompt`; activation mode `generated-prompt`.
- Repetitions: `3`; timeout `240` seconds.
- Evidence: generated prompt path and digest, native root event, exact endpoint and commands, bounded mailbox/gateway state, final response, and stop behavior.
- Permitted effects: disposable gateway/mailbox/agent resources declared by the case.
- Cleanup: stop notifier/gateway and managed agent; remove disposable mailbox, home, and project after evidence freeze.

## Cases

| ID | Introduced At | Stimulus Authority | Context / Pack / Auto Skill | Expected Root and Route | Required Observables | Forbidden Observables / Effects | Driver Invocation Mode | Stimulus Origin | Activation Mode | Expected Initial Root | Expected Delegated Roots | Expected Route |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `PRM-001` | `minimal` | Exact generated gateway notifier prompt containing the run-local endpoint and `$houmao-agent-entrypoint process-emails-via-gateway` | `managed-agent` / agent / present | Agent entrypoint to shared notifier-round child | Fresh identity, exact supplied endpoint, one bounded unread-mail round, stop after current round | Endpoint rediscovery when already supplied, proactive polling, admin route, obsolete skill path scan | `not-applicable` | `generated-prompt` | `generated-prompt` | `houmao-agent-entrypoint` | `houmao-shared-routines`, `houmao-process-emails-via-gateway` | `process-emails-via-gateway/process-round` |
| `PRM-002` | `normal` | Exact generated ordinary mailbox prompt containing `$houmao-agent-entrypoint agent-email-comms` | `managed-agent` / agent / present | Agent entrypoint to shared ordinary-mail child | Fresh identity, expected ordinary mailbox operation, manager/gateway authority | Notifier-round route, transport-owned obsolete top-level skill, admin actor | `not-applicable` | `generated-prompt` | `generated-prompt` | `houmao-agent-entrypoint` | `houmao-shared-routines`, `houmao-agent-email-comms` | generated ordinary-mail operation |
| `PRM-003` | `extended` | Exact maintained generated mailbox or notifier prompt | `missing-dependency`; omit entrypoint or shared sibling as the selected matrix cell declares | Clear missing-installation result | Missing dependency named; no obsolete path discovery | Emulated child instructions, hidden compatibility path, mailbox mutation | `not-applicable` | `generated-prompt` | `generated-prompt` | Dependency matrix below | Dependency matrix below | missing-installation result |

## PRM-003 Dependency Variants

| Variant ID | Missing Dependency | Stimulus Authority | Expected Initial Root | Expected Delegated Roots |
| --- | --- | --- | --- | --- |
| `entrypoint-missing` | Required actor entrypoint omitted | Exact maintained generated mailbox or notifier prompt | `none` | `none` |
| `shared-routines-missing` | `houmao-shared-routines` omitted | Exact maintained generated mailbox or notifier prompt | `houmao-agent-entrypoint` | `none` |

Both variants require a clear missing-installation result without emulation or mailbox mutation. Each inherits `driver_invocation_mode=not-applicable`, `stimulus_origin=generated-prompt`, and `activation_mode=generated-prompt`.

Canonical selectors: `PRM-003/entrypoint-missing` and `PRM-003/shared-routines-missing`.

## Exact-Text Boundary

Generated invocation token, route name, and supplied endpoint are exact-text assertions. Explanatory prose and visible summary are judged semantically. Capture the maintained generated prompt through its production code path; a hand-authored approximation is invalid evidence.

## Guardrails

- DO NOT report generated prompt delivery as automatic driver-origin skill discovery.
- DO NOT hand-edit generated prompt text before submission.
- DO NOT poll for another notifier round after the bounded stop condition.
