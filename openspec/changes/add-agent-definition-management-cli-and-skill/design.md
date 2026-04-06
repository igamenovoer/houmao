## Context

Houmao already has two authoring layers for project-local agent setup:

- `project easy specialist ...` for opinionated catalog-backed specialist authoring
- `project agents roles ...` plus `project agents roles presets ...` for low-level compatibility-tree authoring

The low-level surface can currently create, scaffold, inspect, and remove roles and presets, but it cannot update an existing role prompt or patch an existing preset through `houmao-mgr`. That leaves the current CLI asymmetric and prevents a packaged `houmao-manage-agent-definition` skill from truthfully claiming definition-edit support without falling back to direct filesystem mutation.

This change spans both the low-level project CLI and the packaged system-skill inventory, so it benefits from explicit design decisions before implementation.

## Goals / Non-Goals

**Goals:**

- Add supported low-level CLI verbs for editing project-local role prompts and preset fields in place.
- Expose prompt-content inspection through `houmao-mgr` when an agent explicitly needs to inspect the full role definition.
- Add a packaged `houmao-manage-agent-definition` skill that routes agents to the supported low-level role and preset commands.
- Keep the boundary between definition structure and auth-bundle contents explicit.
- Fold the new skill into the existing `user-control` packaged set so managed homes and CLI-default installs pick it up through the existing set model.

**Non-Goals:**

- Introduce a new top-level `project agents definitions ...` CLI subtree.
- Merge low-level role/preset authoring with `project easy specialist ...`.
- Replace `houmao-manage-credentials` or move auth-bundle content mutation into the new skill.
- Add flag-driven editing for advanced preset blocks such as `mailbox` or `extra`.
- Change the underlying role/preset directory layout under `.houmao/agents/`.

## Decisions

### Keep low-level authoring under the existing `project agents roles` tree

The new update behavior will extend the current CLI family instead of creating a second parallel “definitions” namespace.

Concretely:

- `project agents roles` gains `set`
- `project agents roles presets` gains `set`

Rationale:

- the repository already documents `project agents roles ...` as the low-level compatibility-tree authoring surface
- reusing that tree keeps help output, docs, and tests aligned with the current mental model
- a second namespace would duplicate the same nouns and immediately create routing ambiguity for the packaged skill

Alternative considered:

- add `project agents definitions ...`
  - rejected because it would either wrap the same paths redundantly or require a broader CLI reorganization than this change needs

### Make prompt inspection opt-in on `roles get`

`project agents roles get --name <role>` will keep its current summary-oriented behavior by default. A new opt-in flag such as `--include-prompt` will add the prompt text to the structured output when the caller explicitly needs it.

Rationale:

- the current default `get` payload is compact and safe for ordinary inspection
- prompt text can be long, so always returning it would make list/get outputs noisy and more expensive for agents to process
- the packaged skill still needs a supported CLI path to inspect prompt content when the user asks to view or revise the current definition

Alternative considered:

- always return prompt text from `roles get`
  - rejected because it makes default inspection less readable and changes the existing output contract more than necessary

### Split role updates from preset updates

Role mutation and preset mutation will stay on separate verbs:

- `project agents roles set` updates `system-prompt.md`
- `project agents roles presets set` patches one preset file

`roles set` will accept role-targeted prompt inputs only:

- `--system-prompt <text>`
- `--system-prompt-file <path>`
- `--clear-system-prompt`

The command will require at least one explicit prompt mutation and will continue to maintain the canonical `system-prompt.md` file, including the valid promptless-role case by writing an empty file when cleared.

Rationale:

- the filesystem model already treats the prompt file and preset YAML as distinct authored artifacts
- separate verbs keep argument meaning unambiguous and preserve the role/preset split already present in the parser and docs
- `--clear-system-prompt` preserves the existing “empty prompt is valid” behavior without forcing ad hoc file deletion

Alternative considered:

- one combined definition-set command that mutates both prompt and preset fields at once
  - rejected because it would mix separate source artifacts and make partial updates harder to validate and explain

### Make `presets set` a patch-style command that preserves unmanaged blocks

`project agents roles presets set` will patch only the managed fields on an existing preset:

- auth reference through `--auth <bundle>` or `--clear-auth`
- skill membership through `--add-skill`, `--remove-skill`, and `--clear-skills`
- prompt posture through `--prompt-mode unattended|as_is` or `--clear-prompt-mode`

The command will require at least one explicit change flag. It will preserve unrelated preset content, especially:

- `mailbox`
- `extra`
- unedited `launch` subfields such as `env_records`

Skill-list updates will follow patch semantics:

- start from the current skill list
- remove any named skills requested through `--remove-skill`
- if `--clear-skills` is present, reset the list before additions
- append `--add-skill` values in flag order while deduplicating by first occurrence

Rationale:

- low-level presets can already carry advanced blocks that this change does not intend to own
- patch semantics let operators and packaged skills update one concern without rewriting the entire YAML payload
- separate add/remove/clear flags are safer than treating repeated `--skill` as silent full replacement

Alternative considered:

- use repeated `--skill` as whole-list replacement
  - rejected because it makes incremental edits too destructive and would require callers to restate existing skill membership for simple one-skill changes

### Keep credential-reference edits in scope, but credential-bundle content edits out of scope

The new skill and new preset-update command will treat the preset’s auth reference as part of the agent definition. Updating that reference stays in scope through `project agents roles presets set --auth ...` or `--clear-auth`.

Mutating the underlying bundle contents remains out of scope and stays on:

- `project agents tools <tool> auth list|get|add|set|remove`
- packaged `houmao-manage-credentials`

Rationale:

- the preset’s selected auth bundle is definition structure
- env vars and auth files inside that bundle are secret-bearing bundle contents with a distinct CLI and packaged skill already designed for them

Alternative considered:

- let `houmao-manage-agent-definition` route direct auth-bundle writes too
  - rejected because it would blur the skill boundary and duplicate the existing credential-management workflow

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
- a separate set would add operator complexity without representing a meaningfully different installation decision

## Risks / Trade-offs

- [Patch semantics can become hard to reason about] → Keep the editable field set narrow, require at least one explicit mutation flag, and preserve unrelated blocks instead of rewriting whole preset payloads.
- [Prompt inspection can leak large prompt blobs into automation unexpectedly] → Make prompt text opt-in behind `--include-prompt` and keep default role inspection summary-only.
- [Definition management and credential management may still be confused by users] → Make the packaged skill and docs state explicitly that preset auth references are in scope while auth-bundle contents stay on `houmao-manage-credentials`.
- [Expanded `user-control` installs add one more packaged skill to managed homes] → Reuse the existing set semantics so the additional install surface is intentional and consistently reported through `system-skills list|install|status`.

## Migration Plan

1. Extend the low-level CLI help and implementation under `project agents roles` and `project agents roles presets`.
2. Add or update tests for prompt inspection, prompt mutation, preset patching, and failure cases when no explicit change is provided.
3. Add the new packaged skill asset tree and update the packaged catalog / installer constants for `user-control`.
4. Update `houmao-mgr system-skills` tests and docs to report the expanded `user-control` inventory and CLI-default resolved skill list.
5. Update `houmao-mgr` project CLI reference docs for the new low-level verbs and the auth-reference versus auth-bundle-content boundary.

Rollback is straightforward because this change is additive:

- remove the new packaged skill from the catalog and asset root
- remove the new CLI verbs
- reinstall packaged system skills if a rollback needs the old inventory reflected in an explicit tool home

No persistent data migration is required because existing role roots and preset files remain valid, and the new preset patch path preserves unmanaged blocks instead of rewriting them into a new schema.

## Open Questions

None at proposal time.
