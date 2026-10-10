# Iteration 1: kimi-code 2.1.1 state-matrix capture and detector gap analysis

Status: planned. Question owner: [KQ-1](../key-questions/KQ-1-signal-survival.md). Evidence: none yet (to be written under `../evidences/2026-10-…-state-matrix-*.md` after execution).

## Question

When kimi-code 2.1.1 is driven through its full public state matrix in tmux and recorded at 5 fps, which current-detector signals survive (per KQ-1.1–1.5), and what is the per-state mismatch catalog between the fallback detector's replay output and blind ground truth?

## Frozen Workload

| Component | Value |
| --- | --- |
| Host | This Linux dev host; tmux; no hardware reservation needed |
| Tool under observation | `kimi` 2.1.1 (`kimi --version` → 2.1.1, verified 2026-10-10) |
| Kimi configuration | `KIMI_CODE_HOME=/data/huangzhe/code/houmao/.kimi-code`, OAuth credentials, `default_model = "kimi-code/k3-256k"`, `[secondary_model] default_effort = "max"` (set 2026-10-10) |
| Source ground truth | `extern/orphan/kimi-code` @ 419aced (depth-1 clone, read-only) |
| Coding fixture (existing) | `tests/fixtures/test-projects/boltons` — vendored Boltons library, upstream revision `979fa9b613fa8c0a455ae16ea6f2ec91c11ecafe`, expected pytest collection 437; copied per session and git-baselined (`houmao-baseline` tag) per `src/houmao/demo/shared_tui_tracking_demo_pack/long_horizon/projects.py` (`prepare_boltons_project`). No new mini project is invented for this campaign |
| Prompt source (existing) | Reviewed operation catalog `scripts/demo/shared-tui-tracking-demo-pack/long-horizon/suite.json` (UC-02 suite; kimi cells st-03, st-04, st-05), plus ready-window timing rules from `context/features/2026-07-11-tui-state-tracking-test-plan/usecases/uc-04-verify-kimi-ready-busy-ready-transition.md` and label families from `openspec/specs/kimi-tui-signal-corpus/spec.md` |
| Detector under test | Repo code as of campaign start: `FallbackKimiCodeSignalDetector` (what 2.1.1 resolves to via `shared_tui_tracking/registry.py:122-144`), `activity_window_lines=18`, temporal growth enabled |
| Recorder | `pixi run python -m tools.terminal_record start --mode active --tool kimi --sample-interval-seconds 0.2` (5 fps, user directive); captures escape sequences (`capture-pane -p -e -S -`, service.py:71) |
| Run roots | `tmp/houmao-dev-tui-testing/<run-id>/` per `houmao-dev-tui-testing` artifact contract; campaign `evidences/` holds evidence documents, digests, and run-root references, not bulk copies |
| Driving | Tracker-blind scenario steps only (`send_text`, `send_key`, `wait_seconds`, documented `wait_for_pattern`); no `wait_for_ready`/`wait_for_active` |

## Predeclared Arms

| Arm | Input | Analysis | Output |
| --- | --- | --- | --- |
| A (text scraping, current detector) | Frozen `pane_snapshots.ndjson` (ANSI-stripped view) | `tools.terminal_record analyze --observed-version 2.1.1` replay vs blind labels | Per-state field mismatches; signal survival table |
| B (escape sequences, audit only) | Same frozen snapshots, raw escape-preserving rows | Scripted audit for OSC 133 zone markers and OSC `9;4;3`/`9;4;0` progress sequences per labeled state | Presence/absence table by state (feasibility input for KQ-2) |
| C (event channels) | Not exercised this iteration | — | Deferred to a later iteration (KQ-3) |

One recording feeds Arms A and B; no separate capture is needed because the recorder already preserves escape sequences.

## Scenario (State Matrix)

Test cases are specified in promptfoo-format configs under [2026-10-10-plan-1-state-matrix-capture/](2026-10-10-plan-1-state-matrix-capture/) (`session-1-lifecycle.yaml`, `session-2-operator-surfaces.yaml`, assertion contracts in `asserts/README.md`); see that directory's README for format and ops-vocabulary conventions. Summary below; the YAML files are the predeclared contract.

Two recorded sessions, both running kimi over a fresh copy of the existing Boltons fixture. Session 1 (unattended `--auto`, delegated launch via `houmao-dev-launch-agents use launch-kimi-code`): turn-lifecycle states, reusing the reviewed UC-02 kimi operations. Session 2 (explicit non-`--auto` launch, manual permission mode): operator-interaction states that Never Ask mode suppresses — these need new prompts because the UC-02 catalog and the 0.23.x-era corpus spec (`openspec/specs/kimi-tui-signal-corpus/spec.md`) deliberately exclude confirmation states.

Session 1 operations (prompts adapted from `suite.json` kimi cells st-03/st-05, timing rules from UC-04):

1. Cold start in an untrusted workdir — capture the `Trust this folder?` startup modal, then select "Trust this folder" (documented operator decision; startup-modal coverage).
2. Settled idle — empty editor box, footer, no activity. Hold per UC-04: ready window of ≥2 samples after ≥max(2.0 s, 4× capture interval) idle (at 5 fps: ≥2.0 s).
3. Editing — type without submitting, st-01 style: `{{SAFE}} Read boltons/iterutils.py and tests/test_iterutils.py. Do not edit files. Reply with …` plus a literal suffix, then Backspace over the suffix (draft-editing evidence), hold, then clear.
4. Busy phases and success — submit st-03 op01 verbatim: `{{SAFE}} Use terminal tools now. Run pwd and git status --short. Do not edit files. Reply with the working-directory …`; capture waiting (moon spinner), `Thinking…`, `Working…` phases; settle to a UC-04-sized ready window.
5. Tool + edit workflow — st-03 op02–op04 sequence (read pairwise/windowed, create `tests/test_houmao_long_horizon.py`, run `python -m pytest -q tests/test_houmao_long_horizon.py`); captures sustained tool activity and multi-turn active→ready cycles.
6. Queue / pending input — st-05 style: submit a long prompt (st-05 op04, the ≥35-bullet scan), then while busy type and submit a short follow-up; capture the queue pane hint (`↑ to edit · …`); let it drain; per UC-04 acceptance criterion 7 this leg documents the provider-native queue signature explicitly.
7. Interrupt — st-02/st-05 style: submit a long prompt, wait one confirmed active frame, send `Escape` once; capture `Interrupted by user`; settle past the UC-04 gap rule.
8. Compaction (opportunistic) — `/compact`; capture `Compacting context…` if it renders.
9. Exit — close the tool; capture process/pane loss (st-05 `process_loss` family).

Session 2 operations (manual permission mode, new campaign-designed prompts over the same Boltons copy):

1. Bash approval — submit "Run `git status --short` with your Bash tool, then stop"; capture `▶ Run this command?` with options `1. Approve once` … `4. Reject with feedback`; choose "Reject with feedback" to also capture the inline feedback row.
2. Write approval — submit "Create `docs/houmao-campaign-note.md` with one sentence, then stop"; capture `Write this file?`; reject.
3. Plan review — relaunch with `--plan` (or toggle plan mode); submit "Plan how you would add a `windowed` docstring example to `boltons/iterutils.py`; do not edit files"; capture `Ready to build with this plan?` with `Approve`/`Reject`/`Revise`; choose Revise to capture the revision path.
4. AskUserQuestion — submit "Ask me one multiple-choice question about which boltons module to document, using your question tool"; capture the ` question` dialog with `[N]` options; cancel with Esc.
5. TaskStop and goal-start prompts (opportunistic) — capture if reachable without extra setup.

Retry (`Retrying (N/M) · …`) and subagent/swarm progress rows are opportunistic in both sessions; absence is recorded as missing coverage, not fabricated.

Deviation noted for later spec sync: `openspec/specs/kimi-tui-signal-corpus/spec.md` mandates unattended-only operation with no confirmation states (written for 0.23.x). Session 2 deliberately captures confirmation surfaces; if the campaign promotes fixtures into the maintained corpus, that spec's scenario family list and the unattended-only requirement need revisiting.

## Gates

Pass/fail criteria declared before execution:

- G1 Recording completeness: recorder `manifest.json` has `stopped_at_utc` + `stop_reason`; `pane_snapshots.ndjson` and `input_events.ndjson` exist; `frozen-evidence.json` records SHA-256, byte size, and row counts for every bound file. FAIL → new attempt, preserve this one.
- G2 State coverage: every non-opportunistic state in the scenario has ≥1 contiguous labeled span of ≥2 samples (≥0.4 s at 5 fps). Missing states are declared as coverage gaps in the evidence doc; the iteration may still pass with named gaps.
- G3 Blind-label integrity: `labels.json` complete (every source sample labeled, all eight public fields, no overlaps) and `labels-manifest.json` frozen before any `analyze` or detector inspection. Any breach → labels discarded and re-authored from the raw recording.
- G4 Replay execution: `analyze --observed-version 2.1.1` completes on the source stream and emits `parser_observed.ndjson` + `state_observed.ndjson`; detector identity recorded as `kimi_code` / `fallback`.
- G5 Taint: `run_tainted` and all taint reasons recorded; a tainted run is reported as tainted, never silently treated as clean.
- G6 Unattended discipline: any unexpected confirmation prompt in Session 1 (beyond the planned trust dialog) marks that span failed per the TUI-testing skill rule; the span is excluded from pass claims.

## Measurements and Decision Rules

Measurements:

1. Per-sample agreement on the two user-facing booleans first (directive 2026-10-10): `surface_accepting_input` (ready to enter prompt) and `surface_ready_posture` (accept prompt), grouped by labeled state. Then the remaining six public tracked-state fields as diagnostic detail, grouped the same way.
2. Signal survival table: for every hardcoded assumption in `apps/kimi_code/profile.py` (spinner frames, `ACTIVITY_LABEL_RE`, `APPROVAL_HEADERS`, `APPROVAL_CHOICE_RE`, `PROMPT_TOKEN_RE`, `QUEUE_HINTS`, interrupt strings, footer markers, placeholder detection, provider markers) and `server/tui/parser.py` (startup-modal needles, state-field mapping, hardcoded preset version), record: observed in 2.1.1 surface? detector behaved as designed? citing source sample IDs.
3. Arm B audit: count of samples containing OSC 133 / OSC `9;4` sequences, cross-tabulated by labeled state.

Decision rules (predeclared):

- A signal is **surviving** if it fires correctly on ≥95% of its state's labeled samples and on <5% of other samples.
- A signal is **broken** if it fires on <50% of its state's labeled samples, or fires on ≥5% of samples of an unrelated state.
- Otherwise **degraded**. Unreached states (coverage gap) leave their signals **unresolved**, explicitly.
- Boolean priority: false-ready and sustained false-busy errors on the two user-facing booleans outrank all per-state cosmetic mismatches (per the labeling rubric's admission-safety priority); the iteration's headline metrics are the two boolean agreement rates.
- Interference-only rule (directive 2026-10-10): kimi-internal states beyond the public model (swarm orchestration, retry, compaction) are scored only on whether the public fields stay correct in their presence; failure to name the internal state is never counted as a mismatch.
- Iteration disposition: KQ-1 propositions are marked confirmed/refuted per the survival table; the mismatch catalog is the primary input to the later repair proposal.

## Execution Checklist

- [ ] Freeze this plan, KQ-1 propositions, arms, gates, decision rules (this document is the predeclaration)
- [ ] Create fresh run roots under `tmp/houmao-dev-tui-testing/` (one per session; never reuse a non-empty root)
- [ ] Prepare one Boltons working copy per session from `tests/fixtures/test-projects/boltons` (copy, `houmao-baseline` git baseline, 437-test collection preflight per `prepare_boltons_project`); record source and copy digests
- [ ] Expand the promptfoo-format case specs in `2026-10-10-plan-1-state-matrix-capture/` into runner inputs: `definitions/task.md` and `definitions/scenario.json` per session (catalog_operation refs resolved verbatim from `suite.json`, `{{SAFE}}` expanded), plus the `drivers/tui_driver.py` provider and the `asserts/*.py` scripts per `asserts/README.md` contracts
- [ ] Delegate Session 1 launch: `houmao-dev-launch-agents use launch-kimi-code` (unattended `--auto`, fresh untrusted Boltons workdir); verify live tmux session + pane
- [ ] Start 5 fps active recording on the delegated pane before the first operation
- [ ] Drive Session 1 operations 1–9 with tracker-blind steps; log operation timings
- [ ] Stop recording; verify G1; freeze digests into `capture/frozen-evidence.json`
- [ ] Repeat launch + record + drive + freeze for Session 2 operations 1–5 (manual mode, trusted workdir)
- [ ] Author blind ground truth from raw recordings only (G3); freeze `labels-manifest.json`
- [ ] Run Arm A replay (`analyze --observed-version 2.1.1`) on both sessions; verify G4
- [ ] Run Arm B escape-sequence audit script over both snapshot streams
- [ ] Score measurements against decision rules; fill the signal survival table
- [ ] Write evidence docs under `../evidences/` (one per session), update KQ-1 answer and `../debug-intent.md` status
- [ ] Clean up provider-credential-adjacent temp material per the artifact contract; record cleanup status

## Result

To be added after completion. Corrections to this plan, if any, will be appended with dates; the original text stays.
