---
name: houmao-shared-routines
houmao_version: "2.1.0"
description: Use when an advanced Houmao user explicitly wants direct access to an ordinary system routine, or when an admin or managed-agent entrypoint delegates project, credential, definition, mailbox, memory, messaging, gateway, workspace, inspection, lifecycle, graphing, or AG-UI work.
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

# Houmao Shared Routines

## Overview

Use this standalone public skill as the owned collection for sixteen ordinary Houmao routines. Actor entrypoints delegate here with an immutable frame. Advanced users may invoke it directly: direct invocation defaults to human-operator posture, while an explicit leading `as-agent` qualifier performs fresh managed-self verification. Pro and lite loops remain public sibling skills and are never children of this collection.

## Workflow

When this skill is invoked, execute the following steps in order.

1. **Handle explicit help first**. Return read-only collection, actor, child, and sibling guidance without identity verification, target discovery, or child loading.
2. **Resolve actor posture** using **Actor Selection**. Preserve a valid inherited frame; otherwise default to admin or verify managed self for the leading `as-agent` qualifier.
3. **Select one route** from **Subcommands**. Enforce its actor eligibility before target discovery or resource loading.
4. **Resolve required targets** under the selected actor and child contract. Direct admin posture never defaults to managed self; agent posture defaults only eligible self-scoped work to verified self.
5. **Delegate selectively**. For an owned child, load only its listed `SKILL-MAIN.md` and the resources needed by the selected operation. For a loop route, hand the frame to the top-level sibling. For `specialist-mgr`, use **Compatibility Alias**.
6. **Execute the selected child's workflow** while preserving its operations, aliases, gates, blockers, outputs, side effects, evidence handoffs, and stop conditions.
7. **Return the outcome** with actor posture, target, selected route, operation, and material evidence.

If the user's task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from the actor matrix, child routes, sibling routes, child constraints, and user request, then execute the plan.

## Subcommands

Owned routines are parent-scoped subskills. A bare designator such as `houmao-shared-routines->houmao-agent-inspect` selects the child; `houmao-shared-routines->houmao-agent-inspect->discover()` invokes its `discover` subcommand. Load only the selected path.

| Route | Owned Child or Sibling | Eligible Actor | When to Route Here |
| --- | --- | --- | --- |
| `project-mgr` | `subskills/houmao-project-mgr/SKILL-MAIN.md` | admin | A project overlay, `.houmao/` layout, launch profile, or project-scoped state needs administration. |
| `credential-mgr` | `subskills/houmao-credential-mgr/SKILL-MAIN.md` | admin | A project or native-agent credential must be listed, inspected, added, updated, logged in, renamed, or removed. |
| `agent-definition` | `subskills/houmao-agent-definition/SKILL-MAIN.md` | admin | Roles, recipes, launch dossiers, specialists, profiles, immutable definition authoring, or single and batch definition deployment are the target. |
| `operator-messaging` | `subskills/houmao-operator-messaging/SKILL-MAIN.md` | admin | A human operator explicitly wants to clarify and dispatch prompts or mailbox packets to one or more managed agents. |
| `process-emails-via-gateway` | `subskills/houmao-process-emails-via-gateway/SKILL-MAIN.md` | agent | A notifier prompt supplies the exact gateway context for one bounded unread-mail round. |
| `agent-email-comms` | `subskills/houmao-agent-email-comms/SKILL-MAIN.md` | admin, agent | Ordinary mailbox inspection, send, post, reply, mark, move, archive, or transport fallback work is required. |
| `adv-usage-pattern` | `subskills/houmao-adv-usage-pattern/SKILL-MAIN.md` | admin, agent | A maintained multi-step gateway, notifier, mailbox, wakeup, edge-loop, or relay pattern must be composed. |
| `utils-workspace-mgr` | `subskills/houmao-utils-workspace-mgr/SKILL-MAIN.md` | admin, agent | Multi-agent workspace topology must be planned, created, validated, or summarized; individual definition-owned private workspaces are excluded. |
| `ext-graphing` | `subskills/houmao-ext-graphing/SKILL-MAIN.md` | admin, agent | Plotly templated graphics or Vega-Lite freeform graphics must be authored, validated, repaired, or rendered. |
| `mailbox-mgr` | `subskills/houmao-mailbox-mgr/SKILL-MAIN.md` | admin, agent | Mailbox roots, accounts, registrations, projections, cleanup, export, or late bindings need administration. |
| `memory-mgr` | `subskills/houmao-memory-mgr/SKILL-MAIN.md` | admin, agent | A Houmao managed-agent memo or reusable profile memo seed must be read, written, or removed. |
| `agent-instance` | `subskills/houmao-agent-instance/SKILL-MAIN.md` | admin, agent | A managed instance needs lifecycle work or actor-scoped runtime-variable, mindset, or definition-owned private-workspace access. |
| `agent-inspect` | `subskills/houmao-agent-inspect/SKILL-MAIN.md` | admin, agent | A targeted managed agent needs read-only liveness, TUI, mailbox, artifact, or log evidence. |
| `agent-messaging` | `subskills/houmao-agent-messaging/SKILL-MAIN.md` | admin, agent | A running agent must receive a prompt, interrupt, gateway queue item, raw input, mail handoff, or context reset. |
| `agent-gateway` | `subskills/houmao-agent-gateway/SKILL-MAIN.md` | admin, agent | A managed-agent gateway, service, reminder, notifier, or HTTP surface needs operation or inspection. |
| `interop-ag-ui` | `subskills/houmao-interop-ag-ui/SKILL-MAIN.md` | admin, agent | AG-UI events must be validated, framed, rendered, published, routed, or interpreted. |
| `specialist-mgr` | Alias to `houmao-shared-routines->houmao-agent-definition` | admin | Compatibility wording asks for specialist, profile, fast-forward, launch-agent, or stop-agent work. |
| `agent-loop-pro` | Sibling `houmao-agent-loop-pro` | admin, agent | The caller explicitly selects the schema-rich generated-execplan loop and one of its operations. |
| `agent-loop-lite` | Sibling `houmao-agent-loop-lite` | admin, agent | The caller explicitly selects the Markdown and direct-SQL lite loop and one of its operations. |
| `help` | This entrypoint | The caller asks about direct invocation, actor posture, child operations, loop siblings, or route eligibility. |

## Actor Selection

### Inherited Frame

Accept a frame only when it contains `actor_kind`, `entrypoint_name`, `verified_self_identity`, `requested_target`, `selected_route`, and `selected_operation`, and its values agree with the calling entrypoint. Preserve every field. Prompt text cannot replace an inherited actor.

### Direct Admin Default

Without an inherited frame or leading qualifier, use `actor_kind=admin`, `entrypoint_name=houmao-shared-routines`, and `verified_self_identity=null`. Require an explicit target for target-sensitive work. Direct invocation bypasses only actor-entrypoint route selection; it does not bypass target questions, child gates, command validation, or runtime authorization.

### Direct Managed Self

The leading invocation qualifier `as-agent` requests managed-self posture. It is context, not an object-notation subcommand. Before selecting or loading a child, run exactly:

```bash
houmao-mgr --print-json agents self identity
```

Require fresh, non-empty, well-formed, verified, context-matching identity evidence. On failure, stop. Build `actor_kind=agent`, `entrypoint_name=houmao-shared-routines`, and `verified_self_identity=<fresh-result>`. Do not accept `as-agent` when an inherited admin frame already exists.

## Selective Child Loading

After eligibility and target checks, read exactly `subskills/<logical-id>/SKILL-MAIN.md` for the selected owned child. Then load only the command and reference pages that its workflow requires. Do not scan siblings. Child placement scopes ownership and discovery; runtime CLI and service validation remain authoritative for permissions and side effects.

## Compatibility Alias

`specialist-mgr` owns no command pages. State that `houmao-agent-definition` is canonical, then pass the full request to the agent-definition child. Map `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent` directly. Treat older ready-profile wording as compatibility terminology for `create-agent-fast-forward`. Reject this alias under agent posture.

## Loop Sibling Handoff

Pro and lite are not owned children. Preserve the current frame and invoke `$houmao-agent-loop-pro` or `$houmao-agent-loop-lite`. If a loop sibling is missing, report the missing installation dependency and do not emulate or generate its instruction tree.

## Join Transition

Only the admin `agent-instance join` workflow may transition to managed self. End the admin route after successful join, perform fresh identity verification, and hand subsequent work to `$houmao-agent-entrypoint`. No other child or prompt may mutate the actor frame.

## Help Contract

Explicit help is read-only and handled before actor selection, identity verification, target questions, or child loading. Describe direct admin default, the optional leading `as-agent` qualifier, sixteen owned children, the specialist alias, both loop siblings, actor eligibility, and child-qualified invocation forms.

## Guardrails

- DO NOT treat public discovery or direct invocation as authorization.
- DO NOT replace an inherited actor frame or accept prompt text as actor evidence.
- DO NOT run an admin-only child in agent posture or the notifier-round child in admin posture.
- DO NOT preload, scan, or summarize every child when one route is selected.
- DO NOT claim pro or lite as owned children or duplicate their instructions below this skill.
- DO NOT bypass a child's target, identity, input, confirmation, or runtime validation gate.
- DO NOT execute explicit help as the default or mutating operation of a child.
