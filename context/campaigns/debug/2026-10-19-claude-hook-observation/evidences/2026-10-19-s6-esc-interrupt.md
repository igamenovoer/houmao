# Evidence: S6 Esc interrupt (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19. Iteration: [iteration 1](../iterations/2026-10-19-plan-1-hook-capture-matrix.md). Arm: S6 interrupt. Key question: [KQ-2](../key-questions/KQ-2-delivery-semantics.md) P2.4 (does Esc emit `Stop`?).

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s6/run-20261019T134703Z/` (tmux `hookcap-s6-1861744`, 600 pane samples 13:47:03–13:49:18; session torn down by tmux kill, see driver flaw) |
| Tool | `claude` 2.1.303, skip-permissions lane |
| Collector | gen 1, started 13:47:03 UTC / monotonic 3472374.105864 (pair present) |
| Labels | 2 ranges filled (`s6-generation` s000002–s000037, `s6-post-escape` s000038–s000437) |
| Hook stream | 3 events, `events.ndjson` SHA-256 `d92d3a6b…` |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Notable payload fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 13:47:03 | standard |
| 2 | `UserPromptSubmit` | 13:47:03 | `prompt: Write a long essay about recursion.`, `prompt_id 0f91a959-…` |
| 3 | `UserPromptSubmit` | 13:48:42 | `prompt: Write a long essay about recursion./exit` — **driver-composition artifact** (see flaw below), new `prompt_id` |

**Between Esc (13:47:11) and the /exit typing (13:48:41) — 90 seconds — ZERO hook events arrived.** No `Stop`, no `StopFailure`, no `PostToolUseFailure`. This window is the arm's clean evidence.

## Arm Result (P2.4)

- Esc pressed 8 s into visible generation (driver log monotonic 3472382.69, 13:47:11).
- **`Stop` did NOT fire after Escape** (`s6_stop_after_escape: false`, 90 s bounded wait). **P2.4 answered: an interactive Esc abort is hook-silent.** The design contract's Gap-2 carve-out is confirmed live: design 1.2's "no reliable hook for an interactive Esc interrupt; keep the TUI temporal silent-abort detector" holds on 2.1.303.
- Pane settle (s000038, 13:47:11): footer drops `esc to interrupt` immediately; the interrupted prompt is **restored into the composer as an editable draft** — identical to the prior campaign's 2.1.296 silent-abort surface.

## Best-Effort StopFailure Arm

**Declared before the run and unreached:** no safe fault lane exists. Relay/network cuts are out of bounds (host disturbance), and no other credible API-fault lane is available without risking the machine. **P2.5 unreachable; missing control: a safe, session-scoped API-fault injector** (e.g. a proxy-level 500 lane scoped to one request). Recorded as a named gap, per policy — no improvised fault injection was attempted.

## Driver Flaw (declared, fixed)

After the silent abort the composer held the restored draft; `exit_claude` typed `/exit` onto it, submitting the mangled prompt `Write a long essay about recursion./exit` (UPS#3, 13:48:42). The session then stayed alive through the exit attempts and was killed by teardown. The arm's Esc evidence is unaffected (the 90 s silence window precedes the flaw). Fix applied in `run_capture.py`: `exit_claude` now sends `C-u` (clear draft) before typing `/exit`. No retry needed — the predeclared arm data is complete.

## Gate Verdicts

| Gate | Verdict |
| --- | --- |
| G2 (S6 scope) | partial-by-design — `Stop` family deliberately silent on Esc; every event that did occur was captured; `StopFailure`/`PostToolUseFailure` not otherwise exercisable (named) |
| G3 (pairing) | **PASS** — 600 samples + 3-event stream + 2 labels; monotonic/UTC pair present |

## Cleanup

tmux session killed by teardown (declared above); collector SIGTERMed; no stray processes.
