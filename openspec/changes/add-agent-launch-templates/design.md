## Context

Houmao currently has two durable configuration layers for agent startup:

- source-oriented reusable configuration:
  - low-level named presets under `.houmao/agents/presets/`
  - easy-layer specialists persisted in the project catalog and projected into the compatibility tree
- runtime-only resolved launch state:
  - build manifest inputs
  - runtime `LaunchPlan`

What is missing is a reusable operator-owned layer that captures how one source should be instantiated in a particular context. Today that missing layer is worked around by retyping launch-time inputs such as agent name, workdir, auth override, mailbox inputs, gateway posture, and similar settings every time the operator launches.

The low-level noun `preset` is also overloaded. In practice it behaves as a declarative build recipe, while operators also use it as the unit they launch from. That ambiguity becomes sharper once the system adds a second reusable launch-oriented object.

This change adds a reusable launch-template layer while keeping runtime `LaunchPlan` derived and ephemeral.

## Goals / Non-Goals

**Goals:**
- Introduce a first-class reusable launch-template object distinct from specialists, low-level recipes, and live instances.
- Let operators persist launch-time defaults such as identity, workdir, auth override, mailbox config, launch posture, gateway posture, env defaults, and prompt overlay.
- Keep a clear precedence model across recipe defaults, launch-template defaults, direct CLI overrides, and live runtime mutations.
- Clarify low-level terminology so the source-oriented object is described publicly as a recipe, while keeping compatibility with the existing preset-backed implementation.
- Fit the new object into the existing catalog-backed project model and compatibility projection without making runtime `LaunchPlan` user-authored.

**Non-Goals:**
- Removing runtime `LaunchPlan` or collapsing it into user-authored config.
- Replacing specialists with launch templates or vice versa.
- Defining persisted per-instance live state beyond the existing managed-agent manifest and runtime registry.
- Designing arbitrary prompt transformation engines beyond simple launch-template role-prompt append or replace behavior.
- Renaming every internal path and symbol from `preset` to `recipe` in one step when a compatibility alias is sufficient.

## Decisions

### Decision: Add `LaunchTemplate` as a new durable object between recipe/specialist and instance

The model becomes:

```text
recipe or specialist
        ->
launch template
        ->
build manifest / LaunchPlan
        ->
live instance
```

`LaunchTemplate` is the reusable operator-owned answer to “launch this source in this way.” It is not a live instance and it is not the runtime `LaunchPlan`.

Rationale:
- It solves the missing reuse layer directly instead of overloading specialists or recipes.
- It preserves the current separation between declarative source config and runtime-derived execution state.

Alternatives considered:
- Expand `specialist` to also own instance identity and workdir.
  Rejected because specialist would mix “what the agent is” with “how this specific context should launch it.”
- Expand low-level `preset` to own full launch-time state.
  Rejected because it makes the source recipe and the instantiation profile indistinguishable.

### Decision: Keep source ownership separate from launch-template ownership

Recipes and specialists continue to own reusable source-oriented defaults:
- role
- tool
- setup
- skills
- default auth
- recipe-owned launch defaults
- declarative mailbox defaults that belong to the source itself

Launch templates own reusable instantiation defaults:
- source reference
- agent name or id defaults
- working directory
- auth override
- operator prompt-mode override
- durable env defaults
- mailbox defaults for the launched instance
- gateway or backend posture
- prompt overlay

Rationale:
- This keeps reusable role or tool behavior separate from operator or workspace context.
- It allows multiple launch templates such as `alice`, `bob`, and `nightly-ci` to point at the same recipe or specialist without cloning the recipe.

Alternatives considered:
- Let both recipe and launch template freely own the same fields.
  Rejected because it would make precedence unclear and make inspection harder.

### Decision: Use canonical public `recipe` terminology while keeping `preset` compatibility

The low-level source object is described publicly as a recipe, because that is what the object semantically is: a declarative source-oriented build recipe.

Compatibility strategy:
- existing `.houmao/agents/presets/` storage remains valid in this change
- existing internal types may keep compatibility aliases where practical
- new or revised operator-facing CLI and docs use `recipe` as the canonical term
- `project agents presets ...` remains a compatibility alias for the canonical low-level recipe surface until a future cleanup change decides whether to remove it

Rationale:
- It resolves the ambiguity without forcing a large storage migration in the same change.
- The current code already exposes recipe-shaped compatibility aliases in build and launch paths.

Alternatives considered:
- Hard-rename all storage and commands from `preset` to `recipe` now.
  Rejected because it adds migration churn that is not necessary to land launch templates.
- Keep `preset` as the public term.
  Rejected because it stays ambiguous once launch templates exist.

### Decision: Store launch templates in the project catalog and project them into a dedicated compatibility tree

Catalog:
- add a launch-template object and reference edges to its source
- support source kinds `specialist` and `recipe`
- allow optional managed content references for large prompt-overlay text

Compatibility projection:
- project low-level launch templates under `.houmao/agents/launch-templates/`
- keep recipe projection under `.houmao/agents/presets/` for this change

Rationale:
- It matches the repository’s direction toward catalog-backed semantic storage with compatibility projection for file-tree consumers.
- It gives low-level and easy workflows one durable semantic store.

Alternatives considered:
- Store easy launch templates only in `.houmao/easy/` metadata files.
  Rejected because that repeats the pre-catalog split the repo is moving away from.

### Decision: Support prompt overlays as append-or-replace only in v1

Launch templates may optionally define a prompt overlay with:
- `mode: append`
- `mode: replace`
- text content

The effective role prompt is composed before backend-specific role injection is planned.

Rationale:
- This covers the main “Alice-specific instructions” use case without introducing a templating engine or unbounded prompt mutation semantics.

Alternatives considered:
- No prompt overlay support in v1.
  Rejected because prompt specialization is one of the clearest reasons to create reusable launch templates.
- Arbitrary substitutions and multi-stage transforms.
  Rejected because it adds complexity and weakens prompt provenance.

### Decision: Define one explicit precedence order

Launch resolution uses:

```text
tool adapter defaults
-> recipe defaults
-> launch-template defaults
-> direct CLI overrides
-> live runtime mutations
```

Field-specific notes:
- recipe still owns base source behavior
- launch template may override source-owned launch selections where allowed by contract
- direct CLI overrides remain one-off and do not persist back into the template
- live mailbox registration or similar runtime mutations stay runtime-owned and manifest-backed

Rationale:
- This gives operators a predictable model for inspection and replay.

Alternatives considered:
- Let launch templates overwrite recipe material completely.
  Rejected because templates are instantiation profiles, not replacement recipes.

### Decision: Add template-aware launch flows rather than inventing a second instance registry

Easy surface:
- `project easy template create|list|get|remove`
- `project easy instance launch --template <name>`

Low-level surface:
- canonical recipe-oriented source administration remains under `project agents`
- add low-level launch-template administration under `project agents`
- allow managed launch from a template through `houmao-mgr agents launch --template <name>`

Instance inspection remains derived from the existing runtime manifest and registry. The system does not add a second persisted live-instance catalog in this change.

Rationale:
- The repo already treats instance state as runtime-derived rather than separately authored config.
- A template-backed launch is still just one managed-agent launch.

Alternatives considered:
- Add a persistent instance-definition registry separate from launch templates.
  Rejected because it duplicates the purpose of launch templates and blurs live versus reusable state.

## Risks / Trade-offs

- [Naming split between recipe and preset remains visible internally] -> Keep compatibility aliases intentional, document recipe as canonical public terminology, and defer full storage rename to a follow-up if still valuable.
- [Template sources can become hard to inspect if specialist and recipe paths diverge too much] -> Use a common semantic model and require source-kind plus source-name in template inspection output.
- [Prompt overlays can weaken provenance if their source is opaque] -> Persist overlay mode and text source clearly and surface the effective source plus overlay in inspection paths.
- [Too many launch-owned fields could turn templates into a shadow instance registry] -> Keep templates reusable and declarative, and leave live state in manifests and runtime registry only.
- [Template precedence could surprise users when combined with direct CLI flags] -> Document one explicit precedence order and expose effective values in `get` and launch result output.
- [Catalog and compatibility-projection changes touch multiple modules] -> Keep the projection additive, retain existing preset projection, and implement templates through the same materialization seam the project overlay already uses.

## Migration Plan

1. Add catalog schema support for launch-template objects and their source references.
2. Add compatibility projection for `.houmao/agents/launch-templates/`.
3. Add easy-layer template CRUD and template-backed launch.
4. Add low-level recipe-oriented terminology updates and compatibility aliases for existing preset administration.
5. Add managed `agents launch --template` resolution and precedence support.
6. Update docs and inspection output to distinguish recipe, launch template, live instance, and runtime `LaunchPlan`.

Rollback strategy:
- launch-template code paths are additive, so disabling new CLI entrypoints leaves existing specialist-backed and recipe-backed launch intact
- keeping preset compatibility aliases and existing projection paths reduces rollback pressure on current users

## Open Questions

- Should `houmao-mgr agents launch` also gain a canonical `--recipe` selector in this change, or is `--template` plus existing `--agents` sufficient for the first step?
- Should low-level template files support only inline prompt-overlay text in v1, or also a file-reference form for large overlays?
- Should template-owned mailbox config support both declarative defaults and launch-time late registration metadata, or only the declarative launch-time defaults used at start?
- Should `project easy instance get/list` report the originating launch template whenever one was used, and should that origin become part of the stable runtime inspection contract?
