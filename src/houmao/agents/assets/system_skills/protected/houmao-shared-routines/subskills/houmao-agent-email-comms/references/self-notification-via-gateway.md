---
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

# Self-Notification Through Gateway Reminders Or Self-Mail

The supported multi-step self-notification workflow now lives in the Houmao advanced-usage skill `<public-entrypoint>->houmao-shared-routines->adv-usage-pattern`.

Use that skill's chooser page first when a managed agent wants to notify itself about later work and needs to choose between live gateway reminders and self-mail:

- [../../houmao-adv-usage-pattern/commands/self-notification.md](../../houmao-adv-usage-pattern/commands/self-notification.md)

Use the self-mail mode page when a mailbox-enabled managed agent with a live gateway wants to send follow-up mail to itself, wait for later notifier-driven rounds, and treat unread self-mail as the durable backlog:

- [../../houmao-adv-usage-pattern/commands/self-wakeup-via-self-mail.md](../../houmao-adv-usage-pattern/commands/self-wakeup-via-self-mail.md)

Within that pattern, keep using `<public-entrypoint>->houmao-shared-routines->agent-email-comms` only for the ordinary mailbox operations themselves such as `status`, `list`, `peek`, `read`, `send`, `reply`, and `archive`.
