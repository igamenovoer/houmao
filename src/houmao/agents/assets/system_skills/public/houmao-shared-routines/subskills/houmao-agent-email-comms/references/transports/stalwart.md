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

# Stalwart Online Mail

Use this page for a configured `online` binding whose provider transport is `stalwart`. The same agent can retain an independent offline registration. Online-first canonical identity describes its preferred email identity; it does not choose a delivery channel.

Use the exact gateway URL and `/v1/mail/online/...` action pages. With no gateway, use `houmao-mgr agents self mail <action> --channel online --expected-binding-id <binding_id>`. The manager owns protected provider access; ordinary communication needs no password, management credential, or direct JMAP request.

Keep message and thread references opaque and bound to the selected owner and account. Stop on account replacement or a binding conflict. Online errors do not authorize offline delivery. Read/reply/archive semantics stay the same across supported providers; an unsupported operation reports an explicit error. Operator-origin `post` remains unsupported for Stalwart.

Inspect bounded metadata pages before fetching selected bodies: default 50, maximum 200, optional scoped cursor, no body-in-list option. Preserve query filters through continuation and stop on stale cursor or binding errors. A page count or cached sync sample is not an exact full-inbox total. Peek/read disclose partial-content limits; report them before claiming complete inspection. Archive only after work and required replies succeed. Read or answered state alone does not complete open inbox work, so configured periodic reminders can repeat unchanged eligible work.
