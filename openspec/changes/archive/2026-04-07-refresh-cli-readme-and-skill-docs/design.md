## Context

Houmao docs were last refreshed in the `2026-04-07` post-refactor pass. That same day a substantial wave of feature commits landed (`f7515117`, `e7540c18`, `3b9a83c4`, `f95f7587`, `c9426ff7`, `43a1d8ce`, `e37b245d`, `5f0d6592`, `6bf5c53f`, `22d702a3`, `54f1f40f`, `59d4dd33`, `5f8c3ed7`, plus the managed-prompt-header change), and the doc surfaces that should describe them did not all move with the code.

The current observable drift falls into three buckets:

```
DRIFT BUCKET                    PRIMARY SYMPTOMS                          BLAST RADIUS
───────────────────────────────────────────────────────────────────────────────────────
CLI surface drift               --version, --workdir, --model unknown     ~7 ref pages
                                to docs; --yolo still mentioned;          + README
                                email-comms unification not in
                                agents-mail page

System-skills catalog drift     houmao-agent-email-comms not in           README +
                                README skill table; default install      docs/reference/cli/
                                set in README disagrees with current      system-skills.md
                                system_skills.py defaults                 + getting-started

Conceptual gaps                 No reference page for managed prompt      2 new pages
                                header at all; no narrative tour of
                                the eight system skills bridging
                                README catalog and CLI reference
```

The previous doc-update change (`2026-04-02-update-docs-for-current-codebase`, archived) had a similar shape and is the right template to follow: track-by-track tasks, derive content from source rather than generative summarization, update existing index pages alongside the new ones.

## Goals / Non-Goals

**Goals:**
- Bring `docs/reference/cli/` into agreement with the current `srv_ctrl/commands/` Click decorators and live `--help` output for every page that was last touched on or before `2026-04-07 18:10`.
- Add the two missing conceptual pages: managed-launch prompt header reference, and system-skills overview narrative.
- Polish the `README.md` skill catalog and CLI entrypoint table for the post-`f7515117` state.
- Sweep the docs tree for stale strings (`--yolo`, the legacy `specialist` skill name without the `houmao-manage-` prefix, `agentsys` stragglers).
- Update `docs/index.md` and `docs/reference/index.md` so the two new pages are linked, and verify no cross-reference 404s introduced.
- Do all the above without touching code.

**Non-Goals:**
- Refreshing the older subsystem internals/contracts pages under `reference/system-files/`, `reference/mailbox/contracts/`, `reference/mailbox/operations/`, `reference/gateway/operations/`, `reference/registry/`, `reference/lifecycle/`, and `reference/run-phase/session-lifecycle.md`. These are stale (mostly `2026-04-04`) but their drift is independent of this pass and will get a dedicated change.
- Rewriting the `developer/` guides (TUI parsing, terminal-record, houmao-server internals).
- Restructuring the `docs/` directory layout or `mkdocs.yml` navigation beyond linking the two new pages.
- Touching CLI help text, source docstrings, or any code path. This change is docs-only.
- Adding a new MkDocs theme, plugin, or build step.

## Decisions

### Decision 1: Scope is CLI + concepts + README, not subsystems

**Choice:** This change covers Tracks A (CLI resync), C (new conceptual pages), D (README polish), and E (cleanup sweep) from the explore-mode plan. Track B (subsystem rot under `reference/system-files/`, `reference/mailbox/`, `reference/gateway/operations/`, `reference/registry/`, `reference/lifecycle/`) is explicitly deferred.

**Rationale:** The drift buckets above are largely orthogonal. The CLI/skill/concept drift was caused directly by `2026-04-05`–`2026-04-07` feature commits and is easy to verify against current source. The subsystem-internals drift is older, larger, and crosses multiple ownership boundaries (mailbox protocol, gateway facade, registry contracts) — bundling them would balloon the change and slow the high-value half. Splitting keeps each pass small enough to actually land cleanly.

**Alternatives considered:**
- *Single comprehensive doc pass.* Rejected: prior precedent (`2026-04-02-update-docs-for-current-codebase`) showed that even a 5-track doc change has long lead time; doubling that scope would block the most critical fixes (broken `--yolo` examples, missing `--version`) on unrelated subsystem prose.
- *CLI-only mini change.* Rejected: it would leave the README skill table and the missing conceptual pages stranded, and the next change would still have to revisit the same files.

### Decision 2: Managed prompt header gets its own reference page, not a section in an existing page

**Choice:** Add `docs/reference/run-phase/managed-prompt-header.md` as a standalone reference page rather than appending the content to `docs/reference/run-phase/role-injection.md` or to `docs/getting-started/launch-profiles.md`.

**Rationale:**
- Role injection and the managed header are distinct concepts: role injection is the per-backend mechanism that delivers a prompt to the underlying CLI; the managed header is a Houmao-owned text block prepended to the prompt before backend role injection runs. Folding them into one page conflates "what gets injected" with "how it gets injected."
- The launch-profiles guide already has to explain *how* `--managed-header`/`--no-managed-header` and the stored policy field interact; it should not also have to define what the header text actually contains and why it exists.
- A dedicated page gives the cross-reference links from `agents launch`, `project easy instance launch`, the launch-profiles guide, and the role-injection page somewhere stable to point at.

**Alternatives considered:**
- *New section in `role-injection.md`.* Rejected for the conflation reason above.
- *New section in `launch-profiles.md`.* Rejected: the launch-profiles guide is already long, and most readers reach the prompt header from a launch command rather than from the launch-profile concept.

### Decision 3: System-skills overview lives in `getting-started/`, not `reference/`

**Choice:** Add `docs/getting-started/system-skills-overview.md` (narrative tour) and keep `docs/reference/cli/system-skills.md` (CLI reference) as two separate pages.

**Rationale:**
- The reference page is already deep on flags, defaults, and effective-home resolution. Adding "what each skill is and when each fires" prose to it would dilute the reference.
- The README skill catalog table is the "60-second view"; the CLI reference is the "every flag" view; the missing rung is the "5-minute walkthrough" view that bridges them. That walkthrough belongs in `getting-started/`, where the launch-profiles and easy-specialists guides already sit.
- Putting the overview in `getting-started/` also gives the `docs/index.md` a clean third pillar to link from the getting-started section without cluttering the reference index.

**Alternatives considered:**
- *Single combined `system-skills.md` under reference.* Rejected: forces every reader of the reference to scroll past narrative content they did not need, and forces every reader of the narrative to scroll past flag tables.
- *Section in README.* Rejected: README is already the catalog table; the narrative tour is a doc-site responsibility.

### Decision 4: README polish is incremental edits, not a rewrite

**Choice:** Modify the existing README skill catalog table, "What You Get After Joining" section, and CLI Entry Points table in place rather than restructuring the README.

**Rationale:** The README structure (overview → installation → quickstart → easy specialists → recipes → demos → subsystems → system skills → docs → development) was just stabilized in `2026-04-02-revise-readme-structure` and the `f7515117` commit landed surgical edits on top of it. Restructuring again would invalidate freshly-stabilized navigation and create a churn signal in `git blame` for no benefit.

### Decision 5: Verification by reading source, not by running services

**Choice:** Derive every CLI-page change from the `srv_ctrl/commands/**/*.py` Click decorators and from `houmao-mgr ... --help` output, and derive the system-skills overview from `src/houmao/agents/assets/system_skills/<skill>/SKILL.md` files. Do not require a running houmao-server, gateway, or live agent to verify content.

**Rationale:** This matches the prior pass's verification model. It keeps the change reproducible in CI, avoids depending on environment-specific tool installations, and means the docs stay aligned with declared CLI shape rather than incidental runtime behavior.

## Risks / Trade-offs

**[Risk]** Track B (subsystem internals) deferral leaves obvious staleness in the docs tree visible to readers. → **Mitigation:** call out the deferral explicitly in `proposal.md` "Out of scope" so the gap is documented; open a follow-up change in the same week so the gap window is short.

**[Risk]** CLI reference content can drift again the moment a new feature lands; we will be back here in a month. → **Mitigation:** This is structural and not solvable in one pass. The mitigation is to keep these resync passes small enough to turn around quickly rather than letting them accumulate. The two new conceptual pages also reduce the surface that drifts on every feature commit.

**[Risk]** The managed-prompt-header reference page will overlap with the launch-profiles guide if the boundary is unclear. → **Mitigation:** the new page documents *what the header is and how it composes with role injection*; the launch-profiles guide documents *how the header policy is stored, overridden, and inherited via profiles*. Each page links the other.

**[Risk]** A "stale skill name" sweep could blindly rewrite legitimate uses of the word "specialist" in prose. → **Mitigation:** the sweep targets only the *skill identifier* `specialist` (with the `houmao-` prefix or in skill-related contexts), not the prose noun "specialist." Each replacement is reviewed in context, per the precedent in the `agentsys` sweep requirement.

**[Risk]** The README skill catalog table may need to grow if `houmao-process-emails-via-gateway` is also expected to be listed. → **Mitigation:** the proposal explicitly adds the `houmao-agent-email-comms` row; the design will cover whether `houmao-process-emails-via-gateway` should appear too based on its current install posture in `system_skills.py`.

## Migration Plan

Not applicable — docs-only change with no schema, no API, no on-disk format change. Roll-forward strategy: merge in one PR, update the docs site on the next deploy. Rollback strategy: revert the PR; no data migration needed.

## Open Questions

1. **Should the README CLI Entry Points table list `--version` as a row, or is a footnote/inline mention enough?** Default: footnote next to the `houmao-mgr` row, since `--version` is a flag rather than an entrypoint, but the proposal allows either treatment.
2. **Should the system-skills overview list `houmao-process-emails-via-gateway` alongside `houmao-agent-email-comms`?** Default: yes, because both ship in `src/houmao/agents/assets/system_skills/` today. Confirm against current `system_skills.py` install defaults during implementation; if the notifier-only skill is no longer in the default set, mention it as available-but-not-default rather than dropping it.
3. **Does the `houmao-passive-server` "In development — not ready for use" status line in the README still match reality after the Apr 6 reference rewrite?** Default: re-read the rewritten reference page during implementation and downgrade the warning if the page now describes a usable surface.
