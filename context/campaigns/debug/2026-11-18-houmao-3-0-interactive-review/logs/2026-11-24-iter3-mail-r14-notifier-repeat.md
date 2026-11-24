# Iteration 4 R14: Mail-Notifier Repeat While Unarchived

Date: 2026-11-24. Status: completed. `any_inbox` re-notified three captured times while the message stayed read and unarchived; archiving stopped the repeats; `unread_only` stayed silent for the same read-but-unarchived message.

Plan: [Iteration 4](../iterations/2026-11-24-plan-4-notifier-repeat.md).

## Setup

- `houmao-mgr 3.0.0rc6+g151d0891`
- R13 DSH and Kimi pair on the shared `houmao-default` socket `/tmp/houmao-tmux-1001/8d7bee5d0672038af413d92d/default.sock`
- Recipient: `dsh-mailer-r13` (`b3b721ef-c73e-454e-9ce8-932765ede74e`), binding `reg-1d7b07a257f04f54b3f180085762f148`
- Sender: `kimi-mailer-r13` (`984c48fd-3242-4dea-98f3-fbd858316183`), binding `reg-c5af2391e9834f43a35547fb1f793def`
- DSH notifier initially `unread_only` at 20 seconds; inbox empty

Set DSH to `any_inbox` for the repeat arm:

```bash
houmao-mgr --print-json agents single --agent-id \
  b3b721ef-c73e-454e-9ce8-932765ede74e gateway mail-notifier enable \
  --channel offline --interval-seconds 20 --mode any_inbox \
  --appendix-text 'Notifier repeat test: read the mail but do not archive it; reply READ-NOT-ARCHIVED and stop.'
```

The status then reported `mode: any_inbox`, 20 seconds, and the appendix.

## N1: `any_inbox` Repeat

Kimi sent the test message from its binding at `06:49:07Z`:

```text
Subject: Notifier repeat test
Body: Read this message and reply READ-NOT-ARCHIVED. Do not archive it; leave it unarchived for the repeat test.
```

DSH read the message and did not archive it. The message stayed `read: true`, `archived: false`, `box: inbox` through the repeat arm.

Captured notifier status advances:

| UTC | `last_notification_at_utc` | Message state |
| --- | --- | --- |
| 06:49:33 | 06:49:33 | read, unarchived |
| 06:49:53 | 06:49:53 | read, unarchived |
| 06:50:54 | 06:50:54 | read, unarchived |

The first DSH reply landed at `06:49:26Z`, before the first captured status snapshot, so an earlier wake-up also occurred. The captured evidence is at least three re-notifications for the same unchanged eligible message.

DSH answered each wake-up and left the message unarchived. Its replies:

```text
06:49:26Z  Re: Notifier repeat test
06:49:48Z  Re: Notifier repeat test
06:50:12Z  Re: Notifier repeat test
06:50:46Z  Re: Notifier repeat test
06:51:05Z  Re: Notifier repeat test
```

DSH turns 6 through 9 completed without archiving the message. This matches the documented behavior: repeated wake-ups while the same message remains eligible.

## N2: Archive Stop

The message was archived at approximately `06:51:09Z` through:

```bash
houmao-mgr --print-json agents single --agent-id \
  b3b721ef-c73e-454e-9ce8-932765ede74e mail mark \
  --channel offline --expected-binding-id reg-1d7b07a257f04f54b3f180085762f148 \
  --message-ref "$REF" --archived
```

After a 45-second wait, the next poll at `06:51:54Z` reported:

```text
last_notification_at_utc: 2026-11-24T06:50:54Z
open_count: 0
message_count: 0
```

The timestamp did not advance across more than two intervals. Archive stopped the repeats, as documented.

## N3: `unread_only` Control

DSH was switched back to `unread_only` at 20 seconds and the appendix was cleared. The same message was restored to the inbox as read and unarchived:

```text
read: true
archived: false
box: inbox
```

After 45 seconds, the poll at `06:52:35Z` reported:

```text
mode: unread_only
last_notification_at_utc: 2026-11-24T06:50:54Z
open_count: 1
```

The timestamp did not advance, and the read-but-unarchived message remained in the inbox. This is the documented control: `unread_only` removes read mail from eligibility. The message was then archived for cleanup.

## Agent and Reply Noise

DSH followed the “do not archive” instruction and replied once per wake-up, producing five `Re: Notifier repeat test` messages. Kimi's notifier is `unread_only`; the replies were read, so they did not generate further notifications. Kimi had five read-but-unarchived replies at the end of the test. They were archived as cleanup, and its inbox returned to `open 0`.

The repeat-notification design works, but a real task agent that replies on every reminder can create reply noise. A production notifier prompt or task contract should distinguish “new work” from “repeat reminder” so the agent does not answer the same reminder repeatedly. This is a behavioral observation, not a notifier failure.

## Conclusion

- N1 passed: `any_inbox` re-notified at least three captured times while the message stayed read and unarchived.
- N2 passed: archiving stopped the repeats across more than two intervals.
- N3 passed: `unread_only` stayed silent for the read-but-unarchived message.
- DSH notifier was restored to `unread_only` with an empty appendix; both agent inboxes are clean.
- No product or fixture code changed.
