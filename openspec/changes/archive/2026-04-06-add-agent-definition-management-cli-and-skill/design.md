## Context

Houmao now has three distinct project-local authoring surfaces for agent setup:

- `project easy specialist ...` for opinionated catalog-backed specialist authoring
- `project agents roles ...` and `project agents presets ...` for low-level compatibility projection authoring
- `project agents tools <tool> auth ...` for auth-bundle content management

The low-level role and preset surfaces already support the edit operations that originally motivated this change:

- `project agents roles set` updates the canonical role prompt
- `project agents presets set` patches named preset fields such as auth reference, skill membership, and prompt mode

What is still missing is a packaged Houmao-owned skill aligned with those current surfaces, plus an opt-in way to inspect full role prompt text through `houmao-mgr` itself. Without that, a packaged `houmao-manage-agent-definition` skill would still need to fall back to direct filesystem reads when the user asks to inspect the current prompt.

This change therefore narrows to the remaining current-state gaps instead of re-specifying edit verbs that already landed.

## Goals / Non-Goals

**Goals:**

- Add a packaged `houmao-manage-agent-definition` skill that routes agents to the current low-level role and preset commands.
- Expose prompt-content inspection through `houmao-mgr project agents roles get --include-prompt`.
- Keep the boundary between definition structure and auth-bundle contents explicit.
- Fold the new skill into the existing `user-control` packaged set so managed homes and CLI-default installs pick it up through the existing set model.

**Non-Goals:**

- Reintroduce the retired `project agents roles presets ...` tree or `roles scaffold`.
- Duplicate already implemented `roles set` or `presets set` behavior in a parallel namespace.
- Merge low-level role/preset authoring with `project easy specialist ...`.
- Replace `houmao-manage-credentials` or move auth-bundle content mutation into the new skill.
- Add new editing flags for advanced preset blocks such as `mailbox` or `extra`.

## Decisions

### Keep low-level definition routing on the current split surfaces

The packaged definition-management skill will route to the current low-level CLI families instead of inventing a wrapper namespace:

- `project agents roles ...` for prompt-only role roots
- `project agents presets ...` for named preset resources
- `project agents tools <tool> auth ...` only when rerouting auth-bundle content mutation to `houmao-manage-credentials`

Rationale:

- these are the current maintained surfaces already documented in the CLI reference
- using the current noun split avoids teaching agents a stale command tree
- a wrapper namespace would add duplication without simplifying the underlying model

Alternative considered:

- add `project agents definitions ...`
  - rejected because it would wrap the same current resources redundantly and immediately create routing ambiguity with `roles`, `presets`, and `tools auth`

### Make prompt inspection opt-in on `roles get`

`project agents roles get --name <role>` will keep its current summary-oriented behavior by default. A new opt-in flag `--include-prompt` will add the prompt text to the structured output when the caller explicitly needs it.

Rationale:

- the current default `get` payload is compact and safe for ordinary inspection
- prompt text can be long, so always returning it would make `get` noisier and more expensive for agents to process
- the packaged skill still needs a supported CLI path to inspect prompt content when the user asks to view or revise the current low-level definition

Alternative considered:

- always return prompt text from `roles get`
  - rejected because it changes the default output contract more than necessary

### Scope the new skill around definition structure, not auth-bundle contents

The new skill will treat these edits as definition work:

- role prompt edits through `project agents roles set`
- preset structure edits through `project agents presets add|set|remove`
- preset auth-reference selection through `project agents presets set --auth ...` or `--clear-auth`

It will explicitly keep auth-bundle content mutation on:

- `project agents tools <tool> auth list|get|add|set|remove`
- packaged `houmao-manage-credentials`

Rationale:

- a preset's selected auth bundle is part of the low-level definition structure
- env vars and auth files inside that bundle are secret-bearing bundle contents with their own maintained CLI and packaged skill

Alternative considered:

- let `houmao-manage-agent-definition` route direct auth-bundle writes too
  - rejected because it would blur the boundary between definition editing and credential management

### Keep the packaged skill action-oriented even though the CLI uses multiple nouns

The top-level `houmao-manage-agent-definition` skill will remain organized around operator intent:

- `create`
- `list`
- `get`
- `set`
- `remove`

Each action page will then route to the correct current noun:

- roles for prompt-only role work
- presets for named preset work

Rationale:

- user intent is usually action-first, not noun-first
- an action-oriented skill index stays consistent with the existing packaged skill style
- the action pages can still enforce the current command surfaces and reject stale ones

### Add the new packaged skill to `user-control`

`houmao-manage-agent-definition` will be packaged as another `user-control` system skill rather than a new named set.

Consequences:

- `user-control` membership expands to three skills:
  - `houmao-manage-specialist`
  - `houmao-manage-credentials`
  - `houmao-manage-agent-definition`
- managed launch and managed join keep using the same `user-control` set
- CLI-default installation inherits the new skill automatically through the expanded set, alongside the separate `agent-instance` set

Rationale:

- the new skill belongs with the existing user-authored-definition management tools
- a separate set would add operator complexity without representing a distinct installation choice

## Risks / Trade-offs

- [Users may still confuse role/preset edits with auth-bundle edits] → Make the packaged skill and docs state explicitly that `presets set --auth` changes the selected bundle, while bundle-content mutation stays on `houmao-manage-credentials`.
- [Prompt inspection can leak large prompt blobs into automation unexpectedly] → Make prompt text opt-in behind `--include-prompt` and keep default role inspection summary-only.
- [Action-oriented skill routing could drift back to stale nouns] → Explicitly forbid `roles scaffold` and `roles presets ...` in the packaged skill contract and tests.
- [Expanded `user-control` installs add one more packaged skill to managed homes] → Reuse the existing set semantics so the additional install surface is intentional and consistently reported through `system-skills list|install|status`.

## Migration Plan

1. Extend `project agents roles get` with `--include-prompt`.
2. Add the new packaged skill asset tree and route it to `project agents roles ...` and `project agents presets ...`.
3. Add the new packaged skill to the `user-control` set and update system-skill inventory / reporting coverage.
4. Update docs for the current low-level role/preset/auth boundary and the new packaged skill.
5. Validate the final OpenSpec change against the updated current-state contract.

Rollback is straightforward because this change is additive:

- remove the new packaged skill from the catalog and asset root
- remove `--include-prompt` from `roles get`
- reinstall packaged system skills if a rollback needs the old inventory reflected in an explicit tool home

No persistent data migration is required because the current role roots, named preset files, and auth bundles remain valid and unchanged in layout.

## Open Questions

None at proposal time.
