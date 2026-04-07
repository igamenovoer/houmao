## Context

Houmao already exposes several communication and control seams for managed agents:

- the ordinary managed-agent prompt and interrupt path through `houmao-mgr agents ...` and `POST /houmao/agents/{agent_ref}/requests`
- explicit queued gateway control through `houmao-mgr agents gateway prompt|interrupt` and `POST /houmao/agents/{agent_ref}/gateway/requests`
- raw live control input through `houmao-mgr agents gateway send-keys` and `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`
- mailbox follow-up through `houmao-mgr agents mail ...` and `POST /houmao/agents/{agent_ref}/mail/*`
- lower-level direct gateway HTTP such as `/v1/control/prompt`, `/v1/control/send-keys`, and `/v1/control/headless/next-prompt-session`

Those surfaces already differ in timing, authority, and intent. The docs explicitly separate synchronous prompt turns, queued gateway work, raw control input, mailbox follow-up, and lower-level gateway control. The current packaged Houmao-owned system-skill set, however, has no single skill that teaches agents or external operators how to choose between those paths.

The new `houmao-agent-messaging` skill therefore needs to be:

- broad enough to route across the existing communication surfaces,
- narrow enough not to absorb lifecycle, mailbox transport internals, or specialist CRUD,
- installable both into managed homes and into explicit external tool homes.

Because the packaged system-skill catalog controls both managed auto-install and CLI-default external install behavior, adding this skill also requires catalog, docs, and test updates.

## Goals / Non-Goals

**Goals:**

- Add a packaged Houmao-owned system skill named `houmao-agent-messaging`.
- Make that skill the canonical entry point for communicating with already-running Houmao-managed agents.
- Organize the skill around messaging intent: discovery, normal prompt, interrupt, queued gateway control, raw input, mailbox follow-up, and reset-context guidance.
- Prefer the stable managed-agent seam (`houmao-mgr agents ...` or `/houmao/agents/*`) when it already satisfies the task.
- Make the skill available by default both to managed agents and to explicit external tool-home installs.
- Document reset-context and chat-session control honestly using the current implemented gateway HTTP surfaces when no first-class `houmao-mgr` flag exists.

**Non-Goals:**

- No new runtime, pair API, or gateway control capability is introduced by this change.
- No new `houmao-mgr` messaging flags are added in this change.
- No managed-agent lifecycle actions such as launch, join, stop, relaunch, or cleanup move into this skill.
- No mailbox transport-specific filesystem or Stalwart behavior is duplicated into this skill.
- No automatic gateway attach or other lifecycle repair behavior is added just to make messaging succeed.

## Decisions

### 1. Add a separate packaged messaging skill instead of broadening `houmao-manage-agent-instance`

The new messaging surface will be a separate packaged skill under `src/houmao/agents/assets/system_skills/houmao-agent-messaging/`.

Why:

- `houmao-manage-agent-instance` already has a clear lifecycle-only boundary.
- Prompting, interrupts, raw input, queued gateway work, and mailbox follow-up are not lifecycle actions.
- A separate skill preserves a clean split:
  - instance lifecycle skill = create/adopt/stop/clean live instances
  - messaging skill = communicate with live instances that already exist

Alternative considered:

- Expand `houmao-manage-agent-instance` to include prompt, interrupt, gateway, and mailbox flows.
- Rejected because it would collapse lifecycle and communication into one broad operator skill and directly undo the current lifecycle-only boundary.

### 2. Make the new skill intent-based rather than transport-based

The top-level `SKILL.md` will route by caller intent first, not by backend implementation first. The local action layout will be organized around:

- discovery
- prompt
- interrupt
- gateway queue control
- raw `send-keys`
- mailbox follow-up
- reset-context

Why:

- The existing communication surfaces differ primarily by guarantee and intent:
  - synchronous prompt completion
  - queued gateway admission
  - exact raw terminal mutation
  - mailbox-shaped follow-up
  - reset or chat-session control
- This matches the current docs much better than grouping first by TUI, headless, filesystem mailbox, or Stalwart.

Alternative considered:

- Organize the skill by backend or transport first.
- Rejected because users and agents usually know what they want to do before they know which lower-level control path is appropriate.

### 3. Prefer the managed-agent seam first; use direct gateway HTTP only when it is the correct lower-level path

The messaging skill will prefer:

- `houmao-mgr agents ...` for CLI-driven work
- `/houmao/agents/*` for pair-managed HTTP control

It will use direct gateway `/v1/...` routes only when:

- the current task genuinely requires gateway-only control behavior, and
- the exact live gateway base URL is already available from current context or another supported discovery path.

Why:

- The managed-agent seam is the documented public control surface.
- It avoids asking agents to rediscover or guess gateway listener ports unnecessarily.
- It keeps the messaging skill aligned with the repo’s current “public seam first, lower-level control only when needed” guidance.

Alternative considered:

- Treat direct gateway HTTP as the default operational surface whenever a gateway exists.
- Rejected because the public API and CLI intentionally keep the stable caller contract at the managed-agent seam.

### 4. Include `houmao-agent-messaging` in managed auto-install as well as CLI-default installs

The packaged catalog will gain a dedicated named set for `houmao-agent-messaging`.

That set will be included in:

- `managed_launch_sets`
- `managed_join_sets`
- `cli_default_sets`

The separate `houmao-manage-agent-instance` set will remain CLI-default only.

Why:

- Managed agents need this skill in their own tool homes so they can message peer managed agents or follow operator instructions about communication/control.
- External tool homes also need the skill through CLI-default installs.
- This keeps the existing distinction:
  - lifecycle skill is mostly external/operator-facing
  - messaging skill is useful both inside managed homes and outside them

Alternative considered:

- Keep `houmao-agent-messaging` CLI-default only, like `houmao-manage-agent-instance`.
- Rejected because that would not satisfy the “agents know how to talk to each other” requirement.

### 5. Treat reset-context as an existing API-level capability, not as a new CLI guarantee

The skill will document reset-context and chat-session control through the currently implemented gateway control surfaces:

- direct prompt control with `chat_session.mode = "new"` for reset-then-send behavior
- headless `next-prompt-session` for one-shot next-prompt override

The skill will state clearly when a requested reset flow cannot stay entirely on the current `houmao-mgr` surface because there is no first-class flag for it yet.

Why:

- The capability already exists and matters for messaging.
- Inventing a fake CLI flag or implying a nonexistent `houmao-mgr` shortcut would make the skill inaccurate.
- The skill should route to the real implemented surface, not the idealized one.

Alternative considered:

- Exclude reset-context entirely until a dedicated `houmao-mgr` flag exists.
- Rejected because the user explicitly needs the skill to teach clear-context and chat-session control.

### 6. Reuse the mailbox skills rather than restating transport internals

The new messaging skill will cover mailbox intent at the communication-routing level and then hand off deeper mailbox behavior to the existing mailbox skills when needed.

Why:

- `houmao-email-via-agent-gateway`, `houmao-email-via-filesystem`, `houmao-email-via-stalwart`, and `houmao-process-emails-via-gateway` already define those transport and route contracts.
- Duplicating that logic would create drift between the messaging skill and mailbox skills.

Alternative considered:

- Re-explain all mailbox transport and gateway details inside the new skill.
- Rejected because it would create two competing sources of truth for mailbox behavior.

## Risks / Trade-offs

- [The messaging skill could become a dumping ground for unrelated controls] → Keep the scope pinned to communication with already-running managed agents and leave lifecycle/setup surfaces to their existing skills.
- [Users may confuse synchronous prompt turns, queued gateway requests, and raw `send-keys`] → Use intent-first routing and explicit boundary language in the top-level skill and per-action docs.
- [Managed auto-install broadening may surprise readers who know `houmao-manage-agent-instance` is CLI-default only] → Keep the catalog and docs explicit that `houmao-agent-messaging` is managed-auto-installed while `houmao-manage-agent-instance` remains CLI-default only.
- [Reset-context guidance could overpromise current CLI support] → State the CLI/API boundary directly and route to the existing HTTP surface when that is the only current supported path.
- [Mailbox guidance could drift if duplicated] → Route transport-specific mailbox work back to the existing mailbox skills instead of restating those contracts.

## Migration Plan

1. Add the new packaged `houmao-agent-messaging/` skill tree with its router, action docs, and metadata.
2. Add a dedicated catalog entry and named set for `houmao-agent-messaging`.
3. Update the packaged auto-install set lists so managed launch/join and CLI-default installs select the messaging skill appropriately.
4. Update README and CLI reference docs to explain the new skill and the revised install behavior.
5. Update catalog, installer, and docs-focused tests.
6. Roll back by removing the skill tree and reverting the catalog/default-selection/docs changes. No stored data migration is required.

## Open Questions

- None for this proposal scope. If later work adds first-class `houmao-mgr` chat-session/reset flags, the new skill can narrow its lower-level HTTP guidance without changing its overall role.
