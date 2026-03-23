## 1. Tracker Identity And Metadata

- [ ] 1.1 Extend the server-owned tracked-session and registration metadata types to carry optional observed tool-version information, including `HoumaoRegisterLaunchRequest`, `_ManifestMetadata`, `KnownSessionRecord`, and `HoumaoTrackedSessionIdentity`.
- [ ] 1.2 Load observed tool-version metadata during known-session reconstruction primarily from `session_manifest.launch_policy_provenance.detected_tool_version`, with `session_manifest.launch_plan.launch_policy_provenance.detected_tool_version` and registration metadata as fallback when needed.
- [ ] 1.3 Update live tracker admission and rebuild logic so shared tracker profile resolution depends on tool identity plus observed tool version, including a rebuild guard that reacts to version changes within the same tool family and graceful fallback when version metadata is absent.

## 2. Live Tracking Boundary

- [ ] 2.1 Refactor the live poll path so supported live cycles pass captured raw tmux pane text straight through to `houmao.shared_tui_tracking` as the normal tracker input.
- [ ] 2.2 Remove parsed-surface-derived synthetic tracker input and `_tracker_snapshot_text_from_host()` compatibility heuristics from normal live server execution, keeping any remaining synthetic helper narrowly test-only.
- [ ] 2.3 Remove parser-derived `_should_infer_prompt_submission()` from tracker-authority flow and rely on the shared tracker’s existing raw-snapshot `surface_inference` behavior for public `last_turn.source=surface_inference`.
- [ ] 2.4 Keep server-owned parser execution and parser-fed lifecycle/operator monitoring available for diagnostics and other server functionality, with server-local turn anchors remaining explicit-input lifecycle enrichment rather than tracker authority.
- [ ] 2.5 Update live tracking response assembly and surrounding design/docs language so parser-derived `parsed_surface` plus server-owned `operator_state` / `lifecycle_*` fields are treated as sidecar server evidence while `surface`, `turn`, and `last_turn` remain tracker-owned.

## 3. Verification

- [ ] 3.1 Add or update unit tests covering observed-version-aware tracker construction and rebuild behavior.
- [ ] 3.2 Add or update live tracking tests covering raw-snapshot authority, removal of parser-derived surface-inference arming from tracker authority, parser sidecar behavior, explicit parser-failure diagnostics, and missing-version fallback behavior.
- [ ] 3.3 Update any affected server demo or monitor tests so they reflect the revised tracker-versus-parser ownership split and the continued lifecycle/operator sidecar posture.

## 4. Documentation

- [ ] 4.1 Revise `houmao-server` state-tracking docs to describe raw tmux capture as tracker authority, shared-tracker `surface_inference` ownership, observed-version fallback behavior, and parser output as server-owned enrichment.
- [ ] 4.2 Revise maintainer-facing docs or comments that still imply parser-derived surface, parser-fed lifecycle timing, or server-local anchor state are part of live tracker authority.
