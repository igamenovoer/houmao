## Why

`houmao-server` already embeds the standalone shared TUI tracker, but the live adapter still mixes tracker-owned reduction with parser-owned surface interpretation. That keeps the server boundary fuzzier than the standalone contract the repo has already validated and makes it harder to reason about which fields are authoritative for TUI state tracking.

## What Changes

- Clarify that live TUI state tracking in `houmao-server` is delegated to `houmao.shared_tui_tracking`, with raw tmux pane text plus explicit input events as the tracker authority.
- Change the live server tracking boundary so parser output is no longer part of the state-tracking input path.
- Remove server-local parser-derived surface-inference arming from tracker authority and rely on the shared tracker’s existing raw-snapshot `surface_inference` behavior.
- Keep server-owned parsing available for additional server features and diagnostics, but treat parsed surface data as sidecar enrichment rather than tracker input.
- Keep parser-fed lifecycle/operator monitoring available as server-owned sidecar enrichment for `operator_state`, `lifecycle_timing`, and `lifecycle_authority`, without letting those fields redefine tracker-owned `surface`, `turn`, or `last_turn`.
- Align server-owned tracking metadata and documentation with the standalone tracker boundary, including observed tool-version plumbing from manifest `launch_policy_provenance.detected_tool_version` with registration fallback where needed for profile selection.
- Add verification coverage that exercises the live server adapter against the standalone tracker contract instead of reintroducing server-local tracking semantics.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `official-tui-state-tracking`: live server tracking SHALL delegate TUI state reduction to the standalone shared tracker from raw tmux strings, while any parser-derived data remains server-owned enrichment rather than state-tracking authority.

## Impact

- Affected code:
  - `src/houmao/server/tui/tracking.py`
  - `src/houmao/server/service.py`
  - `src/houmao/server/tui/registry.py`
  - `src/houmao/server/models.py`
  - server-side tests and state-tracking docs
- Affected systems:
  - `houmao-server` live watch path
  - versioned tracked-TUI profile selection for live sessions
  - any server functionality that consumes parser-derived surface data alongside tracker state
- APIs:
  - no new end-user route surface is intended
  - the existing server registration metadata may gain optional observed-version fallback fields
  - any retained parser-derived or lifecycle-derived fields become explicitly non-authoritative for TUI state tracking
