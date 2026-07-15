## Context

UC-03 defines the admission qualification procedures CAL-01, AR-01, and AR-02. The current long-horizon qualification run (`tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers/`) already captures Claude, Codex, and Kimi sessions at 20 fps using the same Boltons fixture, unattended posture, and terminal-record format that UC-03 requires. That corpus is incomplete for UC-02, but it is immediately useful as a development fixture for the UC-03 admission-consumer simulator and for validating the comparator before live runs.

The live gateway already exposes `POST /v1/control/prompt` and the mail-notifier control surfaces. The shared tracker already publishes public state fields including `surface.ready_posture`, `turn.phase`, `surface.accepting_input`, `surface.editing_input`, and `stability.stable`. The missing piece is a harness that (a) replays recorded state through the admission predicate, (b) executes the three live procedures, and (c) correlates independent labels, tracker state, gateway decisions, and provider input evidence into verdicts.

## Goals / Non-Goals

**Goals:**
- Deliver an admission-consumer simulator that can replay any existing terminal-record corpus through the current non-forced admission predicate and emit `would_admit` plus blockers per sample.
- Deliver a live UC-03 procedure runner that executes CAL-01, AR-01, and AR-02 per provider, records evidence, and produces the durable outputs listed in UC-03.
- Reuse the long-horizon recording infrastructure (tmux launch, 20 fps capture, Boltons fixture copy, manifest generation) rather than building a second capture stack.
- Produce a verdict report that distinguishes classification, admission, delivery, and scenario verdicts.

**Non-Goals:**
- Changing the gateway control API, tracker public state schema, or mail-notifier semantics.
- Achieving UC-03 qualification in this change; this change only builds the harness and simulator so qualification can be run.
- Modifying existing UC-02 long-horizon procedures or their recordings.
- Creating a fully automated ground-truth labeler; human independent labels remain authoritative.

## Decisions

### Admission-consumer simulator is a standalone script that consumes recorded public state

The simulator reads `recording/terminal-record/live_state.json` and `recording/terminal-record/pane_snapshots.ndjson` (or the equivalent in older fixtures), evaluates the admission predicate for each sample, and writes `simulated_admission.ndjson`. It does not re-run live gateway calls or re-launch providers.

**Rationale:** This separates classifier replay from live end-to-end evidence, which UC-03 explicitly requires. The same comparator can then be applied to both fixture and live runs.

**Alternatives considered:** Reusing the existing recorded-validation sweep code directly. Rejected because sweep contracts are coarse transition contracts, not per-sample admission decisions.

### Live procedure runner reuses the long-horizon session launcher

CAL-01, AR-01, and AR-02 will use the same unattended launch, Boltons copy, tmux pane, and 20 fps terminal-record capture that the long-horizon runner already uses. A new procedure manifest will be added for each UC-03 procedure.

**Rationale:** Avoids duplicating launch policy, provider-home isolation, fixture copy logic, and cleanup. The existing runner already proved it can launch Claude, Codex, and Kimi unattended.

**Alternatives considered:** A separate UC-03-specific launcher. Rejected because it would reimplement the same launch/capture/cleanup logic and drift out of sync.

### CAL-01 is isolated from AR-01/AR-02 and always uses `--force`

CAL-01 runs in a disposable provider session and is destroyed afterward. Its forced canary may contaminate the session, so its labels and recordings are not used as qualification output without human review.

**Rationale:** Matches UC-03's requirement that forced calibration is evidence calibration, not a passing gateway-safety run.

### Label only completed (`reported`) long-horizon attempts, then test classification correctness

Failed attempts — those whose `attempt-state.json` shows `phase: failed` or a non-terminal status such as `provider_preflight_failed` — are excluded from labeling and from classification testing. Only attempts that reached the `reported` phase (or `awaiting_manual_labels`) have usable recordings and are eligible for label conversion/extension.

The first implementation step is to evaluate the labels that already exist on the latest `reported` long-horizon attempts and to add full per-sample UC-03 labels wherever they are missing. A label covers every source sample and uses one of `ready_immediate`, `busy_active`, `busy_draft`, `busy_overlay`, or `indeterminate`. Labeling is a manual maintainer task; no automated visible-evidence helper is required.

Once labels exist, the harness compares the shared tracker/detector's public tracked-state output against the labels. This is **classification correctness**, not admission correctness. Admission correctness is tested only after classification is sound.

**Rationale:** UC-03's admission predicate is built from public tracker state. If the tracker misclassifies `ready_posture` or `turn.phase`, the admission decision will be wrong even if the predicate logic is correct. Proving classification first isolates detector defects from admission-defects. Failed attempts lack complete recordings and cannot contribute ground truth.

**Alternatives considered:** Building the admission simulator before labels. Rejected because the simulator output is meaningless without trusted ground truth.

### Independent labels use a new `labels.json` schema that supports UC-03 posture values

The label schema extends the existing recorded-validation labels with values `ready_immediate`, `busy_active`, `busy_draft`, `busy_overlay`, and `indeterminate`. Each label cites a source sample id and visible evidence text.

**Rationale:** UC-03 needs more specific readiness labels than the existing state labels. Keeping the same file name and per-sample structure lets us reuse label-review tooling.

### Verdicts are produced by a correlation step after recording and labeling

The harness joins by monotonic time: independent labels, `tracked-state.ndjson`, gateway command trace, queue snapshots, notifier audit rows, and provider input events. It emits four verdicts per checkpoint.

**Rationale:** This mirrors UC-03's explicit requirement to correlate all evidence streams and to keep verdicts separate.

## Risks / Trade-offs

- **[Risk]** Existing long-horizon labels may not cover every sample or may use a different schema than UC-03 needs. → Mitigation: audit existing labels first, convert or extend them to full per-sample UC-03 labels, and only create new labels where gaps exist.
- **[Risk]** Long-horizon recordings are from an incomplete UC-02 run and may contain provider-specific failures. → Mitigation: use them only for simulator development and coarse sanity checks, not as qualification ground truth.
- **[Risk]** The existing recording format may not preserve all fields needed for the admission predicate (e.g., gateway execution idle state, queue depth). → Mitigation: live runs will capture gateway state snapshots alongside TUI samples; the simulator will document which fields are replay-only and which require live capture.
- **[Risk]** `--force` behavior may differ between providers or versions, making CAL-01 classifications unstable. → Mitigation: CAL-01 is rerun for every maintained version selected for qualification, and the classification is recorded per provider/version.
- **[Risk]** Human labeling of busy/draft/overlay boundaries is subjective. → Mitigation: label authors are blind to tracker output, and ambiguous spans are labeled `indeterminate` rather than forced into a busy/ready category.

## Migration Plan

No production migration is required. Deployment is:
1. Add the simulator and procedure scripts under a new `scripts/qualification/tui-prompt-admission/` directory.
2. Wire the scripts into the existing Pixi task surface if useful (e.g., `pixi run qualification-uc-03-simulator` and `pixi run qualification-uc-03-live`).
3. Document how to point the simulator at existing long-horizon recordings for development.

Rollback is directory removal; no persisted state or schema changes are involved.

## Open Questions

- Should the simulator be implemented in Python (consistent with the rest of the project) or as an extension of an existing TypeScript/Bun harness used for AG-UI workbench? The project conventions favor Python for new tooling.
- Should UC-03 live sessions reuse the same `projects/` directory layout as the long-horizon run, or a separate `tmp/uc-03-prompt-admission/` root? A separate root reduces collision but duplicates fixture-copy storage.
- The initial fixture set is the nine replay-ready attempts listed in `20260713T095944Z-long-horizon-test-report.md`. If their existing labels are incomplete, how many additional samples need full UC-03 labels before the classification test is representative?
