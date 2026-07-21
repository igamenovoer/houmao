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

# Dispatch

Use this page when the operator selects `dispatch` or asks this skill to send one or more messages to Houmao-managed agents.

## Inputs

Dispatch can start from:

- clarified intent in chat memory;
- an explicit dispatch prompt in the current request;
- a user-specified external Markdown intent record.

If the operator references an external Markdown record, read that exact path. Do not search for or invent a record path.

## Preflight

Before sending:

1. Confirm the task is a temporary operator messaging action, not durable loop orchestration.
2. Identify target agents, message content, ordering, expected replies, and any explicit or context-implied request for mailbox delivery.
3. Ask only blocking questions if a missing fact could send to the wrong target, use the wrong route, or violate a stated constraint.
4. If the task needs broad clarification rather than a blocking value, stop and recommend `clarify`.
5. If the task needs durable state, retries, scheduling, generated skills, topology validation, or recovery, recommend `<public-entrypoint>->houmao-shared-routines->agent-loop-pro` or `<public-entrypoint>->houmao-shared-routines->agent-loop-lite`.

## Packet Plan

Prepare a compact packet plan before sending. Include one row per packet:

| Field | Meaning |
| --- | --- |
| Target | Managed agent, target mailbox, or target-selection result. |
| Route | `prompt` by default, or `mailbox` when requested or implied by chat context. |
| Content | Prompt/body summary or the concrete message when short. |
| Order | Sequence, priority, or parallel-safe note. |
| Reply expectation | Expected acknowledgement, result, evidence, or no reply. |
| Record update | Chat summary only, or external Markdown path to update. |

The user's task determines whether the plan has one packet or multiple packets. Do not ask the operator to choose a separate single-agent or multi-agent dispatch mode.

## Route Selection

Default to prompt delivery:

- Use prompt delivery for every packet unless the current operator prompt or chat context indicates mailbox delivery.
- Use `<public-entrypoint>->houmao-shared-routines->agent-messaging` ordinary prompt behavior for prompt packets.
- If the target has a live gateway, use ready-only gateway-backed prompt delivery.
- If the target has no live gateway, use ordinary direct managed-agent prompt delivery.
- Select `if-no-pending` or `always` only when the operator explicitly requests the corresponding busy-TUI behavior.
- Do not choose mailbox merely because the target has a mailbox.

Use mailbox only when:

- the operator requests mailbox delivery;
- chat context says the dispatch should be delivered by mail, inbox, thread, asynchronous mailbox note, or reply reference;
- the operator explicitly wants mailbox sender identity semantics.

If a required route is unavailable, report the blocker or ask whether an alternate route is acceptable before sending. Do not silently switch routes.

## Last-Mile Delegation

For `prompt` packets:

- Use `<public-entrypoint>->houmao-shared-routines->agent-messaging`.
- Let that skill own discovery, prompt, gateway-preferred admission-policy selection, fallback managed delivery, and concrete command/API details.

For `mailbox` packets:

- Use `<public-entrypoint>->houmao-shared-routines->agent-email-comms`.
- Let that skill own ordinary mailbox send, operator-origin post, live gateway facade, resolver, and no-gateway fallback details.

## Mailbox Identity

For mailbox dispatch, classify the current operator posture:

- If the current operator agent is a Houmao-managed agent with a usable mailbox binding, use that agent's own mailbox address for ordinary mailbox sends.
- If the current operator agent is outside the Houmao-managed runtime, or no usable own mailbox binding is available, use the supported operator-origin mailbox `post` path.
- Treat the reserved operator-origin sender as the external-operator route. Do not invent per-operator mailbox identities.

Use maintained Houmao facts when available: current context, managed-agent environment facts, gateway/mail resolver output, mailbox binding data, or the lower-level mailbox skill's caller-classification guidance. If required facts are missing, ask for the missing Houmao runtime input.

## Sending

- Send packets in the order required by the task.
- If order is irrelevant and the operator permits parallel or independent delivery, the summary may describe the packets as independent.
- Stop before sending any packet whose target, route, or content remains materially unsafe or unclear.
- Do not send partial batches when doing so would create misleading coordination state; report the blocked plan instead.

## External Records

When dispatch consumes or updates an external Markdown record:

- Use only the path supplied by the operator.
- Append or update a compact dispatch section with target, route, sent/blocked status, timestamp if available, and follow-up expectations.
- Do not store long analysis or duplicate full low-level command output unless the operator asks.

## Summary

After dispatch, report:

- number of packets planned and sent;
- targets reached;
- route used for each target or group;
- blocked packets and reason;
- expected replies or evidence;
- external record path updated, if any.
