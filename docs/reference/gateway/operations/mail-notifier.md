# Gateway Mail-Notifier

Mail operations select `offline` or `online` explicitly. `GET /v1/mail/status` summarizes both channels; `resolve-live` returns revisioned slots under `mailboxes.offline` and `mailboxes.online`. Every lifecycle request uses schema version 3 and includes `expected_binding_id`, including fresh send/post. Keep notifier rounds pinned to their supplied URL, channel, and binding; stop on mismatch rather than re-resolving and resending. Canonical online-first mail identity never selects delivery.

The gateway mail-notifier is a gateway-owned background polling loop that checks the agent's mailbox for open inbox work and injects notification prompts into the gateway request queue.

## What It Does

Use the mail-notifier when a live gateway should wake the agent for shared-mailbox inbox work without requiring another process to poll the mailbox. The default `any_inbox` mode wakes while any inbox mail remains unarchived. The opt-in `unread_only` mode wakes only for unread unarchived inbox mail.

The notifier is part of the live gateway process:

- it polls eligible inbox state through the configured mailbox adapter,
- it renders one gateway-owned notification prompt from a packaged template,
- it enqueues that prompt as an internal `mail_notifier_prompt` request when the gateway is ready.

The prompt is a wake-up bridge between mailbox state and the agent's next prompt round. It is not itself the mailbox processing workflow.

Notifier configuration also carries optional `appendix_text`. When non-empty, that text is appended to each rendered notifier prompt as additional runtime guidance. Use it for run-specific wake-up context such as "handle billing notices first" or "ignore FYI digests for this project"; do not use it to replace the mailbox-processing workflow itself.

Notifier configuration also carries two context policies:

- `context_error_policy` defaults to `continue_current`. With the default, recoverable degraded context remains diagnostic and the notifier does not clear context before wake-up delivery. `clear_context` is opt-in and only applies when the current degraded diagnostic is recognized for the owning CLI tool.
- `pre_notification_context_action` defaults to `none`. `compact` is an opt-in preflight that runs a supported compaction action before notification prompts only when newly eligible mail appears. In v1 this is supported for live Codex TUI gateways through `/compact`; unsupported tool/backend combinations are rejected instead of silently ignored.

## Current Polling Cycle

Each configured channel has an independent schedule and binding-scoped state. Canonical identity changes do not reset either channel. When a selected notifier is enabled, the current implementation runs this cycle:

1. Read the owner/channel/binding notifier record from gateway storage to confirm that polling is enabled and an interval is configured.
2. Wait until the next scheduled poll time on the gateway's monotonic clock.
3. Refresh current gateway status and verify that mailbox support is available from the runtime-owned manifest and mailbox binding.
4. Observe a bounded eligible metadata view outside the terminal lock. Online mail uses account-scoped SQLite checkpoints and bounded JMAP synchronization; offline mail pages its authoritative metadata index. The policy is `read_state=any`, `answered_state=any`, `archived=false` in `any_inbox` mode, or `read_state=unread`, `answered_state=any`, `archived=false` in `unread_only` mode.
5. If the observed view contains no eligible mail, record an `empty` audit row and stop this cycle. An incomplete sample does not establish an empty mailbox; `sync` status reports recovery and view completeness.
6. If eligible mail exists, compute a SHA256 digest from the sorted eligible `message_ref` values.
7. Check whether prompt enqueueing is currently blocked by gateway readiness.
8. If configured and the current eligible set contains at least one mail item that has not yet triggered compaction during its current eligibility stretch, run the pre-notification context action. For Codex TUI `compact`, the gateway sends `/compact`, waits for prompt-ready stabilization, refreshes tracked diagnostics, and adds the current eligible `message_ref` set to its remembered compaction eligibility. Metadata-window eviction, credential refresh, reconnect, or checkpoint rebase never removes remembered entries. Bounded round-robin metadata revalidation removes them only after confirmed deletion or loss of eligibility.
9. If `context_error_policy=clear_context` and the refreshed degraded diagnostic is a recognized Codex compaction diagnostic, run the existing TUI clean-context reset workflow before enqueueing the wake-up prompt.
10. If the gateway is ready, atomically commit one owner/channel/binding/cycle admission and its internal `mail_notifier_prompt` request. Only one pending wakeup per scope and one admission per interval cycle are allowed. Revalidate the origin revision and connection epoch before enqueueing and again before body dispatch. Replacement/detach cancels unstarted obsolete reminders.
11. Reschedule the next poll as `now + interval_seconds`.

Online synchronization defaults to at most five JMAP methods and ten seconds per observation cycle, with 50 metadata records and a 200-record cache cap. A new connection performs separately bounded account/discovery validation, then reuses its immutable credentials and role map. Network calls run outside terminal and SQLite commit locks. A busy body does not prevent checkpoint progress.

Online prompt handoffs and pre-notification context actions hold shared online admission until the started effect returns. Replacement waits within its retirement deadline or reports an explicit busy/uncertain result before activation. A synchronous headless handoff conservatively retains this lease through its turn. No manifest lock spans that external effect.

Online authentication or credential-file availability errors record `poll_error` while preserving the enabled setting and cadence. Restoring or refreshing the same account can recover without re-enabling the notifier. An explicit replacement uses an independent binding scope; attachment does not enable that new notifier automatically.

The digest is currently used for notifier state or audit visibility only. It is not used to suppress later prompt enqueueing for the same unchanged unread snapshot.

## Current Repeat-Notification Behavior

The current implementation may enqueue repeated notifier prompts for the same unchanged eligible inbox snapshot while those messages remain unarchived and eligible for the selected mode.

Important source-truth details:

- the notifier computes `unread_digest` from eligible `message_ref` values,
- the notifier audit trail stores that digest,
- the current enqueue path does not compare the new digest against a previously notified digest before deciding to enqueue,
- `last_notified_digest` exists in the notifier record model, but the current cycle writes it as `None` rather than using it to suppress repeated wakeups,
- pre-notification compaction bookkeeping is tracked separately from prompt-repeat behavior, so unchanged eligible mail can still trigger later wake-up prompts without triggering another `/compact`.

Practical effect:

- unchanged eligible inbox mail can wake the agent again on later notifier cycles,
- unchanged continuously eligible mail does not trigger another pre-notification compaction once the notifier has already compacted for that eligibility stretch,
- newly eligible mail added to an already-compacted eligible set may trigger one additional compaction for the expanded set,
- in `any_inbox` mode, repeated wakeups stop when the message is archived, moved out of inbox, deleted, the notifier is disabled, or the gateway stays unavailable or busy long enough that nothing can be enqueued,
- in `unread_only` mode, marking a message read also removes it from notifier eligibility, so use this mode only when that lower-noise trade-off is intended.

## Readiness-Gated Enqueueing

Eligible mail does not immediately guarantee a prompt. The notifier enqueues only when the gateway is ready to accept prompt work.

The current busy checks include:

- `request_admission = open`
- `active_execution = idle`
- `queue_depth = 0`
- prompt-readiness for the current dispatch mode

If the managed session is busy or not prompt-ready, the cycle is audited as `busy_skip` and the eligible mail remains in the inbox for a later cycle.

Recoverable degraded chat context is diagnostic, not a busy condition by itself. If the session is otherwise prompt-ready and queue admission passes, the notifier enqueues the normal current-context prompt work and does not send `/new`, `/clear`, or any other reset signal solely because degraded context is present. Clean-context notifier work is reported only when `context_error_policy=clear_context` matched a tool-owned degraded compaction diagnostic and the clean-context workflow actually completed.

> **Degraded tmux session vs. degraded chat context.** The notifier's degraded-context handling addresses recoverable chat compaction and server errors visible in the TUI. A structurally broken tmux session (missing primary pane or entire session) is a separate failure mode handled by the managed-agent recovery system. When selected-agent `agents single ... stop` or `agents single ... relaunch` targets an agent whose tmux authority is degraded or stale, the runtime probes tmux first and routes through recovery helpers rather than treating the condition as a notifier-level degraded context. See [Degraded and Stale Active Recovery](../../run-phase/degraded-stale-recovery.md).

For TUI-backed dispatch, the notifier also checks prompt-readiness reasons from the live TUI surface. For headless dispatch, it checks the active direct-turn or terminal-surface readiness state before enqueueing.

## Configuration

The mail-notifier is managed through scoped `houmao-mgr agents single ... gateway mail-notifier` or `houmao-mgr agents self gateway mail-notifier` commands:

| Command | Description |
| --- | --- |
| `status --channel <offline|online>` | Show whether notifier polling is enabled and report last-check metadata. |
| `enable --channel <offline|online> --interval-seconds N [--mode any_inbox|unread_only] [--appendix-text TEXT] [--context-error-policy continue_current|clear_context] [--pre-notification-context-action none|compact]` | Enable or reconfigure polling with interval `N` seconds, the selected mode, optional prompt appendix, and context policies. The current request model requires `N > 0`; the mode defaults to `any_inbox`, context error policy defaults to `continue_current`, and pre-notification context action defaults to `none`. |
| `disable --channel <offline|online>` | Disable polling and stop future notifier prompt enqueueing. Disabling does not clear stored `appendix_text`. |

The live gateway rereads notifier state from storage on each cycle, so enable, disable, and interval changes take effect without restarting the gateway.

Appendix update rules:

- Omitting `--appendix-text` preserves the currently stored appendix.
- Passing non-empty `--appendix-text TEXT` replaces the stored appendix.
- Passing an empty string clears the stored appendix, for example `--appendix-text ''`.

## Status Fields

`GET /v1/mail-notifier/{channel}` returns:

| Field | Meaning |
| --- | --- |
| `enabled` | Whether the notifier currently polls. |
| `interval_seconds` | Current polling interval in seconds, or `null` when disabled. |
| `mode` | Effective notifier mode, `any_inbox` or `unread_only`, including when disabled. |
| `appendix_text` | Effective prompt appendix text. Empty string means no appendix is rendered. |
| `context_error_policy` | Effective degraded-context policy, `continue_current` or `clear_context`. |
| `pre_notification_context_action` | Effective pre-notification action, `none` or `compact`. |
| `supported` | Whether the current session configuration supports mailbox-backed notifier behavior. |
| `support_error` | Why mailbox-backed notifier behavior is unsupported, when applicable. |
| `last_poll_at_utc` | Timestamp of the last completed poll attempt. |
| `last_notification_at_utc` | Timestamp of the last cycle that successfully enqueued a notifier prompt. |
| `last_error` | Most recent poll or mailbox-support error, when present. |
| `sync` | Online persisted view status: phase, view completeness, unseen backlog, incremental support, last success/error, and bounded cache count. Offline is `null`. Status reads do not contact the provider. |

## Audit Outcomes

Notifier audit rows currently use these outcomes in practice:

| Outcome | Meaning |
| --- | --- |
| `empty` | The bounded observed view contained no eligible items. Consult online `sync` status before interpreting this as an empty inbox. |
| `dedup_skip` | This interval cycle already has an admission, or a previous wakeup remains pending. This does not suppress later due reminder cycles. |
| `busy_skip` | Eligible inbox mail existed, but the gateway was busy or not prompt-ready. |
| `enqueued` | The notifier rendered the prompt and enqueued one internal request. |
| `pre_notification_context_error` | The configured pre-notification context action failed, so no notifier prompt was enqueued. |
| `context_recovery_error` | Policy-selected clean-context recovery failed, so no notifier prompt was enqueued. |
| `poll_error` | Mailbox support failed or unread polling raised an error. |

Deduplication uses the durable cycle key and pending request, never the eligible-set digest. Read and answered flags do not complete work in `any_inbox` mode; archive or another confirmed loss of inbox eligibility closes the work.

## Notification Prompt And Skill Guidance

The notifier renders its prompt from:

```text
src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md
```

That template includes:

- a concise tool-specific skill-usage block,
- the exact live gateway URL, selected channel, and expected binding ID,
- a one-line `/v1/mail/*` endpoint summary.

The prompt tells the agent to:

1. process relevant inbox mail through the shared gateway mailbox API,
2. complete that work,
3. archive only completed messages after any required reply succeeds,
4. stop after the round.

The skill-usage block is derived from the runtime-owned manifest and projected mailbox skill installation for the current tool.

When `appendix_text` is non-empty, the rendered prompt also includes:

```text
Additional runtime guidance:
<appendix_text>
```

Current source behavior:

- when the managed `agent` pack is installed, the prompt invokes `$houmao-agent-entrypoint process-emails-via-gateway <gateway-url> channel=<channel> expected_binding_id=<binding-id>`,
- the prompt requires both the installed agent entrypoint and shared-routines sibling, then leaves parent-scoped `SKILL-MAIN.md` selection to sibling routing,
- ordinary mailbox details remain available through the `agent-email-comms` child in shared routines,
- when required static skill siblings are unavailable, the prompt supplies the selected-channel API contract directly. Late binding does not require native skill hot-reload or a body restart.
- missing URL/channel/binding context or a binding mismatch ends the round. Canonical identity does not supply replacement routing.

## Lifecycle Integration

- The notifier loop starts with gateway service initialization and runs until gateway shutdown.
- When polling is disabled or unconfigured, the loop idles on a short internal check interval instead of exiting.
- On shutdown, the gateway signals the notifier thread through the shared stop event and joins it.
- The notifier depends on live gateway readiness. It does not bypass the gateway request queue or prompt-readiness checks.
- The notifier is a live gateway feature. It is not a durable mailbox backlog or reminder queue.

## HTTP Surface

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/v1/mail-notifier/{channel}` | Inspect current notifier status. |
| `PUT` | `/v1/mail-notifier/{channel}` | Enable or reconfigure polling. Body fields are `interval_seconds`, optional `mode`, optional `appendix_text`, optional `context_error_policy`, and optional `pre_notification_context_action`. Omitted `appendix_text` preserves the stored appendix; an empty string clears it. |
| `DELETE` | `/v1/mail-notifier/{channel}` | Disable polling without clearing stored appendix text. |

## See Also

- [Notifier-Prompt-Driven Loop Runtime](notifier-prompt-driven-loops.md)
- [scoped agents gateway mail-notifier](../../cli/agents-gateway.md#mail-notifier)
- [Why Prompt Admission Uses Readiness and Pending Input](../internals/prompt-admission-and-tui-observation.md)
- [Gateway Mailbox Facade](mailbox-facade.md)
- [Gateway Reminders](reminders.md)
- [Agent Gateway Reference](../index.md)

## Source References

- [`src/houmao/agents/realm_controller/gateway_service.py`](../../../../src/houmao/agents/realm_controller/gateway_service.py)
- [`src/houmao/agents/realm_controller/gateway_storage.py`](../../../../src/houmao/agents/realm_controller/gateway_storage.py)
- [`src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md`](../../../../src/houmao/agents/realm_controller/assets/system_prompts/mailbox/mail-notifier.md)
