# Evidence: session 1 lifecycle capture (codex 0.162.1)

Date: 2026-10-12. Iteration: [plan 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md). Run root: `tmp/houmao-dev-tui-testing/2026-10-12-codex-session1-lifecycle-002` (attempt 002; attempt 001 preserved unfrozen at `2026-10-12-codex-session1-lifecycle`, failed on the unhandled trust screen — see plan Corrections).

## Environment and Identity

| Component | Value |
| --- | --- |
| Host | Linux dev host, tmux, pane 220x50 |
| Tool | `codex` codex-cli 0.162.1 (`codex --version` verified) |
| Credential lane | `CODEX_HOME=$PWD/.codex` (ChatGPT login; `codex login status` exit 0) |
| Model / effort | `gpt-6.1-sol` / `medium` (campaign default, user directive) |
| Posture | unattended: `--dangerously-bypass-approvals-and-sandbox -m gpt-6.1-sol -c model_reasoning_effort="medium" -C <workdir>` |
| Workdir | fresh Boltons copy (`tests/fixtures/test-projects/boltons`, `houmao-baseline` tag, 437-test preflight), untrusted git-repo dir |
| Recorder | `tools.terminal_record start --mode active --tool codex --sample-interval-seconds 0.2` (5 fps) |
| Source reference | `extern/orphan/codex` @ 322bbf4 (read-only) |

Commands: `pixi run python scripts/explore/codex-tui-parsing/run_session.py --spec …/session-1-lifecycle.yaml --run-root tmp/houmao-dev-tui-testing/2026-10-12-codex-session1-lifecycle-002`, then `author_labels.py --session session1`, then `run_analysis.py --run-root … [--with-candidate]`, then `evaluate.py …`.

## Frozen Evidence

| File | SHA-256 (prefix) | Rows |
| --- | --- | --- |
| `capture/recording/pane_snapshots.ndjson` | `55844e2e734a0219` | 1907 samples |
| `capture/recording/input_events.ndjson` | `3a19681eb19b` | 77 events |
| `labels/labels.json` | `6fac0c847f73bb3b` | 26 label spans, complete coverage |
| `capture/frozen-evidence.json` | per-file digests | 10 files |

Recording window 06:08:28–06:15:40 UTC. `run_tainted=false`. Recorder `stop_reason` reads `failed: Failed to list tmux clients … can't find session: $63`: the TUI quit itself at 432.5 s (exit leg's second C-c), so the target session was gone at stop; all bound files are complete and digests verified. This is the known recorder teardown quirk, not data loss.

Blind-label ordering: labels frozen 06:27:36 UTC; first replay 06:33 UTC (G3 holds). Tooling correction recorded: this run's `runtime_observations.ndjson` sampled process liveness with the kimi marker (copied default); liveness is instead established by snapshot continuity and drive events. Fixed for later runs in `campaign_lib/runtime_observer.py`.

## Captured State Coverage (G2)

| Family | Span samples | Notes |
| --- | --- | --- |
| startup (splash + provisional composer) | 4 | `› Ask Codex to do anything` visible before first paint completes; no footer model line yet |
| startup_modal (Trust this folder?) | 46 | `› 1. Trust and continue / 2. Quit / enter continue · esc quit`; renders even under bypass for untrusted git-repo workdirs |
| editing | 26 | draft/suffix/erase; composer render-state flicker (dim vs plain) on 1 sample |
| active (5 turns) | 315 | `• Working (Ns • esc to interrupt)` row + footer braille spinner; row blinks off 1-2 samples mid-turn; row hides entirely while the final answer streams |
| queue_pending | 146 | follow-up submitted mid-busy renders as `› <text>` above the status row, then collapses to `+ N lines (^t to expand)`; codex merges it into the running turn (steer; single `Worked for 41s` ends `Q1-DRAIN`) |
| interrupted | 27 | `■ Conversation interrupted - use /feedback if something went wrong`; status row gone; composer placeholder back |
| compaction | 88 | `• Compacting context (Ns • esc to interrupt)` + `└ Making room to continue.` |
| ready | 1254 | incl. per-turn `Worked for Ns • HH:MM` docks |
| tui_down | 1 | `To continue this session, run: codex resume <id>` after double C-c; below min span (partial coverage, declared gap) |

## Detector Scores (per-sample agreement vs blind labels; the two booleans first)

| Arm | accepting_input | ready_posture | false-ready | false-busy | Notes |
| --- | --- | --- | --- | --- | --- |
| A1 fallback (today's 0.162.1 resolution) | 0.973 | 0.887 | 147 | 68 | no modal blocking, no interrupt/compaction/queue semantics |
| A2 0.144.x override | 0.973 | 0.873 | 242 | 0 | render-state prompt classification works; modal misses dominate |
| Candidate 0.162.x (monkey patch) | **0.9995** | **0.9984** | **2** | **1** | remaining boolean misses are 3 seam samples (see below) |

Candidate residual mismatches: compaction 88/88 (only `last_turn_result` carry: GT keeps `interrupted` from the pre-compaction interrupt; reducer resets to `none` when compaction activity reads as a new turn — reducer-level nuance, booleans correct); queue_pending 72/146 (`surface_pending_input` only detectable while the queued echo is visible, samples 277.3–283.2 s; the collapsed `+ N lines` window has no queue signal — documented single-snapshot limitation); ready 14/1254 (turn-seam samples where `last_turn_result` resets one sample early); tui_down 1/1 (accept=unknown vs no; single sample).

Boolean seam misses (candidate, session 1): `s000051` trust-confirm transition (footer not yet painted — startup rule fires one sample long); `s001341`, `s001355` (1-sample growth pauses mid answer-stream).

## Arm B (escape audit)

Zero OSC sequences in 1907 escape-preserving samples: `osc_133=0`, `osc_9_4=0`, `osc_any=0`; SGR present in abundance (281 066). Codex escape channels do not survive tmux capture (same negative as kimi's KQ-2).

## Arm C (rollout event-store inventory)

1 rollout file (`rollout-2026-10-12T14-08-39-….jsonl`, hashed in `comparison/event-inventory.json`). Payload types: `task_started` ×7, `task_complete` ×5, `turn_aborted` ×2, `item_completed` ×30, `message` ×24, `custom_tool_call(+output)` ×8+8, `token_count` ×15, `thread_settings_applied` ×5, `reasoning` ×1. Timestamp alignment to labels: `task_started` 22.2 s vs drive submit 22.05 s / status row 22.44 s; `task_complete` 37.8 s vs `Worked for` dock 37.91 s; turn 2 started 70.4 s (op 70.37 s), completed 85.4 s (dock 85.51 s). Sub-second alignment throughout — the rollout stream is a viable offline oracle for turn boundaries.
