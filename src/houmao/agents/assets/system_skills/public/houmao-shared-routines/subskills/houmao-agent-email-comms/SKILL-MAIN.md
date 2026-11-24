---
name: houmao-agent-email-comms
description: Use when ordinary Houmao mailbox work needs operator-origin posting, managed-agent shared mail, gateway-backed `/v1/mail/*`, or a supported no-gateway transport fallback.
license: MIT
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

# Houmao Agent Email Comms

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines`. Require the immutable admin or verified-agent frame validated by that parent; otherwise stop before mailbox routing.

- Admin branch: use the operator-origin `post` path and require explicit mailbox or managed-agent targets. Do not resolve the operator session as managed self.
- Agent branch: require freshly verified self identity, use the verified agent's ordinary mailbox context by default, and require an explicit peer or account target when the command is not self-scoped.

Preserve the branch through gateway discovery and transport fallback. A notifier-driven unread round enters the agent-only `process-emails-via-gateway` route first.

Use this Houmao skill when you need mailbox work around Houmao-managed agents.

Classify the caller up front:

- Preserve the actor frame established by the parent. An admin uses operator-origin `post` against an explicit target. Missing gateway or mail configuration does not turn a verified agent into an operator.
- If the caller is a verified Houmao-managed agent, use `houmao-mgr agents self mail ...` for ordinary mail. The manager uses the sender's authorized binding and chooses its execution path.

For managed-agent gateway-notified open-mail rounds only, use `houmao-shared-routines->houmao-process-emails-via-gateway` first and return here when that round needs exact mailbox operations or transport-local guidance.

The trigger word `houmao` is intentional. Enter this parent-scoped routine only through `houmao-shared-routines->houmao-agent-email-comms`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$houmao-shared-routines agent-email-comms help`, `help for houmao-agent-email-comms`, `usage for houmao-agent-email-comms`, `available functionality for houmao-agent-email-comms`, or what this skill can do, answer from this section before caller classification, action-page routing, transport-page routing, command execution, or missing-input questions. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me send mail to an agent", route to the matching workflow instead of stopping at generic help.

Purpose: perform ordinary Houmao shared-mailbox operations through the live gateway facade when available, with supported no-gateway fallback guidance.

Available functionality:

- Resolve live mailbox bindings and inspect mailbox status.
- List, peek, read, send, post, reply, mark, move, or archive mailbox messages.
- Choose operator-origin `post` versus managed-agent shared-mailbox workflows.
- Use filesystem or Stalwart transport guidance when no gateway facade is available.

Common starting prompts:

- `$houmao-shared-routines agent-email-comms help`
- `$houmao-shared-routines agent-email-comms status for the current mailbox`
- `$houmao-shared-routines agent-email-comms send a message to <agent>`
- `$houmao-shared-routines agent-email-comms reply to <message_ref>`

Related skills and boundaries:

- Use `houmao-shared-routines->houmao-process-emails-via-gateway` for one notifier-reported open-mail round.
- Use `houmao-shared-routines->houmao-mailbox-mgr` for mailbox root, registration, or late-binding administration.
- Use `houmao-shared-routines->houmao-agent-gateway` for notifier, reminder, or gateway lifecycle work.
- Use `houmao-shared-routines->houmao-agent-messaging` when the task starts as live-agent prompt, interrupt, or mailbox handoff routing.

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Decide the caller posture up front.
2. Preserve the validated actor frame. Admin posting requires an explicit target; a verified agent remains an agent even when its gateway or mailbox is unavailable.
3. Run `houmao-mgr agents self mail resolve-live` to resolve the current managed session. An operator selects an explicit target with `agents single ... mail resolve-live`.
4. Read `mailboxes.offline` and `mailboxes.online` separately. Select the channel explicitly from the request or established round context. Pin that slot's `binding.binding_id`. Canonical mail identity describes the preferred address.
5. Use `houmao-mgr agents self mail <verb> --channel <channel> --expected-binding-id <binding_id>` for routine work. The command signs attached-gateway calls internally with the current managed generation. Scoped operators use their explicitly configured admin signer.
6. End the operation on an admission refusal, unavailable policy, or a binding change. Keep proof and credentials out of commands and result summaries.
7. If the gateway is detached, the scoped command uses the established owner-authorized manager path for the selected channel. An `authoritative: false` result reports request status and requires read-only confirmation when the write outcome remains uncertain.
8. Report send, reply, and post from their first receipts. Use `peek` for details on the binding that owns the receipt reference. Keep message and thread references opaque and preserve their channel and binding.
9. Begin triage with one metadata page of 50 messages (maximum 200). Preserve filters and the opaque cursor when continuing within an explicit page/message budget. `has_more` describes unseen work; returned counts describe this page. Stop the page chain on a stale cursor or binding conflict. Fetch selected content with peek/read and check its completeness before acting.
10. Archive processed messages only after the corresponding mailbox action and any required reply succeed.
11. Include only fields the user explicitly supplied or that were recovered from explicit recent context in fallback commands.


If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.
## Missing Input Questions

- Recover required mailbox values from the current prompt, notifier context, resolver output, or recent mailbox context before asking.
- Ask for any required value that remains missing after discovery. A live gateway base URL is required only for a gateway-specific action.
- When asking for Houmao mailbox-system inputs, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected mailbox action or route
  - `Optional`: gateway-vs-fallback posture, filters, archive-after-success choice, output format, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when caller posture, route, or several required fields need clarification
- DO NOT use this format for user-task content inside a mail body unless the question is about Houmao runtime behavior.

## Subcommands

- Answer `help` from `## Help` before reading action, transport, or reference pages.
- Read [commands/resolve-live.md](commands/resolve-live.md) only when the current prompt or recent mailbox context does not already provide the exact gateway base URL or current binding set.
- Read [commands/status.md](commands/status.md) to inspect current mailbox identity, mailbox transport, or live gateway posture.
- Read [commands/list.md](commands/list.md) to list unread, open, archived, or current mailbox state.
- Read [commands/read.md](commands/read.md) when deciding whether to peek at or read one selected message.
- Read [commands/send.md](commands/send.md) to send one new message.
- Read [commands/post.md](commands/post.md) when the caller is acting as operator or otherwise outside the managed Houmao runtime and needs to leave one operator-origin note in a managed agent mailbox.
- Read [commands/reply.md](commands/reply.md) to reply to one existing message.
- Read [commands/archive.md](commands/archive.md) to archive one or more processed messages.

## Transport Pages

- Read [references/transports/filesystem.md](references/transports/filesystem.md) when the offline binding transport is `filesystem` or `registry` and you need layout, policy, or no-gateway fallback guidance.
- Read [references/transports/stalwart.md](references/transports/stalwart.md) when the online binding transport is `stalwart` and you need direct-access or no-gateway fallback guidance.

## References

- Read [references/endpoint-contract.md](references/endpoint-contract.md) for the shared `/v1/mail/*` route summary.
- Read [references/scoped-cli.md](references/scoped-cli.md) for signed mailbox commands and binding selection.
- Read [references/managed-agent-fallback.md](references/managed-agent-fallback.md) for the supported `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...` fallback surfaces when no live gateway facade exists.
- Read [references/filesystem-resolver-fields.md](references/filesystem-resolver-fields.md) or [references/stalwart-resolver-fields.md](references/stalwart-resolver-fields.md) when transport-local resolver fields matter.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) only when filesystem mailbox layout details are relevant.

## Useful Patterns

- For supported higher-level mailbox and gateway compositions such as self-wakeup through self-mail plus notifier-driven rounds, switch to the Houmao advanced-usage skill `houmao-shared-routines->houmao-adv-usage-pattern`.

## Guardrails

- DO NOT bridge channels, translate addresses, choose a channel from canonical identity, or resend to a replacement binding.
- DO NOT guess the gateway host or port; use the exact base URL already present in prompt or context when available, otherwise use `gateway.base_url` from `houmao-mgr agents self mail resolve-live`.
- DO NOT scrape tmux state directly when the manager-owned resolver is available.
- DO NOT route operator-origin mailbox delivery through ordinary `/v1/mail/{channel}/send`; use the dedicated `post` surface.
- DO NOT derive mailbox internals from visible `message_ref` or `thread_ref` prefixes.
- DO NOT request bodies through list, use removed `include_body`/`--include-body` inputs, automatically drain cursors, or present page counts as exact mailbox totals.
- DO NOT treat truncated or unsupported-limit content as complete; inspect peek/read completeness and report any missing content.
- DO NOT archive a message before the corresponding mailbox action and any required reply succeed.
- DO NOT treat this ordinary communication skill as the whole notifier-round workflow when `houmao-shared-routines->houmao-process-emails-via-gateway` is available.
- DO NOT present direct transport-local access as the first-choice path when a live shared gateway mailbox facade is available.
- DO NOT invent alternate fallback command shapes; use the direct scoped `houmao-mgr agents self mail ...` and `houmao-mgr agents single ... mail ...` commands shown in this skill package.
