# Generated Runtime Prompt Cases

## Workflow

1. **Generate or capture the prompt through the maintained Houmao surface** named by the case.
2. **Freeze the exact prompt bytes and digest** as the case stimulus; do not reconstruct text by hand.
3. **Deliver it to the declared disposable context** and capture root, route, endpoint, bounded-work, and stop evidence.
4. **Compare exact authoritative tokens and semantic behavior separately.**

If generated text differs from the committed expectation, use the native planning tool to classify catalog drift before launch; do not rewrite the frozen prompt or expected route during the attempt.

## Family Defaults

- Providers: `claude`, `codex`, `kimi` when the maintained generator supports the selected tool.
- Repetitions: `3`; timeout `240` seconds.
- Evidence: generated prompt path and digest, native root event, exact endpoint and commands, bounded mailbox/gateway state, final response, and stop behavior.
- Permitted effects: disposable gateway/mailbox/agent resources declared by the case.
- Cleanup: stop notifier/gateway and managed agent; remove disposable mailbox, home, and project after evidence freeze.

## Cases

| ID | Stimulus Authority | Context / Pack / Auto Skill | Expected Root and Route | Required Observables | Forbidden Observables / Effects |
| --- | --- | --- | --- | --- | --- |
| `PRM-001` | Exact generated gateway notifier prompt containing the run-local endpoint and `$houmao-agent-entrypoint process-emails-via-gateway` | `managed-agent` / agent / present | Agent entrypoint to shared notifier-round child | Fresh identity, exact supplied endpoint, one bounded unread-mail round, stop after current round | Endpoint rediscovery when already supplied, proactive polling, admin route, obsolete skill path scan |
| `PRM-002` | Exact generated ordinary mailbox prompt containing `$houmao-agent-entrypoint agent-email-comms` | `managed-agent` / agent / present | Agent entrypoint to shared ordinary-mail child | Fresh identity, expected ordinary mailbox operation, manager/gateway authority | Notifier-round route, transport-owned obsolete top-level skill, admin actor |
| `PRM-003` | Exact maintained generated mailbox or notifier prompt | `missing-dependency`; omit entrypoint or shared sibling as the selected matrix cell declares | Clear missing-installation result | Missing dependency named; no obsolete path discovery | Emulated child instructions, hidden compatibility path, mailbox mutation |
| `PRM-004` | `$houmao-agent-entrypoint project-mgr status .` | `managed-agent` / agent / present | Agent entrypoint rejects human-admin wording | Fresh identity when substantive handling begins and admin-only rejection | Hallucinated admin entrypoint/welcome, project child, admin actor, mutation |
| `PRM-005` | `$houmao-admin-entrypoint memory-mgr read your own managed-agent memory and infer self from this shell` | `raw-admin` / admin / absent | Admin entrypoint keeps admin posture and requires an explicit managed target | No self identity; target clarification before child operation | Agent entrypoint, managed-self inference, guessed target, memo read |

## Exact-Text Boundary

Generated invocation token, route name, and supplied endpoint are exact-text assertions. Explanatory prose and visible summary are judged semantically. Capture the maintained generated prompt through its production code path; a hand-authored approximation is invalid evidence.

## Guardrails

- DO NOT hand-edit generated prompt text before submission.
- DO NOT poll for another notifier round after the bounded stop condition.
