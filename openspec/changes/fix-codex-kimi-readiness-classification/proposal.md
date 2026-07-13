## Why

Frozen 20 fps Codex and Kimi Code recordings show sustained false-ready classification that would allow downstream prompt admission while the provider is still processing or retaining input. The existing UC-03 report identifies the dangerous observation, but its generated labels and causal explanations are not reliable enough to guide the fix, so the detector rules, capture gate, and replay oracle must be corrected together.

## What Changes

- Recognize Kimi Code's source-backed queued-message pane as current busy evidence while preserving the existing moon and braille spinner signals.
- Recognize current Codex pending-steer, rejected-steer, and queued-follow-up panes as current busy evidence, including surfaces where the ordinary working row is temporarily hidden.
- Restrict Codex retry activity detection to source-backed live status shapes and recognize current model/list selectors as blocking overlays.
- Prevent a newly detected provider process from inheriting readiness from a stale pre-restart pane surface before fresh provider chrome and prompt evidence appear.
- Make long-horizon capture readiness gates provider-specific and require a post-submit busy or progress edge before accepting a later ready return.
- Replace mechanically remapped tracker-shaped "ground truth" with direct UC-03 readiness labels, explicit evidence provenance, diagnostics-first mapping, and reproducible replay summaries.
- Add recorded-sample regression tests and replay the frozen Codex/Kimi corpus across canonical and reduced cadences until sustained state misclassification is removed; short transition-boundary noise remains reportable but does not justify a sustained false-ready interval.

## Capabilities

### New Capabilities
- `tui-readiness-regression-qualification`: Defines reproducible source-backed readiness labels, capture-gate lifecycle requirements, and recorded replay acceptance for prompt-admission state classification.

### Modified Capabilities
- `codex-tui-state-tracking`: Treat current pending-input surfaces and bounded retry/selector surfaces according to Codex 0.144 TUI semantics.
- `kimi-code-tui-support`: Treat current Kimi queue-pane surfaces as busy and non-ready even when spinner rows fall outside the narrow activity window.
- `official-tui-state-tracking`: Keep readiness conservative across provider process-generation changes until a fresh current TUI surface is observed.

## Impact

Affected areas include `src/houmao/shared_tui_tracking/apps/{codex_tui,kimi_code}/`, shared retained-pane surface handling, the long-horizon capture harness, UC-03 qualification scripts, detector unit tests, and frozen replay evidence under `tmp/tui-state-tracking-long-horizon/`. Public tracked-state field names and gateway APIs remain unchanged; their classification becomes more accurate and conservative during active, overlay, and restart-startup surfaces.
