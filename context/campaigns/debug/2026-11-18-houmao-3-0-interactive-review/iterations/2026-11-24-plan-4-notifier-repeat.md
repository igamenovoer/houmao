# Iteration Plan 4: Mail-Notifier Repeat While Unarchived

Status: completed on `3.0.0rc6+g151d0891` using the R13 DSH/Kimi pair on the shared `houmao-default` server. N1 `any_inbox` repeated while the message stayed read and unarchived, N2 archive stopped the repeats, and N3 `unread_only` stayed silent. Date: 2026-11-24. Campaign: [debug-intent.md](../debug-intent.md). Question owner: [KQ-4](../key-questions/KQ-4-local-mailbox-and-notifier.md). Model lane: self-hosted `Qwen/Qwen3.8-27B-FP8` at `http://127.0.0.1:14888/v1`.

## Question

In `any_inbox` mode, does the gateway mail-notifier enqueue a new wake-up on later poll cycles while an inbox message remains unarchived, including after the message has been read? Does archiving stop the repeats? Does `unread_only` remain silent for a read-but-unarchived message, as the documented control?

## Frozen Workload

- `houmao-mgr 3.0.0rc6+g151d0891`
- R13 DSH `dsh-mailer-r13` (`b3b721ef-c73e-454e-9ce8-932765ede74e`) and Kimi `kimi-mailer-r13` (`984c48fd-3242-4dea-98f3-fbd858316183`)
- Shared `houmao-default` tmux socket `/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/default.sock`
- Shared roots under `tmp/houmao-30-iter3-mailbox-r13/`
- Offline filesystem mailbox; both notifiers currently enabled at `20s`

## Predeclared Arms

| Arm | Surface | Required live evidence |
| --- | --- | --- |
| N1 | `any_inbox` repeat | A message remains unarchived after a read; `last_notification_at` advances on at least two later poll cycles, and the target receives more than one wake-up for the same message snapshot |
| N2 | Archive stop | After the message is archived, `last_notification_at` stops advancing across at least two full intervals |
| N3 | `unread_only` control | With the same read-but-unarchived message, `unread_only` does not advance `last_notification_at`; the message remains eligible only after it is marked unread again |

## Gates

- **G1 — Baseline**: Recipient inbox is empty, notifier is enabled, gateway is healthy, and the selected mode is visible in `mail-notifier status`.
- **G2 — Repeat**: The sent message is read but not archived; the recipient's `last_notification_at` advances at least twice while the message remains unarchived.
- **G3 — Stop**: Archive the message; no later notification timestamp advances across two intervals.
- **G4 — Control**: Switch to `unread_only` with a read-but-unarchived message; no notification fires until the message is marked unread.

## Command Contract

Set DSH to `any_inbox` with a short interval and explicit non-archive guidance:

```bash
houmao-mgr --print-json agents single --agent-id \
  b3b721ef-c73e-454e-9ce8-932765ede74e gateway mail-notifier enable \
  --channel offline --interval-seconds 20 --mode any_inbox \
  --appendix-text 'Notifier repeat test: read the mail but do not archive it; reply READ-NOT-ARCHIVED and stop.'
```

Send one test mail from Kimi's binding:

```bash
houmao-mgr --print-json agents single --agent-id \
  984c48fd-3242-4dea-98f3-fbd858316183 mail send \
  --channel offline --expected-binding-id reg-c5af2391e9834f43a35547fb1f793def \
  --to dsh-mailer-r13@houmao.localhost \
  --subject 'Notifier repeat test' \
  --body-content 'Read this message and reply READ-NOT-ARCHIVED. Do not archive it; leave it unarchived for the repeat test.'
```

Observe:

```bash
houmao-mgr --print-json agents single --agent-id <dsh-id> gateway mail-notifier status --channel offline
houmao-mgr --print-json agents single --agent-id <dsh-id> state
houmao-mgr --print-json agents single --agent-id <dsh-id> mail list --channel offline \
  --expected-binding-id reg-1d7b07a257f04f54b3f180085762f148 \
  --box inbox --read-state any --not-archived
```

If the agent archives the message before repeats are observed, restore eligibility with `mail mark --unarchived --read` and record that as a manual eligibility reset. Archive at the end and verify the timestamps stop. Restore the notifier to `unread_only` after G3.

## Evidence

Record the notifier status before and after each phase, `last_notification_at` timestamps, DSH turn starts and outcomes, the message read/archived flags, and any manual eligibility reset. Keep the session log under `logs/2026-11-24-iter3-mail-r14-notifier-repeat.md`.

## Result

N1, N2, and N3 passed. `any_inbox` advanced `last_notification_at` at `06:49:33Z`, `06:49:53Z`, and `06:50:54Z` while the message stayed read and unarchived. Archiving it stopped the advances across more than two intervals. `unread_only` did not notify for the same read-but-unarchived message. DSH replied once per wake-up, producing five test replies that were archived as cleanup. See [the R14 log](../logs/2026-11-24-iter3-mail-r14-notifier-repeat.md).

## Deferred Scope

Stalwart online mail, JMAP sync, CCCC, execution-owner switching, and the DeepSeek lane remain deferred. This iteration covers only the offline filesystem notifier repeat behavior.
