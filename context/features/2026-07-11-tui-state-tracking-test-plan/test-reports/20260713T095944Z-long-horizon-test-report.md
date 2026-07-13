# UC-02 Long-Horizon TUI State-Tracking Test Report

Date: 2026-07-13

Run root: `tmp/tui-state-tracking-long-horizon/2026-07-13-all-providers`

## Outcome

The full 12-cell matrix did not qualify. Nine cells completed native TUI capture, blind labeling, and all ten replay schedules. None matched the frozen manual timeline exactly on the canonical 20 Hz stream. Four of the nine recorded cells passed every fixed-rate safety oracle at 10 Hz, 5 Hz, and 2 Hz; five did not.

Three cells could not produce a complete qualifying recording. Claude ST04 and Codex ST02 could not hold the required short-lived active surface long enough for their next scripted action. Kimi ST05 failed preflight because Kimi Code 0.23.6 binds Ctrl+D to delete-forward rather than empty-editor exit, so its required exit/restart procedure is unsupported.

The run produced valid tracker evidence for 181 of 242 planned operations. Eight of the nine complete cells passed their independent engineering contract. Codex ST05 completed all 21 TUI operations and all replay schedules, but failed engineering because it created `houmao_artifactsst05.txt` instead of `houmao_artifacts/st05.txt`.

## Environment and Protocol

- Claude Code: 2.1.207, launched through the Claude-Kimi unattended profile.
- Codex: 0.144.1 with `gpt-5.6-sol medium`, using HTTP/HTTPS/ALL proxy `127.0.0.1:7990`.
- Kimi Code: 0.23.6 with `kimi-for-coding-highspeed`.
- Project fixture: the vendored Boltons checkout under `tests/fixtures/test-projects/boltons`.
- Capture cadence: 20 Hz native pane snapshots plus asciicast v3.
- Blind review: tracker-free 5 Hz MP4 generated before labels were completed.
- Replay schedules: canonical 20 Hz; 10 Hz, 5 Hz, and 2 Hz at zero and half-phase offsets; deterministic jittered, gapped, and bursty schedules.
- Operator mode: unattended for every provider. No Gemini CLI artifact was created.

## Matrix Results

| Cell | Complete operations | Engineering | Canonical tracker | Fixed-rate safety | Canonical mismatches | Result |
| --- | ---: | --- | --- | --- | ---: | --- |
| Claude ST01 | 20/20 | pass | fail | pass | 609/652 | tracker not qualified |
| Claude ST02 | 20/20 | pass | fail | pass | 2297/2310 | tracker not qualified |
| Claude ST03 | 20/20 | pass | fail | pass | 3285/3371 | tracker not qualified |
| Claude ST04 | 16/20 | not reached | not run | not run | n/a | `stimulus_too_short` |
| Codex ST01 | 20/20 | pass | fail | fail | 67/563 | tracker not qualified |
| Codex ST02 | 3/20 | not reached | not run | not run | n/a | `stimulus_too_short` |
| Codex ST03 | 20/20 | pass | fail | fail | 95/2032 | tracker not qualified |
| Codex ST04 | 20/20 | pass | fail | fail | 46/230 | tracker not qualified |
| Codex ST05 | 21/21 | fail: `unsafe_mutation_scope` | fail | fail | 358/1234 | engineering and tracker failed |
| Kimi ST03 | 20/20 | pass | fail | pass | 748/753 | tracker not qualified |
| Kimi ST04 | 20/20 | pass | fail | fail | 50/57 | tracker not qualified |
| Kimi ST05 | 0/21 | not reached | not run | not run | n/a | `unsupported_exit_surface` |

“Fixed-rate safety” means all six 10 Hz, 5 Hz, and 2 Hz phase variants passed the safety oracles. It does not mean the reported states matched the manual labels.

## State-Tracking Findings

### Claude

Claude preserved transition order and passed every delayed-cadence safety oracle in ST01, ST02, and ST03. The dominant strict mismatch was conservative `surface_ready_posture=unknown` during visibly active periods that the operator labeled `no`: 609 samples in ST01, 2,294 in ST02, and 3,285 in ST03. This is meaningful but less dangerous than reporting a false ready posture.

ST02 also exposed a downstream-relevant editing gap. After the scripted interruption failed to stop the original long task, the recovery prompt remained visibly queued in the Claude editor. The operator labeled 1,358 samples as editing while the tracker reported non-editing. Three samples also disagreed on ready versus active. The recording preserves the `/ork` command corruption and the prolonged queued-draft interval.

### Codex

Codex produced the closest strict timelines, but every recorded Codex cell failed at least one fixed-rate safety schedule. The dominant safety failure was `no_terminal_fabrication`; ST05 additionally failed `liveness_loss_propagates` in all ten schedules and `active_precedes_terminal` in four schedules.

ST03 missed 19 manually active samples as ready. ST05 missed 313 manually active samples as ready. Around exit/restart, ST05 failed to report six manually labeled `tui_down` samples and reported `tui_down` once after the native TUI had returned. These liveness errors matter to controllers that use readiness to decide when to send the next operation.

The first Codex ST05 rerun also demonstrated a harness defect: the provider had been launched as the pane process, so Ctrl+D killed the pane and left no shell for restart. The final attempt used a retained owning shell and successfully captured the intended TUI-down and restart sequence.

### Kimi

Kimi ST03 showed a systematic posture inversion against the native review: 640 samples labeled active were reported ready, and 108 samples labeled ready were reported active. The same 748 of 753 samples disagreed on accepting-input and ready-posture fields. Fixed-rate safety oracles still passed because they do not currently reject sustained active/ready inversion; the oracle set is therefore too weak to protect downstream schedulers from this failure mode.

Kimi ST04 covered the `/model` overlay and recovery controls. The operator kept the overlay interval unknown rather than inventing readiness. The tracker disagreed on 50 of 57 samples and failed all ten schedules, primarily through false terminal outcomes. Kimi ST05 remains untestable under the reviewed procedure because the current CLI has no Ctrl+D empty-editor exit surface.

## Ground-Truth Audit Limitation

Manual label completion occurred before any replay artifact existed, and each recording and label digest was frozen before replay. A post-replay audit nevertheless found a defect in the operator drafting rubric for Codex: its initial active check matched the historical UI phrase “press esc to interrupt and send immediately,” not only the live `Working (... esc to interrupt)` row. The frozen labels were not changed after tracker output became visible. The operator rubric artifact now uses the bounded live-row pattern for future runs.

This defect can overstate some Codex active-versus-ready and terminal mismatch counts. Treat the Codex strict counts as exploratory rather than release-certifying until a fresh attempt receives independently reviewed labels. It does not explain the directly observed ST05 liveness window, the Claude ready-posture behavior, or the Kimi active/ready inversion.

## Harness Findings Fixed During the Run

- Added a one-second Codex delay between literal text delivery and Enter to clear Codex’s 120 ms paste-enter suppression window.
- Required Codex’s native `esc to interrupt` live row for active-gate detection instead of treating a nonempty editor as active.
- Retained a shell beneath provider TUIs so exit/restart operations have a real restart surface.
- Kept engineering and tracker verdicts independent, allowing a complete recording to reach blind labeling when the agent fails its file-edit contract.
- Sampled blind-review video at the requested lower cadence and removed staging PNGs after encoding.
- Fixed aggregate reporting to count `PlannedCell.operations` rather than reference a nonexistent property.

One invalid Kimi ST04 attempt resulted from running two recorders concurrently: both used the internal tmux name `HMREC-terminal-record`. The collision was preserved as invalid orchestration evidence, and the cell was rerun sequentially to produce the valid attempt reported above.

## Preserved Evidence

- 24 asciicast v3 files are preserved across valid and failed attempts, totaling 9,787,366 bytes.
- 25 pane-snapshot streams are preserved, totaling 381,291,566 bytes.
- Nine tracker-free blind-review MP4 files are preserved, one for each complete replayed cell.
- Each replayed attempt contains the frozen labels, ten source mappings, ground-truth timelines, tracker timelines, comparison reports, safety-oracle results, and failure slices.
- The generated machine report is `aggregate/qualification-report.json`; the human-readable generated summary is `aggregate/qualification-report.md`.
- The tracker-free drafting rubric and command outputs are under `operator/`.

Transient provider homes and definition workdirs were removed after capture. A final scan found no credential-named files, `sk-` token candidates, `ANTHROPIC_API_KEY` assignments, or `OPENAI_API_KEY` assignments in the preserved run tree.

## Replay-Ready Recordings

Nine recordings are immediately usable for deterministic tracker replay. Each has a complete 20 Hz pane-snapshot stream, authoritative managed-input history, runtime observations, a frozen recording digest, complete blind manual labels, and all required replay artifacts.

| Provider | Cell | Attempt | Replay readiness |
| --- | --- | --- | --- |
| Claude | ST01 | `a007` | ready |
| Claude | ST02 | `a001` | ready |
| Claude | ST03 | `a001` | ready |
| Codex | ST01 | `a004` | ready |
| Codex | ST03 | `a004` | ready |
| Codex | ST04 | `a002` | ready |
| Codex | ST05 | `a004` | ready; engineering verdict failed independently |
| Kimi | ST03 | `a008` | ready |
| Kimi | ST04 | `a003` | ready |

This gives three replay-ready Claude recordings, four Codex recordings, and two Kimi recordings.

The other 15 preserved casts are diagnostic-only. Their attempts failed, were aborted, or were invalidated before complete blind labels and replay admission. They can support forensic analysis and future focused regression authoring, but they must not be treated as qualified replay fixtures without separate completeness validation and labeling. One invalid Kimi ST04 recorder-collision attempt has a partial snapshot stream but no cast and is also excluded.

## Implementation Verification

- `pixi run pytest -q tests/unit/demo/shared_tui_tracking_demo_pack tests/unit/terminal_record tests/unit/shared_tui_tracking tests/unit/agents/test_launch_policy.py tests/unit/agents/test_native_launch_resolver.py tests/unit/agents/realm_controller/test_tmux_control_input.py`: 257 passed.
- `pixi run python -m pytest -q -n 16 tests/unit/agents tests/unit/cao`: 844 passed.
- `pixi run lint`: passed.
- `pixi run format`: passed; a final check reported no formatting drift.
- `pixi run typecheck`: seven pre-existing Literal-narrowing errors remain in `managed_launch_force.py`, `managed_prompt_header.py`, and `launch_policy/engine.py`; none of those files changed in this work.
- `pixi run test`: 2,310 passed and 13 skipped; two unrelated baseline tests failed because `extern/orphan/plotly.js/dist/plot-schema.json` is absent and one Click assertion expects the older text `No such option '--endpoint'` instead of current `No such option: --endpoint`.
- The vendored Boltons fixture has no Git changes. Generated caches and all agent edits stayed in run-local project copies.

## Recommended Next Run

Fix the Kimi 0.23.6 detector profile, add a safety oracle that rejects sustained active/ready inversion, and independently relabel fresh Codex attempts with the corrected live-edge rubric. Revise ST04 and ST02 stimuli so the required active state is observable without depending on a long model response. Replace Kimi ST05’s unsupported Ctrl+D procedure with a current native exit surface only after the use case is explicitly revised.
