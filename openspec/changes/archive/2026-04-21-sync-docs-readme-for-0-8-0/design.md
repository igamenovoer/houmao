## Context

The 0.8.0 release bumped several user-visible capabilities whose *deep* reference pages under `docs/reference/` have already been updated (registry lifecycle record, gateway coalescing, mail-notifier context recovery, reuse-home launch flag, pairwise-v3 skill). Feature commits that touched these deep pages generally did **not** update the two places new users actually land:

- `README.md` — currently asserts three loop skills and lists only two pairwise variants in both its §4 loop table and its bottom System Skills table. Its auto-install paragraph still reads "both pairwise variants" for the `core` / `user-control` expansion.
- `docs/index.md` — has a single-line mention of pairwise-v3 in the getting-started blurb, but its Subsystems block links to the top-level index of each subsystem and does not surface the 0.8.0 capabilities (coalescing, context-recovery policy, lifecycle record states, reuse-home / stop-relaunch anchors).

This change is a surgical README + landing-page refresh. All target reference pages already exist and already carry the content being linked to; no new pages, no new sections, no CLI changes, no schema changes.

## Goals / Non-Goals

**Goals:**
- Make `houmao-agent-loop-pairwise-v3` discoverable from the README loop table, the README System Skills catalog table, and the README auto-install paragraph, with wording that matches `src/houmao/agents/assets/system_skills/catalog.toml`.
- Make the four 0.8.0 subsystem capabilities (coalescing, mail-notifier context-recovery policy, lifecycle registry record, reuse-home / stop-relaunch) discoverable from `docs/index.md` via its Subsystems block.
- Preserve every existing README narrative element that is still correct — the "See it in action" video, the writer-team example, the step-by-step quick-start — with no rewrites beyond the surgical additions above.

**Non-Goals:**
- No new getting-started pages or reference pages. Stop/relaunch and reuse-home are adequately covered by existing reference pages.
- No "What's new in 0.8" section in the README. CHANGELOG.md already fills that role; the entry points need evergreen updates, not a release-note block.
- No changes to already-synced pages: `loop-authoring.md`, `system-skills-overview.md`, `quickstart.md`, `easy-specialists.md`, `launch-profiles.md`, `docs/reference/registry/**`, `docs/reference/gateway/**`, `docs/reference/run-phase/session-lifecycle.md`.
- No edits to `mkdocs.yml` (site uses auto-nav; no files are added, renamed, or deleted).
- No edits to the story-writer example, its Mermaid diagram, or the 0.7-era narrative around the video.

## Decisions

### Decision 1 — Extend existing tables rather than rewrite them

The README §4 Agent Loop section and the System Skills table are both dense but well-structured. We insert a single row per table and adjust one narrative count ("three" → "four") rather than refactoring the section. This keeps diff size tiny and preserves all surrounding cross-references, which matter for `docs-readme-system-skills` scenarios that assert specific linked pages.

*Alternatives considered:* replace the README loop-table with a prose-first recommendation tree. Rejected — the compact table maps directly to skill-selection scenarios in `docs-loop-authoring-guide` and is what readers compare to the `loop-authoring.md` guide. Adding one row is strictly additive.

### Decision 2 — Source pairwise-v3 descriptions from already-synced docs

For both new table rows (README §4 loop table, README System Skills table), copy the description text from:
- `docs/getting-started/system-skills-overview.md` line 73 (the canonical one-liner for v3), and
- `docs/getting-started/loop-authoring.md` (for the lifecycle verb list).

This avoids introducing a new canonical description for v3 that can drift from the other doc surfaces.

### Decision 3 — Update auto-install paragraph to the three-variant wording

`catalog.toml` shows v3 is in both `core` (managed launch + join auto-install) and `all` (CLI default). The existing requirement in `docs-readme-system-skills` ("includes both pairwise variants when `user-control` includes both") is already extended in spirit; we update the delta to require **all three** pairwise variants in the expansion wording.

### Decision 4 — `docs/index.md` Subsystems block gets inline anchors, not a new page

The block already lists each subsystem with a one-line description and a top-level index link. For 0.8.0 discoverability we extend each affected line with an additional anchor link into the *section* of the existing reference page that covers the 0.8.0 capability:

| Subsystem line | Additional anchor added |
|---|---|
| Gateway | link to `contracts/protocol-and-state.md#coalescing` (or the coalescing section heading as it exists) |
| Mailbox → mail-notifier | link to `operations/mail-notifier.md#context-recovery-policy` |
| Agent Registry | link to `contracts/record-and-layout.md#lifecycle-state` |
| Run Phase / Session Lifecycle | add `session-lifecycle.md#reuse-home` anchor to Run Phase list |

Implementation note: before writing the edits, verify that each target page actually has the named heading / anchor. If an anchor is missing, link the page and mention the capability by name in the index description rather than inventing a fragment.

*Alternatives considered:* add a new "What 0.8.0 Changed" subsection to `docs/index.md`. Rejected — release-note framing is CHANGELOG's job. The Subsystems block is evergreen and should stay capability-oriented.

### Decision 5 — Leave every other doc surface untouched

`docs/getting-started/system-skills-overview.md:73` already has the v3 row, and `docs/getting-started/loop-authoring.md` already has 10 occurrences of v3. `docs/index.md:20` already references v3 in the loop-authoring getting-started blurb. The change deliberately does not revise these — they are already sync'd, and touching them would expand the change surface without improving discoverability further.

## Risks / Trade-offs

- **[Risk] Anchor drift in target reference pages** → Mitigation: during implementation, verify each anchor target exists (grep the heading text in the target page). If a heading has moved since the last doc commit, either update the anchor or drop the fragment and rely on the page + description to carry the pointer.
- **[Risk] README "three loop skills" phrase appears in multiple spots** → Mitigation: grep `three.*loop` and `all three` in README before committing and patch every occurrence, since `docs-readme-system-skills` scenario `§4 introduces all three loop skills` is being intentionally widened to four.
- **[Risk] docs-readme-system-skills spec §4-requirement wording says "all three loop skill options"** → Mitigation: update that delta requirement in this change to "all four loop skill options" so the scenario does not drift back after merge.
- **[Trade-off] No standalone v3 getting-started page** → Accepted. The SKILL.md plus `loop-authoring.md` (10 v3 hits) is already the authoritative authoring surface. Adding a getting-started page risks drift without clear reader benefit. Revisit only if 0.9.0 introduces an operating-model change requiring top-level framing.
- **[Trade-off] Video and writer-team narrative stays 0.7-era** → Accepted. The video still depicts a valid pairwise run; the example still works end-to-end. Replacing or re-narrating is out of scope.

## Migration Plan

Not applicable — this change edits two Markdown files and adds no behavior, schema, or CLI surface. Rollback is `git revert`.

## Open Questions

- Do target reference pages have stable heading slugs for the anchors we want to link to, or should the index simply link the page and describe the capability inline? Resolve during implementation with a quick grep of each target page.
