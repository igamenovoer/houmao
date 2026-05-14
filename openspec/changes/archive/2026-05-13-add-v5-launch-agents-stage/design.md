## Context

The v5 execution workflow now separates preparation and readiness validation, but the live-agent launch transition remains ambiguous. `prepare-agents` may defer launch until workspace and validation facts exist, while `start` currently checks whether agents are live or launchable before sending the first loop trigger. That makes `start` too broad and leaves no explicit command for turning prepared launch profiles into live managed agents.

The intended runtime model benefits from a stricter split:

```text
prepare-agents
prepare-workspace      # or equivalent manual workspace readiness evidence
validate-loop
launch-agents
start
```

`prepare-workspace` is an optional command only when the user prepares workspaces manually or the generated execplan does not require managed workspaces. The readiness evidence still matters: `validate-loop` must see either a `prepare-workspace` report or equivalent manual facts when workspace posture is required.

## Goals / Non-Goals

**Goals:**

- Add `launch-agents` as the execution stage that owns the live-agent transition.
- Make `prepare-agents` produce launchable profiles and concrete launch facts, not live agents as normal behavior.
- Make `validate-loop` validate pre-launch readiness: prepared profiles, workspace evidence, mailbox/gateway/notifier posture, harness, run artifacts, state posture, and no in-chat waiting.
- Make `launch-agents` launch prepared agents and verify liveness without sending loop-start work.
- Make `start` send the first loop trigger only after agents are live.
- Allow manual workspace setup by documenting the required equivalent workspace readiness evidence.

**Non-Goals:**

- Do not add new Houmao CLI/runtime behavior.
- Do not change the maintained launch implementation owned by `houmao-agent-instance` or supported easy-instance surfaces.
- Do not make `launch-agents` repair profiles, install skills, create workspaces, or alter generated execplan artifacts.
- Do not make `start` create or launch agents.
- Do not change the mail-notifier runtime model.

## Decisions

### Add `launch-agents` Between Validation And Start

`launch-agents` should be an execution subcommand routed by the top-level v5 skill. It reads generated agent bindings, prepared agent/profile facts, workspace readiness facts or accepted manual equivalents, notifier/mail posture, and launch profile cwd/memo posture. It then launches missing live agents through maintained Houmao launch surfaces and reports live-agent/session facts.

Alternative considered: keep final launch inside `start`. That preserves fewer commands, but it keeps `start` responsible for two different side effects: process launch and loop trigger delivery. Separating them gives operators a clean checkpoint between "agents are running" and "loop work has begun."

### Make `prepare-agents` Prepare Launchability, Not Launch

`prepare-agents` should create/update specialists or profiles, install generated skills, bind support skills, prepare notifier prompts and memo posture, and record concrete launch facts. It should not launch agents as normal behavior. If it discovers already-live suitable agents, it can report them, but not depend on live launch side effects.

Alternative considered: keep opportunistic launch in `prepare-agents` when workspace posture is already ready. That keeps ambiguity: operators cannot tell whether `prepare-agents` is a profile-prep command or a launch command.

### Validate Pre-Launch Readiness

`validate-loop` should remain read-only and should run before `launch-agents`. It should validate that agents are prepared and launchable, not require that they are live. It should also accept manual workspace facts when the user chose not to run `prepare-workspace`, as long as those facts satisfy the generated workspace contracts.

After `launch-agents`, `start` still performs a final lightweight check for liveness and start-trigger prerequisites, but does not repeat full validation or repair missing preparation.

Alternative considered: validate after launch only. That catches live-agent posture, but it would force agent processes to exist before obvious missing workspace, mailbox, harness, or state blockers are reported.

### Keep Start As Loop Begin

`start` should require live agents or a current `launch-agents` report. Its normal job is to initialize any start-time state left by the harness contract and deliver the generated first trigger through maintained messaging or mailbox surfaces. It should not call `launch-agents` implicitly.

Alternative considered: allow `start` to launch if agents are "intentionally launchable." That reintroduces the ambiguity this change removes.

## Risks / Trade-offs

- More execution commands for operators to learn -> Mitigate by documenting the canonical stage order in the top-level skill, generated defaults, and developer design docs.
- Users may skip `prepare-workspace` and provide incomplete manual workspace facts -> Mitigate by making `validate-loop` require explicit equivalent readiness evidence when workspace posture is required.
- Existing wording may still imply `prepare-agents` can launch -> Mitigate by removing normal launch actions from `prepare-agents` and moving them into `launch-agents`.
- `start` becomes stricter and may block where it previously launched opportunistically -> Mitigate by reporting the exact missing `launch-agents` step and live-agent facts needed.
