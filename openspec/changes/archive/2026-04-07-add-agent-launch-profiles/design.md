## Context

Houmao already treats easy and non-easy command families as different operator contracts rather than accidental duplication.

- Easy surfaces assume common use cases and hide lower-level launch detail.
- Non-easy surfaces expose more of the contract so operators must answer more questions explicitly.

That split exists today for source definitions:

- easy source definition: specialist
- low-level source definition: recipe, with `preset` compatibility still visible in current storage and CLI

The missing piece is birth-time launch configuration. Operators can persist reusable source definitions, but not reusable launch context in a way that respects the same easy-versus-explicit split.

This change adds a shared launch-profile semantic layer while keeping two distinct user-facing authoring surfaces:

- easy `profile`, specialist-backed and opinionated
- low-level `launch-profile`, recipe-backed and explicit

Runtime `LaunchPlan` remains derived and ephemeral.

## Goals / Non-Goals

**Goals:**
- Introduce reusable birth-time launch configuration without collapsing easy and explicit operator lanes into one CLI surface.
- Keep user-facing differentiation sharp:
  - easy `profile` for specialist-backed common cases
  - explicit `launch-profile` for recipe-backed low-level control
- Reuse one shared persistence and launch-resolution model under those two surfaces.
- Keep a clear precedence model across source defaults, profile defaults, direct CLI overrides, and live runtime mutations.
- Continue clarifying the low-level source noun as `recipe` while keeping compatibility where needed.

**Non-Goals:**
- Replacing specialists with profiles or recipes with launch profiles.
- Collapsing `project easy instance launch` and `agents launch` into one operator surface.
- Making runtime `LaunchPlan` user-authored.
- Introducing arbitrary prompt transformation engines beyond append-or-replace prompt overlays.
- Renaming every internal `preset` path or symbol in the same change when compatibility aliases are sufficient.

## Decisions

### Decision: One shared `LaunchProfile` semantic object, two user-facing authoring lanes

Under the hood, the system adds one shared launch-profile object family that captures reusable birth-time launch defaults.

User-facing surfaces stay split:

```text
easy lane:
  specialist -> profile -> instance

explicit lane:
  recipe -> launch-profile -> managed agent
```

Rationale:
- This preserves the repo's intentional easy-versus-explicit UX split.
- It avoids implementing two unrelated persistence models for the same underlying launch concept.

Alternatives considered:
- One shared `project launch-profiles ...` surface for both lanes.
  Rejected because it erases the intended difference between easy and explicit operator workflows.
- Two entirely separate semantic models.
  Rejected because persistence, precedence, projection, and runtime provenance would duplicate unnecessarily.

### Decision: Easy surface uses `profile` as the noun and remains specialist-backed

The easy birth-time object is surfaced as:

```text
houmao-mgr project easy profile ...
houmao-mgr project easy instance launch --profile <name>
```

Easy profiles are specialist-backed and opinionated:
- source is always one specialist
- authoring surface is smaller and assumption-rich
- first-time users do not have to answer every low-level launch question up front

Rationale:
- `profile` reads naturally within `project easy ...`
- it stays aligned with the easy command family's goal of lowering operator burden

Alternatives considered:
- Keep `template` in the easy lane.
  Rejected because it is too generic.
- Use `birth-profile` publicly.
  Rejected because it is not natural CLI vocabulary even though it captures the intended semantics.

### Decision: Explicit surface uses `launch-profile` as the noun and remains recipe-backed

The explicit birth-time object is surfaced as:

```text
houmao-mgr project agents launch-profiles ...
houmao-mgr agents launch --launch-profile <name>
```

Explicit launch profiles are recipe-backed and low-level:
- source is one named recipe
- authoring surface exposes more of the launch contract
- behavior should not depend on easy-only assumptions

Rationale:
- `launch-profile` is specific enough to distinguish it from recipe/source definitions and from live instances
- it fits the existing low-level `project agents ...` family

Alternatives considered:
- Use only `profile` in the low-level lane too.
  Rejected because it becomes too ambiguous once easy profiles also exist.

### Decision: Keep launch commands split by operator contract

This change preserves both launch surfaces:

- `project easy instance launch`
- `agents launch`

Their difference is intentional:

- `project easy instance launch` is project-aware, specialist/easy-profile oriented, and assumption-rich
- `agents launch` is explicit, lower-level, and centered on recipe or launch-profile selection

Rationale:
- The easy lane is designed to hide choices a first-time user should not need to care about.
- The explicit lane exists precisely so those choices are visible when operators want precise control.

### Decision: Source ownership stays separate from birth-time ownership

Source definitions keep owning reusable source-oriented defaults:
- role
- tool
- setup
- skills
- default auth
- recipe-owned launch defaults
- source-owned mailbox defaults when those belong to the source recipe itself

Birth-time profiles own reusable instantiation defaults:
- source reference
- managed-agent identity defaults
- working directory
- auth override
- operator prompt-mode override
- durable env defaults
- mailbox defaults for the launched instance
- gateway or headless posture
- prompt overlay

Rationale:
- It keeps “what this agent is” separate from “how this recurring launch context should instantiate it.”

### Decision: Use canonical public `recipe` terminology while keeping `preset` compatibility

The low-level source object is described publicly as a recipe.

Compatibility strategy:
- existing `.houmao/agents/presets/` storage remains valid in this change
- existing internal compatibility aliases may stay where practical
- new or revised operator-facing CLI and docs use `recipe` as the canonical term
- `project agents presets ...` remains a compatibility alias for the canonical recipe surface until a future cleanup change decides otherwise

### Decision: Store launch profiles in the catalog and project them into `.houmao/agents/launch-profiles/`

Catalog support:
- one shared launch-profile object family
- source-kind provenance for specialist-backed easy profiles and recipe-backed explicit launch profiles
- managed content references for larger prompt-overlay payloads

Compatibility projection:
- materialize projected launch profiles under `.houmao/agents/launch-profiles/`
- retain `.houmao/agents/presets/` for recipe projection in this change

Rationale:
- It gives both easy and explicit authoring lanes one durable semantic store.
- It preserves file-tree compatibility for low-level inspection and launch resolution.

### Decision: Prompt overlays remain append-or-replace only in v1

Both easy profiles and explicit launch profiles may define a prompt overlay with:
- `mode: append`
- `mode: replace`
- text content

The effective role prompt is composed before backend-specific role injection planning.

### Decision: One explicit precedence order

Launch resolution uses:

```text
tool adapter defaults
-> recipe defaults
-> launch-profile defaults
-> direct CLI overrides
-> live runtime mutations
```

For easy profiles, specialist-backed source resolution compiles down into the same recipe-backed resolution layers before the profile layer applies.

Live runtime mutations such as late mailbox registration remain runtime-owned and do not rewrite the stored profile.

### Decision: Runtime provenance records both source lane and birth-profile lane

Launch metadata and runtime inspection should preserve, in secret-free form:
- whether the launch originated from a specialist or recipe source
- whether the birth-time reusable config came from an easy profile or an explicit launch profile
- the originating profile name when available

Rationale:
- It makes inspection and replay understandable without collapsing the easy and explicit models together.

## Risks / Trade-offs

- [Two user-facing nouns for birth-time config could feel inconsistent] -> Keep the semantic model shared, document the UX split explicitly, and make the distinction align with the existing easy-versus-explicit command philosophy.
- [Profile versus launch-profile could still be confusing without source context] -> Always show source kind and source name in inspection output.
- [Shared storage plus split UX can drift if one surface gains fields the other cannot explain] -> Define one underlying object model and treat the easy surface as a constrained authoring view over that model.
- [Keeping both launch surfaces increases documentation work] -> Treat the difference as part of the product contract rather than as accidental duplication.
- [Recipe/preset naming split remains visible internally] -> Keep recipe canonical in docs and help output, defer full storage rename if it remains valuable later.

## Migration Plan

1. Rename the active proposal and docs vocabulary from launch templates to launch profiles.
2. Add catalog schema support for shared launch-profile objects and source-lane provenance.
3. Add compatibility projection for `.houmao/agents/launch-profiles/`.
4. Add easy `profile` CRUD and profile-backed instance launch.
5. Add explicit `project agents launch-profiles ...` authoring and `agents launch --launch-profile ...` resolution.
6. Update runtime provenance, inspection output, docs, and recipe terminology references.

Rollback strategy:
- launch-profile support is additive, so disabling new CLI entrypoints leaves existing specialist-backed and recipe-backed launch intact
- preset compatibility aliases and existing preset projection reduce rollback pressure on current users

## Open Questions

- Should easy `profile create` allow only a curated subset of fields in v1, or should it expose the full launch-profile field set with easy defaults layered on top?
- Should explicit `project agents launch-profiles add` require more fields up front than easy profile creation so the non-easy contract stays intentionally explicit?
- Should runtime inspection report the profile lane as `easy-profile` versus `launch-profile`, or present only the profile name plus source kind?
- Should low-level launch-profile authoring accept inline prompt-overlay text only in v1, or also a file-reference form for larger overlays?
