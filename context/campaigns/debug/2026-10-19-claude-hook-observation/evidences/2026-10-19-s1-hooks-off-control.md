# Evidence: S1 hooks-off control (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S1-control (P2.3 matched-prompt hooks-off control). Key question: [KQ-2](../key-questions/KQ-2-delivery-semantics.md) P2.3 (hook-channel wall-time cost).

## Run Identity

| Component | Value |
| --- | --- |
| Run root (primary) | `tmp/hook-capture/s1-control/run-20261019T140530Z/` (tmux `hookcap-s1-control-1903762`, 77 pane samples 14:05:30–14:05:48) |
| First attempt | `run-20261019T140227Z/` — discarded: `wait_for_answer` refreshed its stability clock against the original snapshot on every poll, so it could only return at the 150 s timeout (harness bug, fixed; the killed run's tmux session was cleaned manually). |
| Launch | `claude-deepseek` with **no `--settings`** (hooks off); no observer settings generated; collector still started (uniform teardown) and recorded **zero events** — hooks-off confirmed |
| Labels | 2 ranges filled (`s1c-turn-1` s000003–s000038, `s1c-turn-2` s000039–s000075) |
| Timing evidence | `pane_snapshots.ndjson` SHA-256 `b968ab18…`, `driver-input-events.ndjson` `2f7479e4…` |

## P2.3 Measurement (hooks ON: S1 run-20261019T131758Z; hooks OFF: this run)

| Turn | Prompt | S1 (hooks on): UPS → Stop | Control (hooks off): submit → answer visible | Control: submit → settled |
| --- | --- | --- | --- | --- |
| 1 | `Reply with exactly: OK` | 13:17:58 → 13:18:00 (**2.0 s**) | 14:05:31 → s000009 14:05:32 (**≈1.3 s**) | 8.184 s (incl. 6 s stability dwell) |
| 2 | `What is 2+2? Reply with just the number.` | 13:18:01 → 13:18:02 (**1.0 s**) | 14:05:39 → ~14:05:40 (**≈1.5 s**) | 8.184 s (incl. 6 s stability dwell) |

**P2.3 verdict: no measurable hook overhead at this granularity.** Both lanes answer these trivial turns in 1–2 s; the difference between hooks-on `Stop` delivery and hooks-off visible-answer is sub-second and inside the control's measurement floor (1 s poll interval + 6 s stability dwell in the settle heuristic; the pane-frame method of the analysis stage can tighten it). Note the comparison is between the authoritative hook timestamp (S1) and a visible-surface heuristic (control) — the paired monotonic/UTC bases exist in both runs' `channel.json`/`manifest.json` for a frame-exact analysis.

## Run Notes

- Model gate passed (`deepseek-flash[1m]` banner); no trust dialog (consistent with all prior arms).
- Provider behaved normally; both answers correct (`OK`, `4`).
- No hook events of any kind (empty `events.ndjson`, collector counts all zero) — the control is clean.

## Harness Fix

`PaneDriver.wait_for_answer` now tracks the previous pane digest and only restarts the stability clock when the pane actually mutates (previously it compared only against the pre-submit snapshot, so any post-answer frame counted as "changing" forever and the wait could only end at timeout).

## Gate Verdicts

| Gate | Verdict |
| --- | --- |
| G3 (pairing) | partial by design — pane recording + labels + timings present; hook stream intentionally absent (hooks-off control). Gap recorded here, not ignored. |

## Cleanup

tmux killed by teardown; collector SIGTERMed; no leftovers.
