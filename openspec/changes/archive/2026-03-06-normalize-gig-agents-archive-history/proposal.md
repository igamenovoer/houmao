## Why

`gig-agents` already contains migrated runtime/CAO archived OpenSpec changes, but many of those artifacts still reference legacy `agent_system_dissect` paths and other non-local references. This weakens historical readability and makes archive documents feel disconnected from the current repository.

## What Changes

- Normalize already-migrated archived OpenSpec artifacts so they read as native `gig-agents` history.
- Rewrite legacy module/path references in archive artifacts from `agent_system_dissect` naming to `gig_agents` + current repo paths where applicable.
- Resolve non-local archive references by copying required referenced artifacts into `gig-agents` (preserving directory structure) or replacing unnecessary references with local equivalents.
- Normalize stale OpenSpec cross-links in archive markdown from active-change paths (`openspec/changes/<id>/...`) to archive-resolved paths.
- Add an archive-reference audit contract so new migrated artifacts do not reintroduce references to main-workspace-only paths.

## Capabilities

### New Capabilities
- `openspec-archive-history-hygiene`: defines self-contained, repository-local reference requirements for archived OpenSpec artifacts in `gig-agents`.

### Modified Capabilities
- `brain-launch-runtime`: clarify historical archive reference expectations for runtime-related OpenSpec history in `gig-agents` documentation context.
- `cao-server-launcher`: clarify historical archive reference expectations for CAO launcher-related OpenSpec history in `gig-agents` documentation context.

## Impact

- Affected system: `openspec/changes/archive/**` markdown artifacts in `gig-agents`.
- Affected docs/context trees: `context/issues/known/**` and any additional copied reference docs required by archived links.
- Validation impact: archive reference audit checks (regex/path-existence based) for migrated history quality.
- No runtime/API behavior changes; this is historical artifact normalization and repository hygiene.
