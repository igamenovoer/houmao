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

# Route Mailbox Work To The Mail Skills

Use this action only when the target has mailbox capability and the current task needs mailbox work instead of a normal prompt turn or raw gateway control.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and mailbox intent from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or mailbox intent is still missing, ask the user in Markdown before proceeding.
4. Use `agents single ... mail resolve-live` or `agents self mail resolve-live` first when the task needs current mailbox bindings, mailbox capability confirmation, or an exact live `gateway.base_url`.
5. When the mailbox task is a notifier-driven open-mail round and current context already provides the exact live gateway base URL, hand off to `<public-entrypoint>->houmao-shared-routines->process-emails-via-gateway`.
6. Otherwise hand off ordinary mailbox work to `<public-entrypoint>->houmao-shared-routines->agent-email-comms`.
7. Use the resolver output to tell the selected mailbox skill whether the turn has a live `gateway.base_url` or must use no-gateway fallback guidance.
8. Report the selected mailbox lane and any resolved live-gateway fact that matters for the handoff.

## Discovery Shape

Resolve live bindings before handoff:

```text
<chosen houmao-mgr launcher> agents single --agent-name <name> mail resolve-live
```

Managed-agent HTTP discovery surface:

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

After `resolve-live`:

- use `<public-entrypoint>->houmao-shared-routines->agent-email-comms` for ordinary mailbox `status`, `list`, `peek`, `read`, `send`, `reply`, or `archive` work
- use `<public-entrypoint>->houmao-shared-routines->process-emails-via-gateway` for one live-gateway open-mail round that already has the exact current base URL in context

## Guardrails

- Do not guess mailbox capability, mailbox addresses, or message references.
- Do not restate filesystem layout, Stalwart credential handling, managed-agent mailbox operation routes, or the lower-level `/v1/mail/*` contract here.
- Do not perform mailbox operations directly from this routing page.
- Do not turn mailbox work into a raw `send-keys` or ordinary prompt workflow.
- Do not skip scoped `agents ... mail resolve-live` when the task depends on whether a live gateway mailbox facade exists.
- Do not guess a direct gateway base URL for mailbox work.
