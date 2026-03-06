# Implementation Notes: normalize-gig-agents-archive-history

## Scope And Exclusion

This implementation normalizes archived OpenSpec artifacts under
`openspec/changes/archive/**` to remove legacy/non-local references.

Explicit exclusion honored:
- `2026-03-06-extract-agent-runtime-to-gig-agents`

No files under that archive ID were modified in this change.

## Pre-Normalization Inventory

Reference scan (before edits) identified:
- 96 legacy `agent_system_dissect` references
- 9 stale active-change links (`openspec/changes/<id>/...`) with archive targets
- 13 non-local/missing contextual references (magic-context or missing context docs)

## Classification And Mapping

| Reference family | Classification | Action | Target/Result |
| --- | --- | --- | --- |
| `agent_system_dissect` module/path tokens | `rewrite` | Replaced with `gig_agents` namespace/path forms in archived markdown artifacts | `src/gig_agents/...`, `python -m gig_agents...`, `gig_agents.*` |
| `openspec/changes/<id>/...` where archived counterpart exists | `rewrite` | Rewrote to archive-resolved paths | `openspec/changes/archive/<date>-<id>/...` |
| `magic-context/instructions/explain/make-api-tutorial-pack.md` | `localize-by-copy` + `rewrite` | Copied instruction snapshot into repo-local context tree, rewrote references | `context/instructions/explain/make-api-tutorial-pack.md` |
| `context/issues/known/issue-cao-claude-code-output-mode-last-marker-mismatch.md` | `localize-by-copy` | Copied from main workspace context into `gig-agents` context tree | `context/issues/known/issue-cao-claude-code-output-mode-last-marker-mismatch.md` |
| `context/issues/features/feat-gemini-headless-parser-architecture.md` (and old `context/issues/feat-...`) | `rewrite` + `localize-by-copy` | Rewrote old path form to `features/` and copied issue snapshot | `context/issues/features/feat-gemini-headless-parser-architecture.md` |
| `context/issues/known/issue-cao-server-fixed-port-9889.md` | `localize-by-copy` | Copied issue snapshot | `context/issues/known/issue-cao-server-fixed-port-9889.md` |
| `context/logs/code-reivew/20260227-140000-cao-claude-fresh-config-dir-bugfix.md` | `localize-by-copy` | Copied log snapshot | `context/logs/code-reivew/20260227-140000-cao-claude-fresh-config-dir-bugfix.md` |
| `context/hints/agent-identity-resolution.md` (missing upstream artifact) | `localize-by-copy` (authored local snapshot) | Added minimal local hint doc to satisfy archived reference | `context/hints/agent-identity-resolution.md` |

No `remove-as-unneeded` cases were required for this migration batch.

## Audit Contract

Added script:
- `scripts/openspec/audit_archive_history.sh`

Checks implemented:
1. Forbidden legacy namespace (`agent_system_dissect`) in archived artifacts.
2. Forbidden main-workspace absolute paths.
3. Stale active-change links where archived equivalents exist.
4. Existence of normalized local references (`context/...` and `openspec/changes/archive/...`).

## Spot Checks

Representative readability/link-resolution checks after normalization:
- Runtime history:
  - `openspec/changes/archive/2026-03-05-unify-headless-tmux-backend/design.md`
  - `openspec/changes/archive/2026-03-05-fix-cao-bootstrap-window-shell-first-attach/discuss/discuss-20260305-091708.md`
- Launcher history:
  - `openspec/changes/archive/2026-03-05-cao-server-launcher/design.md`
  - `openspec/changes/archive/2026-03-05-cao-server-launcher-demo-pack/proposal.md`

Observed result: references now use `gig_agents` namespace/path forms and
archive-resolved OpenSpec links, with required context references available
inside `gig-agents`.
