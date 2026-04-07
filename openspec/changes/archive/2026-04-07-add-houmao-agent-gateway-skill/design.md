## Context

Houmao already exposes a broad gateway surface, but the current packaged system-skill split does not give that surface one canonical skill boundary.

Today the repository already has:

- lifecycle-oriented guidance in `houmao-manage-agent-instance`,
- communication-oriented guidance in `houmao-agent-messaging`,
- transport and mailbox-round guidance in the mailbox skills,
- implemented gateway behavior for attach, detach, status, raw TUI tracking, direct control, mail-notifier, and in-memory wakeups.

That leaves a gap. Gateway-specific work such as attach flows, current-session discovery, direct gateway-only HTTP routes, and reminder surfaces like `/v1/wakeups` or `mail-notifier` either gets mixed into the messaging skill or left to raw documentation. The desired skill needs to serve both:

- outsiders working from outside the attached session through `houmao-mgr agents gateway ...` or `/houmao/agents/{agent_ref}/gateway...`, and
- an attached agent working from inside the managed tmux session through manifest-first discovery, live gateway bindings, and direct gateway-only surfaces when those are the supported path.

The packaged system-skill catalog also controls default installation into managed homes and explicit external tool homes, so adding the new gateway skill is not just a docs change. The catalog, list/install/status output, and user-facing docs all need to acknowledge the new skill.

## Goals / Non-Goals

**Goals:**

- Add a packaged Houmao-owned system skill named `houmao-agent-gateway`.
- Make that skill the canonical packaged entry point for gateway-specific lifecycle, discovery, gateway-only control, and gateway reminder services.
- Keep the skill accurate to the current implementation, including manifest-first attach discovery, live-binding rules, and the fact that wakeups are direct gateway HTTP and are not durable across gateway restart.
- Include the new skill in managed auto-install and CLI-default installs so both attached agents and external operators can use it.
- Update the current system-skills inventory docs so the new gateway skill appears alongside lifecycle and messaging skills with a clear boundary.

**Non-Goals:**

- No new gateway API, CLI command family, or managed-agent server projection is introduced by this change.
- No new durable reminder queue is added; wakeups stay ephemeral and mail-notifier stays mail-specific.
- No ordinary prompt/mail workflow is moved wholesale out of `houmao-agent-messaging` or the mailbox skills.
- No launch, join, stop, relaunch, or cleanup lifecycle work moves into the new gateway skill.
- No transport-specific filesystem or Stalwart mailbox internals are duplicated into the new skill.

## Decisions

### 1. Add a separate packaged gateway skill instead of broadening the messaging skill

The new surface will live in its own packaged directory under `src/houmao/agents/assets/system_skills/houmao-agent-gateway/`.

Why:

- Gateway lifecycle and gateway-only control are not the same concern as ordinary managed-agent conversation.
- `houmao-agent-messaging` already has a clear “communicate with an already-running agent” role.
- A separate gateway skill keeps the product split legible:
  - `houmao-manage-agent-instance` = live-agent lifecycle
  - `houmao-agent-messaging` = ordinary communication and mailbox follow-up
  - `houmao-agent-gateway` = gateway-specific lifecycle, discovery, and gateway-only services

Alternative considered:

- Expand `houmao-agent-messaging` to absorb attach, detach, wakeups, notifier control, and gateway discovery.
- Rejected because it would blur ordinary communication with gateway control-plane behavior and make the messaging skill too broad.

### 2. Organize the gateway skill by gateway intent, not by every route family

The top-level `SKILL.md` will route into local action pages such as:

- lifecycle
- discover
- gateway-services
- wakeups
- mail-notifier

Why:

- Users usually know they want to attach, inspect, schedule a reminder, or manage notifier behavior before they know the exact route family.
- This matches the current gateway docs better than flattening every HTTP path into the top-level skill.

Alternative considered:

- Make the skill a raw endpoint index only.
- Rejected because the existing system-skill family favors routing/action pages rather than one flat route inventory.

### 3. Prefer the managed-agent seam first, then drop to direct gateway HTTP only when that is the actual supported path

The new skill will prefer:

- `houmao-mgr agents gateway ...` for CLI-driven lifecycle and notifier work,
- `/houmao/agents/{agent_ref}/gateway...` for pair-managed HTTP control,
- direct `{gateway.base_url}/v1/...` only when the task genuinely requires the live gateway listener and the exact base URL is already available from a supported discovery result.

That especially matters for wakeups, because the current implementation exposes them only on direct `/v1/wakeups` and does not project them through `houmao-mgr agents gateway ...` or the managed-agent API.

Why:

- The managed-agent seam is the stable public control surface when it exists.
- Direct gateway HTTP should stay a lower-level gateway-only tool, not the default teaching path.
- This keeps the skill honest about today’s implementation gaps around wakeup projection.

Alternative considered:

- Treat the direct gateway listener as the primary surface whenever a live gateway exists.
- Rejected because it bypasses the intended public control seam and forces unnecessary endpoint discovery.

### 4. Distinguish three discovery lanes in the skill instead of pretending one rule covers everything

The skill will describe three distinct discovery rules:

- manifest-first current-session discovery for attach/lifecycle targeting inside the owning tmux session,
- live gateway binding discovery through `HOUMAO_AGENT_GATEWAY_HOST`, `HOUMAO_AGENT_GATEWAY_PORT`, and validated live status when the caller already needs the live listener,
- `houmao-mgr agents mail resolve-live` for mailbox-related gateway work where the supported contract is exact `gateway.base_url`.

Why:

- The repo explicitly treats mailbox façade discovery as different from generic gateway env scraping.
- The current implemented contract is manifest-first, not `HOUMAO_GATEWAY_ATTACH_PATH`/`HOUMAO_GATEWAY_ROOT` first.
- The skill needs to avoid teaching one discovery shortcut that is wrong for mailbox work or current-session attach.

Alternative considered:

- Tell agents to always scrape live gateway env vars directly.
- Rejected because that is not the supported mailbox discovery contract and it ignores manifest-first attach rules.

### 5. Add the gateway skill to managed auto-install as well as CLI-default installs

The packaged catalog will gain a dedicated named set for `houmao-agent-gateway`.

That set will be included in:

- `managed_launch_sets`
- `managed_join_sets`
- `cli_default_sets`

Why:

- The attached agent is one of the intended users of the skill, especially for current-session discovery and self-reminder workflows.
- External operator installs also need it through the CLI-default install path.
- This follows the same reasoning used earlier for `houmao-agent-messaging`.

Alternative considered:

- Keep `houmao-agent-gateway` CLI-default only.
- Rejected because it would fail the “inside the attached agent” half of the requested workflow.

### 6. Be explicit that wakeups are useful but not durable

The skill will describe:

- `/v1/wakeups` as the supported short-lived self-reminder surface,
- those wakeups as in-memory live-gateway state,
- loss of pending wakeups on gateway stop or restart,
- mail-notifier as mailbox-unread reminder control rather than a general unfinished-job persistence layer.

Why:

- This is one of the main places a skill can accidentally overpromise.
- The existing gateway contract is explicit that wakeups are ephemeral and direct.
- The user’s desired “unfinished jobs” guidance must stay accurate to the current implementation.

Alternative considered:

- Present wakeups as the general failure-recovery answer for unfinished jobs.
- Rejected because the current gateway contract does not make that durability guarantee.

## Risks / Trade-offs

- [Gateway and messaging responsibilities could overlap in confusing ways] → Keep the new skill gateway-specific and keep ordinary prompt/mail work centered on `houmao-agent-messaging` plus the mailbox skills.
- [The skill could accidentally teach retired or partial discovery contracts] → Anchor the skill on manifest-first attach discovery, live binding env only for live listener discovery, and `agents mail resolve-live` for mailbox façade discovery.
- [Users may overtrust wakeups as durable recovery state] → State the in-memory lifetime and restart-loss behavior explicitly in the skill and docs requirements.
- [Adding another managed auto-install skill broadens the default surface] → Keep the new skill narrowly focused and update the docs that enumerate the current packaged families.
- [Documentation drift could persist if inventory pages are not updated with the new skill] → Modify the README and CLI-reference specs alongside the skill and installer specs in the same change.

## Migration Plan

1. Add the new packaged `houmao-agent-gateway/` skill tree with router, action pages, references, and metadata.
2. Extend the packaged system-skill catalog with the new skill and a dedicated named set.
3. Update the fixed managed-launch, managed-join, and CLI-default set lists to include the new set.
4. Update the `houmao-mgr system-skills` inventory expectations and the docs that enumerate the packaged skill families.
5. Update focused catalog/installer/CLI tests and any doc-facing tests that assert the current inventory.
6. Roll back by removing the packaged skill tree and reverting the catalog, CLI inventory, docs, and test updates. No persisted user data migration is required.

## Open Questions

- None for proposal scope. If later work adds managed-agent or CLI projections for wakeups, the skill can prefer those higher-level surfaces without changing its role as the gateway-focused packaged skill.
