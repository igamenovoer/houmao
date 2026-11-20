# Configure and Handle Wakeups

Mail provides the durable work record. Use scoped `gateway mail-notifier` when a live gateway should wake the agent for inbox work. Check the channel binding and notifier status. The default mode tracks unarchived inbox mail, while unread-only mode limits wakeups to unread items. Use `gateway reminders` when the trigger should be a schedule.

For a notifier round, keep the supplied gateway URL, channel, and expected binding ID on every mailbox operation. End the round if one is missing or the binding changed. Inspect a bounded set of relevant messages and resume interrupted work first. Verify the requested result, send any required reply, and archive only after processing and reply delivery succeed. Then finish the round.

`houmao-mgr agents self gateway mail-notifier --help` shows notifier controls. [Mail Notifier Operations](https://igamenovoer.github.io/houmao/reference/gateway/operations/mail-notifier/) · [Notifier-Driven Workflows](https://igamenovoer.github.io/houmao/reference/gateway/operations/notifier-prompt-driven-loops/)
