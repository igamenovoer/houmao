## Context

`houmao-mgr project easy specialist` is already a small command family, not just a single create command. The current packaged system skill, `houmao-create-specialist`, only teaches `project easy specialist create`, while the CLI also supports `list`, `get`, and `remove`. That mismatch makes the packaged skill name and its documented workflow narrower than the actual operator task.

The system-skill runtime model is intentionally simple. The catalog maps one skill name to one packaged directory, and installation copies that directory verbatim into the target tool home. There is no first-class runtime notion of nested Houmao subskills. That means the broader specialist-management surface must still project as one top-level skill directory, with any finer routing handled inside the skill content itself.

This rename is also a migration problem, not just a tree move. Installed system-skill ownership is keyed by skill name and projected directory, so moving from `houmao-create-specialist` to `houmao-manage-specialist` must explicitly remove the old owned path and update recorded install state.

## Goals / Non-Goals

**Goals:**

- Replace the create-only packaged skill with a broader packaged specialist-management skill named `houmao-manage-specialist`.
- Make the top-level `SKILL.md` an index/router that selects action-specific guidance for `create`, `list`, `get`, and `remove`.
- Keep create-only credential discovery and vendor-login guidance attached only to the create flow.
- Migrate Houmao-owned installed homes cleanly from the old skill name to the new one.
- Keep the current `houmao-mgr project easy specialist` CLI surface unchanged.

**Non-Goals:**

- Changing `houmao-mgr project easy specialist` subcommand semantics or flags.
- Expanding the packaged skill to cover `project easy instance launch`, `instance list|get|stop`, or managed-agent runtime operations.
- Introducing a new runtime concept of independently installable nested subskills.
- Preserving backward compatibility for explicit external references to the old packaged skill name beyond one owned install migration.

## Decisions

### Decision: Keep one installable skill and make `SKILL.md` a router

The packaged runtime skill will be a single top-level skill directory named `houmao-manage-specialist`. Its `SKILL.md` will act as an index that:

- identifies the requested specialist-management action,
- loads one action-specific document for `create`, `list`, `get`, or `remove`,
- keeps `instance launch` and other easy-instance operations explicitly out of scope.

Action-specific details will live under local action documents such as `actions/create.md` and `actions/remove.md`.

Why this approach:

- It matches the current system-skill installer and catalog model, which project one directory per skill.
- It keeps one Houmao-owned specialist-management entry point instead of multiplying installable skills for closely related actions.
- It lets the create path stay detailed without bloating the top-level entry page.

Alternative considered:

- Separate installable skills such as `houmao-create-specialist`, `houmao-list-specialists`, and `houmao-remove-specialist`.
  Rejected because the current runtime model does not need or benefit from that granularity, and it would fragment one operator workflow across multiple skill names.

### Decision: Keep credential discovery scoped to the create action only

The current credential-source and vendor-login behavior remains relevant only for `project easy specialist create`. The broader skill will keep those rules under the create action and continue to use tool-specific reference pages only when the chosen action is create and the user requested a discovery mode.

Why this approach:

- `list`, `get`, and `remove` do not need credential lookup logic.
- It preserves the current security posture and discovery guardrails without repeating them across unrelated actions.
- It keeps the top-level router concise.

Alternative considered:

- Keep credential-source rules in the top-level `SKILL.md`.
  Rejected because it would make the index page creation-heavy again and blur the simpler read-only or destructive non-create actions.

### Decision: Treat the rename as owned-path migration in install state

The packaged catalog and installed-home state will treat `houmao-manage-specialist` as the current skill name. Reinstall or auto-install flows must detect previously owned `houmao-create-specialist` records and previously owned projected directories, remove those old owned paths, and persist only the new renamed skill in install state.

Why this approach:

- The current install-state merge logic is keyed by skill name, so a rename without migration would leave stale owned directories and stale recorded names behind.
- Removing the old owned path prevents duplicate specialist-management skills from showing up in external tool homes.

Alternative considered:

- Keep the old skill installed as an alias.
  Rejected because it would keep duplicate skill trees alive, weaken ownership rules, and prolong divergence between packaged inventory and installed state.

### Decision: Keep CLI behavior unchanged and document the rename at the system-skill layer

The change affects the packaged Houmao-owned skill and the `system-skills` inventory, not the underlying `project easy specialist` subcommands. The CLI continues to expose `create`, `list`, `get`, `remove`, and the separate `instance` group exactly as it does now.

Why this approach:

- The user request is to broaden the packaged skill scope around existing CLI behavior, not to redesign the CLI.
- Keeping the CLI stable makes the change mostly a documentation, packaging, and migration update.

Alternative considered:

- Rename or regroup the CLI itself around a broader “manage specialist” command.
  Rejected because it is out of scope and would introduce unrelated command-surface churn.

## Risks / Trade-offs

- [Installed homes that are never reinstalled keep the old skill until touched again] → Migration will run on the next explicit install, managed join, or managed build that uses the shared installer.
- [A router-style top-level skill can become vague if the action split is weak] → Keep `SKILL.md` short and explicit about when to load each action document and what remains out of scope.
- [Destructive `remove` guidance is easier to trigger once it becomes part of the packaged skill] → Add remove-specific guardrails requiring an explicit specialist name and clear reporting of preserved auth and skill paths.
- [OpenSpec capability folder names remain historical even though the runtime skill is renamed] → Keep the delta specs explicit about the new runtime skill name and use archive sync notes to record the superseding contract.

## Migration Plan

1. Add the new packaged skill directory `houmao-manage-specialist/` with router-style action docs and updated UI metadata.
2. Update the packaged system-skill catalog so `project-easy` resolves `houmao-manage-specialist` instead of `houmao-create-specialist`.
3. Update the shared installer and install-state handling so previously owned `houmao-create-specialist` records and projected paths migrate to `houmao-manage-specialist`.
4. Update system-skill CLI tests, packaged-skill tests, and reference docs to use the renamed skill.
5. Remove the old packaged `houmao-create-specialist` asset tree once migration coverage is in place.

Rollback:

- Restore the old packaged catalog entry and skill tree in a follow-up build.
- Reinstall into affected homes to project the older skill again if rollback is required during development.

## Open Questions

- None for implementation planning. The main remaining cleanup question is whether the long-lived main OpenSpec capability folder names should be renamed in a separate maintenance change.
