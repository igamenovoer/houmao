---
metadata:
  skill_invocation_notation: >
    Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
    SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
    accepted only as legacy input when SKILL-MAIN.md is absent.
    Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
    `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
    `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
    subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
    by parent subcommand parent. Intermediate subcommands act as object generators.
    Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Shared Loop Ledger, Resend Discipline, Supervision, and `houmao-cccc` Options

Both `pairwise-edge-loop` and `relay-loop` share the same mutable ledger separation, inspect-before-resend protocol, single-reminder supervision model, and channel options.

## 1. Mutable Loop Ledger vs Managed Memory

Keep mutable coordination counters and seen-ID deduplication outside `houmao-memo.md` and `pages/` (use mailbox state, reminder state, runtime variables, or an operator-designated work artifact file; write optional human-readable summaries under `$HOUMAO_AGENT_PAGES_DIR/{edge-loops,relay-loops}/` only when requested).

| Ledger Field | Purpose |
| --- | --- |
| `edge_loop_id` or `loop_id` + `handoff_id` | Stable correlation key reused across every resend of the same round or hop; receivers persist seen IDs to deduplicate repeated deliveries without re-running work. |
| `role` & peer endpoints | `driver`/`worker` (`peer_agent`) or `loop origin`/`ingress`/`relay`/`egress` (`upstream_agent`, `downstream_agent`). |
| `phase` & `attempt_count` | Current state (`sent`, `working`, `result_sent`, `completed`) and retry count. |
| `sent_at` & `next_review_at` | Timestamp sent and next supervisor review time. |
| `receipt_due_at`, `result_due_at`, `result_ack_due_at` | Distinct lateness deadlines for receipt, final result, and result acknowledgement (derived from user SLA/urgency; ask with `Required`/`Optional` labels when materially unclear rather than guessing). |
| `max_attempts` or `give_up_at` | Escalation/stop ceiling. |
| `last_receipt_ref`, `last_result_ref`, `last_result_ack_ref` | Opaque mail/delivery references confirming each transition. |

## 2. Inspect-Before-Resend Rule

When a supervisor wakeup reviews due rows:

1. **Check mailbox (or delivery receipts) first** via `houmao-shared-routines->houmao-agent-email-comms` and advance any rows with matching receipts, results, or acks.
2. **Peek the downstream agent read-only** via `houmao-shared-routines->houmao-agent-inspect` when a due signal is still missing; if the downstream agent is actively working on that exact ID, advance `next_review_at` and do **not** resend.
3. **Probe narrowly only as a last resort** via `houmao-shared-routines->houmao-agent-messaging` when read-only inspection is unavailable or inconclusive.
4. **Resend with the identical `edge_loop_id` / `handoff_id`** only when the signal is overdue and the downstream agent cannot be confirmed as owning the work, then end the turn without waiting in chat.

## 3. Single Supervisor Reminder + Optional Self-Mail Checkpoint

- **One repeating supervisor reminder per agent**: configure one `repeat` reminder via `houmao-shared-routines->houmao-agent-gateway` (`[edge-supervisor]` or `[relay-supervisor]`) to review the entire active ledger in one bounded pass. Never create one live reminder per active row (the gateway dispatches one reminder at a time, so per-row reminders block one another).
- **Optional self-mail checkpoint (`[edge-backlog]` / `[relay-backlog]`)**: at most one idempotent unarchived self-mail pointer back to the active ledger when restart backlog anchoring is desired; archive/delete it as soon as the ledger empties so `mail-notifier` stops waking the agent.

## 4. Handoff Channel Options: `request`, `prompt`, Mail, and `houmao-cccc`

| Channel | Command / Surface | When to Prefer |
| --- | --- | --- |
| Attributed work request | `houmao-mgr agents single ... request --text <task>` | Preferred peer-to-peer handoff under default `agent-requester` policy (automatically signed by current managed session when `--source-agent-id` and `--unsigned` are omitted). |
| Direct queued prompt | `houmao-mgr agents single ... prompt` | Operator-grade turn injection when caller holds `agent-operator` authority and wants `ready-only` / `if-no-pending` / `always` gateway prompt admission. |
| Houmao mailbox | `houmao-mgr agents self mail send\|reply` (`/v1/mail/{channel}/*`) | Durable receipt, final-result, and ack envelopes (`schema_version: 3`, pinned `expected_binding_id`). |
| `houmao-cccc` group chat / queue | `houmao-cccc chat send\|reply\|pull\|deliveries` (`/v1/plugins/{instance}/*`) | Shared CCCC group coordination using `--connection-token` (from `houmao-cccc members`), idempotent `--operation-id`, push gateway delivery (`--handle`) or direct Actor profile queue polling (`--direct-profile ... chat pull` -> `--event-ref`), and explicit delivery receipts (`chat deliveries`). Keep `houmao-cccc` group chat distinct from native Houmao `prompt` and `/v1/mail/*`. |
