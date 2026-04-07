## Context

The `add-agent-launch-profiles` change has shipped the catalog support, two CLI authoring lanes, the explicit-launch-profile-backed `agents launch --launch-profile` flow, and the canonical `recipe` naming with `presets` retained as a CLI compatibility alias. Documentation has not caught up. Concrete state of the repo at the start of this change:

- README.md, `docs/getting-started/agent-definitions.md`, `docs/getting-started/quickstart.md`, and `docs/reference/cli/system-skills.md` already carry partial in-tree edits that flip the noun from `preset` to `recipe` in a few places. Those edits are correct as far as they go but they are a small first nibble, not the full doc job.
- `docs/reference/cli/houmao-mgr.md` does not mention `recipes`, `launch-profiles`, or `easy profile` anywhere. The `project easy` and `project agents` tables list only the old verbs, and `agents launch` is described without `--launch-profile`.
- `docs/getting-started/easy-specialists.md` describes a two-step easy lane (specialist → instance) and never mentions easy profiles.
- `docs/getting-started/overview.md` opens by stating that the model is "preset + setup + auth", which is now actively wrong with respect to the new canonical naming.
- `docs/reference/build-phase/launch-overrides.md` shows a precedence pipeline of "adapter defaults → preset overrides → direct overrides" with no launch-profile layer. The existing spec for that page even bans the word `recipe` in favor of `preset`, so the spec itself needs editing.
- `docs/reference/run-phase/launch-plan.md` does not mention launch-profile provenance fields on the manifest.
- A handful of light-touch reference and getting-started pages use `preset` in user-facing prose where the canonical noun is now `recipe`.

The design challenge for this change is choosing where the conceptual model lives, how to reuse it across the existing docs without copy-pasting the precedence chain, and how to keep the spec deltas tight enough that this remains a docs-only change with no code or CLI surface drift.

## Goals / Non-Goals

**Goals:**

- Make the new launch-profile surface fully discoverable from the public docs site without restating the conceptual model in every reference page.
- Land the canonical `recipe` user-facing noun in operator-facing documentation while keeping `preset` only as the on-disk projection path name and the CLI compatibility alias.
- Preserve all existing scenarios in the docs spec capabilities; this change MODIFIES a small number of requirements rather than dropping them.
- Use mermaid diagrams for every new or rewritten diagram (per the user's explicit instruction in this change) so that the launch-profiles guide and the rewritten easy-specialists diagram do not introduce more ASCII art.
- Keep the docs change scoped to user-facing operator guidance. Developer-internal docs that use "preset" in the parser-detector sense (under `docs/developer/tui-parsing/` and friends) are explicitly out of scope.

**Non-Goals:**

- Renaming the on-disk projection directory `.houmao/agents/presets/`. The active `add-agent-launch-profiles` change explicitly keeps that path stable.
- Renaming the `project agents presets ...` compatibility alias. It remains documented as a valid alias, just not as the canonical surface.
- Touching code, tests, the active CLI surface, or non-docs spec capabilities. Spec deltas in this change live entirely under `docs-*` capabilities.
- Re-numbering or restructuring the existing reference site layout. The change adds one new page under `docs/getting-started/` and edits existing pages in place.
- Adding migration guidance beyond noting that `presets` remains a compatibility alias. The active change has already covered the operator migration story.

## Decisions

### Decision: Place the new conceptual page under `docs/getting-started/`

Rationale:

- The launch-profile concept is operator-facing and is the natural next step after the easy-specialists page.
- The `getting-started` section is where every other "what is this object family and when do I use it" page lives (overview, agent-definitions, easy-specialists, quickstart).
- Placing it under `reference/build-phase/` would tie the page to one technical surface and lose the easy-versus-explicit framing.

Alternatives considered:

- `docs/reference/build-phase/launch-profiles.md` — rejected because the page is conceptual, not build-phase plumbing.
- `docs/reference/cli/launch-profiles.md` — rejected because the page is not a CLI reference for one command surface; it has to span both `project easy profile` and `project agents launch-profiles`.
- A subsection inside `easy-specialists.md` only — rejected because the explicit lane is recipe-backed and does not belong inside an "easy" page.

### Decision: Keep the easy-specialists filename and add an "Easy Profiles" section in place

Rationale:

- README.md and `docs/index.md` already cross-link to `docs/getting-started/easy-specialists.md`. A rename would create a ripple of incoming-link edits with no real value.
- Inside the page, the easy lane is now a three-step model (specialist → optional easy profile → instance). The simplest stable framing is to keep "easy specialists" as the page name and present easy profiles as a sibling step within the same page.
- The new launch-profiles guide is the canonical home for the shared conceptual model. The easy-specialists page links there for "what is a launch profile in general" instead of restating the precedence chain inline.

Alternatives considered:

- Rename to `easy-lane.md` — rejected because of the link ripple and the ambiguous filename.
- Split easy specialists and easy profiles into two sibling pages — rejected because the easy-instance section belongs to both and would be duplicated.

### Decision: Modify the existing docs spec capabilities rather than introduce one large new "docs-launch-profiles" capability

Rationale:

- Each existing `docs-*` capability already owns one specific kind of doc (getting-started, easy-specialist guide, CLI reference, build-phase reference, run-phase reference, site structure). Adding launch-profile awareness fits naturally inside those existing requirements.
- This keeps the spec graph stable: the new requirements live next to the existing requirements they modify.
- The only new capability is `docs-launch-profiles-guide`, which exists for the dedicated new page that has no existing home in the spec graph.

Alternatives considered:

- One monolithic `docs-launch-profiles` capability that owns all related requirements across all pages — rejected because it would create cross-cutting ownership over content that other docs capabilities already own.
- Inline edits without spec deltas — rejected because the existing build-phase reference spec actively bans the word `recipe`, so the spec must be edited regardless.

### Decision: Use mermaid for every new and rewritten diagram

Rationale:

- The user explicitly asked for mermaid in this change.
- The repo's own markdown style guide already prefers mermaid fenced code blocks for diagrams that should render inline in common Markdown renderers.
- Several of the affected pages already use mermaid (quickstart, README sequence diagram, overview), so this is consistent with the established convention.

Affected diagrams:

- new launch-profiles guide: precedence pipeline mermaid diagram, source-versus-birth-time taxonomy mermaid diagram.
- rewritten easy-specialists guide: replace the existing ASCII three-box lifecycle picture with a mermaid flowchart that shows specialist → optional easy profile → instance → managed agent.
- refreshed launch-overrides reference: keep the existing mermaid precedence diagram, but extend it with the launch-profile layer between recipe overrides and direct overrides.

The CLI reference command-shape trees (`houmao-mgr.md`) remain ASCII pseudo-trees because they are command shapes, not flow diagrams, and the existing spec scenarios reference them as text blocks.

### Decision: Reconcile, do not redo, the existing in-tree partial edits

Rationale:

- The unstaged edits to README.md, `docs/getting-started/agent-definitions.md`, `docs/getting-started/quickstart.md`, and `docs/reference/cli/system-skills.md` are correct as far as they go. Redoing them from scratch risks losing the small-but-correct first pass.
- The new specs in this change reference the same vocabulary the partial edits already use (`recipe`, `launch profile`, `easy profile`).
- During implementation, the apply step inspects each of those files and either keeps the existing edits or adds the missing pieces, instead of deleting and re-writing.

### Decision: Vocabulary sweep is bounded by the spec deltas

Rationale:

- The light-touch reference pages listed in the proposal need a `preset → recipe` substitution but their existing requirements do not need to change. The proposal lists those files explicitly so the implementation is bounded.
- The sweep does NOT touch developer/TUI-parsing pages where "preset" means parser detector preset.
- The sweep keeps `preset` in any sentence that names the on-disk projection path `.houmao/agents/presets/` or the legacy compatibility alias.

## Risks / Trade-offs

- [Two user-facing nouns for the same underlying object family stay visible (`profile` vs `launch-profile`).] → The launch-profiles guide makes this distinction load-bearing rather than accidental, and the easy-specialists and CLI reference rewrites both link there for the canonical explanation.
- [The vocabulary sweep is a manual judgement call between user-facing prose and the legitimate `presets/` directory name.] → The spec deltas explicitly call out "keep `preset` only when naming the on-disk projection path or the compatibility alias" so the implementation has a clear rule.
- [The existing build-phase reference spec previously demanded `preset` instead of `recipe`. Modifying that requirement could surprise reviewers.] → The MODIFIED requirement spells out the new vocabulary rule and explains that the source noun is now `recipe`. The on-disk path remains `presets/`.
- [README and `docs/index.md` already link to easy-specialists; restructuring that page risks broken anchors.] → Decision above keeps the filename and adds the new section inside the same page, so all existing incoming links continue to resolve.
- [Several pages cross-link to the new launch-profiles guide. If the page is renamed during apply, those links break.] → The site-structure spec records the canonical path `docs/getting-started/launch-profiles.md` explicitly, so the implementation cannot move the page without updating the spec.

## Migration Plan

This is a docs-only change, so there is no runtime migration. The implementation order is:

1. Create the new `docs/getting-started/launch-profiles.md` first because every other doc edit links to it.
2. Heavy-rewrite `docs/reference/cli/houmao-mgr.md` next because the CLI reference is the most user-visible doc with the largest gap.
3. Heavy-rewrite `docs/getting-started/easy-specialists.md` next so that the easy lane has a complete current-state explanation.
4. Refresh the medium-touch pages (`overview.md`, `launch-overrides.md`, `launch-plan.md`, `cli.md`).
5. Sweep the light-touch reference pages.
6. Reconcile the existing partial edits on README.md, `agent-definitions.md`, `quickstart.md`, `system-skills.md`.
7. Update `docs/index.md` and `mkdocs.yml` to surface the new page.
8. Run `pixi run docs-serve` locally to confirm mkdocs builds without dangling references.

Rollback strategy: every edit lives in a single docs commit, so rollback is `git revert`.

## Open Questions

- Should the launch-profiles guide include a worked example pair (one easy profile, one explicit launch profile) inline, or keep examples short and link to the runnable demos under `scripts/demo/`? The current draft of the spec leaves this open; the implementation can decide based on whether a runnable demo for launch profiles already exists by the time of writing.
- Should the easy-specialists page add a short "Picking a lane" decision flowchart at the very top, or rely on the comparison table for that role? Both options satisfy the spec; the implementation can choose whichever reads more cleanly in mkdocs.
- Should `docs/reference/cli.md` get its own short launch-profile paragraph, or just a one-line pointer to `houmao-mgr.md`? The spec currently requires a short paragraph and a pointer; if the rewrite of `houmao-mgr.md` ends up being self-contained enough, the `cli.md` paragraph can shrink to a single sentence during apply.
