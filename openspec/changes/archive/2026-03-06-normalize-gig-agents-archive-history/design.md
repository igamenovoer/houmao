## Context

`gig-agents` already stores a large set of archived OpenSpec changes under
`openspec/changes/archive/`. Those archives were migrated from another workspace,
and many documents still contain legacy references that break historical
readability in this repository:

- legacy module/path names (`agent_system_dissect`),
- links that still point at active-change paths (`openspec/changes/<id>/...`),
- references to files that only existed in the original workspace.

At the same time, `gig-agents` now has its own `context/` and `extern/` trees,
so we can make archive references self-contained without depending on the main
workspace.

## Goals / Non-Goals

**Goals:**
- Make archived OpenSpec artifacts read as if they were authored in
  `gig-agents` all along.
- Remove main-workspace-only references from archived OpenSpec artifacts.
- Preserve historical context by copying required referenced files into
  `gig-agents` while keeping source-relative structure.
- Define a repeatable archive-reference audit so future archive migrations do
  not regress.
- Exclude migration work for
  `2026-03-06-extract-agent-runtime-to-gig-agents` from this change.

**Non-Goals:**
- Alter runtime behavior, APIs, or implementation under `src/gig_agents/`.
- Rewrite historical technical decisions beyond path/reference normalization.
- Backfill unrelated documentation outside archive-reference needs.
- Change archive dates, change IDs, or artifact chronology.

## Decisions

### 1) Normalize references using a deterministic classification pass
Process each archived markdown artifact and classify every reference into one of
three buckets:

- repository-local and valid: keep as-is,
- repository-local but stale format: rewrite (for example active-change path to
  archive path),
- non-local or legacy workspace reference: localize by copy or rewrite.

Rationale: this avoids ad-hoc edits and makes results auditable.

Alternative considered:
- Manual free-form edits per file.
  - Rejected due to high drift risk and poor repeatability.

### 2) Rewrite archive-internal OpenSpec links to archive-resolved paths
When a historical document points to `openspec/changes/<id>/...`, rewrite to the
archived location when applicable:
`openspec/changes/archive/<date>-<id>/...`.

Rationale: archived history should resolve within archive trees, not active
change trees that may no longer exist.

Alternative considered:
- Keep legacy links unchanged and rely on reader interpretation.
  - Rejected because it leaves broken links and weakens archive trust.

### 3) Localize non-local references via in-repo snapshots with preserved structure
If an archived document needs an external reference for historical context,
import that file into `gig-agents` (for example under `context/...` or
`extern/...`) while preserving source directory structure as much as practical.
If the reference is incidental, remove or replace it with a local equivalent.

Rationale: self-contained archives are easier to read, review, and maintain.

Alternative considered:
- Keep references to files outside `gig-agents`.
  - Rejected because it violates the portability requirement for migrated
    history.

### 4) Establish an archive-hygiene audit contract
Introduce a deterministic audit check (scripted or command recipe) that scans
archived artifacts for forbidden patterns and unresolved references.

Minimum checks:
- no `agent_system_dissect` tokens in archived artifacts,
- no hard-coded main-workspace absolute paths,
- no stale `openspec/changes/<id>/...` references where archived equivalents
  exist,
- copied reference targets exist at the normalized paths.

Rationale: this turns one-time cleanup into a sustainable quality gate.

Alternative considered:
- Rely only on manual review.
  - Rejected because scale and future migrations make manual-only enforcement
    brittle.

## Risks / Trade-offs

- [Risk] Over-normalizing could remove useful historical detail.
  - Mitigation: only rewrite path/reference forms; keep decision content intact.

- [Risk] Copied snapshots can drift from their original source over time.
  - Mitigation: treat copied files as historical snapshots and avoid claiming
    they are live mirrors.

- [Risk] Regex audits can produce false positives/negatives.
  - Mitigation: keep forbidden-pattern checks small and explicit, and pair with
    path-existence verification.

- [Risk] Some references may be ambiguous after repository expansion.
  - Mitigation: prefer preserved-structure copies when ambiguity cannot be
    resolved confidently.

## Migration Plan

1. Inventory and classify archive references.
2. Rewrite stale internal links and legacy path tokens.
3. Copy required non-local references into `gig-agents` with preserved
   structure.
4. Run archive-hygiene audit and fix remaining violations.
5. Spot-check representative archive documents for readability and continuity.

## Open Questions

- None. Scope and exclusions are explicit for this change.
