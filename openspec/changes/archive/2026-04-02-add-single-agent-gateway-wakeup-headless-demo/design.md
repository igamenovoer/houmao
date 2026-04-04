## Context

The supported `single-agent-mail-wakeup/` demo is intentionally scoped to one `project easy` TUI specialist and teaches operator flows such as re-attaching to the live interactive agent surface. Houmao already supports tmux-backed native headless sessions, project-local specialist launch through `project easy instance launch --headless`, and live gateway attach for headless backends, but there is no maintained demo that exercises the full project-local mailbox wake-up workflow on that headless surface.

The new demo must preserve the strengths of the current supported pack:

- one canonical demo-owned output root,
- project-local overlay state under a sibling `overlay/`,
- reusable overlay-backed specialist/auth/setup state across fresh runs,
- project-local mailbox registration and filesystem delivery,
- live gateway attach plus mail-notifier polling,
- durable inspect and verify artifacts.

At the same time, the headless operator model differs from the TUI pack:

- the managed agent is headless, not parser-led TUI,
- readiness and verification should not depend on TUI posture,
- the session is still tmux-backed, so `attach` remains meaningful,
- the gateway should still run in a separate watchable tmux window.

## Goals / Non-Goals

**Goals:**

- Add a new supported demo pack at `scripts/demo/single-agent-gateway-wakeup-headless/`.
- Keep the demo project-local and demo-owned, with `outputs/project/`, `outputs/overlay/`, and sibling registry/control/log/evidence directories.
- Launch one project-easy specialist in headless mode while preserving a demo-owned tmux session.
- Keep the headless agent and gateway in separate tmux windows so `attach` and `watch-gateway` remain useful in stepwise operation.
- Support both automatic and stepwise flows with persisted demo state and follow-up commands.
- Verify completion through gateway evidence, headless runtime evidence, project artifact creation, and actor-scoped unread completion.
- Keep the existing `single-agent-mail-wakeup/` TUI demo unchanged as a separate supported operator surface.

**Non-Goals:**

- Reworking the existing `single-agent-mail-wakeup/` demo to serve both TUI and headless contracts.
- Changing generic managed-agent, mailbox, or gateway semantics beyond what the new demo needs.
- Adding email mailbox transport to the new demo.
- Establishing Gemini unattended readiness in this same change if the platform contract is not already maintained.
- Replacing `minimal-agent-launch/` as the smallest headless launch example.

## Decisions

### 1. Create a separate supported demo pack instead of extending the TUI pack

The new demo will live under `scripts/demo/single-agent-gateway-wakeup-headless/` and will get its own supported-demo spec and README entry.

Why:

- The existing supported demo explicitly teaches a TUI specialist contract.
- Headless readiness, inspection, and operator expectations differ even though both surfaces remain tmux-backed.
- A separate pack keeps docs, tests, and verification sharper and avoids an explosion of conditional behavior in the current pack.

Alternative considered:

- Add `--headless` lanes to `single-agent-mail-wakeup/`.
  Rejected because it would mix two operator contracts into one pack and make the maintained README and verification contract harder to understand.

### 2. Reuse the same output-root and overlay model as the TUI pack

The headless pack will still default to one canonical pack-local `outputs/` root with:

- `project/` for the copied worktree,
- `overlay/` for project-local Houmao state,
- `registry/`, `control/`, `logs/`, `deliveries/`, and `evidence/` as sibling demo-owned artifacts.

Fresh starts will preserve reusable overlay-backed specialist/auth/setup state while resetting overlay-local mailbox, runtime, jobs, and run-local evidence.

Why:

- This model already matches project-easy behavior and avoids leaking demo state into the operator environment.
- It preserves the ability to reuse project-local specialists across repeated runs.
- It keeps the new pack structurally parallel to the supported TUI pack without collapsing their contracts.

Alternative considered:

- Use per-tool output roots or independent runtime-root overrides without an overlay-first model.
  Rejected because it would diverge from the current project-local specialist workflow and make the demo less representative.

### 3. Keep a tmux-backed headless session with separate agent and gateway windows

The headless demo will still run inside one demo-owned tmux session. The managed headless agent remains in the primary agent window, and gateway attach runs in a separate watchable auxiliary window.

Stepwise commands will behave as follows:

- `start`: launch the headless specialist with `project easy instance launch --headless`, then attach the live gateway in a foreground auxiliary tmux window.
- `attach`: reattach the operator to the demo tmux session for direct inspection.
- `watch-gateway`: poll the authoritative gateway window metadata and render the gateway console without requiring manual tmux window discovery.

Why:

- Headless runtimes are still tmux-backed in Houmao’s runtime model.
- The user explicitly wants `attach` to remain meaningful.
- A separate gateway window preserves the same operator observability value as the TUI demo.

Alternative considered:

- Treat headless mode as “no tmux” and remove `attach`.
  Rejected because it does not match the actual runtime model and would weaken stepwise inspection.

### 4. Scope the maintained lanes to currently supported unattended headless backends

This change will define the new demo contract around maintained headless lanes that already have a supported unattended startup posture. That means Claude and Codex are the expected initial lanes for the new pack.

Gemini will not be treated as part of the maintained v1 contract unless its unattended launch-policy path is made explicit first.

Why:

- The demo requires unattended launch posture in order to be a reliable supported demo.
- Claude and Codex already have maintained unattended policy registries.
- Gemini headless exists as a runtime backend, but that alone is not enough to claim a maintained unattended demo lane.

Alternative considered:

- Include Gemini immediately because the backend exists.
  Rejected because the higher-level operator contract would overstate current platform readiness.

### 5. Define verification around headless runtime evidence rather than TUI posture

The new demo’s inspect and verify surfaces will continue to treat success as:

- gateway notifier evidence showing unread work was detected and processed,
- the requested deterministic project artifact being created,
- actor-scoped unread count reaching zero,
- structural project-mailbox corroboration.

In addition, the headless demo will collect managed-agent headless evidence, such as summary state, detailed state when available, and durable turn artifacts or last-turn metadata when available, instead of relying on parser-specific TUI readiness semantics.

Why:

- Headless runs should not be evaluated through interactive TUI posture assumptions.
- Managed-agent and gateway surfaces already expose transport-neutral and headless-specific state.
- Turn evidence is the natural complement to gateway notifier evidence on a headless path.

Alternative considered:

- Continue using the TUI demo’s readiness and verification signals unchanged.
  Rejected because those signals are not canonical for headless sessions.

### 6. Reuse demo structure and helpers selectively, not by forcing a shared abstraction upfront

Implementation should reuse proven patterns from the TUI demo where they already align, especially around output-root ownership, persisted state, mailbox delivery, and report sanitization. The new demo should still keep its own models, driver, runtime flow, and documentation so its operator contract remains explicit.

Why:

- The two demos share substantial filesystem and verification patterns.
- Their runtime semantics differ enough that deep early abstraction would likely blur the contracts.
- A dedicated pack makes later refactoring easier once the headless-specific workflow stabilizes.

Alternative considered:

- Fully abstract both demos behind one shared pack framework before adding the new demo.
  Rejected because it adds design and implementation risk without first proving the headless contract.

## Risks / Trade-offs

- [Headless backend differences between Claude and Codex] → Keep per-tool tracked parameters and rely on existing launch-policy coverage rather than inventing one generic launch assumption.
- [Gateway attach or notifier enable races remain visible in demos] → Reuse the existing bounded retry and persist gateway/notifier evidence for diagnosis.
- [The new demo duplicates some structure from the TUI pack] → Prefer local clarity first; extract shared helpers only after both supported contracts are stable.
- [Users may expect Gemini because a Gemini headless backend exists] → State explicitly in docs and specs that maintained demo lanes follow supported unattended policy coverage, not just backend existence.
- [Attach semantics may be misunderstood as “interactive TUI control”] → Document that `attach` re-enters the tmux-backed headless demo session for inspection, not a parser-led TUI workflow.

## Migration Plan

This change is additive.

1. Add the new demo pack, README entry, and OpenSpec capability.
2. Implement the new demo alongside the existing TUI demo without changing the current TUI contract.
3. Add tests for the new driver, runtime helpers, and report contract.
4. Keep rollback simple: remove the new demo pack and its README entry if the supported contract proves incorrect before broader adoption.

No existing user data migration is required because the new demo owns its own pack-local output root.

## Open Questions

- Should the headless demo’s verify path require managed-agent detailed state explicitly, or treat it as opportunistic evidence layered on top of summary state plus turn artifacts?
- Once Gemini unattended support becomes a maintained platform capability, should it expand this same demo pack or land as a follow-up change with fresh demo evidence?
