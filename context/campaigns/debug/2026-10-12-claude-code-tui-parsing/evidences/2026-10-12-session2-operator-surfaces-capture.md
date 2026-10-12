# Evidence: Session 2 operator-surfaces captures (claude 2.1.296, OpenLux relay, sonnet)

Date: 2026-10-12. Iteration: [iteration 1](../iterations/2026-10-12-plan-1-state-matrix-capture.md). Key questions: [KQ-1](../key-questions/KQ-1-signal-survival.md) (P1.8), [KQ-2](../key-questions/KQ-2-transcript-oracle.md).

Session 2 ran twice. Attempt 001 (run root `2026-10-12-claude-session2-operator-surfaces`, 1864 samples, snapshot SHA-256 `cd1ebd7b329f0b70…`, labels `7873441e9331d6ee…`) discovered that 2.1.296's default permission mode auto-approves the bait legs; attempt 002 (run root `…-002`, 1104 samples, snapshot SHA-256 `d4ab23e91832d3fd…`, labels `82e1e5e4e580132d…`) added a project `.claude/settings.json` ask-rule overlay to force the dialogs. Both are frozen and labeled; 002 is the approval evidence, 001 is the auto-mode evidence. `run_tainted=false` on both.

## Finding: Auto Mode Is the Default and Suppresses Classic Approvals

Attempt 001 startup renders a banner block: "Auto mode is now Claude Code's default permission mode. Auto mode lets Claude handle permission prompts automatically… runs the ones it assesses as lower-risk, and blocks the rest." Footer: `⏵⏵ auto mode on (shift+tab to cycle) · ← for agents`. Under auto mode:

- The `touch /tmp/…` shell bait ran with no dialog (`Ran 1 shell command`, dock `✻ Churned for 18s · done`).
- The `Write` bait was auto-allowed (`⎿ Allowed by auto mode classifier`) — the turn then stalled ~180 s on relay latency and was interrupted by the runner's recovery Esc (`⎿ Interrupted · What should Claude do instead?`, no verb dock).
- Binary audit: the mode-cycle labels in 2.1.296 are only `auto mode on`, `plan mode on`, `bypass permissions on` — there is no ask-everything mode to switch into.

Deterministic approval forcing (validated by a post-freeze live probe, then attempt 002): project `.claude/settings.json` with `{"permissions": {"ask": ["Bash(touch:*)", "Write"]}}` overrides auto mode per rule and renders the classic dialog.

## Attempt 002 Approval Surfaces (as captured)

| Span | Samples | Surface |
| --- | --- | --- |
| startup_modal | s000001–s000051 | same trust dialog as session 1 |
| command approval | s000108–s000121 | Boxed panel (`╌` rules): `Bash command` / `Run shell command` / the command, then `Ask rule Bash(touch:*) overrides auto mode for this command.` + `/permissions to let auto mode decide`, question `Do you want to proceed?`, options `❯ 1. Yes` / `2. No`, footer `Esc to cancel · Tab to amend` |
| post-denial | s000122+ | `⎿ Interrupted · What should Claude do instead?` **and** a verb dock `✻ Baked for 9s · done 10:19 PM` — denial docks a completion marker, unlike codex |
| edit approval | s000226–s000990 | Boxed `Create file` panel with content preview; question **`Do you want to create houmao-campaign-note.md?`** (not `Do you want to proceed?`); options `❯ 1. Yes` / `2. Yes, and always allow access to <dir> for this session (shift+tab)` / `3. No`; held 180 s through the driver's wrong-needle wait, dismissed by the runner recovery Esc at 223.02 s |
| post-denial | s000991+ | `⎿ User rejected write to ../../../../../docs/houmao-campaign-note.md` + dock `✻ Cogitated for 8s · done 10:22 PM` |
| model_picker | s001071–s001084 | same `Select model` picker as session 1 |

Note: in both approval legs the agent targeted `docs/houmao-campaign-note.md` relative to the outer repository root, not the Boltons workdir (002 dialog targeted `/data/huangzhe/code/houmao/docs/…`; the denial prevented any write; 001's write landed in a mangled flattened path under `tmp/`, cleaned up post-run). Recorded as a fixture-prompting quirk, not a detector issue.

## Arm A: Detector Replay vs Blind Labels (002, 1104 samples)

| Field | A1 (2.1.x) | A2 (fallback) |
| --- | --- | --- |
| surface_accepting_input | **0.2355** | **0.2355** |
| surface_ready_posture | **0.1667** | **0.1667** |
| surface_editing_input | 0.2346 | 0.2328 |
| surface_pending_input | 0.1703 | 0.1703 |
| turn_phase | 0.2364 | 0.2364 |
| last_turn_result | 0.2219 | 0.2219 |
| diagnostics_availability | 1.0 | 1.0 |

843 false-ready samples (both arms): trust modal (51) + command dialog (14) + edit-dialog dwell (765) + picker (13). Every modal reads as a usable composer because the dialogs render `❯ 1. Yes`-style option lines that satisfy the bare prompt token, and the detector has no claude modal overlay inventory at all. Session 2 is the false-ready worst case and the primary justification for a modal-shield-first repair.

Attempt 001 (auto mode, no dialogs): accepting 0.9657 / ready_posture 0.4920 / last_turn 0.9796 (A1), with 63 false-ready (trust modal + picker dwell) — consistent with session 1's structural story.

## Arm A Signal Audit (002, 1104 samples; selected rows)

| Signal | Fired/Expected | False fires | Verdict | Note |
| --- | --- | --- | --- | --- |
| `❯` prompt token | 260/260 | 843 | broken on modals | false-fire set = the modal dwells |
| composer `─` rules | 260/260 | 0 | surviving | |
| approval `Do you want to proceed?` | 14/779 | 0 | **broken** | command dialog only; the edit dialog asks `Do you want to create <name>?` — the family needs the generalized `Do you want to` + option-list shape |
| approval persistent option `Yes, and don't ask again` | 0/779 | 0 | **broken** | command dialog had no persistent row; edit dialog renders `Yes, and always allow access to … (shift+tab)` |
| interrupt full-line regex | 168/168 | 801 | degraded | matches when visible; scrollback persistence false-fires across later spans (needs live-edge scoping) |
| interrupt prefix at live edge | 67/168 | 0 | degraded | the line scrolls above the live edge during the long dwell |
| footer `esc to interrupt` | 76/76 | 0 | surviving | |
| spinner line regex | 3/76 | 0 | **broken** | busy frames render the suffix-less `✻ Cerebrating… ` variant (trailing space, no `(Ns · …)` parenthetical) which the regex cannot match |
| trust dialog needles | 50/51 | 0 | surviving | |
| verb-set completion / `● ` block / queued proxy | n/a (no success span) | 983 / 983 / 302 | scrollback noise | quantifies why dock scoping matters |

## Arm B: Escape Sequences

Zero OSC 133 / OSC `9;4` in 1104 samples (002) and 1864 samples (001). Same verdict as session 1: no state-bearing escape channels.

## Arm C: Transcript Oracle (002)

Transcript inventory: `user` 6, `assistant` 3, `system` 4 (subtypes: `turn_duration` 2, `local_command` 2), `attachment` 10, `permission-mode` 3, `mode` 3, `last-prompt` 3, `file-history-snapshot` 2, `ai-title` 2, `atis-latch` 3, `cost-state` 1.

`turn_duration` events align exactly with the denial seams: 27.404 s (command-leg Esc denial at 27.34 s) and 222.846 s (edit-leg recovery-Esc denial at ~222.8 s). Denials register as completed turns with duration — the oracle distinguishes outcome only via the following user/assistant records, not the duration record itself.

## Cost Note (G7)

Both sessions ran `sonnet` throughout (banner + picker-verified). One corrective re-run (002) and one short probe were the only deviations from the two-session budget; both are recorded in the iteration plan's Corrections. No relay faults occurred; error/retry surfaces remain a declared coverage gap.
