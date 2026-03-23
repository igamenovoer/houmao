## Context

`houmao-server` already instantiates the standalone shared tracker session and feeds it live observations, but the live adapter still treats parser-derived surface state as intertwined with tracking authority. That leaves the current implementation and documentation with a mixed model:

- raw tmux pane text is already available and already fed into `houmao.shared_tui_tracking`
- parser-derived `HoumaoParsedSurface` is still threaded through the live adapter as if it were part of state-tracking authority
- some server-side tracker wiring still falls back to synthetic snapshot text derived from parsed surface data
- observed tool-version metadata exists in launch/session provenance, but the live adapter does not reliably carry it into shared tracker profile selection

The standalone tracked-TUI module is already the intended semantic center for `surface`, `turn`, and `last_turn`. The missing step is to make the `houmao-server` boundary reflect that intent cleanly: the server owns live acquisition, server-only parsing, diagnostics, and route shaping, while the standalone module owns TUI state tracking.

This change is cross-cutting because it touches the live poll path, tracker/session identity, parser ownership, tests, and the OpenSpec definition of the server tracking boundary.

## Goals / Non-Goals

**Goals:**
- Make `houmao.shared_tui_tracking` the sole authority for live TUI state reduction in `houmao-server`.
- Define raw tmux pane text plus explicit prompt-submission events as the live adapter input to the standalone tracker.
- Keep server-owned parsing available for additional server features, diagnostics, and operator-facing evidence without making parser output part of state-tracking authority.
- Keep the existing parser-fed lifecycle/operator monitoring path available as server-owned sidecar enrichment for `operator_state`, `lifecycle_timing`, and `lifecycle_authority`.
- Remove live adapter dependence on parser-derived synthetic tracker input outside explicit test/debug seams.
- Carry observed tool-version metadata into live tracker profile selection when available.
- Preserve the current public server-facing state vocabulary centered on `diagnostics`, `surface`, `turn`, `last_turn`, and `stability`.

**Non-Goals:**
- Adding tmux replay, recorded validation, or terminal-recorder workflows to `houmao-server`.
- Moving `terminal_record`, demo-pack replay, or sweep logic into the live server.
- Removing all parser-derived fields from server routes in this change.
- Replacing server-owned diagnostics, stability, or route shaping with shared-tracker-owned equivalents.
- Removing or redesigning the existing server-owned lifecycle/operator enrichment path in this change.
- Unifying the server-local and shared-tracker turn-anchor models in this change.
- Redesigning the standalone tracker contract itself beyond the live adapter boundary needed here.

## Decisions

### Decision: The live server tracking path delegates reduction to the standalone tracker from raw tmux text

`houmao-server` will treat raw captured pane text as the authoritative input for live TUI state tracking. The live adapter will feed that raw text, plus explicit input submission events when available, into `houmao.shared_tui_tracking`.

Parser output will no longer be considered part of the tracking input path. If raw capture is unavailable, the cycle is degraded at the server diagnostics layer rather than repaired by fabricating tracker input from parser-owned fields.

Rationale:
- The standalone module already defines the tracker input contract as raw snapshot text plus explicit-input evidence.
- This matches the boundary already validated by the standalone demo pack.
- It avoids mixing parser semantics and tracker semantics in one reducer path.

Alternatives considered:
- Keep the current mixed path where parsed surface can be converted back into synthetic tracker input.
  Rejected because it makes parser-derived normalization part of live tracking authority and weakens the intended standalone boundary.
- Replace live tracking with parser-only reduction.
  Rejected because the standalone tracker already owns the supported TUI state machine.

### Decision: Server-owned parsing remains a sidecar capability, not tracker authority

The server will continue to parse raw tmux capture through the official parser when server-owned functionality needs structured surface interpretation, parser diagnostics, anomaly reporting, or operator-facing evidence. That parsed surface remains server-owned enrichment.

The parsed surface may still be included in route payloads and demo displays, but it is not the authoritative source of `surface`, `turn`, or `last_turn`.

Rationale:
- The user explicitly wants additional parsing preserved for server functionality.
- Existing server routes and demos still consume parser-derived evidence.
- Keeping parser output available avoids forcing unrelated server features to regress just to clean up state-tracking ownership.

Alternatives considered:
- Remove parsing from the live server entirely.
  Rejected because the server still has parser-owned features and evidence needs.
- Keep parsing as a required precondition for state tracking.
  Rejected because it preserves the current authority confusion.

### Decision: Server-owned lifecycle/operator monitoring remains a parser-fed sidecar

`houmao-server` will continue to run its parser-fed lifecycle pipeline and turn-anchor bookkeeping for server-owned enrichment such as `operator_state`, `lifecycle_timing`, and `lifecycle_authority`.

Those fields remain part of the published or internal server view, but they are not authoritative for tracker-owned `surface`, `turn`, or `last_turn`. Timing disagreement between the parser-fed lifecycle view and the shared tracker view is treated as an ownership split, not as a request to reintroduce parser authority into tracked TUI state.

Rationale:
- Existing routes, docs, and demo/debug surfaces still consume lifecycle/operator enrichment.
- The user asked to preserve additional parsing needed by server functionality while keeping state tracking delegated to the standalone tracker.
- Removing the lifecycle path or collapsing it into shared tracker state would broaden the change beyond the boundary cleanup requested here.

Alternatives considered:
- Remove the lifecycle/operator pipeline in this change.
  Rejected because it would alter existing server-owned enrichment semantics and expand scope.
- Let parser-fed lifecycle state continue to implicitly define tracker-owned turn semantics.
  Rejected because it leaves ownership blurry.

### Decision: Shared tracker raw-snapshot inference owns public `surface_inference`

The live adapter will no longer arm tracker authority from parser-derived submit-ready heuristics such as `_should_infer_prompt_submission()`. Public `last_turn.source=surface_inference` semantics will come from the shared tracker’s existing raw-snapshot inference behavior.

The server-local anchor system remains for server-owned lifecycle enrichment, and in this change it stays tied to explicit input submissions rather than parser-derived surface-inference heuristics.

Rationale:
- The shared tracker already supports raw-snapshot `surface_inference`, so a second server-local inference layer is unnecessary.
- This removes the remaining parser-to-tracker authority bridge without redesigning the shared tracker contract.
- It keeps the server-local lifecycle path narrow and explicit.

Alternatives considered:
- Replace parser-derived surface inference with a new server-local raw-text heuristic.
  Rejected because the shared tracker already owns this responsibility.
- Keep parser-derived surface inference as a documented exception.
  Rejected because it weakens the authority boundary this change is meant to establish.

### Decision: Observed tool version becomes part of live tracker identity

When available, the live server will carry observed tool-version metadata from server-owned launch/session provenance into the shared tracker session so the tracker can resolve the closest-compatible profile for the live tool.

Manifest-backed launch/session provenance is the primary source, specifically `session_manifest.launch_policy_provenance.detected_tool_version` with `session_manifest.launch_plan.launch_policy_provenance.detected_tool_version` as a compatibility fallback. Registration payloads may carry fallback metadata when manifest provenance is absent.

Rationale:
- The shared tracker registry is already version-aware.
- The standalone demo/live-watch path already resolves and passes observed version.
- Leaving `observed_version=None` in the server forces fallback profiles and diverges from the intended contract.

Alternatives considered:
- Keep `observed_version=None` in live server tracking.
  Rejected because it undercuts the versioned-profile contract already documented in the repo.
- Probe tool version directly from the live watch worker on every cycle.
  Rejected because manifest-backed launch provenance is already available and avoids repeated probing.

### Decision: Server-owned diagnostics remain separate from tracker-owned state

The server will continue to own:

- tmux transport and capture errors
- process-tree liveliness
- parser success/failure and parsed-surface diagnostics
- parser-fed lifecycle/operator enrichment
- route-facing payload assembly
- visible-state stability over the published response

The standalone tracker will continue to own:

- `surface.accepting_input`
- `surface.editing_input`
- `surface.ready_posture`
- `turn.phase`
- `last_turn.result`
- `last_turn.source`
- tracker-profile resolution and tracker-local transition semantics

Rationale:
- This preserves the intended layering in the existing docs and shared core.
- It allows parser failure or transport degradation to stay explicit without turning parser internals into tracker inputs.

Alternatives considered:
- Push server diagnostics into the standalone tracker.
  Rejected because transport/process/parser ownership is host-specific, not generic tracked-TUI logic.
- Collapse server stability into tracker stability.
  Rejected because the server’s published signature includes host-owned fields beyond tracker state.

### Decision: Live adapter verification focuses on boundary correctness, not replay ownership

Implementation verification for this change will focus on live-adapter tests and contract-oriented server tests. Replay, recorder, and standalone validation remain outside `houmao-server`.

Where parity matters, the server should be checked against the standalone tracker contract, not extended to own replay features.

Rationale:
- The user explicitly ruled out tmux replay as a server feature.
- The repository already has standalone replay and recorded-validation tooling.

Alternatives considered:
- Add a server replay mode to prove parity internally.
  Rejected because it expands server scope in the wrong direction.

## Risks / Trade-offs

- [Risk] Parser-derived fields may still leak back into tracking decisions through leftover helper logic. → Mitigation: remove or explicitly isolate synthetic snapshot fallback paths from normal live execution.
- [Risk] Parser-derived surface inference or parser-gated stability may still leak into tracker-authority transitions. → Mitigation: remove parser-derived `_should_infer_prompt_submission()` from tracker-authority flow and rely on shared tracker raw-snapshot inference instead.
- [Risk] Existing tests or demos may implicitly depend on parser-owned fields being treated as tracking authority. → Mitigation: update tests and docs to separate tracker-owned and parser-owned meanings explicitly.
- [Risk] Wiring observed tool version through server identity may touch registration and manifest-loading seams. → Mitigation: make the new metadata optional and use manifest provenance as the primary source with graceful fallback.
- [Risk] Dual tracker/lifecycle or dual-anchor views may appear contradictory to maintainers. → Mitigation: document the ownership split explicitly in design and server docs rather than letting the coexistence remain implicit.
- [Risk] Parsing every cycle while making it non-authoritative could look redundant. → Mitigation: keep the boundary explicit in code and docs; defer any parser execution optimization to a later change.

## Migration Plan

1. Extend server-owned tracked-session metadata to carry optional observed tool version across registration, manifest enrichment, known-session identity, and live tracker wiring.
2. Load that version primarily from manifest `launch_policy_provenance.detected_tool_version`, with registration fallback when manifest provenance is absent.
3. Update `LiveSessionTracker` so tracker-session construction and rebuilds depend on both tool identity and observed version.
4. Simplify the live adapter so raw tmux capture is the normal tracker input and parsed-surface-derived synthetic tracker input is removed from normal live execution.
5. Remove parser-derived surface-inference arming from tracker-authority flow and rely on the shared tracker’s raw-snapshot inference, while keeping explicit-input server anchors for lifecycle enrichment.
6. Preserve parser execution and parser-fed lifecycle/operator monitoring for server-owned diagnostics and other server functionality, but document them as non-authoritative for tracked TUI state.
7. Update live server tests, state-tracking docs, and any affected monitor/demo wording to reflect the new authority split.

Rollback is a normal code revert. No persistent data migration is required beyond tolerating older registration records or manifests that omit observed tool version.

## Open Questions

- Should `parsed_surface` remain in the public terminal-state route long-term, or should a later change move parser-owned evidence behind a separate server-owned inspection surface once the authority split is complete?
