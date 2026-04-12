## Context

Easy specialists are catalog-backed source definitions that compile to the `.houmao/agents/` compatibility tree. Today `project easy specialist create` supports same-name replacement after confirmation, but replacement has recreate semantics: the operator must respecify fields they want to preserve, otherwise optional fields such as skills, prompt mode, model config, setup choice, and durable env records may be dropped. Easy profiles already have a separate `set` command with patch semantics, and low-level recipes have `presets set` for targeted mutation, so the specialist source-definition lane is the inconsistent part.

The current implementation also treats the catalog and managed content store as authoritative. Directly editing `.houmao/agents/presets/<name>.yaml` is not the right user-facing fix because the projection may be rematerialized from the catalog later.

## Goals / Non-Goals

**Goals:**

- Add a patch-style specialist edit command that preserves unspecified stored fields.
- Let operators update common specialist source-definition fields without removing and recreating the specialist.
- Keep edits catalog-backed and refresh the compatibility projection after mutation.
- Reuse existing validation semantics for prompt input, skill directory import, setup existence, credential display-name lookup, model config, prompt mode, and persistent env records.
- Update agent-facing system skill guidance and human-facing docs so users discover the patch path.

**Non-Goals:**

- Rename specialists, change role names, or change the tool lane in the first version.
- Mutate credential contents through `specialist set`; credential contents stay owned by `project credentials` and `credentials`.
- Mutate running managed agents or existing runtime homes in place.
- Add a new catalog schema version unless implementation proves the existing tables cannot express the patched state.
- Make `.houmao/agents/` projection files an authoritative editing surface.

## Decisions

### Decision: Add `project easy specialist set` instead of expanding replacement semantics

`project easy specialist set --name <specialist> ...` will be the ordinary edit command. It will load the existing specialist, compute a new complete specialist source state, and store it back while preserving fields not mentioned by the CLI invocation.

Replacement remains `project easy specialist create --name <specialist> ... --yes`. That command keeps create semantics where omitted optional fields are not implicitly preserved.

Alternative considered: make `create --yes` preserve unspecified fields. Rejected because that would make create semantics differ from easy-profile replacement and would blur the distinction between patch and replacement.

### Decision: Keep the first patch surface scoped to stable specialist identity and tool lane

The initial `set` command will not accept `--tool` or a rename option. A specialist name is currently tied to role name and default preset naming, and the tool lane determines provider mapping, credential validation, auth profile lookup, setup path, launch policy, and Gemini headless rules. Allowing those fields to change in the same patch command would make a routine skill edit carry high migration risk.

Operators who need to change the tool lane can continue using same-name replacement or create a new specialist with a new name.

### Decision: Use existing field-family mutation patterns

The command should expose these field families:

- prompt: `--system-prompt`, `--system-prompt-file`, `--clear-system-prompt`
- skills: `--with-skill <dir>`, `--add-skill <name>`, `--remove-skill <name>`, `--clear-skills`
- setup: `--setup <name>`
- credential reference: `--credential <display-name>`
- launch prompt mode: `--prompt-mode unattended|as_is`, `--clear-prompt-mode`
- model config: `--model`, `--clear-model`, `--reasoning-level`, `--clear-reasoning-level`
- durable specialist env: repeatable `--env-set NAME=value`, `--clear-env`

`--with-skill` imports and adds a skill directory. `--add-skill` binds an already available project skill by name. Removing or clearing skill bindings does not delete shared skill content.

### Decision: Recompute then store the complete specialist state

The command should use a helper parallel to `_store_launch_profile_from_cli`: load current specialist metadata, resolve requested mutations, reject empty mutations, then store the resolved state through catalog-backed specialist storage.

Implementation can stage preserved prompt/skill inputs from the current projection after first materializing from the catalog, or introduce a small catalog helper that updates content references directly. If using the existing `store_specialist_from_sources(...)` helper, avoid passing canonical content-store paths as their own snapshot source because copying a file or tree onto itself is fragile. The projection or an explicit temporary staging path is safer as a snapshot source.

If a setup change changes the canonical preset name, the old projected preset file should be removed after the catalog update so `.houmao/agents/presets/` does not retain a stale specialist-owned recipe.

### Decision: Specialist edits affect future launches only

`specialist set` updates the reusable source definition. It does not rewrite live manifests, running homes, tmux sessions, or already-launched agent behavior. Users should relaunch or rebuild from the specialist when they want the edited source to take effect.

## Risks / Trade-offs

- Stale projection files after setup changes → Remove the old projected preset when the resolved preset name changes and then rematerialize the catalog projection.
- Accidentally deleting shared skills → Treat skill removal as binding removal only; keep content cleanup out of scope unless an existing shared-content cleanup path already owns it.
- Credential confusion → `--credential` only selects an existing display-name credential for the specialist's current tool. Credential creation and mutation remain in credential-management commands.
- Empty patch commands creating noisy rewrites → Reject `specialist set --name <specialist>` when no update or clear flag is supplied.
- Drift between system skill guidance and CLI flags → Update the packaged `houmao-specialist-mgr` action guidance and tests along with the CLI command.
