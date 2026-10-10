# Evidence: Session 1 — Turn-Lifecycle State Matrix (kimi-code 2.1.1, `--auto`)

Date: 2026-10-10. Iteration: [plan 1](../iterations/2026-10-10-plan-1-state-matrix-capture.md). Key question: [KQ-1](../key-questions/KQ-1-signal-survival.md).

## Run Identity

| Field | Value |
| --- | --- |
| Run root | `tmp/houmao-dev-tui-testing/2026-10-10-kimi-2.1.1-session1-lifecycle/` |
| Tool | kimi 2.1.1 (`Never Ask` posture, `--auto`), tmux pane 220x50 |
| Recorder | `tools.terminal_record`, active mode, 0.2 s interval (5 fps), 1909 samples over 430.6 s |
| Recording SHA-256 | `2e835b00b9f5b41a9624a0d0dc8745cfcd9ff7afa8a501c028fb7501abb8fa69` (`pane_snapshots.ndjson`) |
| Labels | 23 ranges, complete coverage, frozen 2026-10-10T14:04:47Z, `labels_sha256=93c225b4...` |
| Fixture | Boltons copy, baseline tag `houmao-baseline`, collection preflight 437 passed |
| Spec | `iterations/2026-10-10-plan-1-state-matrix-capture/session-1-lifecycle.yaml` (8 cases, 38 ops, 0 drive failures) |

## Gates

G1 recording integrity: pass (after re-freeze; see deviations). G2 coverage: pass with two declared gaps (`compaction`, `tui_down`). G3 blind-label integrity: pass. G4 replay execution: pass for baseline (`kimi_code` / `>=0.34.0`) and candidate (`kimi_code` / `2.1.x-candidate`). G5 taint: none recorded. G6 unattended discipline: pass; the trust modal was the planned, predeclared intervention.

## What the Session Captured

The long scan turn (st-05 op04, 35 bullets) did not finish within the 120 s drain window; it ran 137 s until the Escape leg interrupted it. The queued follow-up and the interrupt-target prompt drained through the provider queue. `/compact` submitted while streaming was rejected with `Error: Cannot /compact while streaming — press Esc or Ctrl-C first.` (visible from s001867). The exit leg's double Ctrl-C found the TUI busy: busy Ctrl-C interrupts the turn instead of arming exit, so kimi stayed alive through recording end. `tui_down` and true `compaction` rendering are declared coverage gaps. A subagent surface was captured incidentally: `⠦ Explore Agent Running (…)` rows during the long scan.

## Arm A: Detector Replay vs Blind Ground Truth

Per-sample agreement over 1909 samples (candidate = monkey-patched 2.1.x detector, `campaign_lib.patches`):

| Field | Baseline `>=0.34.0` | Candidate v3 |
| --- | --- | --- |
| surface_accepting_input (ready to enter prompt) | 0.520 | 0.992 |
| surface_ready_posture (accept prompt) | 0.919 | 0.992 |
| turn_phase | 0.927 | 1.000 |
| surface_editing_input | 0.941 | 0.941 |
| surface_pending_input | 0.983 | 0.983 |
| last_turn_result | 0.974 | 0.989 |
| last_turn_source | 0.963 | 0.979 |
| diagnostics_availability | 1.000 | 1.000 |
| false_ready samples | 139 | 0 |
| false_busy samples | 0 | 0 |

Baseline false-ready spans (139 samples): braille-phase busy spans (`Thinking…`/`Working…` are invisible to the dead label regex, so the surface reads idle-ready mid-turn).

Candidate v3 residual mismatches (none admission-critical): draft-while-busy underdetection on `editing_busy` (94 samples, `surface_editing_input` no vs yes); startup-modal surfaces report `unknown` where GT says `no` (15 samples x 4 fields; safe direction); queue-hint scrollback linger past drain (16 samples); boundary-quantized `last_turn_*` spans (30 samples); interrupted attribution suppressed while a follow-up turn is active (11 samples, deliberate trade-off, see Findings).

## Signal Survival (Session 1 Families)

| Signal | Fired / expected | False fires | Verdict |
| --- | --- | --- | --- |
| `PROMPT_TOKEN_RE` editor detection | 1894/1894 | 0 | surviving |
| trust modal needle (`Trust this folder?`) | 15/15 | 0 | surviving (uncovered by parser) |
| queue hint (`↑ to edit · …`) | 671/671 | 16 | degraded (scrollback linger) |
| interrupt strings | 11/11 | 134 | degraded (scrollback persistence) |
| legacy activity label `\b(working|thinking)\.\.\.` | 0/1041 | 0 | broken |
| 2.1 activity labels (`Thinking…`/`Working…`/Retry/Compacting/Orchestrating) | 210/1041 | 0 | phase-scoped (braille phases only; 210/665 of braille samples) |
| moon spinner frames | 831/1041 | 0 | phase-scoped |
| braille spinner frames | 665/1041 | 0 | phase-scoped |
| spinner union (moon OR braille at live edge) | 1041/1041 | 0 | complete busy coverage |
| `\x1b[2m` placeholder escape (raw) | 1821/1909 samples carry it | n/a | pervasive as dim styling; the placeholder branch is scoped to the prompt line, which never carries it: dead but inert |

Unlabeled braille lines (455 samples) are subagent rows: `⠦ Explore Agent Running (…)`. The candidate label set should add `Agent Running`.

## Arm B: Escape-Sequence Audit

Zero OSC 133 and zero OSC `9;4` sequences in all 1909 escape-preserving samples (SGR present in every sample as control). Semantic escape channels do not survive `tmux capture-pane -p -e`.

## Findings Feeding the Repair Proposal

1. Busy-phase visibility requires the spinner union, not the label regex; the 0.11-era label regex is dead in 2.1.1 (`Thinking…`/`Working…`, U+2026, capitalized).
2. `Interrupted by user` persists in scrollback; the reducer prioritizes `interrupted` over `active_evidence` (`session.py:351`), so a resumed turn reads ready forever unless the detector suppresses stale notices when activity is present. Candidate does this at the detector level.
3. kimi auto-approves Write/Edit inside a git-worktree workspace (`git-cwd-write-approve` policy); approval captures for Write need out-of-workspace paths.
4. Busy Ctrl-C interrupts; it does not arm exit. Exit testing needs a settled idle surface first.

## Deviations

- Attempt 001 of session 1 is the only attempt; the exit and compaction legs are coverage gaps declared above, not retried (their blockers are themselves findings 3-4).
- `session.cast` digests were re-frozen after the recorder's asciinema attach outlived controller stop; `pane_snapshots.ndjson` digests are unchanged and labels remain validly bound. The runner now waits for recorder-session teardown before freezing.
- The campaign runtime observer under-reported `supported_process_alive` (pane-pid children only); `pane_pid_alive` is the liveness evidence for this run. Fixed in tooling for later iterations.
