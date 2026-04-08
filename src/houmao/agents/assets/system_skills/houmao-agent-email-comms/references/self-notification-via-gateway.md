# Self-Notification Through Gateway Reminders Or Self-Mail

The supported multi-step self-notification workflow now lives in the Houmao advanced-usage skill `houmao-adv-usage-pattern`.

Use that skill's chooser page first when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail:

- [../../houmao-adv-usage-pattern/patterns/self-notification.md](../../houmao-adv-usage-pattern/patterns/self-notification.md)

Use the self-mail mode page when a mailbox-enabled managed agent with a live gateway wants to send follow-up mail to itself, wait for later notifier-driven rounds, and treat unread self-mail as the durable backlog:

- [../../houmao-adv-usage-pattern/patterns/self-wakeup-via-self-mail.md](../../houmao-adv-usage-pattern/patterns/self-wakeup-via-self-mail.md)

Within that pattern, keep using `houmao-agent-email-comms` only for the ordinary mailbox operations themselves such as `status`, `check`, `send`, `reply`, and `mark-read`.
