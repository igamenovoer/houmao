## Context

Houmao already exposes most of the inspection data needed to understand a managed agent, but those surfaces are fragmented across different seams and skills:

- coarse managed-agent identity and availability through `houmao-mgr agents list` and `houmao-mgr agents state`
- transport-specific detail through `GET /houmao/agents/{agent_ref}/state/detail`
- live gateway posture through `houmao-mgr agents gateway status`
- raw gateway-owned TUI tracking through `houmao-mgr agents gateway tui state|history|watch`
- mailbox discovery and actor-scoped mailbox state through `houmao-mgr agents mail resolve-live`, `status`, and `check`
- late mailbox-binding posture through `houmao-mgr agents mailbox status`
- headless turn evidence through `houmao-mgr agents turn status|events|stdout|stderr`
- runtime-owned artifacts such as `manifest.json`, `gateway/state.json`, `gateway/logs/gateway.log`, and headless turn-artifact files under the session root
- raw tmux visibility through direct tmux attach or pane capture on the local host

Today those surfaces are spread across `houmao-agent-instance`, `houmao-agent-messaging`, `houmao-agent-gateway`, `houmao-agent-email-comms`, `houmao-mailbox-mgr`, and general runtime docs. That makes "inspect this managed agent" a cross-cutting read problem with no dedicated packaged owner.

The main constraints for this change are:

- inspection must remain read-oriented and must not collapse into prompt, interrupt, attach, detach, repair, registration, or cleanup workflows
- supported managed-agent and gateway seams should stay authoritative whenever they already expose the needed state
- direct filesystem and tmux peeking must remain bounded local fallback paths rather than the default first step
- the packaged system-skill catalog must stay flat and continue using named sets plus fixed auto-install selections

## Goals / Non-Goals

**Goals:**

- Add a canonical packaged Houmao-owned `houmao-agent-inspect` skill for read-only managed-agent inspection.
- Route generic inspection through a stable evidence ladder that starts from supported CLI or HTTP surfaces and falls back to local artifacts only when needed.
- Cover both TUI-backed and headless managed agents under one inspection-oriented skill without pretending they share the same observation model.
- Clarify ownership boundaries so lifecycle, messaging, gateway, and mailbox skills remain focused on their primary operational domains.
- Install the new skill by default wherever Houmao already installs the current managed-agent operational skill family.

**Non-Goals:**

- Add a new runtime control API or a new `houmao-mgr agents inspect` command family in this change.
- Move ordinary prompt, interrupt, mailbox send or reply, gateway attach or detach, or mailbox registration flows into the new skill.
- Replace the manual `terminal-recorder-workflow` skill or make recorder capture part of the default inspection path.
- Rework the managed-agent detail API, mailbox protocol, or gateway protocol beyond how the new skill consumes their current surfaces.

## Decisions

### 1. Add one dedicated read-only inspection skill instead of extending lifecycle or gateway skills

`houmao-agent-inspect` will become the packaged owner of generic "inspect this managed agent" work. Extending `houmao-agent-instance` would keep inspection mixed with lifecycle mutation, while extending `houmao-agent-gateway` would incorrectly center all inspection on gateway-specific state even when no live gateway is attached.

Alternatives considered:

- Extend `houmao-agent-instance`: rejected because lifecycle and inspection are different operator intents and have different safety boundaries.
- Fold inspection into `houmao-agent-messaging`: rejected because mailbox, logs, artifacts, and raw tmux visibility are not primarily messaging concerns.
- Keep the current fragmented model: rejected because it leaves no canonical entry point for inspection.

### 2. Use a supported-surface-first evidence ladder

The skill will route inspection in this order:

1. managed-agent discovery and summary state
2. transport-specific detail or live gateway TUI state
3. actor-scoped mailbox posture
4. runtime-owned logs and artifacts
5. raw tmux peeking only when the caller explicitly needs the live pane or supported surfaces are insufficient

This keeps the managed-agent seam authoritative while still allowing local spelunking when the supported surfaces do not expose the needed evidence.

Alternatives considered:

- Prefer raw tmux visibility first: rejected because it is local-only, easy to misread, and weaker than the maintained discovery surfaces for identity and transport posture.
- Restrict the skill to managed-agent CLI only: rejected because the existing detail API and local artifact inventory are already part of the supported inspection story.

### 3. Model inspection by intent, with transport-specific action lanes

The new skill will use one top-level router and action-specific guidance pages:

- `discover`
- `screen`
- `mailbox`
- `logs`
- `artifacts`

`screen` will diverge by transport:

- TUI-backed agents: use summary state, managed-agent detail, and live gateway TUI state or history when present; raw tmux attach or capture is a local last-resort lane
- headless agents: use managed-agent detail plus `agents turn status|events|stdout|stderr`; do not teach auxiliary tmux topology as the primary inspection contract

Alternatives considered:

- One monolithic SKILL.md: rejected because inspection spans too many evidence classes and would become hard to route safely.
- Separate TUI and headless skills: rejected because the initial user intent is still "inspect this managed agent" and the transport split should remain inside the skill.

### 4. Keep mailbox inspection split between actor-scoped follow-up and structural admin views

The new skill will treat mailbox inspection as two different domains:

- actor-scoped mailbox posture and unread state through `agents mail resolve-live`, `agents mail status`, and `agents mail check`
- structural mailbox or late-binding inspection through `houmao-mailbox-mgr` and `agents mailbox status`

This reuses the current mailbox boundary instead of duplicating transport-local mailbox internals in the new skill.

Alternatives considered:

- Duplicate mailbox manager guidance inside `houmao-agent-inspect`: rejected because it would blur actor-state and structural-state semantics.
- Restrict the skill to non-mailbox inspection: rejected because mailbox posture is part of understanding a live managed agent.

### 5. Install the new skill as a first-class managed-agent operational skill

The packaged catalog will define a dedicated `agent-inspect` named set containing `houmao-agent-inspect`. That set will be added to:

- `managed_launch_sets`
- `managed_join_sets`
- `cli_default_sets`

The skill will remain separate from `user-control`, `agent-instance`, `agent-messaging`, and `agent-gateway` rather than being folded into another set.

Alternatives considered:

- Fold the skill into `agent-gateway`: rejected because inspection is broader than gateway state.
- Add it only to CLI defaults: rejected because managed homes should receive the same canonical operational skill set.

### 6. Clarify existing skill boundaries by delegation rather than by removing useful local checks

`houmao-agent-messaging` and `houmao-agent-gateway` will keep the inspection surfaces they need for their own operational paths, such as gateway queue decisions or gateway-only TUI tracker work. But generic requests to inspect liveness, mailbox posture, logs, runtime artifacts, or tmux backing will route to `houmao-agent-inspect`.

This preserves existing supported workflows without leaving inspection ownership ambiguous.

## Risks / Trade-offs

- [Multiple inspection surfaces may disagree] → Mitigation: define the evidence ladder explicitly and keep summary state or managed-agent detail ahead of raw tmux or file inspection.
- [CLI lacks a first-class wrapper for `/houmao/agents/{agent_ref}/state/detail`] → Mitigation: allow the skill to use managed-agent HTTP routes when already operating in pair-managed context, and otherwise keep CLI plus local artifact guidance sufficient.
- [Raw tmux attach can tempt callers into mutation] → Mitigation: position raw tmux peeking as a local last-resort inspection lane and prefer capture or read-oriented guidance before attach.
- [Boundary overlap with messaging or gateway skills may remain confusing] → Mitigation: add explicit delegation requirements to the modified skill specs and keep the new skill read-only.

## Migration Plan

1. Add the new packaged `houmao-agent-inspect` skill assets and action pages under the maintained system-skill asset root.
2. Update the packaged system-skill catalog and auto-install selections to include the new `agent-inspect` set.
3. Update existing packaged skill guidance where generic inspection ownership needs explicit delegation.
4. Update tests and operator-facing inventory expectations for `houmao-mgr system-skills`.

Rollback is straightforward because this change adds one packaged skill and catalog membership without requiring persistent data migration. If the rollout must be reverted, Houmao can remove the packaged skill assets and catalog references and reinstall the previous skill selection.

## Open Questions

- Should a later follow-up add a first-class CLI wrapper for managed-agent detailed inspection so the skill does not need to rely on pair-managed HTTP when it wants `/state/detail`?
- Should `houmao-touring` explicitly route generic live-agent inspection to `houmao-agent-inspect` in the same implementation change, or can that remain a small follow-up once the new skill exists?
