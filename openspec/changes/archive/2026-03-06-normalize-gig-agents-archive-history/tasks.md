## 1. Archive Inventory And Mapping

- [x] 1.1 Build an inventory of archived markdown artifacts under `openspec/changes/archive/**` that still contain legacy/non-local references.
- [x] 1.2 Classify each flagged reference as `rewrite`, `localize-by-copy`, or `remove-as-unneeded`, and record the target local path for each rewrite/copy.
- [x] 1.3 Exclude `2026-03-06-extract-agent-runtime-to-gig-agents` from this migration scope and ensure no tasks modify that archive.

## 2. Normalize Archived OpenSpec References

- [x] 2.1 Rewrite stale OpenSpec links from `openspec/changes/<id>/...` to `openspec/changes/archive/<date>-<id>/...` when archived targets exist.
- [x] 2.2 Replace legacy `agent_system_dissect` module/path references in archived artifacts with `gig_agents`-native equivalents where applicable.
- [x] 2.3 Update `brain-launch-runtime` and `cao-server-launcher` archive artifacts so required references resolve entirely within `gig-agents`.

## 3. Localize Required Supporting Artifacts

- [x] 3.1 Copy required non-local referenced files into `gig-agents` under `context/` or `extern/` while preserving source directory structure.
- [x] 3.2 Update archive references to point at localized copies and remove references that are no longer necessary.
- [x] 3.3 Add/refresh minimal README notes in affected copied trees when needed so future readers understand these are historical-support snapshots.

## 4. Add Audit Contract And Validate

- [x] 4.1 Add an archive-hygiene audit command/script that fails on forbidden patterns (`agent_system_dissect`, main-workspace absolute paths, unresolved normalized links).
- [x] 4.2 Run the audit against all archived artifacts and fix any violations until clean.
- [x] 4.3 Spot-check representative archived changes for readability and link resolution after normalization (including runtime and launcher histories).
