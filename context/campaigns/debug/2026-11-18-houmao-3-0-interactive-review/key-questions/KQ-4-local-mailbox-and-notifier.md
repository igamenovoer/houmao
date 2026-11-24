# KQ-4: Two-Agent Local Filesystem Mail and Notifier

Date: 2026-11-20. Updated: 2026-11-24. Status: answered for the offline filesystem lane by R13 and R14; M4 teardown pending. This file covers only the offline filesystem transport and its gateway notifier. Stalwart online mail and `houmao-cccc` remain deferred.

## Question

Can a DSH Web agent and a Kimi Code Web agent, sharing one offline filesystem registry and mailbox root, exchange mail in both directions and wake each other through the live gateway mail-notifier without body restart, duplicate delivery, or replay?

## Critical Propositions

### KQ-4.1: Shared Offline Authority

Both agents resolve distinct addresses from the same registry and mailbox root. Each launch records an active offline binding, and neither agent can claim the other's address.

- **Test criteria**: Shared registry initialization, two successful launch-time filesystem bindings, distinct addresses, and an occupied-address conflict check.

### KQ-4.2: Channel-Scoped Delivery

A sender's `offline` send appears in the recipient's inbox with the correct sender, subject, body, and binding-scoped message reference. The recipient's binding ID is required for every lifecycle request.

- **Test criteria**: Send, list, peek, read, reply, and archive through the sender and recipient scopes; a stale or wrong binding ID fails explicitly.

### KQ-4.3: Notifier Wake-Up

The recipient's enabled notifier observes eligible unread inbox mail and enqueues one wake-up prompt while the target is idle. A busy target records `busy_skip` and does not lose or duplicate the message. Disabling the notifier stops future wake-ups without clearing mail.

- **Test criteria**: Notifier `supported: true`, an `enqueued` audit row, one native turn per eligible message, `busy_skip` under load, and no wake-up after disable.

### KQ-4.4: Round Completion and Clean Teardown

The receiver replies and archives the original message; the sender receives the reply and archives it. Both agents stop cleanly without leaving an owned gateway, host, notifier, or tmux session.

- **Test criteria**: Reply ancestry, archive removing eligibility, both directions completed, and G4 teardown evidence.

## Answer

Answered for the local filesystem lane; final teardown pending. On 2026-11-20, a DSH Web agent and a Kimi Web agent shared one offline filesystem registry and mailbox root, held distinct addresses, and exchanged mail in both directions. Each side's gateway mail-notifier enqueued exactly one completed `mail_notifier_prompt` for the eligible message, and each native turn read, replied, and archived through the direct `/v1/mail/offline/*` API. The notifier disabled cleanly and produced no later wake-up.

Two caveats remain from the first run. The test role replied to every message, so the exchange formed a repeating reply chain; both notifiers were disabled before the next wake-up. This is a role-design issue, not a notifier failure. The fixture also set `system_skills.mode: none`, so the agents lacked the managed mailbox skill pack and guessed the `reply` and `archive` field names before succeeding. Busy-skip and final teardown were unrun at that point.

A clean rerun on 2026-11-20 used the updated fixture default and installed the complete `agent` pack in both runtime homes. The terminal `Re:` stop rule ended the exchange after one reply. Kimi used `houmao-mgr agents self mail` and completed the round, but `houmao-mgr agents self identity` failed first with `Current-session attach is unavailable for local tmux-backed control because neither HOUMAO_AGENT_DEF_DIR nor shared-registry runtime.agent_def_dir is available`, costing about three minutes of source and tmux investigation. DSH manually exported the session environment and completed the terminal round without replying. Both inboxes ended empty, and `busy_skip` was observed on both sides while the targets were active. See the [system-skill rerun](../logs/2026-11-20-iter3-two-agent-mail-r2-system-skills.md).

A third run on `houmao-mgr 3.0.0rc5+local.f7f4245.dirty` (commit `f7f42458`) verified the managed-self fix. `agents self identity` returned the managed identity JSON for both agents with exit `0`; the Kimi turn completed in about 43 seconds instead of three minutes. Both inboxes ended empty, both gateways recorded one completed notifier request, and the only remaining error was a minor `mail archive --box` option mismatch that the agent corrected. See the [managed-self fix rerun](../logs/2026-11-20-iter3-two-agent-mail-r3-self-identity-fix.md).

A fourth run on 2026-11-23 used `houmao-mgr 3.0.0rc5+local.0d642af` and host Kimi `2.7.2`. The manifest records `supported_versions: ">=2.6.0"`, live-verifying the Kimi Web version-floor fix from #90. Both managed-self checks and the complete mail round passed without agent-side command errors; the prior `archive --box` mistake did not recur. Kimi produced one `busy_skip` while active, each gateway completed exactly one notifier request, later polls stayed empty, and the `Re:` stop rule prevented a loop. The first launch required an explicit `mailbox init`, which was a test-setup omission and was corrected before launch. R3 teardown completed before R4; R4 remains running for inspection, so its teardown is pending. See the [version-floor rerun](../logs/2026-11-23-iter3-two-agent-mail-r4-version-floor.md).

A fifth run on 2026-11-24 used `houmao-mgr 3.0.0rc6+g151d0891` with both agents on the shared `houmao-default` tmux server. Cross-agent `mail resolve-live` succeeded, and the full round completed with exactly one message in each direction. Kimi's first `mail send` returned the compact write receipt (`status: verified`, `authoritative: true`, top-level `message_ref`); Kimi confirmed the stored message with a read-only peek and did not resend. DSH's notifier woke DSH once, DSH replied `MAIL-OK`, Kimi's notifier woke once, and Kimi archived the reply. Both inboxes ended empty, with one archived message and one sent message on each side. No duplicate delivery occurred. The same run also exercised operator-directed follow-up: Kimi delegated an S2 paper search, persistent upstream HTTP 429s blocked it, the operator redirected DSH to the Tavily CLI, and DSH replied with a four-paper report that Kimi archived. A reply-to-self routing wrinkle during the amendment was detected and corrected by the agent. R13 agents remain running for inspection, so M4 teardown is still pending. See the [compact-receipt rerun](../logs/2026-11-24-iter3-mail-r13-compact-receipts.md).

R14 on 2026-11-24 targeted the documented repeat behavior. In `any_inbox`, DSH's `last_notification_at` advanced at `06:49:33Z`, `06:49:53Z`, and `06:50:54Z` while the same message stayed read and unarchived; DSH replied once per wake-up and left it unarchived. Archiving it stopped the advances across more than two intervals. With `unread_only`, the same read-but-unarchived message did not notify. The repeated wake-ups work as designed; the agent's one-reply-per-reminder behavior produced five test replies that were archived as cleanup. See the [notifier repeat run](../logs/2026-11-24-iter3-mail-r14-notifier-repeat.md).

## Scope

This question covers the local filesystem mailbox transport, its two-sided mail lifecycle, and the gateway mail-notifier for DSH Web and Kimi Web. It does not cover Stalwart online mail, JMAP synchronization, CCCC chat or deferred Mail, execution-owner switching, or the DeepSeek lane.
