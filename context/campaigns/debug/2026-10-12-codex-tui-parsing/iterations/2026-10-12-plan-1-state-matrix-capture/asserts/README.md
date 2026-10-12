# Iteration 1 Assertion Contracts

Contracts for the `file://asserts/*.py` entries referenced by [../session-1-lifecycle.yaml](../session-1-lifecycle.yaml) and [../session-2-operator-surfaces.yaml](../session-2-operator-surfaces.yaml). Scripts are implemented at execution time by the campaign's replay evaluator (`scripts/explore/codex-tui-parsing/`); this file predeclares their behavior so the YAML specs are reviewable before any code exists.

All scripts follow promptfoo's Python assertion contract: `get_assert(output, context) -> dict` returning at minimum `{pass: bool, reason: str}`, plus `score`, `named_scores`, and `component_results` where listed. `output` is the dict returned by `drivers/tui_driver.py:call_api` for the case (run root, recording manifest path, replay timeline path, labels path, digests); `context.vars` carries the case vars. Scripts read frozen artifacts; they never re-run the session and never inspect live detector state.

Two roles, per the format convention:

- **gate** — returns `pass: false` on breach; fails the case. Maps to plan gates G1–G3/G5.
- **measure** — always returns `pass: true`; findings are reported via `named_scores` / `component_results`. Iteration 1 expects detector mismatches; they are the output, not a failure.

## recording_integrity.py (gate)

- Inputs: driver result `output` (recording `manifest.json`, `frozen-evidence.json`).
- Checks: recorder status `stopped` with `stopped_at_utc` and `stop_reason`; `pane_snapshots.ndjson` and `input_events.ndjson` exist; SHA-256, byte size, and row count recorded for every bound file; `run_tainted` and taint reasons recorded.
- Fails when: any bound file is missing, digests mismatch, or the recorder was never stopped. A tainted run does not fail this gate by itself but is reported in `reason`.

## label_integrity.py (gate)

- Inputs: `labels.json`, `labels-manifest.json`, source recording digest.
- Checks: every source sample has exactly one label; all eight public tracked-state fields present per range (per `houmao-dev-tui-testing/references/state-labeling.md`); ranges ordered, non-overlapping; label manifest bound to the frozen recording digest; label freeze timestamp precedes any replay artifact timestamp (blind-label ordering, plan G3).
- Fails when: coverage gaps, overlaps, missing fields, or evidence that labeling happened after replay.

## coverage_spans.py (gate)

- Inputs: `labels.json`.
- Config: `required_spans` (list of state-family names: `ready`, `editing`, `active`, `queue_pending`, `interrupted`, `approval_modal`, `model_picker`, `warnings_screen`, `compaction`, `tui_down`), `min_span_samples` (default 3 = 0.6 s at 5 fps), `optional` (bool).
- Checks: each required span family appears in labels with at least one contiguous range of ≥ `min_span_samples`.
- Fails when: a non-optional span is absent or too short. `optional: true` spans report a coverage gap in `reason` without failing.

## field_agreement.py (measure)

- Inputs: replay timelines for both arms (Arm A1: `analyze --observed-version 0.162.1` → fallback detector; Arm A2: `analyze --observed-version 0.144.0` → maintained 0.144.x profile) and frozen `labels.json`.
- Behavior: per arm, per public tracked-state field, computes sample-level agreement between detector output and ground truth, grouped by labeled state family. Always `pass: true`.
- Outputs: `named_scores` led by the two user-facing booleans (`surface_accepting_input` = ready to enter prompt, `surface_ready_posture` = accept prompt; directive 2026-10-10), then per-field agreement ratios for the remaining public fields (`turn_phase`, `surface_editing_input`, `surface_pending_input`, `last_turn_result`, …); `component_results` per state family per arm. These scores are the KQ-1 mismatch catalog in numeric form.

## signal_audit.py (measure)

- Inputs: frozen `pane_snapshots.ndjson` (escape-preserving), labels, and the hardcoded signal inventory from `src/houmao/shared_tui_tracking/apps/codex_tui/` (`signals/prompt_behavior.py` prompt regex and placeholder/draft classification, `signals/activity.py` status-row and tool-cell families, `profile.py` `_CODEX_WORKED_PREFIX`, `signals/interrupted.py` interruption and steer-handoff texts, `signals/overlays.py` overlay needles, `signals/error_cells.py` terminal-failure regex inventory, provider markers).
- Behavior: for each detector signal, counts fired/missed against the labeled spans where that signal is expected, plus false fires on unrelated spans. Always `pass: true`.
- Outputs: `named_scores` per signal (`fired`, `missed`, `false_fired`); `component_results` rows feed the survival table (surviving ≥95% / broken <50% / degraded, per the plan's decision rules). Also emits the Arm B escape-sequence tallies (OSC 133 / OSC `9;4` presence per labeled state) from the raw snapshot stream.
