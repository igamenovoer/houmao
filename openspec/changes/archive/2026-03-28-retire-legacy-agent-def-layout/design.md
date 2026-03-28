## Context

Houmao has already standardized on a canonical agent-definition model built from:

- `skills/<skill>/SKILL.md`
- `roles/<role>/system-prompt.md`
- `roles/<role>/presets/<tool>/<setup>.yaml`
- `tools/<tool>/adapter.yaml`
- `tools/<tool>/setups/<setup>/`
- `tools/<tool>/auth/<auth>/`

That model is implemented in the parsed agent catalog and in preset-backed launch helpers such as `resolve_demo_preset_launch(...)`. However, the repository still carries two overlapping kinds of migration residue:

1. The current `scripts/demo/` tree and its companion `src/houmao/demo/`, docs, tests, and OpenSpec capabilities still treat old demo packs as maintained, runnable product surface.
2. Shared live fixtures, explore helpers, and docs still contain old path families such as `brains/api-creds/`, `brains/brain-recipes/`, or `blueprints/` even where the canonical preset/setup/auth model already exists.

The result is an inconsistent repository contract:

```text
supported live system:        refactorable Houmao subsystems
current repo obligations:     live systems + old demo packs + demo specs
practical outcome:            demos and their old layout assumptions block refactors
```

The requested change is to de-authorize the current demo surface first: archive the current demo packs as historical reference, remove their current spec/test/doc obligations, and keep only shared live fixtures and live non-demo workflows on the active canonical contract.

## Goals / Non-Goals

**Goals:**

- Move the current `scripts/demo/*` trees under `scripts/demo/legacy/` as archive-only historical material.
- Remove the current demo-pack OpenSpec capabilities and companion demo-support specs so they stop constraining live system refactors.
- Remove or demote tests, docs, and helper surfaces that currently treat archived demos as supported workflows.
- Keep remaining live shared fixtures, explore workflows, and docs on the canonical agent-definition layout.

**Non-Goals:**

- Redesigning replacement demos in the same change.
- Preserving current demo packs as runnable or tested workflows after they move under `scripts/demo/legacy/`.
- Renaming every compatibility-shaped field such as `recipe_path`, `brain_recipe_path`, or `blueprint_path` in one pass when those fields survive only in archived code or compatibility-only shared surfaces.
- Reworking unrelated live subsystem behavior beyond what is needed to remove archived-demo obligations and keep live shared fixtures/docs canonical.

## Decisions

### Decision: Current `scripts/demo/*` trees become archive-only historical material

The current demo-pack directories will move under `scripts/demo/legacy/` and will no longer be treated as supported operator surface.

Why:

- The repo is about to redesign demos, so preserving the current packs as runnable/spec'd workflows creates churn with little product value.
- Archiving them preserves historical implementation/reference material without forcing current subsystems to keep satisfying old demo contracts.
- This is the cleanest way to stop old demos from blocking system refactors.

Alternatives considered:

- Keep old demos live and just canonicalize their agent-definition trees. Rejected because it still leaves a large maintained spec/test/doc surface coupled to obsolete workflows.
- Delete old demos entirely. Rejected because keeping them under `scripts/demo/legacy/` is useful redesign reference.

### Decision: Archived demos are exempt from current guarantees

Code and content under `scripts/demo/legacy/` will not be covered by current OpenSpec product requirements, CI expectations, operator docs, or path-stability guarantees. It is historical reference only until redesigned replacements exist.

Why:

- This avoids turning archival material into de facto maintained surface by accident.
- It gives maintainers freedom to refactor live systems without dragging old demos along.
- It makes the redesign boundary explicit.

Alternatives considered:

- Keep archive demos runnable but unsupported. Rejected because “runnable but unsupported” still tends to pull in path, test, and compatibility obligations.

### Decision: Live contracts must stop depending on demo-pack capabilities

The change will remove direct demo-pack capability specs from `openspec/specs/` and revise cross-cutting capabilities so the active system contract no longer requires current demo packs to exist or remain runnable.

Why:

- Specs are currently one of the main reasons demos block refactors.
- Cross-cutting contracts such as CAO demo obligations and demo launch recovery keep demo-era requirements alive even when the underlying product surface is moving on.
- Removing demo authority at the spec layer is necessary before refactors can proceed cleanly.

Alternatives considered:

- Move demo directories first and clean up specs later. Rejected because stale specs would still block or confuse later refactors.

### Decision: Supported tracked agent-definition trees stay canonical; archived demos do not define the live contract

The canonical `skills/`, `roles/`, `tools/`, `setups/`, and `auth/` layout continues to define the live repository contract for supported fixtures, tests, docs, and non-demo workflows. Archived demo trees do not relax or redefine that contract.

Why:

- The live system still needs one authoritative agent-definition model.
- Shared fixtures and explore workflows should not keep old layout baggage just because archived demos preserve historical examples.
- This keeps the current canonical model intact while narrowing the supported surface.

Alternatives considered:

- Let archived demos continue to influence the live canonical contract. Rejected because that recreates the blocking condition this change is meant to remove.

### Decision: Fixture credential snapshots converge on the canonical `tools/` archive

The live fixture tree will retire `tests/fixtures/agents/brains/api-creds.tar.gz.gpg` and standardize snapshot guidance on the existing canonical archive `tests/fixtures/agents/tools.tar.gz.enc`.

Why:

- The canonical fixture README already documents `tools.tar.gz.enc` as the encrypted snapshot of `tests/fixtures/agents/tools/`, including `tools/<tool>/auth/**`.
- Leaving a tracked encrypted archive under `brains/` would keep a legacy-only subtree alive solely for provisioning.
- This cleanup remains valuable even after the current demos move to archive-only status.

Alternatives considered:

- Keep the legacy archive as a documented exception. Rejected because it weakens the live canonical fixture contract.

### Decision: Work in authority order: specs/docs/tests first, archive moves second

Implementation will proceed in this order:

1. Remove current demo authority from specs, docs, and gating tests.
2. Move the current demo trees under `scripts/demo/legacy/` and add explicit archive framing.
3. Remove or demote supporting code/test/doc surfaces that still point at archived demo paths as supported current workflows.
4. Keep shared live fixtures/docs/explore workflows on the canonical layout and retire leftover legacy fixture/archive references.

Why:

- De-authorizing specs/tests/docs first stops the old demos from blocking unrelated live work.
- Archive moves are cleaner once the repo no longer promises those surfaces are maintained.
- Shared live fixture cleanup should happen after the demo surface boundary is explicit.

Alternatives considered:

- Move directories first. Rejected because it leaves stale current-surface obligations behind.

### Decision: Shared live compatibility cleanup stays narrower than full demo redesign

This change will not redesign replacement demos or comprehensively remove every compatibility symbol. It only removes the old demo surface from the active contract and keeps remaining live shared surfaces off legacy layout dependencies.

Why:

- Full redesign is separate work.
- The immediate goal is to unblock refactors, not to finish every cleanup opportunity in one pass.
- Some compatibility surfaces may remain in the live system temporarily even after demos are archived.

Alternatives considered:

- Bundle demo redesign into this change. Rejected because it delays the needed de-authorization step.

## Risks / Trade-offs

- [Spec removal scope is broad and easy to under-enumerate] → Group direct demo specs and their companion support specs explicitly in the task list instead of treating spec cleanup as implicit fallout from path moves.
- [Archived demo paths may survive in docs/tests as if still supported] → Remove or demote those surfaces before or together with the archive move.
- [Live shared fixture cleanup could get lost inside demo retirement] → Keep explicit tasks for `tests/fixtures/agents/`, encrypted fixture snapshots, and live explore/docs surfaces that remain supported.
- [Archived demos may still be mistaken for supported workflows] → Add explicit archive framing under `scripts/demo/legacy/` and keep supported docs free of current demo-pack recommendations.

## Migration Plan

1. Remove direct demo-pack capability specs and revise cross-cutting capability specs so the maintained contract no longer requires current demos.
2. Move current `scripts/demo/*` directories under `scripts/demo/legacy/` with explicit archive-only framing.
3. Remove or demote docs, tests, and helper/module surfaces that still point at archived demos as current supported workflows.
4. Keep supported live fixtures, explore workflows, and agent-definition docs on the canonical layout, including retiring the legacy fixture credential snapshot and stale `brains/` / `blueprints/` references.
5. Verify that supported docs/tests/specs no longer treat archived demos as maintained surface and that remaining live canonical-layout work still has clear tasks.

Rollback strategy:

- Because this is repository-owned archive and contract cleanup, rollback is a normal git revert of the change if a supposedly archived demo still turns out to be needed as maintained surface.
- No persistent data migration or external system rollback is required.

## Open Questions

- Which parts of `src/houmao/demo/` should be archived as historical implementation versus deleted outright once the `scripts/demo/legacy/` move happens?
- Should any archived demo have a thin top-level pointer README left behind under `scripts/demo/` during the redesign window, or should `scripts/demo/` contain only redesigned surfaces going forward?
- After demo retirement lands, which live subsystem should get the first redesigned replacement workflow?
