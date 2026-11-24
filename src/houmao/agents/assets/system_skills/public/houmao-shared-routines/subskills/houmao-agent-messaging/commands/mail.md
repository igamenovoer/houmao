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

# Route Mailbox Work To The Mail Skills

Use this action when the current task needs recipient contact or a mailbox handoff.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and mailbox intent from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or mailbox intent is still missing, ask the user in Markdown before proceeding.
4. Use the known recipient address for the explicit channel. If the request names an agent and omits its address, read `agents single ... mail resolve-live` for the selected channel. Published contact is sufficient for addressing ordinary mail.
5. Hand off ordinary mailbox work to `houmao-shared-routines->houmao-agent-email-comms`. For outbound agent mail, pass the recipient address and channel to the sender's `agents self mail send --channel <channel>` workflow. Recipient gateway availability and readiness do not gate delivery.
6. For a notifier-driven open-mail round, hand off to `houmao-shared-routines->houmao-process-emails-via-gateway` with the exact live `gateway.base_url` from current context or verified discovery.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Discovery Shape

Resolve a named recipient's address when needed:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> mail resolve-live
```

Managed-agent HTTP discovery surface:

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

After `resolve-live`, read `mailboxes.offline` or `mailboxes.online` according to the selected channel. A result with `source: registry_projection` is published contact with unverified availability.

Pass the recipient address to the mailbox skill. The sender's binding and credentials come from verified self authority.

## Guardrails

- DO NOT guess mailbox capability, mailbox addresses, or message references.
- DO NOT restate filesystem layout, Stalwart credential handling, managed-agent mailbox operation routes, or the lower-level `/v1/mail/*` contract here.
- DO NOT perform mailbox operations directly from this routing page.
- DO NOT turn mailbox work into a raw `send-keys` or ordinary prompt workflow.
- DO NOT skip scoped `agents ... mail resolve-live` when the task depends on whether a live gateway mailbox facade exists.
- DO NOT guess a direct gateway base URL for mailbox work.
