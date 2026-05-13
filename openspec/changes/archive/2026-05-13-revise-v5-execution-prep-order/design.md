## Context

The current loop skill says managed-workspace execution normally proceeds as `prepare-workspace`, `prepare-agents`, then `start`. That order is wrong for standard managed workspaces because workspace-manager inputs include concrete agent and launch-profile names. Those names are resolved by agent preparation, not by workspace preparation.

There are also two kinds of validation that should remain distinct:

- `validate-execplan`: authoring-time validation of generated files, contracts, package shape, and source/generated-output posture.
- `validate-loop`: execution-time readiness validation of prepared agents, prepared workspace, mailbox/gateway/notifier posture, harness availability, run artifacts, and start preconditions.

## Goals / Non-Goals

**Goals:**

- Make `prepare-agents`, `prepare-workspace`, `validate-loop`, `start` the normal execution order.
- Add a `validate-loop` execution subskill and top-level routing entry.
- Revise `prepare-agents` to produce concrete agent/profile facts consumed by workspace preparation.
- Revise `prepare-workspace` to require or consume prepared agent/profile facts when managed workspace setup needs concrete names.
- Move execution readiness blocking out of `validate-execplan` and into `validate-loop`.
- Revise `start` so it depends on `validate-loop` or performs only a final lightweight readiness check.
- Preserve the rule that `prepare-agents` and `prepare-workspace` do not call each other.

**Non-Goals:**

- Do not add new Houmao CLI/runtime behavior.
- Do not change how `houmao-utils-workspace-mgr` prepares standard workspaces.
- Do not make `prepare-agents` create workspaces.
- Do not make `prepare-workspace` create agents, specialists, or live instances.
- Do not change the mail-notifier runtime model.

## Decisions

### Put Agent Preparation Before Workspace Preparation

Normal execution order should be:

```text
prepare-agents
prepare-workspace
validate-loop
start
```

`prepare-agents` is responsible for resolving concrete identities:

- concrete agent ids;
- launch profile names;
- prompt/definition sources;
- generated skill installation requirements;
- maintained support skill requirements;
- notifier prompt material;
- memo seed posture;
- profile mutation intent that can later receive workspace cwd or memo workspace rules.

It should not require workspace readiness first. It may defer live launch when launch cwd/workspace facts are still pending.

Alternative considered: keep workspace first and ask `prepare-workspace` to infer agent names from generated bindings. That fails when agent preparation changes, normalizes, creates, or confirms concrete profile names.

### Workspace Preparation Consumes Prepared Agent Facts

`prepare-workspace` remains the workspace adapter to `houmao-utils-workspace-mgr`, but its input contract should include prepared agent/profile facts from `prepare-agents`.

It should use:

- generated workspace contracts from `execplan/specs/workspace/workspace.toml`;
- generated agent bindings from `execplan/agents/bindings.toml`;
- prepared concrete agent/profile facts reported by `prepare-agents`;
- operator approval for workspace-manager execution.

It should not create agents or install skills. It may update launch profile cwd or memo seed workspace rules only where the workspace manager owns that behavior and the profile facts already exist.

Alternative considered: let `prepare-workspace` create placeholder agent/profile names. That creates a second source of truth and can diverge from actual project agent/profile creation.

### Add `validate-loop` As The Execution Readiness Gate

`validate-loop` should be an execution subcommand, distinct from `validate-execplan`.

It checks whether the loop is ready to start:

- execplan validation is current enough;
- prepared concrete agents/profiles exist;
- generated/private skills are installed or project-scoped as required;
- maintained mail support skills are bound where needed;
- workspace facts match concrete agent/profile names;
- launch cwd and memo seed posture match workspace contracts;
- mailbox/gateway/notifier posture is ready for mail-driven loops;
- harness commands/imports are usable when generated skills depend on the harness;
- run artifact directories and state initialization are ready;
- no runtime behavior depends on in-chat waiting.

`validate-loop` reports blockers and warnings. `start` should require it or repeat only essential final checks before sending the first trigger.

Alternative considered: keep runtime readiness inside `start`. That makes `start` too broad and gives operators no separate preflight command.

### Keep `validate-execplan` Authoring-Focused

`validate-execplan` should continue checking generated package shape, contracts, parseability, generated skill structure, communication contracts, state contracts, workspace contracts, and platform boundaries. It may check that generated lifecycle docs mention the right stage order, but it should not require live agent/profile/workspace/mailbox readiness.

Alternative considered: extend `validate-execplan` into runtime validation. That blurs generated artifact correctness with environment readiness and makes authoring validation depend on local execution state.

### Preserve Stage Independence

The stages are ordered by preconditions and operator workflow, not by nested calls:

- `prepare-agents` does not call `prepare-workspace`;
- `prepare-workspace` does not call `prepare-agents`;
- `validate-loop` does not mutate agents or workspaces except for explicitly documented read-only checks;
- `start` does not silently repair preparation gaps.

This keeps recovery and re-run behavior legible.

## Risks / Trade-offs

- Renaming the readiness gate adds another command operators must learn -> Mitigation: document the execution sequence in the top-level router and defaults reference.
- `prepare-agents` may sound like it launches agents even when workspace is not ready -> Mitigation: state that live launch may be deferred until after workspace preparation and `validate-loop`.
- Some current validation text lives in `validate-execplan` and must move conceptually -> Mitigation: keep package-shape checks in `validate-execplan`; put live/prepared-state checks in `validate-loop`.
- Workspace setup may still need profile mutation -> Mitigation: allow `prepare-workspace` to update prepared launch profiles only through workspace-manager-owned behavior after agent/profile facts exist.
