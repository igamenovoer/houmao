## 1. Label Existing Long-Horizon Recordings

- [ ] 1.1 Use the nine replay-ready attempts from report `20260713T095944Z-long-horizon-test-report.md` as the initial fixture set:
  - Claude ST01 `a007`, Claude ST02 `a001`, Claude ST03 `a001`
  - Codex ST01 `a004`, Codex ST03 `a004`, Codex ST04 `a002`, Codex ST05 `a004`
  - Kimi ST03 `a008`, Kimi ST04 `a003`
  - Skip attempts whose `attempt-state.json` shows `phase: failed` or non-terminal statuses such as `provider_preflight_failed`.
- [ ] 1.2 Audit existing `labels/labels.json` files on those attempts for coverage and schema compatibility.
- [ ] 1.3 Define the UC-03 `labels.json` schema with `ready_immediate`, `busy_active`, `busy_draft`, `busy_overlay`, and `indeterminate` values plus source-sample evidence citations.
- [ ] 1.4 Convert or extend existing labels to full per-sample UC-03 labels; create additional labels only where gaps exist.
- [ ] 1.5 Produce a label inventory report that lists, per attempt, the count of labeled samples and any remaining gaps.

## 2. Classification-Correctness Test Harness

- [ ] 2.1 Create `scripts/qualification/tui-prompt-admission/` directory and a Python package/module layout.
- [ ] 2.2 Implement a parser for the long-horizon terminal-record format: `session.cast`, `live_state.json`, `pane_snapshots.ndjson`, and `input_events.ndjson`.
- [ ] 2.3 Implement a label-expansion utility that turns sparse labels into a per-sample UC-03 readiness timeline.
- [ ] 2.4 Implement a classification comparator that compares the shared tracker/detector's public tracked state (`surface_ready_posture`, `turn_phase`, `surface_accepting_input`, `surface_editing_input`, etc.) against the labeled timeline and reports the first mismatch.
- [ ] 2.5 Run the classification comparator against the labeled attempts per provider and produce a classification-correctness report.

## 3. Admission-Consumer Simulator

- [ ] 3.1 Implement the non-forced admission predicate using the same public tracked-state fields the live gateway consumes.
- [ ] 3.2 Add the simulator CLI that reads a recording root and writes `simulated_admission.ndjson` with `would_admit`, `blockers`, and `decision_time` per sample.
- [ ] 3.3 Run the simulator against at least one existing long-horizon recording per provider and verify output schema.
- [ ] 3.4 Add a label-comparator that compares the simulator's `would_admit` against `ready_immediate` spans and reports the first mismatch.

## 4. Live Procedure Runner

- [ ] 4.1 Add a CAL-01 procedure manifest that launches a disposable unattended session, submits the long read-only prompt, forces the canary, classifies native behavior, and destroys the session.
- [ ] 4.2 Add an AR-01 procedure manifest with the twelve operations using both `houmao-mgr gateway prompt` and direct `POST /v1/control/prompt`.
- [ ] 4.3 Add an AR-02 procedure manifest that enables the one-second unread-only notifier, posts operator-origin mail, observes busy skips, and verifies enqueue/release.
- [ ] 4.4 Integrate the existing long-horizon session launcher, 20 fps terminal-record capture, Boltons fixture copy, and cleanup into the UC-03 runner.
- [ ] 4.5 Add gateway command trace capture (`gateway-command-trace.ndjson`), queue snapshots, and notifier audit rows to the live runner outputs.

## 5. Correlation, Verdicts, and Documentation

- [ ] 5.1 Implement a correlation step that joins independent labels, tracked state, gateway command trace, queue snapshots, notifier audit rows, and provider input events by monotonic time.
- [ ] 5.2 Emit `classification_verdict`, `admission_verdict`, `delivery_verdict`, and `scenario_verdict` per checkpoint.
- [ ] 5.3 Implement failure-slice generation that preserves the first divergent sample, the outside prompt/mail event, blockers, gateway decision, and provider-visible consequence.
- [ ] 5.4 Generate the UC-03 report at `context/features/2026-07-11-tui-state-tracking-test-plan/test-reports/<ts>-prompt-admission-readiness.md` after a live run.
- [ ] 5.5 Add a Pixi task for the classification comparator and a Pixi task for the live qualification runner.
- [ ] 5.6 Document how to label recordings, run the classification comparator, point the simulator at existing recordings, and execute live UC-03 procedures.
