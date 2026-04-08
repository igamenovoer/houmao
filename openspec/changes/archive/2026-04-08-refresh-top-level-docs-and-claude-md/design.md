## Context

Post–April 2026, Houmao's high-traffic docs were refreshed alongside each refactor PR, but a few top-level framing and navigation surfaces escaped those sweeps:

- `README.md` still opens with a "Current Status" paragraph from when the CLI surface was actively churning.
- `CLAUDE.md` still describes the retired `AgentPreset` model and omits several new `src/houmao/` subsystems.
- `docs/index.md` landing navigation lags behind `docs/reference/index.md`.
- `docs/reference/agents/` remains as a dedicated runtime-managed-agent subtree that mostly duplicates `run-phase/`, `system-files/`, and `cli/`.
- `cao_rest` and `houmao_server_rest` are described without any "unmaintained" signal, even though repo policy is to keep them frozen.

The goal is a narrow consistency pass, not a full rewrite. User direction: remove stale framing, consolidate duplicated subtrees, mark deprecated backends clearly, and do not invent compatibility shims for retired doc locations.

## Goals / Non-Goals

**Goals:**

- `README.md` no longer leads with a misleading stability warning.
- `CLAUDE.md` accurately reflects current build/run phase vocabulary and current source layout, so future agent sessions do not start from stale assumptions.
- `docs/index.md` navigation matches `docs/reference/index.md` coverage of current CLI and run-phase reference pages.
- `docs/reference/agents/` is retired cleanly — no empty placeholders, no compatibility redirects.
- The two documents that used to live under `agents/` but remain useful (`project-aware-operations.md`, `codex-cao-approval-prompt-troubleshooting.md`) find new homes that match their topic rather than the retired subtree.
- Deprecated legacy backends (`cao_rest`, `houmao_server_rest`) are prominently labeled as unmaintained wherever they are still documented.

**Non-Goals:**

- No curated `mkdocs.yml` navigation block. Auto-discovery continues to back the MkDocs site.
- No rewrite of the `docs/developer/` guides (`tui-parsing/`, `houmao-server/`, `terminal-record/`). User deferred that work.
- No deletion of `cao_rest` or `houmao_server_rest` source code, tests, or reference pages — only a deprecation banner.
- No new top-level "runtime-managed agents" page to replace the retired subtree. Readers land on existing `run-phase/`, `system-files/`, and `cli/` homes instead.
- No changes to any `src/houmao/**` source file.

## Decisions

### Decision 1: Retire `docs/reference/agents/` instead of restructuring it in place

The subtree's contracts, operations, and internals pages overlap heavily with already-current pages under `run-phase/`, `system-files/`, and `cli/`. The post–April recipe/launch-profile/project-overlay vocabulary lives in those pages, not in the `agents/` subtree. A "refresh in place" pass would end up rewriting most of the subtree to be thin wrappers that duplicate other pages — classic compatibility cruft.

**Alternatives considered:**

- *Refresh the `agents/` pages in place against current code.* Rejected because it preserves content duplication and leaves readers wondering which home is canonical.
- *Merge the `agents/` content into a single consolidated `run-phase/managed-sessions.md` page.* Rejected because `run-phase/session-lifecycle.md` and `run-phase/backends.md` already serve that role.

**Consequence:** The `agents-reference-docs` spec is retired as a capability. Every existing requirement moves to REMOVED with a migration pointer.

### Decision 2: Move `project-aware-operations.md` into `system-files/`

The page is about overlay discovery, root resolution, and how commands resolve `.houmao/` — a filesystem-boundary concern. `system-files/` is the existing home for root resolution and ownership rules, so it is the natural receiving tree.

**Alternatives considered:**

- *`docs/reference/project-aware-operations.md` at the top of `reference/`.* Rejected because it would be a standalone page with no subtree home and would repeat work for the landing page navigation.
- *`docs/getting-started/project-aware-operations.md`.* Rejected because the content is reference material, not getting-started narrative.

**Consequence:** The `docs-project-aware-operations` spec path changes from `docs/reference/agents/operations/project-aware-operations.md` to `docs/reference/system-files/project-aware-operations.md`. The two inbound links (`system-skills-overview.md`, `easy-specialists.md`) and any other referrers must be updated.

### Decision 3: Move `codex-cao-approval-prompt-troubleshooting.md` to `docs/reference/` and add a deprecation banner

The page documents a legacy `cao_rest` behavior. Under the "keep legacy backend docs as deprecated" policy it should be retained, but it cannot stay under the retired `agents/` subtree. Placing it at the top of `docs/reference/` keeps it adjacent to `realm_controller.md`, where the other legacy backend content lives.

The banner language should match the one added to `realm_controller.md` so readers see a consistent "unmaintained — may be incorrect" signal for the whole legacy surface.

### Decision 4: Deprecation banner is a prose block, not a new admonition style

The docs use Material-for-MkDocs admonitions elsewhere, but introducing a new banner style (CSS class, shared include, etc.) would expand scope. A bold-prefixed callout block at the top of each legacy section is enough to carry the "unmaintained" signal and does not require any tooling or theme changes.

Proposed wording pattern:

> **Unmaintained — Deprecated Backend.** The `<name>` backend remains in the codebase as an escape hatch, but its documentation is no longer actively maintained. Content below may be incorrect or stale. Prefer `local_interactive` for new work.

### Decision 5: CLAUDE.md updates are narrow — source layout + build/run vocabulary only

The file has many sections that are still correct (pixi commands, convention rules, git hygiene, markdown style). This change touches only the sections that have concrete drift: the "Source Layout" subsection and the "Build phase" bullet that still mentions `AgentPreset`. The `config/` one-liner gets its CAO reference removed. Everything else is left alone.

**Consequence:** A new single-requirement capability spec (`docs-project-instructions-file`) is introduced to anchor the accuracy bar, but the scope of that spec is intentionally narrow so we don't accidentally turn CLAUDE.md into a heavyweight managed document.

### Decision 6: `docs/index.md` gets link additions, not a structural rewrite

The landing page's section headings (Getting Started, Reference → CLI/Build Phase/Run Phase/Subsystems/Other, Developer Guides) are still correct. The gaps are missing leaf links under existing sections. This change adds those leaf links and removes the single `reference/agents/index.md` pointer. No new sections. No reordering.

## Risks / Trade-offs

- **Risk:** Readers who bookmarked `docs/reference/agents/*` pages will hit 404s on the hosted MkDocs site. → **Mitigation:** Accepted per user direction ("do not leave stale stuff there just for compatibility"). The retired pages are not widely linked externally and the landing page now points at the current homes.
- **Risk:** Moving `project-aware-operations.md` breaks any external deep link to the old path. → **Mitigation:** Same as above. Inbound in-repo links are updated in the same change.
- **Risk:** The deprecation banner wording could drift across pages. → **Mitigation:** A single agreed wording pattern lives in Decision 4. Implementation tasks reuse it verbatim.
- **Trade-off:** Not curating `mkdocs.yml` nav leaves the landing page navigation slightly different from the auto-generated MkDocs nav. The `docs/index.md` fix addresses the reader-facing gap; MkDocs nav curation can be a separate change later if needed.

## Migration Plan

Not applicable — doc-only change with no runtime state, no API, no schema, and no versioned artifacts. Rollback is a single `git revert`.

## Open Questions

None. All five open threads from the explore phase have been resolved by the user's `/openspec-propose` answer.
