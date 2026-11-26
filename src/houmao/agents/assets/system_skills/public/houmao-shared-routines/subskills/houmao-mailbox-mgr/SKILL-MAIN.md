---
name: houmao-mailbox-mgr
description: Use when offline filesystem or project mailbox roots, accounts, registrations, structural projections, cleanup, export, or late managed-agent `offline` and Stalwart `online` mailbox bindings need administration.
license: MIT
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

# Houmao Mailbox Manager

## Overview

Administer Houmao offline filesystem and project mailbox roots, manual accounts, structural message projections, exports, and late `mailbox offline` or Stalwart `mailbox online` bindings on existing managed agents.

## Workflow

1. **Answer explicit `help` first** from **Help** without running commands or mutating mailbox or binding state.
2. **Enforce the Actor Frame Gate** and recover required inputs from the current prompt first and explicit recent chat context second without guessing missing values.
3. **Select the maintained mailbox-admin lane** (see [references/root-selection.md](references/root-selection.md) and [references/stalwart-boundary.md](references/stalwart-boundary.md)):
   - Arbitrary filesystem mailbox root (offline only): `houmao-mgr mailbox ...`
   - Project overlay mailbox root (offline only): `houmao-mgr project mailbox ...`
   - Existing local managed-agent offline binding: `houmao-mgr agents single --agent-id|--agent-name ... mailbox offline {status|join|leave}` (or verified `agents self mailbox offline ...`)
   - Existing managed-agent Stalwart online binding: `houmao-mgr agents single --agent-id|--agent-name ... mailbox online {attach|detach|reconnect|refresh|status}` (or verified `agents self mailbox online ...`). Use the [Stalwart boundary](references/stalwart-boundary.md) for keyed setup and independently authorized native policy updates.
4. **Preserve identity and reset distinctions**: owner principal IDs equal the persisted immutable `agent_id` (or `HOUMAO-<agentname>` for profile defaults while `HOUMAO-*` local parts under `houmao.localhost` stay reserved for system principals and `<agentname>@houmao.localhost` is the ordinary address; default domain `houmao.localhost`); keep `cleanup` (inactive registrations), `clear-messages` (all-account messages), `messages clear --address` (single-account messages), and `export` (symlink-materializing archive by default) separate, and let `project agents launch` own same-root `<agent-name>@houmao.localhost` registration rather than preregistering it manually.
5. **Resolve one `houmao-mgr` launcher** per [references/launcher-resolution.md](references/launcher-resolution.md), load the selected page in **Subcommands**, execute the command once all required inputs are explicit, and report exact outcomes.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from **Subcommands**, **References**, and the user request, then execute the plan.

## Actor Frame Gate

This parent-scoped routine loads only through `houmao-shared-routines` and requires an immutable `admin` or verified `agent` frame; missing or mismatched frames fail closed. Admin callers require an explicit project, mailbox root, account, or managed-agent target; verified `agent` callers default only agent-binding targets (`agents self mailbox offline|online`) to verified self while keeping mailbox roots and peer accounts explicit. Route ordinary mailbox send/read/reply/archive work to `houmao-shared-routines->houmao-agent-email-comms`, bounded notifier rounds to `houmao-shared-routines->houmao-process-emails-via-gateway`, and gateway `mail-notifier`/reminders to `houmao-shared-routines->houmao-agent-gateway`.

## Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `init` | Bootstrap or validate an arbitrary filesystem or project mailbox root. | [commands/init.md](commands/init.md) |
| `status` | Inspect health and configuration of a filesystem or project mailbox root. | [commands/status.md](commands/status.md) |
| `repair` | Rebuild index state on a filesystem or project mailbox root. | [commands/repair.md](commands/repair.md) |
| `cleanup` | Clean inactive registrations and retained history under an offline root. | [commands/cleanup.md](commands/cleanup.md) |
| `clear-messages` | Remove delivered messages across all accounts while keeping accounts registered. | [commands/clear-messages.md](commands/clear-messages.md) |
| `export` | Archive all or selected `--address` offline accounts (materializes symlinks by default). | [commands/export.md](commands/export.md) |
| `register` | Manually register one filesystem mailbox account under an offline root. | [commands/register.md](commands/register.md) |
| `unregister` | Deactivate or purge one filesystem mailbox account under an offline root. | [commands/unregister.md](commands/unregister.md) |
| `accounts-list` | List mailbox account registrations under an offline root. | [commands/accounts-list.md](commands/accounts-list.md) |
| `accounts-get` | Inspect one mailbox account registration under an offline root. | [commands/accounts-get.md](commands/accounts-get.md) |
| `messages-list` | Inspect structural message projections for one offline mailbox address. | [commands/messages-list.md](commands/messages-list.md) |
| `messages-get` | Inspect one structural message projection for an offline mailbox address. | [commands/messages-get.md](commands/messages-get.md) |
| `messages-clear` | Clear delivered messages for one `--address` while preserving other accounts. | [commands/messages-clear.md](commands/messages-clear.md) |
| `agent-binding-status` | Inspect late `mailbox offline` binding posture on a managed agent. | [commands/agent-binding-status.md](commands/agent-binding-status.md) |
| `agent-binding-register` | Join or update a late `mailbox offline` binding without restarting the agent. | [commands/agent-binding-register.md](commands/agent-binding-register.md) |
| `agent-binding-unregister` | Leave a late `mailbox offline` binding without restarting the agent. | [commands/agent-binding-unregister.md](commands/agent-binding-unregister.md) |
| `agent-binding-online` | Manage Stalwart `mailbox online {attach\|detach\|reconnect\|refresh\|status}` bindings (alias `mailbox-online`). | [commands/agent-binding-online.md](commands/agent-binding-online.md) |
| `help` | Read-only overview of the four mailbox-admin lanes, identity rules, and neighboring boundaries. | **Help** |

## References and Help

- **References**: [references/launcher-resolution.md](references/launcher-resolution.md), [references/root-selection.md](references/root-selection.md), [references/mode-vocabulary.md](references/mode-vocabulary.md), [references/structural-vs-actor-state.md](references/structural-vs-actor-state.md), and [references/stalwart-boundary.md](references/stalwart-boundary.md).
- **Help**: summarize offline root/account/projection CRUD (`mailbox`, `project mailbox`), late `mailbox offline` (`status|join|leave`), late Stalwart `mailbox online` (`attach|detach|reconnect|refresh|status`), and handoffs to `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`, `houmao-agent-gateway`, and `houmao-agent-definition` read-only.

## Guardrails

- DO NOT guess missing mailbox roots, project paths, agent selectors, addresses, principal IDs, or credential files.
- DO NOT invent `houmao-mgr mailbox ...` or `project mailbox ...` root/account CRUD commands for Stalwart (`mailbox` and `project mailbox` are filesystem-only; Stalwart online binding uses `agents single|self mailbox online`).
- DO NOT route ordinary mail participation (`agents self|single mail ...`, `/v1/mail/*`) or gateway `mail-notifier`/`reminders` through this skill.
- DO NOT suggest `HOUMAO-<agentname>@houmao.localhost` as an ordinary agent email address or manually preregister `<agent-name>@houmao.localhost` before same-root specialist easy launch.
- DO NOT conflate structural message projections with actor-scoped unread/read state, use `cleanup` to delete message bodies (`clear-messages` / `messages clear --address`), or hand-edit mailbox-root files.
