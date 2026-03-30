## Context

The current `houmao-mgr` CLI handles named-resource conflicts inconsistently. Several durable create and register flows fail immediately when a resource name is already in use, even when the system already has enough information to replace or refresh the managed state safely after explicit operator approval.

This is most visible in four places:

- generic filesystem mailbox registration,
- project-scoped mailbox registration,
- late managed-agent mailbox registration, and
- `project easy specialist create`.

The codebase already contains two relevant implementation signals:

- Click-based interactive confirmation is already used for workspace trust on launch.
- mailbox internals already support a narrow replacement-confirmation hook for unreadable managed files.

At the same time, live runtime session conflicts are not equivalent to durable resource conflicts. Replacing a running managed agent can imply stop, relaunch, shared-registry, mailbox-binding, and tmux-session consequences. That makes runtime launch a different design problem from durable resource overwrite confirmation.

## Goals / Non-Goals

**Goals:**

- Define one consistent overwrite-confirmation contract for selected durable named-resource CLI commands.
- Support both interactive confirmation and non-interactive confirmation through `--yes`.
- Preserve existing mailbox `safe`, `force`, and `stash` semantics instead of collapsing them into a single overwrite behavior.
- Let `project easy specialist create` replace an existing specialist definition in one step after explicit confirmation.
- Fail clearly in non-interactive contexts when destructive replacement would occur without `--yes`.

**Non-Goals:**

- Do not change `houmao-mgr agents launch` or `houmao-mgr project easy instance launch` to overwrite or replace live sessions.
- Do not redefine mailbox `stash` as an implicit fallback.
- Do not broaden this change to all low-level project authoring commands such as role init, setup add, preset add, or auth add.
- Do not merge overwrite confirmation with unrelated prompts such as workspace-trust `--yolo`.

## Decisions

### Decision: Use one shared command-level overwrite confirmation policy

Selected create and register commands will adopt a shared user-visible policy:

- no conflict: proceed without prompt,
- conflict requiring destructive replacement with `--yes`: proceed without prompt,
- conflict requiring destructive replacement without `--yes` and with an interactive terminal: prompt once,
- conflict requiring destructive replacement without `--yes` and without an interactive terminal: fail clearly before mutation.

Rationale:

- This gives operators a uniform contract across the selected CLI surfaces.
- It matches existing Click-based interaction patterns.
- It keeps automation explicit by requiring `--yes` instead of guessing.

Alternatives considered:

- Ad hoc prompts in each command. Rejected because prompt text, TTY behavior, and failure semantics would drift.
- Global environment-variable bypass. Rejected because it is less explicit per invocation and easier to misuse in automation.

### Decision: Keep mailbox modes intact and layer confirmation on top

Mailbox registration already has three meaningful modes: `safe`, `force`, and `stash`. This change will preserve that vocabulary.

The design contract is:

- `safe` remains the default non-destructive attempt.
- `stash` remains an explicit operator-selected alternative and is never chosen automatically.
- Any path that would actually replace existing durable mailbox state requires confirmation unless `--yes` is present.
- When the default `safe` flow hits a replaceable conflict and the operator confirms overwrite, the CLI may continue with replacement semantics for that request instead of forcing the operator to rerun manually.

Rationale:

- The mailbox layer already distinguishes replacement from stash, and that distinction matters for artifact layout and retained history.
- Preserving the existing mode vocabulary avoids surprising operators who already know the mailbox lifecycle model.

Alternatives considered:

- Automatically convert every safe conflict into force. Rejected because it hides a destructive transition behind a default mode.
- Automatically fall back from safe to stash. Rejected because stash changes storage behavior and is not equivalent to overwrite.

### Decision: Treat specialist replacement as a specialist-scoped update, not a remove-and-recreate workflow

`project easy specialist create` will gain a confirmed replacement path for an existing specialist name. The replacement scope is:

- the specialist definition persisted in the project catalog,
- the specialist-owned generated prompt and preset projection for that specialist name.

The replacement path must not delete shared skills, shared auth content, or unrelated live runtime sessions solely because the specialist is replaced.

Rationale:

- The project catalog already supports upsert-style storage and the compatibility projection already supports managed tree replacement.
- Requiring a separate manual remove step is unnecessary friction for a flow that is fundamentally updating one reusable specialist definition.

Alternatives considered:

- Force operators to run `specialist remove` and then `specialist create`. Rejected because it turns one logical update into a fragile two-step workflow.
- Delete all referenced auth and skill content on replacement. Rejected because those resources may be shared across specialists.

### Decision: Exclude live session launch conflicts from this change

This change will not redefine conflict handling for `houmao-mgr agents launch` or `houmao-mgr project easy instance launch`.

Rationale:

- Live-session replacement is not just a name conflict. It can involve tmux session ownership, shared-registry generation conflicts, mailbox attachment state, and stop/relaunch semantics.
- The current request is specifically about named resource overwrite confirmation. Durable resources can support a clean prompt contract without solving session lifecycle replacement.

Alternatives considered:

- Fold `agents launch` into the same overwrite contract. Rejected because there is no single obvious definition of “overwrite” for a live runtime session.

## Risks / Trade-offs

- [Risk] The CLI could prompt on conflicts that are not actually replaceable. → Mitigation: only use the overwrite-confirmation path for known replaceable conflict classes; preserve hard failures for unsupported or ambiguous conflicts.
- [Risk] New prompts could break unattended automation. → Mitigation: every selected destructive path gets `--yes`, and non-interactive failure messages must point to it clearly.
- [Risk] Mailbox semantics become confusing if `safe` sometimes leads to replacement. → Mitigation: keep the transition explicit in help/docs and require operator confirmation before replacement.
- [Risk] Specialist replacement may overwrite projection files that users edited manually. → Mitigation: define replacement as specialist-owned generated state and document that scope explicitly.
- [Risk] Scope could expand into low-level project authoring commands before the shared helper is proven. → Mitigation: limit this change to mailbox registration and project-easy specialist create.

## Migration Plan

No repository data migration is required.

Implementation rollout is expected to be:

1. add a shared overwrite-confirmation helper and `--yes` plumbing in the relevant CLI commands,
2. update mailbox registration flows to use the helper,
3. update specialist-create conflict handling to use the helper,
4. add unit coverage for interactive, declined, and non-interactive `--yes` cases,
5. update CLI reference and workflow documentation.

Rollback is straightforward: remove the `--yes` options and revert the commands to fail-fast conflict handling.

## Open Questions

- Whether a later follow-up should extend the same overwrite-confirmation helper to low-level project authoring commands such as role init, preset add, setup add, and auth add.
