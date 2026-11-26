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

# Manage Online Mailbox Binding Without Relaunch

## Workflow

1. **Enforce the actor frame and target**: require an explicit `--agent-id` or `--agent-name` in admin posture, or use verified `agents self` in managed-agent posture.
2. **Select the online lifecycle verb**: choose `status` (safe configured identity without remote probing), `attach` (validate and bind an existing Stalwart account), `reconnect`, `refresh`, or `detach`.
3. **Verify JMAP and credential prerequisites for `attach`**: require an existing Stalwart account (`--address`, `--login-identity`), an owner-private `--credential-source` JSON file on the agent host, either `--jmap-url` or `--base-url`, and `--trust-jmap-origin` when the JMAP scheme, host, or port requires explicit origin approval (including HTTP intranet endpoints).
4. **Run the selected `mailbox online` command** without restarting the agent body or altering the `offline` mailbox slot.
5. **Confirm Inbox, Sent, and Archive readiness** on `attach`, `reconnect`, or `refresh`, and report the resulting binding ID, revision, and status.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the owning skill, [../references/stalwart-boundary.md](../references/stalwart-boundary.md), and the user request, then execute the plan.

## Command Shapes

```bash
# Safe configured status (does not probe remote JMAP or print credentials)
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox online status
<chosen houmao-mgr launcher> agents self mailbox online status

# Attach an existing Stalwart account through a live gateway companion
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox online attach \
  --provider stalwart \
  --address <address> \
  --login-identity <login> \
  --credential-source <owner-private-json-file> \
  [--jmap-url <exact-jmap-url> | --base-url <server-base-url>] \
  [--trust-jmap-origin <scheme://host:port>] \
  [--account-id <jmap-account-id>] \
  [--replace] \
  [--expected-revision <rev>] \
  [--timeout-seconds <float>]

# Detach, reconnect, or refresh without restarting the agent body
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox online detach [--expected-revision <rev>]
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox online reconnect [--expected-revision <rev>]
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox online refresh [--expected-revision <rev>]
```

Replace `agents single --agent-id <agent-id>` with `agents self` when operating on verified self in `agent` posture.

## Readiness and Boundary Notes

- Online mailbox attachment requires a live gateway companion on the target managed agent and leaves the `offline` filesystem slot untouched.
- Stalwart accounts must already exist and expose ready `Inbox`, `Sent`, and `Archive` mailbox roles; `houmao-mgr mailbox ...` and `houmao-mgr project mailbox ...` remain offline-only and never provision Stalwart server roots or accounts.
- Pass `--replace` only when the caller authorizes replacing an existing online account or endpoint with a fresh binding ID; pass `--expected-revision` to pin an observed online slot revision.
- Ordinary mail reading, sending, replying, and archiving on an attached `online` channel route to `houmao-shared-routines->houmao-agent-email-comms`.

## Guardrails

- DO NOT pass passwords inline on the command line or expose `--credential-source` file contents in chat or logs.
- DO NOT add `--trust-jmap-origin` for an untrusted or unconfirmed HTTP endpoint without explicit caller approval.
- DO NOT invent `houmao-mgr mailbox ...` or `houmao-mgr project mailbox ...` commands for Stalwart server or account administration.
