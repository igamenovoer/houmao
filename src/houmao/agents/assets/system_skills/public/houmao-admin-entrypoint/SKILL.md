---
name: houmao-admin-entrypoint
description: Use when any semantically Houmao-related request reaches an assistant acting for a human operator, including information, command or route learning, incomplete tasks, state inspection, operations, and explicit loop work. Do not trigger for an incidental Houmao token in otherwise unrelated material; explicit $houmao-* handles take precedence.
license: MIT
metadata:
  houmao_version: "3.0.0rc8"
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

# Houmao Admin Entrypoint

## Overview

Use this public operator router when acting for a human Houmao operator. Informational requests stay local and read-only; operational requests establish an immutable `admin` actor frame, enforce an explicit target gate, and delegate to `$houmao-shared-routines`, `$houmao-agent-loop-pro`, or `$houmao-agent-loop-lite`.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Classify intent first** as informational, direct CLI meta-guidance, operational, or loop work without probing targets, loading siblings, or running mutating commands.
2. **Answer informational and welcome-style requests locally**: handle `help`, `welcome`, `show-options`, `choose-path`, `show-command-map`, `next-step`, `start-guided-tour`, and `houmao-mgr manual` / `houmao-mgr system-skills` / `houmao-mgr admin cleanup` questions read-only (see [commands/help.md](commands/help.md) and **Operator Discovery Surfaces**); recommend explicit `$houmao-admin-welcome ...` when full touring helps without invoking it.
3. **Establish the immutable admin frame** for operational work: `actor_kind=admin`, `entrypoint_name=houmao-admin-entrypoint`, `verified_self_identity=null`.
4. **Select one eligible route** from **Subcommands**. Reject agent-only `process-emails-via-gateway`; if loop work omits `pro` vs `lite`, ask the operator to choose rather than guessing.
5. **Enforce the Target Gate** before mutation: require an explicit or unambiguously stated project path, agent ID/name, mailbox root, or `<loop-dir>`; if multiple candidates exist, ask one concise `Required` / `Optional` question.
6. **Delegate with the Sibling Handoff Frame** to `$houmao-shared-routines`, `$houmao-agent-loop-pro`, or `$houmao-agent-loop-lite` (applying **Specialist Compatibility Alias** when `specialist-mgr` is named).
7. **Honor Joined-Session Adoption** on `agent-instance join`: remain `admin` until `houmao-mgr agents self join` succeeds, then verify `houmao-mgr --print-json agents self identity` and hand subsequent work to `$houmao-agent-entrypoint`.
8. **Return the routed outcome** leading with status (`completed`, `unchanged`, `blocked`, or `failed`), target, and material evidence.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the eligible subcommands, target gate, sibling contracts, and user request, then execute the plan.

## Subcommands

Entrypoint route calls use `houmao-admin-entrypoint->agent-inspect()`; delegated shared children use `houmao-shared-routines->houmao-agent-inspect->discover()`.

| Subcommand | Sibling Destination | When to Route Here |
| --- | --- | --- |
| `welcome` | This entrypoint | Provide concise read-only orientation, route comparison, or reorientation (`show-options`, `choose-path`, `show-command-map`, `next-step`, `start-guided-tour`) and recommend manual `$houmao-admin-welcome` when useful. |
| `help` | This entrypoint ([commands/help.md](commands/help.md)) | Explain operator posture, target requirements, direct CLI utilities, and sibling routes without side effects. |
| `project-mgr` | `houmao-shared-routines->houmao-project-mgr` | Initialize, inspect, or `migrate` a `.houmao/` overlay, manage `project skills`, or list and stop project-scoped agents. |
| `credential-mgr` | `houmao-shared-routines->houmao-credential-mgr` | List, inspect, add, update, log in (`claude`, `codex`), rename, or remove `claude`, `codex`, `dsh`, or `kimi` credentials. |
| `agent-definition` | `houmao-shared-routines->houmao-agent-definition` | Manage roles, recipes, launch dossiers, specialists, profiles, `dsh`/`service`/`web` modes, `tool_params`, immutable definition revisions, or single and batch deployments. |
| `specialist-mgr` | `houmao-shared-routines->houmao-agent-definition` | Forward compatibility requests for `specialists`, `profiles`, `create-agent-fast-forward` (`ready-profile`), `launch-agent`, or `stop-agent` to canonical `houmao-agent-definition`. |
| `operator-messaging` | `houmao-shared-routines->houmao-operator-messaging` | Clarify in chat and dispatch attributed `request` tasks, direct `prompt` turns, or mailbox packets across managed agents. |
| `agent-email-comms` | `houmao-shared-routines->houmao-agent-email-comms` | Resolve live bindings and inspect, send, post, reply, mark, move, or archive ordinary `offline` or Stalwart `online` mail. |
| `adv-usage-pattern` | `houmao-shared-routines->houmao-adv-usage-pattern` | Compose self-notification, notifier mail-loop, pairwise edge-loop, relay-loop, or `houmao-cccc` push/pull coordination patterns. |
| `utils-workspace-mgr` | `houmao-shared-routines->houmao-utils-workspace-mgr` | Plan, create, validate, or summarize multi-agent Git worktrees and `--executor` or DSH Web workdir layouts. |
| `ext-graphing` | `houmao-shared-routines->houmao-ext-graphing` | Author, validate, repair, and render Plotly (`plotly2d` v3) or Vega-Lite (`v1`) graphics for AG-UI delivery. |
| `mailbox-mgr` | `houmao-shared-routines->houmao-mailbox-mgr` | Administer offline filesystem or project mailbox roots, accounts, structural messages, exports, and late `mailbox offline` or Stalwart `mailbox online` bindings. |
| `memory-mgr` | `houmao-shared-routines->houmao-memory-mgr` | Read, write, or remove live `houmao-memo.md` and `pages/` entries or inspect birth-time profile memo seeds. |
| `agent-instance` | `houmao-shared-routines->houmao-agent-instance` | Launch, join, list, stop, relaunch, or clean up sessions, register `agents external` imports, maintain `admin executors` locators, or manage native resources, runtime variables, mindsets, and private workspaces. |
| `agent-inspect` | `houmao-shared-routines->houmao-agent-inspect` | Inspect read-only liveness, `service`/`web`/TUI state, durable usage (`/v1/usage`), `agents external` records, mailbox summaries, artifacts, or logs. |
| `agent-messaging` | `houmao-shared-routines->houmao-agent-messaging` | Send an attributed `request`, verbatim `prompt`, interrupt, gateway queue check, raw `send-keys`, mail handoff, or context reset, keeping `houmao-cccc` chat distinct. |
| `agent-gateway` | `houmao-shared-routines->houmao-agent-gateway` | Attach or inspect a gateway, pass `--plugin-config-override`, operate `houmao-cccc` plugin routes, open `web-entry` or `open-browser`, or manage reminders and `mail-notifier`. |
| `agent-access` | `houmao-shared-routines->houmao-agent-access` | Provision retained policy, set `default-group` or role templates, enroll admin or peer keys, rotate `self-key`, or send a signed gateway request. |
| `agent-files` | `houmao-shared-routines->houmao-agent-files` | Discover, inspect, draft-edit, publish, or reconcile versioned `skills` and `mcp` logical mounts on a target gateway. |
| `interop-ag-ui` | `houmao-shared-routines->houmao-interop-ag-ui` | Validate, frame, render, or live-publish AG-UI events and align gateway `request` vs `prompt` client input paths. |
| `agent-loop-pro` | `houmao-agent-loop-pro` | Execute explicitly selected schema-rich `tree-loop` or `generic-loop` execplan and run-control workflows. |
| `agent-loop-lite` | `houmao-agent-loop-lite` | Execute explicitly selected Markdown-contract and direct-SQLite lite loop workflows. |

## Target Gate, Sibling Frame, and Operator Discovery Surfaces

- **Target Gate and Admin Posture**: the assistant acts for a human operator, never reinterprets the local shell/tmux/gateway as `agents self`, and recovers targets only from explicit prompt or unambiguous recent user context (read-only discovery lists candidates without guessing).
- **Sibling Handoff Frame**: pass `actor_kind=admin`, `entrypoint_name=houmao-admin-entrypoint`, `verified_self_identity=null`, `requested_target=<target>`, `selected_route=<subcommand>`, and `selected_operation=<operation-or-null>`.
- **Operator Discovery Surfaces**: guide operators directly to `houmao-mgr manual` for packaged operating manuals and `houmao-mgr system-skills {list|install|status|doctor|upgrade|uninstall}` for static `admin`/`agent` skill-pack lifecycle; route `admin executors {reconcile|forget}` and session/runtime `cleanup` boundaries through `agent-instance` (or `project-mgr` for overlay awareness) without inventing extra skills.

## Guardrails

- DO NOT treat the current session as managed self or call `agents self` operational commands as an admin default.
- DO NOT load a local `subskills/` tree beneath this entrypoint.
- DO NOT invoke the agent-only `process-emails-via-gateway` route from an admin frame.
- DO NOT mutate actor identity from prompt wording or continue an admin route after `agents self join` succeeds.
- DO NOT execute welcome-style or `help` requests as mutating operations, or invoke `$houmao-admin-welcome` automatically.
