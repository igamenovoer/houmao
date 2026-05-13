## Context

The packaged v5 loop skill already uses subskills for authoring and execution, but the top-level `SKILL.md` still contains detailed reusable guidance: scaffold profiles, generated contract defaults, bookkeeping defaults, TOML conventions, runtime mail semantics, and maintained Houmao platform boundaries. This makes activation expensive and encourages every invocation to load guidance that is only relevant to some operations.

The skill package also has two distinct documentation audiences:

- runtime guidance that an invoking agent must read while using the skill;
- maintainer design notes under `dev/design/` that help future authors revise or extend the skill.

The proposed split keeps runtime guidance inside the normal skill package, outside `dev/design/`, and makes the top-level entrypoint a short router.

## Goals / Non-Goals

**Goals:**

- Keep `SKILL.md` focused on activation, root invariants, operation list, routing, and global constraints.
- Move detailed reusable runtime guidance into reference pages that routed subskills can read on demand.
- Make each authoring and execution subskill explicit about which reference pages it must read first.
- Preserve existing behavior, operation names, scaffold profiles, generated defaults, runtime mail model, and platform-boundary rules.
- Keep `dev/design/` as maintainer-facing design intent, not runtime instruction.

**Non-Goals:**

- Change generated execplan directory structure or scaffold templates.
- Change the semantics of `init`, `create-intention`, `clarify intent`, execplan generation stages, validation, or execution commands.
- Add new external dependencies.
- Rename the packaged skill or remove existing operation routes.

## Decisions

### Use runtime reference pages under `subskills/reference/`

Detailed shared guidance should move to files such as:

```text
subskills/reference/
  scaffold-surface.md
  generated-contract-defaults.md
  generation-pipeline.md
  runtime-mail-model.md
  platform-boundaries.md
```

These pages are part of skill execution and can be read by routed operation pages. They are not maintainer-only design documents.

Alternative considered: place the pages under `dev/design/`. Rejected because invoking agents need this guidance during normal operation, while `dev/design/` is explicitly for maintainers revising the skill.

### Keep `SKILL.md` as the stable router

The entrypoint should retain:

- activation rules;
- `<loop-dir>` requirement;
- `intention/` source and `execplan/` generated-output invariant;
- concise operation list;
- routing table;
- global constraints.

The entrypoint should remove detailed default policy sections and replace them with pointers to routed subskills and reference pages. This keeps invocation cheap while preserving discoverability.

Alternative considered: shorten only wording inside `SKILL.md`. Rejected because the problem is structural: detailed guidance belongs behind progressive disclosure.

### Let subskills declare their reference dependencies

Each routed operation page should include a short `Read first` section listing the runtime reference pages it depends on. Example:

```markdown
## Read First

- `../reference/scaffold-surface.md`
- `../reference/generated-contract-defaults.md`
- `../reference/generation-pipeline.md`
```

This makes the dependency graph visible and prevents operation pages from duplicating shared policy.

Alternative considered: require every subskill to read all reference pages. Rejected because it recreates the entrypoint bloat at the route level.

### Split references by concern, not by current heading names

The split should follow operational concerns:

- scaffold surface: profiles, template authority, scaffold script usage;
- generated contract defaults: artifact layout, README convention, state/bookkeeping, TOML descriptions;
- generation pipeline: process-first ordering and downstream regeneration dependencies;
- runtime mail model: notifier-driven turns, on-event/on-tick behavior, no in-chat waiting;
- platform boundaries: maintained Houmao skills for workspace, mailbox, gateway, messaging, lifecycle, memory, and inspection.

This shape lets `init` read only scaffold guidance while `execplan-fast-forward` and stage generators read deeper defaults.

## Risks / Trade-offs

- Reference dependency drift → Keep each operation page's `Read first` list explicit and validate that links resolve.
- Guidance duplication between `SKILL.md`, references, and operation pages → Treat reference pages as the shared source for detailed defaults; keep the entrypoint and operation pages concise.
- Agents may skip required references → Use imperative `Read first` sections near the top of each operation page and keep reference file names purpose-based.
- Over-fragmentation → Limit the initial split to a small number of durable concern pages rather than one page per paragraph.

## Migration Plan

1. Add `subskills/reference/` pages with migrated detailed runtime guidance.
2. Trim `SKILL.md` to activation, invariants, operations, routing, and global constraints.
3. Add `Read first` sections to routed authoring and execution subskills.
4. Update maintainer design docs to describe the runtime-reference split.
5. Validate that all referenced pages exist and `SKILL.md` no longer duplicates detailed defaults.

Rollback is straightforward: reference content can be re-expanded into `SKILL.md` if the split proves too fragmented, without changing generated loop behavior.

## Open Questions

- None.
