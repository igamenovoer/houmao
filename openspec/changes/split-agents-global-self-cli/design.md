## Context

The current public CLI has three overlapping ways to operate on managed agents:

```text
project agents  -> selected project overlay
agents          -> shared registry and explicit single-agent control
agents          -> current tmux session when selectors are omitted in some subfamilies
```

`project agents` already has a relatively clear job: launch and inspect managed-agent instances that belong to the selected project overlay. The top-level `agents` family is less clear because it mixes zero-or-many registry/fleet operations, explicit single-agent operations, current-session self operations, current-session adoption, and external-agent reference onboarding.

This change keeps `agents` as the domain namespace and makes the operating lens explicit:

```text
houmao-mgr agents global ...   # zero-or-many local managed-agent registry/fleet lens
houmao-mgr agents single ...   # one explicitly selected local managed-agent lens
houmao-mgr agents self ...     # caller's current tmux session holding one agent
houmao-mgr agents external ... # external-agent registry/reference lens
houmao-mgr project agents ...  # selected project lens
```

## Goals / Non-Goals

**Goals:**

- Make the `agents` command family mode-explicit by introducing `agents global`, `agents single`, `agents self`, and `agents external`.
- Keep `project agents` as the selected-project facade for project-owned instances.
- Define `agents global` by target cardinality: operations that target no individual agent, or operations that target multiple local managed agents as a fleet.
- Move explicit one-agent operations to `agents single` with a group-level `--agent-id` or `--agent-name` selector.
- Move current-session adoption to `agents self join`.
- Keep `agents single` and `agents self` as separate authority surfaces with intentionally different operation sets.
- Move external-agent registry/reference onboarding into `agents external` while keeping external lifecycle management outside this user's `houmao-mgr`.
- Remove implicit current-session fallback from non-self commands.
- Remove managed-agent birth from the global management surface; keep project-backed launch under `project agents launch`.
- Preserve the underlying runtime, registry, gateway, mailbox, and turn implementations where possible by refactoring command registration and target-resolution wrappers.
- Update docs, command templates, and packaged skill guidance so agents choose command paths by target ownership.

**Non-Goals:**

- Do not change the managed-agent registry schema solely for this CLI split.
- Do not change mailbox, gateway, TUI tracking, or headless turn protocols.
- Do not remove external/imported managed-agent support.
- Do not implement `agents self leave` in this change; reserve that future inverse for the same current-session membership family.
- Do not make `agents self` a selector alias for `agents single`, and do not mirror selected-agent lifecycle recovery/cleanup authority under `self`.
- Do not introduce a top-level `houmao-mgr self` command.
- Do not add backward-compatibility shims unless a future decision explicitly chooses temporary aliases.

## Decisions

### Decision: Keep `agents` as the domain namespace

Use:

```text
houmao-mgr agents global ...
houmao-mgr agents single --agent-id <id> ...
houmao-mgr agents single --agent-name <name> ...
houmao-mgr agents self ...
houmao-mgr agents external ...
```

rather than introducing new top-level command families.

Rationale: zero-or-many registry management, one-agent control, current-session membership, and external imported references are all agent-domain operations. Keeping them under `agents` lets the top-level command tree remain stable while removing the ambiguity inside the `agents` family.

Alternative considered: `houmao-mgr self ...` for current-session operations and a flatter top-level agent tree. This is shorter for self calls but creates another top-level family and leaves explicit single-agent targeting less structured.

### Decision: `agents global` owns zero-or-many local managed-agent operations

`agents global` SHALL mean operations whose target cardinality is no individual managed agent or multiple local managed agents. It SHALL NOT target exactly one selected agent.

Expected global operations:

```text
agents global list
```

Additional global commands may be added when their target is the local managed-agent registry as a whole, a filtered fleet, or a multi-agent operation such as a future stop-all command. Global commands SHALL NOT accept single-agent selectors such as `--agent-id` or `--agent-name`; filters that still select zero-or-many agents remain allowed.

`agents global` SHALL NOT expose first-birth launch commands, current-session adoption, exactly-one selected-agent control, or external-agent reference administration.

Rationale: global should read as “show or maintain the local registry/fleet as a whole.” If a command needs `--agent-id` or `--agent-name`, it belongs to `single`. If a command acts on zero agents as an informational registry query or on many agents as a fleet action, it belongs to `global`.

Alternative considered: keep single-agent controls under `global` with required selectors. That is explicit enough mechanically, but the group still mixes zero-or-many and exactly-one responsibilities.

### Decision: `agents single` owns one explicitly selected local managed agent

`agents single` SHALL require exactly one group-level selector for one local managed-agent identity:

```text
houmao-mgr agents single --agent-id <id> <operation>
houmao-mgr agents single --agent-name <name> <operation>
```

Expected single operations include:

```text
agents single --agent-id <id> state
agents single --agent-id <id> prompt
agents single --agent-id <id> interrupt
agents single --agent-id <id> stop
agents single --agent-id <id> relaunch
agents single --agent-id <id> gateway ...
agents single --agent-id <id> mail ...
agents single --agent-id <id> mailbox ...
agents single --agent-id <id> memory ...
agents single --agent-id <id> turn ...
agents single --agent-id <id> cleanup ...
```

Nested single-agent subcommands SHALL consume the group-level selector and SHALL NOT repeat `--agent-id` or `--agent-name` on every leaf command.

`agents single` MAY expose out-of-session lifecycle controls that mutate, interrupt, stop, restart, revive, or clean up the selected managed-agent runtime. Direct selected-agent lifecycle commands such as `prompt`, `interrupt`, `stop`, `relaunch`, and `cleanup` SHALL be registered under `single`.

`agents single relaunch` SHALL use explicit selected-agent targeting and MAY perform the broader relaunch contract for that selected agent, including active tmux-backed refresh, stopped relaunchable-record revival, and degraded/stale active-record recovery where the existing runtime supports those cases.

`agents single` SHALL NOT expose current-session membership commands such as `join` or the future inverse `leave`.

Rationale: this makes responsibility obvious in the command string. `single` is the place for one explicit target and for operations an operator runs against that target from outside its tmux session; `self` is the place for the current tmux session; `global` is the place for zero-or-many registry/fleet operations. Keeping stop and cleanup under `single` avoids encouraging an agent to destroy its own tmux session or lifecycle artifacts from inside that session.

Alternative considered: keep `--agent-id` / `--agent-name` on every leaf command. That avoids Click context plumbing but repeats selectors and makes the tree harder for agents and humans to reason about.

### Decision: `agents self` owns current tmux-session membership and self operations

`agents self` targets the current tmux session that holds one local managed agent. It exposes `join` for adopting the current tmux session into the Houmao registry and exposes follow-up operations that resolve the already registered current managed agent from the caller's tmux session metadata.

Expected self operations:

```text
agents self join
agents self identity
agents self state
agents self prompt
agents self interrupt
agents self relaunch
agents self gateway ...
agents self mail ...
agents self mailbox ...
agents self memory ...
agents self turn ...
```

Self follow-up commands SHALL not accept `--agent-id`, `--agent-name`, or `--current-session`. They may fail clearly when not run inside a registered managed-agent tmux session.

`agents self prompt` and `agents self interrupt` SHALL target the current managed-agent tmux session without accepting explicit agent selectors.

`agents self relaunch` SHALL refresh the active tmux-backed surface for the caller's current managed session. It SHALL require resolvable current-session manifest authority and SHALL NOT perform selected-agent registry lookup, stopped relaunchable-record revival, degraded/stale active-record recovery, or cross-session targeting. Its contract is narrower than `agents single --agent-id <id> relaunch` and `agents single --agent-name <name> relaunch`, even though both command families share the active tmux-backed relaunch primitive.

`agents self` SHALL NOT mirror the full selected-agent lifecycle surface. In particular, this change SHALL NOT expose maintained public paths for `agents self stop` or `agents self cleanup`.

`agents self join` MAY accept new-identity creation fields such as `--agent-name` and optional `--agent-id`; those fields describe the identity being created for the current tmux session and are not selectors for another agent.

The later `agents self leave` inverse belongs in the same family, but implementing leave is out of scope for this change.

Rationale: `self` is defined by the current tmux session as the target, and that tmux session is expected to hold one managed-agent identity. That lets `join` and a future `leave` form a pair while preserving selector-free self operations after the session is registered. `self relaunch` matches the existing current-session relaunch behavior: it assumes current tmux authority exists and refreshes the active primary surface. Because the caller may be the managed agent running inside that tmux session, `self` must avoid stop and cleanup controls whose effects can destroy the caller's own session or lifecycle artifacts while the command is still executing.

Alternative considered: make `self` a flag on single-agent commands. That repeats the old selector multiplexing problem and makes current-session command intent less visible.

### Decision: `agents external` owns external-agent registry/reference onboarding

`agents external` manages external agents that are brought into Houmao's shared registry as remotely owned or communication-only references. It exposes `register`, `list`, `get`, `verify`, and `remove`.

`agents external` SHALL NOT expose local lifecycle management for those agents. The external agent's lifecycle is controlled by the system or user that owns the external runtime, not by this user's `houmao-mgr`.

Rationale: external references may appear in shared discovery, but they do not have the same local runtime authority as a joined or project-launched managed agent. Pulling them out from under `global` avoids making global management mean both local runtime control and external reference onboarding.

Alternative considered: keep `external` under `agents global`. That is mechanically smaller but keeps global as a catch-all and blurs local zero-or-many runtime authority with external registry/reference onboarding.

### Decision: `project agents` remains a project ownership lens

`project [--project-dir <dir>] agents ...` continues to select a project overlay and operate only on instances that belong to that overlay. It uses project-local names and validates runtime manifest ownership before inspecting or mutating existing instances.

Project-backed launch-profile launch stays here:

```text
houmao-mgr project --project-dir /repo agents launch --profile reviewer
```

Rationale: project launch profiles and specialists are project resources. A global or single launch path that accepts project profiles recreates the same top-level target-selection ambiguity that the recent project targeting change removed. Raw native/provider construction is also birth from source definitions, so it belongs in internal native-agent surfaces rather than global or single management.

Alternative considered: keep `agents global launch --launch-profile`. This is convenient for legacy command memory but makes global launch depend on project overlay discovery.

### Decision: Implement through command registration and shared target contexts

The lowest-risk implementation path is to keep runtime operations intact and reorganize command groups:

- create `agents_global_group` for zero-or-many local managed-agent registry/fleet operations,
- create `agents_single_group` with group-level target context and register one-agent commands there,
- create `agents_self_group` and register current-session membership/self wrappers there,
- create `agents_external_group` and register external-agent registry/reference onboarding commands there,
- update `agents_group` to expose only `global`, `single`, `self`, and `external`,
- split target resolution helpers into explicit single and self variants and gate command availability by authority surface,
- update command-template families and docs after the command tree is reshaped.

Rationale: the behavioral change is mostly target selection and public command shape. Runtime controllers, registry publication, mailbox operations, and gateway clients should not need structural rewrites.

Alternative considered: duplicate the full implementation for single and self command families. That would make the tree easy to build but would create high drift risk in command behavior.

## Risks / Trade-offs

- **Risk: Existing scripts break because direct `houmao-mgr agents ...` paths disappear.** → Mitigation: document the migration table prominently and update packaged skills/templates in the same change.
- **Risk: Group-level single selectors require Click context plumbing.** → Mitigation: add a small typed context helper and test nested command selector propagation.
- **Risk: Current-session commands lose useful explicit outside-tmux targeting.** → Mitigation: keep outside-tmux targeting under `agents single`; `self` deliberately targets only the current tmux session.
- **Risk: Users expect `self relaunch` to have the same broad recovery behavior as `single relaunch`.** → Mitigation: document `self relaunch` as active-current-session refresh only and add routing tests that reserve stopped/degraded relaunch recovery for selected-agent targeting.
- **Risk: Moving `join` under `self` makes self partly pre-registration.** → Mitigation: define `self` as current tmux-session targeting, with `join` as the membership creation command and all other self commands requiring an existing identity.
- **Risk: Removing global launch hides raw launch workflows.** → Mitigation: document project launch as the public birth path and keep direct native/provider plumbing in internals when still needed.
- **Risk: Old docs and command templates keep generating ambiguous `agents ...` paths.** → Mitigation: add command-template and docs tasks that sweep all generated examples and packaged skill guidance.

## Migration Plan

1. Introduce `agents global`, `agents single`, `agents self`, and `agents external` groups and move command registration behind those groups.
2. Add group-level selector context for `agents single` and update one-agent commands to consume it.
3. Update target-resolution helpers so non-self paths never use current-session fallback and self paths target the current tmux session.
4. Move current-session adoption to `agents self join` and keep future `leave` semantics aligned with that family.
5. Keep destructive selected-agent lifecycle controls under `agents single`, allow `agents self prompt`, `agents self interrupt`, and the narrower active-current-session `agents self relaunch`, and prevent `agents self` from exposing direct stop/cleanup commands.
6. Remove global/root launch from the maintained public command tree; keep project-backed birth under `project agents launch`.
7. Update command templates, docs, and packaged system skills to emit the new command paths.
8. Run focused CLI help/routing tests, then full lint/type/unit checks.

Rollback is straightforward before release: restore the old `agents_group` direct registrations and remove the new groups. Because no registry schema or persisted runtime format changes are planned, rollback does not require data migration.
