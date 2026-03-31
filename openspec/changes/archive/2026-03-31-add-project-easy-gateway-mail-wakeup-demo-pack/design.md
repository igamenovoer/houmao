## Context

The repository already contains archived mailbox and gateway demo packs, including a legacy single-agent gateway wake-up pack and a legacy mail ping-pong pack. Those packs are useful reference material, but the maintained `scripts/demo/` surface currently lacks a supported demo for the modern `houmao-mgr project easy` workflow that operators now use for Claude Code and Codex TUI specialists.

The target workflow is already expressed as a validated testcase: create a demo-owned project, initialize project-local state, create a specialist through `project easy`, attach a live gateway, enable mail notifier polling, inject one filesystem-backed operator message, observe agent wake-up, and verify both artifact creation and actor-scoped unread completion. The design must keep all generated state under the demo output root while avoiding dependence on `<project>/.houmao` as an incidental cwd-relative default.

## Goals / Non-Goals

**Goals:**
- Publish a supported runnable demo under `scripts/demo/single-agent-mail-wakeup/` for the single-agent project-easy gateway wake-up flow.
- Support two maintained lanes: Claude Code TUI and Codex TUI.
- Keep the copied project, redirected overlay, logs, deliveries, and evidence under one demo-owned output root that is ignored from git.
- Use `HOUMAO_PROJECT_OVERLAY_DIR` as the authoritative overlay-selection contract so the demo can run from the copied project root while storing Houmao overlay state under a sibling demo-owned directory.
- Define one stable success contract built on gateway wake-up evidence, agent-created output, actor-scoped unread completion, and structural project-mailbox inspection.

**Non-Goals:**
- Reworking existing product CLI contracts for `project`, `project easy`, `project mailbox`, or gateway mail-notifier behavior.
- Supporting headless lanes, mixed TUI/headless lanes, or two-agent ping-pong behavior in this demo pack.
- Promoting archived demo packs wholesale without adapting them to the maintained project-easy and overlay-redirected workflow.
- Defining a new authoritative mailbox read-state contract on project-mailbox admin surfaces.

## Decisions

### Create a new supported pack instead of reviving a legacy pack in place

The new workflow differs materially from the archived single-agent wake-up pack: it is project-scoped, `project easy`-driven, and verification now treats `project mailbox messages list|get` as structural inspection rather than read-state authority. A new supported demo under `scripts/demo/single-agent-mail-wakeup/` keeps the maintained surface clear and avoids inheriting legacy operator contracts that no longer match current behavior.

Alternative considered: move the archived `gateway-mail-wakeup-demo-pack` out of `legacy/` and update it in place. Rejected because the new demo should present a different operator story and filesystem contract rather than disguising a compatibility break as a simple relocation.

### Keep the copied project and the Houmao overlay as sibling roots under the demo output directory

The demo output root will contain both:
- `project/`: copied dummy project and operator-visible worktree
- `overlay/`: redirected Houmao project overlay root

All project-aware commands will run from `project/` while exporting `HOUMAO_PROJECT_OVERLAY_DIR=<output-root>/overlay`. This keeps project files easy to inspect, keeps Houmao state clearly separated, and uses the documented automation-oriented overlay redirect contract instead of relying on `<cwd>/.houmao`.

Alternative considered: put `.houmao/` inside the copied project. Rejected because the repo already exposes `HOUMAO_PROJECT_OVERLAY_DIR` for controlled automation, and separating project content from overlay state makes ownership and cleanup clearer.

### Reuse the legacy single-agent wake-up pack as implementation reference, not as behavioral source of truth

The legacy single-agent wake-up pack already has a useful shape for:
- tool-scoped output roots,
- generated-state containment,
- pack-local `.gitignore`,
- delivery artifact staging,
- inspect/report generation,
- auto/start/inspect/verify/stop style commands.

The new pack should reuse that structural pattern where it still fits, but the behavior contract must be rewritten around `project init`, `project easy specialist create`, `project mailbox`, and actor-scoped mailbox completion.

Alternative considered: derive the new pack from the two-agent ping-pong pack. Rejected because ping-pong introduces server-owned, two-agent, and multi-turn concerns that are orthogonal to this single-agent project-easy wake-up tutorial.

### Scope the supported lanes to Claude Code TUI and Codex TUI only

The demo will support only the two maintained TUI lanes because the motivating testcase is a TUI wake-up flow and because this keeps the operator story narrow:
- launch one project-easy specialist,
- attach one gateway,
- watch one wake-up,
- verify one artifact and one unread-set completion condition.

Alternative considered: include headless or mixed-mode parity in the first version. Rejected because that expands the launch and observation matrix without improving the clarity of the core single-agent wake-up teaching flow.

### Use actor-scoped unread completion as the success boundary

The demo will verify completion through `houmao-mgr agents mail check --unread-only` together with the requested output artifact and gateway notifier evidence. `houmao-mgr project mailbox messages list|get` remains part of the demo, but only as structural inspection of canonical and projection metadata.

Alternative considered: require project-mailbox `read: true` for the delivered message. Rejected because the repository explicitly removed that ambiguous contract from mailbox admin and project-mailbox inspection surfaces.

### Keep the command surface tutorial-shaped

The demo should expose:
- `auto`
- `start`
- `manual-send`
- `inspect`
- `verify`
- `stop`
- `matrix`

This is enough for one-shot success, stepwise inspection, and both-tool coverage without introducing the higher-volume message-driving behaviors used by broader legacy packs.

Alternative considered: start with burst delivery or multi-message drive loops. Rejected because those workflows belong to the broader archived gateway demos, not to the narrow project-easy wake-up tutorial.

## Risks / Trade-offs

- [Gateway attach and notifier enable race after launch] -> The pack should retain an explicit readiness check and allow one bounded retry path before treating the run as failed.
- [Project-easy launch posture drifts away from unattended TUI defaults] -> The demo should verify the selected specialist launch posture during start/inspect and fail clearly if the lane is not runnable unattended.
- [Fixture auth layout differs across tools or local machines] -> Preflight should check the expected Claude and Codex fixture auth roots up front and name the missing path in failures.
- [Overlay redirect is forgotten for one subcommand] -> Centralize command invocation through one helper that always exports `HOUMAO_PROJECT_OVERLAY_DIR` for project-aware commands.
- [Legacy helper reuse pulls in outdated verification assumptions] -> Keep the verification contract explicit in the new pack and treat legacy code as implementation reference only.

## Migration Plan

1. Add the new supported demo under `scripts/demo/single-agent-mail-wakeup/`.
2. Add the demo to `scripts/demo/README.md` as a supported demo.
3. Keep the archived legacy gateway and ping-pong packs in `scripts/demo/legacy/` for historical reference.
4. Land demo-local inputs, runner, README, `.gitignore`, and implementation code together so the supported surface is complete when introduced.

No user-data migration is required because this change adds a new demo surface and demo-owned generated output roots only.

## Open Questions

- None for apply-ready planning. The remaining work is implementation detail within the chosen pack contract.
