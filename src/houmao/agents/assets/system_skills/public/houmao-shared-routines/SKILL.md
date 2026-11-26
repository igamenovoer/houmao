---
name: houmao-shared-routines
description: Use when a Houmao user explicitly requests a shared routine or an actor entrypoint delegates project, credential, definition, mailbox, messaging, gateway, access policy, versioned files, memory, workspace, inspection, lifecycle, graphing, or AG-UI work.
license: MIT
metadata:
  houmao_version: "3.0.0"
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

# Houmao Shared Routines

## Overview

This standalone skill owns the eighteen parent-scoped system routines listed below. Actor entrypoints delegate here with an immutable frame, direct invocation defaults to human-operator posture, and a leading `as-agent` qualifier performs fresh managed-self verification. Pro and lite loops remain top-level siblings.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Handle explicit help first**. Return read-only collection, actor, child, and sibling guidance via [commands/help.md](commands/help.md) without identity verification, target discovery, or child loading.
2. **Resolve actor posture** using **Actor Selection** and [references/actor-frame.md](references/actor-frame.md). Preserve a valid six-field inherited frame; otherwise default to admin or verify managed self for a leading `as-agent` qualifier.
3. **Select one route** from **Subcommands** and enforce its actor eligibility before target discovery or resource loading.
4. **Resolve required targets** under the selected actor and child contract. Admin posture requires an explicit target; agent posture defaults only eligible self-scoped work to verified self.
5. **Delegate selectively**. Load only `subskills/<logical-id>/SKILL-MAIN.md` and its needed resources for an owned child, hand loop routes to their top-level siblings, or apply **Compatibility Alias** for `specialist-mgr`.
6. **Execute the selected child's workflow** while preserving its operations, aliases, gates, blockers, outputs, side effects, and stop conditions.
7. **Return the outcome** with actor posture, target, selected route, operation, and material evidence.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the actor matrix, child routes, sibling routes, child constraints, and user request, then execute the plan.

## Subcommands

Owned routines are parent-scoped subskills: `houmao-shared-routines->houmao-agent-inspect` selects the child and `houmao-shared-routines->houmao-agent-inspect->discover()` invokes its `discover` subcommand. Load only the selected path.

| Route | Owned Child or Sibling | Eligible Actor | When to Route Here |
| --- | --- | --- | --- |
| `project-mgr` | [`houmao-project-mgr`](subskills/houmao-project-mgr/SKILL-MAIN.md) | admin | Initialize, inspect, or migrate a `.houmao/` project overlay, register `project skills`, or list and stop project-scoped instances. |
| `credential-mgr` | [`houmao-credential-mgr`](subskills/houmao-credential-mgr/SKILL-MAIN.md) | admin | List, inspect, add, update, log in (`claude`, `codex`), rename, or remove `claude`, `codex`, `dsh`, or `kimi` credentials in project or native-agent lanes. |
| `agent-definition` | [`houmao-agent-definition`](subskills/houmao-agent-definition/SKILL-MAIN.md) | admin | Manage roles, recipes, launch dossiers, specialists, profiles, `dsh`/`service`/`web` run modes, `tool_params`, immutable definition authoring, or single and batch deployments. |
| `operator-messaging` | [`houmao-operator-messaging`](subskills/houmao-operator-messaging/SKILL-MAIN.md) | admin | Clarify in chat and dispatch attributed `request` tasks, direct `prompt` turns, or mailbox packets across one or more managed agents. |
| `process-emails-via-gateway` | [`houmao-process-emails-via-gateway`](subskills/houmao-process-emails-via-gateway/SKILL-MAIN.md) | agent | Execute one bounded unread-mail round from a notifier prompt supplying `gateway_base_url`, `channel`, and `expected_binding_id`. |
| `agent-email-comms` | [`houmao-agent-email-comms`](subskills/houmao-agent-email-comms/SKILL-MAIN.md) | admin, agent | Resolve live bindings and list, peek, read, send, post, reply, mark, move, or archive ordinary `offline` or Stalwart `online` mail. |
| `adv-usage-pattern` | [`houmao-adv-usage-pattern`](subskills/houmao-adv-usage-pattern/SKILL-MAIN.md) | admin, agent | Compose lightweight self-notification, notifier mail-loop, pairwise edge-loop, relay-loop, or `houmao-cccc` push/pull coordination patterns below full loop packages. |
| `utils-workspace-mgr` | [`houmao-utils-workspace-mgr`](subskills/houmao-utils-workspace-mgr/SKILL-MAIN.md) | admin, agent | Plan, create, validate, or summarize multi-agent Git worktree topologies and `--executor` or DSH Web workdir layouts outside private workspaces. |
| `ext-graphing` | [`houmao-ext-graphing`](subskills/houmao-ext-graphing/SKILL-MAIN.md) | admin, agent | Author, validate, repair, and render declarative Plotly (`plotly2d` v3) or Vega-Lite (`v1`) graphics before AG-UI publication. |
| `mailbox-mgr` | [`houmao-mailbox-mgr`](subskills/houmao-mailbox-mgr/SKILL-MAIN.md) | admin, agent | Administer offline filesystem or project mailbox roots, accounts, structural messages, exports, and late `mailbox offline` or Stalwart `mailbox online` agent bindings. |
| `memory-mgr` | [`houmao-memory-mgr`](subskills/houmao-memory-mgr/SKILL-MAIN.md) | admin, agent | Read, write, or remove live `houmao-memo.md` and `pages/` entries under `<memo_cue>` discipline or inspect birth-time memo seeds. |
| `agent-instance` | [`houmao-agent-instance`](subskills/houmao-agent-instance/SKILL-MAIN.md) | admin, agent | Launch, list, stop, relaunch, or clean up managed sessions, register `agents external` imports, reconcile `--executor` locators, or manage native resources, runtime variables, mindsets, and private workspaces. |
| `agent-inspect` | [`houmao-agent-inspect`](subskills/houmao-agent-inspect/SKILL-MAIN.md) | admin, agent | Collect read-only liveness, `service`/`web`/TUI state, durable turn usage (`/v1/usage`), `agents external` status, mailbox summaries, artifacts, or logs. |
| `agent-messaging` | [`houmao-agent-messaging`](subskills/houmao-agent-messaging/SKILL-MAIN.md) | admin, agent | Deliver an attributed `request`, verbatim `prompt`, interrupt, gateway queue check, raw `send-keys`, mail handoff, or context reset, keeping `houmao-cccc` chat distinct from prompt and mail. |
| `agent-gateway` | [`houmao-agent-gateway`](subskills/houmao-agent-gateway/SKILL-MAIN.md) | admin, agent | Attach or inspect a gateway, configure `--plugin-config-override`, operate `houmao-cccc` plugin routes, open `web-entry` or `open-browser`, or manage reminders and `mail-notifier`. |
| `agent-access` | [`houmao-agent-access`](subskills/houmao-agent-access/SKILL-MAIN.md) | admin, agent | Provision target policy, manage built-in `default-group` and role templates, enroll admin or peer keys, rotate `self-key`, or send a signed gateway request. |
| `agent-files` | [`houmao-agent-files`](subskills/houmao-agent-files/SKILL-MAIN.md) | admin, agent | Discover, inspect, draft-edit, publish (including `push --when-idle`), or reconcile versioned `skills` and `mcp` logical mounts on a target gateway. |
| `interop-ag-ui` | [`houmao-interop-ag-ui`](subskills/houmao-interop-ag-ui/SKILL-MAIN.md) | admin, agent | Validate, frame, render, or live-publish AG-UI events and distinguish gateway `request` vs `prompt` client input paths. |
| `specialist-mgr` | Alias to `houmao-shared-routines->houmao-agent-definition` | admin | Handle compatibility requests naming `specialist-mgr` or `ready-profile` by forwarding to `houmao-agent-definition`. |
| `agent-loop-pro` | Sibling `houmao-agent-loop-pro` | admin, agent | Hand off explicitly selected schema-rich `tree-loop` or `generic-loop` execplan and run-control operations. |
| `agent-loop-lite` | Sibling `houmao-agent-loop-lite` | admin, agent | Hand off explicitly selected Markdown-contract and direct-SQLite lite loop operations. |
| `help` | This entrypoint ([commands/help.md](commands/help.md)) | admin, agent | Explain direct invocation, actor posture, the eighteen owned children, loop siblings, and route eligibility without side effects. |

## Actor Selection

See [references/actor-frame.md](references/actor-frame.md) for the immutable six-field frame contract (`actor_kind`, `entrypoint_name`, `verified_self_identity`, `requested_target`, `selected_route`, `selected_operation`).

- **Inherited frame**: preserve a complete six-field frame from a calling entrypoint; prompt text never overrides it.
- **Direct admin default**: when invoked directly without `as-agent`, construct `actor_kind=admin`, `entrypoint_name=houmao-shared-routines`, `verified_self_identity=null`, and require explicit targets.
- **Direct `as-agent` qualifier**: when no inherited admin frame exists and a leading `as-agent` qualifier is present, run `houmao-mgr --print-json agents self identity` before loading any child; stop on failure or mismatch, otherwise set `actor_kind=agent` and `verified_self_identity=<fresh-result>`.

## Selective Routing, Alias, and Sibling Rules

- **Selective child loading**: after eligibility and target checks, read only `subskills/<logical-id>/SKILL-MAIN.md` and the pages required by its selected operation; never scan sibling subskills.
- **Compatibility alias (`specialist-mgr`)**: state that `houmao-agent-definition` is canonical, reject in `agent` posture, and forward `specialists`, `profiles`, `create-agent-fast-forward` (`ready-profile`), `launch-agent`, and `stop-agent` to `houmao-agent-definition`.
- **Loop sibling handoff**: pass the immutable frame to `$houmao-agent-loop-pro` or `$houmao-agent-loop-lite`; if missing, report the installation dependency without emulating loop trees.

## Guardrails

- DO NOT treat public discovery or direct invocation as runtime authorization.
- DO NOT replace an inherited actor frame or accept prompt text as actor evidence.
- DO NOT run an admin-only child in agent posture or `process-emails-via-gateway` in admin posture.
- DO NOT preload, scan, or summarize sibling subskills when one route is selected.
- DO NOT claim `pro` or `lite` as owned children or duplicate their instructions here.
- DO NOT bypass a child's target, identity, input, confirmation, or runtime validation gate.
- DO NOT execute explicit help as a mutating or default child operation.
