## Context

Houmao currently has two separate asset stories for agent-facing content:

- project bootstrap assets live under `src/houmao/project/assets/starter_agents/` and feed overlay initialization,
- runtime-owned mailbox skills live under `src/houmao/agents/realm_controller/assets/system_skills/` and are installed through mailbox-specific helper code.

That split leaks into runtime behavior. Managed brain construction installs selected project skills plus mailbox-specific Houmao skills, while joined-session adoption uses a second mailbox-specific installation path. External agents that are not launched by Houmao have no supported `houmao-mgr` workflow for installing the current Houmao-owned `houmao-*` skills into their own tool homes before using Houmao contracts.

The change is intentionally narrow. It covers only the current Houmao-owned `houmao-*` skills, which are mailbox-oriented today. It does not add new skills, does not redesign future skill authoring, and does not pull project bootstrap assets into the same ownership bucket.

## Goals / Non-Goals

**Goals:**

- Package the current Houmao-owned `houmao-*` skills under one maintained runtime asset root.
- Define one explicit schema contract for the packaged skill catalog and validate it during loading.
- Define one shared installer contract for projecting selected current Houmao-owned skills into Claude, Codex, and Gemini homes.
- Reuse that installer for managed brain construction, joined-session adoption, and explicit operator-driven installation into external tool homes.
- Preserve today's tool-visible skill locations so runtime prompts, docs, and tests do not need a wholesale contract rewrite.
- Record Houmao-owned install state in the target home so repeated installs are idempotent and unrelated user-authored content is preserved.

**Non-Goals:**

- Designing or shipping new Houmao-owned skills.
- Generalizing the system to non-skill asset kinds such as provider-specific slash-command packs.
- Replacing project-local user skill selection from presets or the catalog-backed overlay.
- Adding configurable conditional rule evaluation or other dynamic selection logic beyond named sets, explicit repeated `--set` / `--skill` selection, and fixed auto-install set lists.

## Decisions

### Decision: Keep project bootstrap assets and Houmao-owned system skills in separate asset roots

The current Houmao-owned `houmao-*` skills will move to a neutral packaged runtime asset root under `src/houmao/agents/assets/`, while `src/houmao/project/assets/starter_agents/` remains the project bootstrap source tree.

Rationale:

- project bootstrap assets seed repo-local overlay content and tool adapters,
- Houmao-owned system skills are runtime-installed assets that may target arbitrary external tool homes,
- keeping them separate avoids coupling external home installation to project overlay/catalog semantics.

Alternatives considered:

- Move everything under `project/assets`.
  Rejected because external tool-home installation is not a project-overlay concern.
- Leave system skills under `realm_controller/assets/system_skills`.
  Rejected because that keeps mailbox/runtime internals as the apparent owner of assets that need broader CLI installation support.

### Decision: Introduce one simple packaged system-skill catalog with named sets and one shared installer

The implementation will introduce one packaged catalog file plus one shared installer module for the current Houmao-owned `houmao-*` skills.

The authoritative packaged catalog will live alongside the packaged skills, for example at `src/houmao/agents/assets/system_skills/catalog.toml`.

That packaged catalog will have one explicit schema contract and one matching JSON Schema document, for example `src/houmao/agents/assets/system_skills/catalog.schema.json`.

That catalog will describe only the current skill set in this change and will contain three sections:

- `skills`: the full inventory of current installable Houmao-owned skills and the packaged asset subpath for each one,
- `sets`: named skill sets whose members are explicit current skill names,
- `auto_install`: fixed named set lists for Houmao-managed launch, Houmao-managed join, and CLI default installation.

The installer will accept a target tool home plus either:

- one or more named sets resolved from the packaged catalog, or
- an explicit selected skill list from the CLI, or
- one of the fixed `auto_install` set lists from the packaged catalog.

Set members will be explicit skill names. This change will not add conditional rule evaluation, set nesting, transport-based catalog expansion, or other dynamic profile machinery. Tool-specific visible path rules remain in code for now rather than being moved into the catalog.

Loading the packaged catalog will:

1. read the packaged TOML,
2. convert it into the normalized JSON-like data structure expected by the loader,
3. validate that payload against the packaged JSON Schema,
4. only then resolve named sets or auto-install set lists.

Rationale:

- one packaged catalog keeps managed launch, join, and explicit external installation on the same source of truth,
- one installer removes mailbox-specific code duplication,
- named sets let operators and internal flows reuse curated selections without inventing future rule machinery.
- schema validation keeps malformed packaged config from silently producing partial install behavior.

Alternatives considered:

- Keep mailbox-specific helper functions and add a second explicit CLI around them.
  Rejected because it preserves duplicated logic and keeps the refactor partial.
- Reuse project preset skill projection directly.
  Rejected because project-selected skills and Houmao-owned runtime-installed skills have different ownership and lifecycle rules.
- Add profile/rule-based catalog resolution now.
  Rejected because the current requirement is only to support curated named sets plus fixed auto-install set lists.

### Decision: Validate the packaged catalog with JSON Schema during loading

The packaged catalog will declare an explicit schema version and will be validated against a packaged JSON Schema during load.

Validation will fail closed before any set expansion, auto-install resolution, or filesystem mutation begins.

The schema will validate at minimum:

- required top-level sections,
- `schema_version`,
- skill record shape,
- set record shape,
- auto-install set-list shape,
- string-array membership types.

Cross-reference checks that JSON Schema does not express cleanly, such as set members referring to unknown skills or auto-install lists referring to unknown sets, will still be enforced by the loader after schema validation and before installation proceeds.

Rationale:

- the catalog is packaged configuration that affects automatic installs into real tool homes,
- explicit schema validation makes format drift and bad packaged data fail early and predictably,
- JSON Schema gives a stable contract for tests and future evolution.

Alternatives considered:

- Rely only on ad hoc Python validation.
  Rejected because the user explicitly wants an explicit schema contract and schema-based validation.
- Store the catalog directly as JSON to avoid TOML-to-JSON normalization.
  Rejected because TOML remains fine as an authoring format as long as the loader validates the normalized structure against JSON Schema.

### Decision: Keep set resolution flat and explicit in this change

Catalog `sets` will expand only to explicit skill names. Sets will not reference other sets in this change.

When installation input includes multiple sets plus explicit skill names, resolution will:

1. expand sets in the order given,
2. append explicit skill names,
3. deduplicate by first occurrence.

Unknown set names or unknown skill names will fail explicitly.

Rationale:

- flat set resolution is easy to validate and document,
- the current skill inventory is small,
- it avoids introducing recursive expansion or precedence rules before they are needed.

Alternatives considered:

- Allow sets to include other sets.
  Rejected because it adds recursion and cycle validation without a current need.
- Allow implicit “all” behavior when no set is supplied.
  Rejected because explicit selection or explicit default is clearer.

### Decision: Preserve current visible tool-native paths for the current skill set

The installer will preserve today's visible projected paths for the current skills:

- Claude: `skills/<houmao-skill>/`
- Codex: `skills/mailbox/<houmao-skill>/`
- Gemini: `.agents/skills/<houmao-skill>/`

The installer may use per-skill/per-tool projection metadata internally, but the user-facing projection contract remains unchanged for this change.

Rationale:

- managed prompts, docs, tests, and demos already rely on these paths and naming conventions,
- preserving visible paths reduces migration risk while still changing the ownership and installation internals,
- Codex can keep the mailbox subtree for the current mailbox-oriented skill set without forcing a broader surface redesign now.

Alternatives considered:

- Flatten Codex to `skills/<houmao-skill>/` immediately.
  Rejected because it changes a visible contract that this refactor does not need to change.
- Add compatibility mirrors in multiple locations.
  Rejected because the project has been moving away from hidden or duplicate skill mirrors.

### Decision: Install by copy and record Houmao-owned install state inside the target home

Houmao-owned system skills will be copied into the target home and tracked through a hidden Houmao-owned install-state record under the target home, for example `.<houmao>/system-skills/install-state.json`.

That state will record:

- target tool,
- installed current skill names,
- projected relative paths,
- content/version metadata sufficient for idempotent reinstall and owned-path detection.

The installer will preserve unrelated user-authored skill content. If a required projected path collides with content that is not recorded as Houmao-owned, installation fails unless the operator explicitly forces replacement.

Rationale:

- external homes cannot rely on project-local symlink sources,
- copied packaged assets survive independent use of the target tool home,
- install-state ownership is the cleanest way to distinguish Houmao-managed projected content from unrelated files.

Alternatives considered:

- Symlink packaged assets into target homes.
  Rejected because external homes may outlive the workspace layout and because packaged resources are not stable project-local authoring roots.
- Blind overwrite of reserved `houmao-*` paths.
  Rejected because external homes may already contain user-managed content and the installer must fail closed.

### Decision: Add a top-level `houmao-mgr system-skills` command family

The operator-facing CLI surface will be a new top-level `houmao-mgr system-skills` group with:

- `list`
- `install`
- `status`

`install` will target explicit tool homes and support repeatable `--set <name>`, repeatable `--skill <name>`, and `--default` for the CLI default set list from the packaged catalog.

Rationale:

- the target is an arbitrary tool home, not a project overlay or a currently running managed session,
- top-level placement makes the command discoverable for human- or agent-operated external homes,
- it keeps project-local content management separate from Houmao-owned runtime asset installation.

Alternatives considered:

- Put the command under `houmao-mgr project`.
  Rejected because project overlay semantics do not apply to arbitrary external homes.
- Put the command under `houmao-mgr agents`.
  Rejected because the target may be an external home with no managed session identity.

### Decision: Use fixed set-based auto-install lists for managed launch and join

The packaged catalog will contain fixed `auto_install` set lists for:

- managed launch,
- managed join,
- CLI default installation.

Managed brain construction and joined-session adoption will resolve their internal auto-install behavior from those set lists rather than from a flat skill list embedded in code.

For joined sessions, the existing explicit opt-out posture stays in place for this change through the current `--no-install-houmao-skills` operator-facing behavior, but the meaning broadens from mailbox-only installation to catalog-driven managed-join current Houmao-owned skill installation.

Rationale:

- one catalog-driven auto-install section avoids drift between launch, join, and CLI default behavior,
- broadening the existing opt-out keeps operator intent stable while the underlying installer changes,
- later changes can add more selection controls without redoing the ownership model.

Alternatives considered:

- Always install every current Houmao-owned skill.
  Rejected because the user wants curated subsets.
- Add fully configurable conditional selection in this refactor.
  Rejected because it expands scope beyond named sets and fixed auto-install lists.

## Risks / Trade-offs

- [Collision with existing external-home content] → Track Houmao-owned projected paths explicitly and fail closed on non-owned collisions unless the operator uses force.
- [Malformed packaged catalog causes partial install behavior] → Validate the normalized catalog payload against packaged JSON Schema and fail before set expansion or filesystem mutation.
- [Over-generalizing around future skill types] → Keep the registry limited to the current skill set and avoid introducing non-skill asset kinds in this change.
- [Path-contract churn across tools] → Preserve current visible tool-native projected paths for the current skills and only change the source/installer internals.
- [Join opt-out naming remains mailbox-flavored] → Keep the existing flag semantics for now to reduce churn, and revisit naming in a later CLI cleanup once broader system-skill coverage exists.

## Migration Plan

1. Introduce the packaged system-skill asset root, `catalog.toml`, `catalog.schema.json`, named sets, fixed auto-install set lists, and shared installer for the current Houmao-owned skill set.
2. Update managed brain construction to resolve its internal auto-install behavior from the catalog’s managed-launch set list instead of direct mailbox-specific projection.
3. Update joined-session adoption to use the same installer and the catalog’s managed-join set list while preserving explicit opt-out behavior.
4. Add the `houmao-mgr system-skills` command family for explicit external-home installation and inspection using set-based selection.
5. Update mailbox/runtime docs and tests to describe the shared installer contract rather than mailbox-only installation internals.
6. Remove or reduce the old mailbox-only installation helpers after tests and docs validate the shared path.

Rollback is straightforward because the visible skill paths remain unchanged. Reverting to the prior installer path only requires restoring the old mailbox-specific projection calls and removing the new CLI group.

## Open Questions

- Should a later follow-up rename `--no-install-houmao-skills` to a more general flag once non-mailbox Houmao-owned skills exist?
- Should future work add managed-launch opt-out or per-role set extension once the current set-based installer refactor is complete?
