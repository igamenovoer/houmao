# Evidence: T1 slow lifecycle hooks — awaited delays (kimi 2.2.0)

Date: 2026-10-20. Iteration: [iteration 1](../iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md). Arm: T1. Key questions: [KQ-3](../key-questions/KQ-3-delivery-semantics.md).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/kimi-hook-capture/t1/run-20261020T135150Z/` (tmux `kimihook-t1-3952334`, pane `%246`) |
| Tool | kimi 2.2.0, `--auto`; `SessionStart` and `SessionEnd` hook commands prefixed with `sleep 3; ` |
| Baseline | amended-gate S0 `tmp/kimi-hook-capture/s0/run-20261020T133111Z/` (ready 3.219 s; SS 0.238 s after prompt; exit 0.968 s) |
| Collector | gen 1, port 45517, 5 accepted events |
| Recording | 63 samples; labels `t1-ready-delay`, `t1-exit-delay` |
| Model cost | **one short OK turn** (required to create the session in the TUI lane; no longer zero-cost) |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Delay vs S0 |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:51:56.855 | **3.245 s after prompt** vs 0.238 s = **+3.007 s** |
| 2 | `UserPromptSubmit` | 13:51:56.983 | 0.128 s after SS |
| 3 | `TurnStarted` | 13:51:57.054 | — |
| 4 | `Stop` | 13:52:00.808 | prompt→Stop 7.199 s (includes the 3 s SS wait) |
| 5 | `SessionEnd` | 13:52:04.776 | 3.504 s after exit start |

## Measurements

| Measure | T1 | S0 baseline | Delta |
| --- | --- | --- | --- |
| Ready composer | 2.877 s | 3.219 s | **-0.342 s** (no delay) |
| `SessionStart` after prompt | 3.245 s | 0.238 s | **+3.007 s** |
| Exit (`/exit` → tmux gone) | 3.984 s | 0.968 s | **+3.016 s** |
| `SessionEnd` after exit start | 3.504 s | 0.968 s class (immediate) | ~+3 s |

The slow `SessionStart` hook delays **session creation**, not the ready composer: the TUI reaches the composer before any session exists. The slow `SessionEnd` hook delays process exit by the full 3 s. No timeout kill occurred (3 s < the 5 s hook timeout); the SIGTERM/SIGKILL path was not exercised.

## Verdict

**PASS for the awaited lifecycle.** Both delays are quantitatively the injected 3 s. The predeclared "time-to-ready delayed by ~3 s" is **refuted**: ready is unaffected because session creation is lazy. The corrected measurement is prompt→`SessionStart` (+3.007 s) and exit (+3.016 s).

## Harness Corrections (2026-10-20)

- T1 now sends one OK prompt to create the session (the amended-gate consequence); the arm is no longer zero-model-cost. Recorded here and in the iteration plan.
- The baseline selector now requires an amended-gate S0 run (`extra.g1.passed`) and reads its prompt→SS delay.

## Cleanup

`kimihook-t1-3952334` exited via `/exit`; collector stopped. Run root retained under `tmp/kimi-hook-capture/t1/`.
